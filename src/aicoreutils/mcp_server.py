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

from .parser._parser import build_parser

# ── JSON Schema type mapping ──

_TYPE_MAP: dict[type[Any] | None, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    None: "string",
}

# ── Tool description overrides (clear help text for MCP consumers) ──

_COMMAND_DESCRIPTIONS: dict[str, str] = {
    "catalog": "List prioritized GNU Coreutils categories for agents.",
    "schema": "Print the aicoreutils JSON protocol and exit codes.",
    "coreutils": "Describe or list the aicoreutils coreutils-inspired command surface.",
    "tool-list": "Return a compact tool list for LLM function-calling context.",
    "pwd": "Print the current working directory as JSON.",
    "basename": "Return final path components of file paths.",
    "dirname": "Return parent directory path components.",
    "realpath": "Resolve file paths to absolute canonical form deterministically.",
    "readlink": "Read symbolic link targets or canonicalize paths.",
    "test": "Evaluate path predicates and return structured JSON results.",
    "[": "Evaluate a small subset of test/[ expression predicates.",
    "ls": "List directory contents as structured JSON.",
    "dir": "Alias for ls — structured directory listing.",
    "vdir": "Alias for ls — verbose directory listing.",
    "stat": "Return file metadata as structured JSON.",
    "cat": "Read file contents with bounded JSON output by default.",
    "head": "Return the first N lines of files as JSON.",
    "tail": "Return the last N lines of files as JSON.",
    "wc": "Count bytes, chars, lines, and words in files as JSON.",
    "md5sum": "Compute MD5 hash of files as JSON.",
    "sha1sum": "Compute SHA-1 hash of files as JSON.",
    "sha224sum": "Compute SHA-224 hash of files as JSON.",
    "sha256sum": "Compute SHA-256 hash of files as JSON.",
    "sha384sum": "Compute SHA-384 hash of files as JSON.",
    "sha512sum": "Compute SHA-512 hash of files as JSON.",
    "b2sum": "Compute BLAKE2b hash of files as JSON.",
    "hash": "Compute hash of files with selectable algorithm as JSON.",
    "cksum": "Return CRC32 checksums for files or stdin.",
    "sum": "Return simple 16-bit byte sums for files or stdin.",
    "sort": "Sort text lines from files or stdin deterministically.",
    "comm": "Compare two sorted files and return column-tagged records.",
    "join": "Join two files on a selected field.",
    "paste": "Merge corresponding lines from multiple files.",
    "shuf": "Shuffle input lines with optional deterministic seed.",
    "tac": "Reverse input lines from files or stdin.",
    "nl": "Number input lines with a deterministic subset of GNU nl.",
    "fold": "Wrap long input lines to a fixed character width.",
    "fmt": "Reflow paragraphs to a fixed character width.",
    "csplit": "Split input at regex matches with dry-run and overwrite protection.",
    "split": "Split input into chunked files with dry-run and overwrite protection.",
    "od": "Dump input bytes as structured rows.",
    "numfmt": "Convert numbers between plain, SI, and IEC unit systems.",
    "tsort": "Topologically sort whitespace-separated dependency pairs.",
    "pr": "Paginate text into deterministic pages.",
    "ptx": "Build a simple permuted index from input text.",
    "uniq": "Collapse adjacent duplicate lines from files or stdin.",
    "cut": "Select fields, characters, or bytes from each input line.",
    "tr": "Translate or delete literal characters from files or stdin.",
    "expand": "Convert tabs to spaces in files or stdin.",
    "unexpand": "Convert spaces to tabs in files or stdin.",
    "base64": "Encode or decode base64 data.",
    "base32": "Encode or decode base32 data.",
    "basenc": "Encode or decode base16/base32/base64/base64url data.",
    "date": "Return current or supplied time as structured JSON.",
    "env": "Return environment variables as structured JSON.",
    "printenv": "Return selected environment variables.",
    "whoami": "Return the current user identity as JSON.",
    "groups": "Return group IDs and names where the platform exposes them.",
    "id": "Return user ID and group membership as JSON.",
    "uname": "Return system information (kernel, hostname, etc.) as JSON.",
    "arch": "Return the machine architecture.",
    "hostname": "Return the system hostname.",
    "hostid": "Return a deterministic host identifier.",
    "logname": "Return the current login name.",
    "uptime": "Return system uptime in seconds.",
    "tty": "Check if stdin is a TTY and report terminal name.",
    "users": "List currently logged-in users.",
    "pinky": "Return detailed user records.",
    "who": "Return logged-in user sessions.",
    "nproc": "Return the number of available CPU cores.",
    "df": "Return disk space usage for filesystems as JSON.",
    "du": "Estimate file space usage as JSON.",
    "dd": "Copy and convert input to output with bounded preview and dry-run support.",
    "sync": "Flush cached writes to disk where supported.",
    "dircolors": "Return color configuration (disabled for agent-friendly output).",
    "seq": "Print a sequence of numbers as JSON.",
    "printf": "Format and print text with printf-style conversions.",
    "echo": "Echo input text as JSON.",
    "pathchk": "Validate path name components.",
    "factor": "Compute prime factors of integers.",
    "expr": "Evaluate arithmetic and comparison expressions in a safe AST subset.",
    "true": "Succeed with an ok envelope (exit 0).",
    "false": "Succeed with a false predicate envelope (exit 1).",
    "sleep": "Pause for a specified number of seconds.",
    "timeout": "Run a command with a bounded timeout and captured output.",
    "stdbuf": "Run a command with controlled stdout/stderr buffering.",
    "chroot": "Plan or run a command inside a changed root with explicit confirmation.",
    "stty": "Inspect terminal settings deterministically.",
    "nice": "Run a command with a niceness adjustment where supported.",
    "kill": "Plan or send a signal to a process with explicit confirmation.",
    "nohup": "Run a command immune to hangups with explicit confirmation.",
    "chcon": "Plan or apply an SELinux security context with explicit confirmation.",
    "runcon": "Plan or run a command under an SELinux context with explicit confirmation.",
    "yes": "Repeatedly output a string with bounded output.",
    "mkdir": "Create directories with dry-run and parent creation support.",
    "touch": "Update file timestamps or create empty files.",
    "cp": "Copy files and directories with dry-run and overwrite protection.",
    "mv": "Move/rename files and directories with dry-run and overwrite protection.",
    "ln": "Create hard or symbolic links with dry-run and overwrite protection.",
    "link": "Create hard links with dry-run and overwrite protection.",
    "chmod": "Change file permissions (octal modes only).",
    "chown": "Change file ownership with dry-run support.",
    "chgrp": "Change file group ownership with dry-run support.",
    "truncate": "Shrink or extend file sizes with dry-run and overwrite protection.",
    "mktemp": "Create temporary files or directories safely.",
    "mkfifo": "Create named pipes with dry-run support.",
    "mknod": "Create device nodes with dry-run support.",
    "install": "Copy files and set attributes with dry-run support.",
    "ginstall": "Alias for install — copy files and set attributes.",
    "tee": "Read stdin and write to files and stdout with dry-run support.",
    "rmdir": "Remove empty directories with dry-run support.",
    "unlink": "Remove single files with dry-run support.",
    "rm": "Remove files and directories with dry-run support.",
    "shred": "Overwrite and remove files with explicit confirmation.",
}


