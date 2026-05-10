"""MCP (Model Context Protocol) server for aicoreutils.

Implements JSON-RPC 2.0 over stdio without external dependencies.
Exposes all 114 aicoreutils commands as MCP tools for AI agents.

Security modes:
    --profile NAME     Apply a built-in security profile (readonly, workspace-write, explicit-danger)
    --read-only        Allow only read-only tools (no file writes/deletes)
    --allow-command X  Only allow specific commands (repeatable)
    --deny-command X   Block specific commands (repeatable)

Usage:
    python -m aicoreutils.mcp_server --profile readonly
    python -m aicoreutils.mcp_server --profile workspace-write
    python -m aicoreutils.mcp_server --read-only
    python -m aicoreutils.mcp_server --allow-command ls --allow-command cat
    python -m aicoreutils.mcp_server --deny-command rm --deny-command shred
    # or: aicoreutils-mcp --read-only
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, cast

from . import __version__
from .core.encoding import decode_bytes
from .parser._parser import build_parser
from .registry.tool_schema import _EXPLICIT_ALLOW_TOOLS, _READ_ONLY_TOOLS, _WORKSPACE_WRITE_TOOLS, _command_tools

_PROFILE_CHOICES = ("readonly", "workspace-write", "explicit-danger")


class MCPSecurityPolicy:
    """Immutable security policy for MCP tool access control.

    Merges profile-based allow/deny lists with explicit command-level
    overrides and provides a single check_access() entry point.
    """

    def __init__(
        self,
        *,
        profile: str | None = None,
        read_only: bool = False,
        allow_commands: set[str] | None = None,
        deny_commands: set[str] | None = None,
    ) -> None:
        # Resolve profile-based allow list
        profile_allow: set[str] | None = None
        if profile is not None:
            if profile == "readonly":
                profile_allow = set(_READ_ONLY_TOOLS)
            elif profile == "workspace-write":
                profile_allow = set(_READ_ONLY_TOOLS) | set(_WORKSPACE_WRITE_TOOLS)
            elif profile == "explicit-danger":
                profile_allow = None
            else:
                raise ValueError(f"Unknown MCP security profile: {profile}")

        # Resolve profile-based deny list
        profile_deny = set(_EXPLICIT_ALLOW_TOOLS) if profile == "workspace-write" else set()

        # Merge explicit overrides
        merged_allow = set(profile_allow) if profile_allow is not None else None
        if allow_commands:
            merged_allow = set(allow_commands) if merged_allow is None else merged_allow | allow_commands

        merged_deny = profile_deny | (deny_commands or set())

        self._allow: frozenset[str] | None = frozenset(merged_allow) if merged_allow is not None else None
        self._deny: frozenset[str] = frozenset(merged_deny)
        self._read_only: bool = read_only or profile == "readonly"

    def check_access(self, name: str) -> dict[str, Any] | None:
        """Return None if access is granted, or an error dict if denied."""
        if name in self._deny:
            return {
                "ok": False,
                "error": {"code": "SECURITY_DENIED", "command": name, "reason": "Command is in the deny list."},
            }
        if self._allow is not None:
            if name in self._allow:
                return None
            return {
                "ok": False,
                "error": {"code": "SECURITY_DENIED", "command": name, "reason": "Command is not in the allow list."},
            }
        if self._read_only and name not in _READ_ONLY_TOOLS:
            return {
                "ok": False,
                "error": {
                    "code": "SECURITY_DENIED",
                    "command": name,
                    "reason": "Read-only mode is active; this command may modify files or state.",
                },
            }
        return None


# ── Legacy compatibility wrappers (kept for test imports) ────────────


def _merge_security_policy(
    *,
    profile: str | None = None,
    read_only: bool = False,
    allow_commands: set[str] | None = None,
    deny_commands: set[str] | None = None,
) -> tuple[bool, set[str] | None, set[str] | None]:
    """Legacy wrapper — prefer MCPSecurityPolicy directly."""
    policy = MCPSecurityPolicy(
        profile=profile, read_only=read_only, allow_commands=allow_commands, deny_commands=deny_commands
    )
    return policy._read_only, set(policy._allow) if policy._allow is not None else None, set(policy._deny) or None


def _check_tool_access(
    name: str,
    *,
    read_only: bool = False,
    allow_commands: set[str] | None = None,
    deny_commands: set[str] | None = None,
) -> dict[str, Any] | None:
    """Legacy wrapper — prefer MCPSecurityPolicy.check_access() directly."""
    policy = MCPSecurityPolicy(read_only=read_only, allow_commands=allow_commands, deny_commands=deny_commands)
    return policy.check_access(name)


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an aicoreutils command by name with the given arguments.

    Security checks (read-only, allow/deny) are performed by the caller
    before this function is invoked.
    """
    parser = build_parser()

    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    if subparsers_action is None or name not in subparsers_action.choices:
        return {"ok": False, "error": f"Unknown command: {name}"}

    subparser = subparsers_action.choices[name]
    func = subparser.get_default("func")
    if func is None:
        return {"ok": False, "error": f"No handler for command: {name}"}

    # Build CLI args from JSON arguments dict
    args_list: list[str] = []

    # Collect all non-hidden actions
    for action in subparser._actions:
        dest = action.dest
        if dest in ("help", "pretty", "command"):
            continue
        if dest == argparse.SUPPRESS:
            continue

        value = arguments.get(dest)
        if value is None:
            continue

        if action.option_strings and len(action.option_strings) > 0:
            # Optional argument
            flag = action.option_strings[0]
            if isinstance(value, bool):
                if value:
                    args_list.append(flag)
            elif isinstance(value, list):
                for item in value:
                    args_list.append(flag)
                    args_list.append(str(item))
            else:
                args_list.append(flag)
                args_list.append(str(value))
        else:
            # Positional argument
            if isinstance(value, list):
                args_list.extend(str(v) for v in value)
            else:
                args_list.append(str(value))

    # Parse through argparse
    try:
        ns = parser.parse_args([name] + args_list)
    except SystemExit:
        return {"ok": False, "error": f"Argument parsing failed: {json.dumps(args_list)}"}

    # Execute
    from .parser._parser import dispatch  # noqa: E402

    try:
        raw_result = dispatch(ns)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    # dispatch returns (exit_code, result_dict)
    if isinstance(raw_result, tuple):
        exit_code, result = raw_result
    else:
        exit_code = 0
        result = raw_result

    if isinstance(result, bytes):
        decoded = decode_bytes(result, encoding="utf-8", errors="replace")
        result = {"raw_output": decoded.text}
    elif isinstance(result, dict):
        result["_exit_code"] = exit_code
    return result


