"""MCP (Model Context Protocol) server for aicoreutils.

Implements JSON-RPC 2.0 over stdio without external dependencies.
Exposes all 114 aicoreutils commands as MCP tools for AI agents.

Usage:
    python -m aicoreutils.mcp_server
    # or: aicoreutils-mcp
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, cast

from . import __version__
from .parser._parser import build_parser
from .tool_schema import _command_tools


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute an aicoreutils command by name with the given arguments."""
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
    from .parser._parser import dispatch

    try:
        raw_result = dispatch(ns)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    # dispatch returns (exit_code, result_dict)
    if isinstance(raw_result, tuple):
        exit_code, result = raw_result
    else:
        result = raw_result

    if isinstance(result, bytes):
        result = {"raw_output": result.decode("utf-8", errors="replace")}
    elif isinstance(result, dict):
        result["_exit_code"] = exit_code if isinstance(raw_result, tuple) else 0
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


def server_loop() -> None:
    """Run the MCP JSON-RPC server loop on stdio."""
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


def main() -> None:
    """Entry point for aicoreutils-mcp."""
    try:
        server_loop()
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        pass


if __name__ == "__main__":
    main()