def _arg_to_schema(action: argparse.Action) -> dict[str, Any]:
    """Convert an argparse action to a JSON Schema property."""
    schema: dict[str, Any] = {
        "description": action.help or "",
    }

    if action.choices is not None:
        schema["type"] = "string"
        schema["enum"] = list(action.choices)
    elif action.type in _TYPE_MAP:
        schema["type"] = _TYPE_MAP[action.type]
    else:
        schema["type"] = "string"

    if action.default is not None and action.default is not argparse.SUPPRESS:
        schema["default"] = action.default

    return schema


def _command_tools() -> list[dict[str, Any]]:
    """Generate MCP tool list from all registered argparse subcommands."""
    parser = build_parser()
    subparsers_action = None
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subparsers_action = action
            break

    if subparsers_action is None:
        return []

    tools: list[dict[str, Any]] = []
    for name, subparser in sorted(subparsers_action.choices.items()):
        properties: dict[str, Any] = {}
        required: list[str] = []

        # Separate positionals from optionals
        for action in subparser._actions:
            dest = action.dest
            if dest in ("help",):
                continue
            if dest == argparse.SUPPRESS:
                continue
            # Skip container positional added by add_subparsers
            if action.default is not None and dest == "command":
                continue

            prop_schema = _arg_to_schema(action)

            if action.option_strings is None or len(action.option_strings) == 0:
                # Positional argument
                if action.nargs in ("*", "+", "?"):
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"type": "string"}
                if action.required:
                    required.append(dest)
                properties[dest] = prop_schema
            else:
                # Optional argument
                if action.nargs == 0 and action.const is not None:
                    prop_schema["type"] = "boolean"
                properties[dest] = prop_schema

        description = _COMMAND_DESCRIPTIONS.get(name, subparser.description or "")

        tools.append(
            {
                "name": name,
                "description": description,
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )

    return tools


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
                        "serverInfo": {"name": "aicoreutils", "version": "0.3.1"},
                        "capabilities": {"tools": {}},
                    },
                }
            )

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            tools = _command_tools()
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