# ── MCP JSON-RPC Server ──


def _send(response: dict[str, Any]) -> None:
    """Write a JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()


def _read_request() -> dict[str, Any] | None:
    """Read a JSON-RPC request from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return cast(dict[str, Any], json.loads(line))
    except json.JSONDecodeError:
        return None


def server_loop(
    *,
    profile: str | None = None,
    read_only: bool = False,
    allow_commands: set[str] | None = None,
    deny_commands: set[str] | None = None,
) -> None:
    """Run the MCP JSON-RPC server loop on stdio with optional security controls."""
    policy = MCPSecurityPolicy(
        profile=profile,
        read_only=read_only,
        allow_commands=allow_commands,
        deny_commands=deny_commands,
    )

    while True:
        request = _read_request()
        if request is None:
            break

        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "aicoreutils", "version": __version__},
                        "capabilities": {"tools": {}},
                    },
                }
            )

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            parser = build_parser()
            tools = _command_tools(parser)
            _send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})

            # Security gate — check before execution
            access_denied = policy.check_access(tool_name)
            if access_denied is not None:
                content = json.dumps(access_denied, ensure_ascii=False, sort_keys=True)
                _send(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": content}],
                            "isError": True,
                        },
                    }
                )
                continue

            result = _call_tool(tool_name, tool_args)
            content = json.dumps(result, ensure_ascii=False, sort_keys=True)
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": content}],
                    },
                }
            )

        else:
            _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}})


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the MCP server."""
    parser = argparse.ArgumentParser(
        prog="aicoreutils-mcp",
        description="AICoreUtils MCP server — exposes CLI commands as MCP tools.",
    )
    parser.add_argument("--read-only", action="store_true", help="Only allow read-only tools.")
    parser.add_argument(
        "--profile",
        choices=_PROFILE_CHOICES,
        default=None,
        help="Apply a built-in security profile: readonly, workspace-write, or explicit-danger.",
    )
    parser.add_argument(
        "--allow-command", action="append", default=None, metavar="CMD", help="Only allow this command (repeatable)."
    )
    parser.add_argument(
        "--deny-command", action="append", default=None, metavar="CMD", help="Block this command (repeatable)."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for aicoreutils-mcp.

    When called programmatically, pass argv=None to avoid SystemExit from
    test runner arguments appearing in sys.argv.
    """
    args = _parse_args(argv if argv is not None else [])

    allow_commands = set(args.allow_command) if args.allow_command else None
    deny_commands = set(args.deny_command) if args.deny_command else None

    try:
        server_loop(
            profile=args.profile,
            read_only=args.read_only,
            allow_commands=allow_commands,
            deny_commands=deny_commands,
        )
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
