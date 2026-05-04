"""Tool schema generation for LLM function-calling.

Auto-generates parameter schemas from argparse subparser definitions.
Used by both the MCP server and the tool-list command.
"""

from __future__ import annotations

import argparse
from typing import Any

_TYPE_MAP: dict[type[Any] | None, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    None: "string",
}

_COMMAND_DESCRIPTIONS: dict[str, str] = {
    "[": "Evaluate path predicates — alias for 'test'. Read-only. Use to check file existence, type, or permissions in scripts. See also 'test'.",
    "arch": "Return the machine architecture (e.g., x86_64, aarch64). Read-only. Use for platform-conditional operations. See also 'uname' for full system info.",
    "b2sum": "Compute BLAKE2b hash of files as JSON. Read-only. Use for high-speed cryptographic hashing — faster than SHA-2/3 on many platforms. See also 'hash'.",
    "base32": "Encode or decode base32 data from files or stdin. Read-only. Human-friendlier than base64. Returns JSON by default, raw with --raw. See also 'base64', 'basenc'.",
    "base64": "Encode or decode base64 data from files or stdin. Read-only. Use for standard base64 encoding/decoding. Returns JSON by default, raw with --raw. See also 'base32', 'basenc'.",
    "basename": "Return the final path component of file paths, stripping directory prefixes. Read-only. Use to extract filenames. See also 'dirname' for parent directories.",
    "basenc": "Encode or decode base16/base32/base64/base64url data from files or stdin. Read-only. Use --encoding to select format. Returns JSON by default. See also 'base64', 'base32'.",
    "cat": "Read file contents with bounded JSON output by default. Read-only. Use --raw for full plain text. Supports byte-offset and length. See also 'head', 'tail', 'od'.",
    "catalog": "List prioritized GNU Coreutils categories for agents. Read-only. Use to discover available command surface by function. See also 'tool-list'.",
    "chcon": "Plan or apply an SELinux security context to files. Potentially destructive. Use --dry_run to preview. Requires --allow_context to execute. See also 'runcon'.",
    "chgrp": "Change file group ownership with dry-run support. Destructive. Use to change group assignment. See also 'chown', 'chmod'.",
    "chmod": "Change file permissions (octal modes only, e.g., 755). Destructive. Use to set read/write/execute permissions. Use --dry_run to preview. See also 'chown', 'chgrp'.",
    "chown": "Change file ownership with dry-run support. Destructive, typically requires elevated privileges. Use to transfer ownership. See also 'chgrp', 'chmod'.",
    "chroot": "Plan or run a command inside a changed root directory. Potentially destructive, requires elevated privileges. Use --dry_run to preview. Requires --allow_chroot to execute.",
    "cksum": "Return CRC32 checksums for files or stdin. Read-only. Use for fast data-transmission integrity checks. Not for security — prefer 'sha256sum'. Returns checksum and byte count.",
    "comm": "Compare two sorted files and return column-tagged records (lines unique to each and common to both). Read-only. Requires pre-sorted input — use 'sort' first. See also 'join'.",
    "coreutils": "List all available commands or describe individual tools by name. Read-only. Use 'list=true' to enumerate tools. See also 'tool-list' for LLM-optimized output.",
    "cp": "Copy files and directories with dry-run and overwrite protection. Destructive to destination. Overwrite disabled by default. Use --dry_run to preview. See also 'mv', 'install'.",
    "csplit": "Split input into multiple files at regex match points with dry-run and overwrite protection. Destructive (creates files). Use --dry_run to preview. See also 'split'.",
    "cut": "Select specific fields, characters, or bytes from each input line. Read-only. Use to extract columns from tabular data. See also 'paste', 'tr'.",
    "date": "Return current or supplied time as structured JSON. Read-only. Use to query system time or parse date strings. See also 'uptime'.",
    "dd": "Copy and convert input to output with bounded preview and dry-run support. Destructive to output. Use for block-level data copying. Use --dry_run to preview.",
    "df": "Return disk space usage for filesystems as JSON. Read-only. Use to check free space across mounted filesystems. See also 'du' for per-directory usage.",
    "dir": "List directory contents in structured format — alias for 'ls'. Read-only. Use for clean column-aligned output. See also 'ls', 'vdir'.",
    "dircolors": "Return LS_COLORS configuration. Read-only. Color output disabled by default for agent-friendly display. Use to inspect shell color mappings.",
    "dirname": "Return parent directory path components from file paths. Read-only. Use to extract directory portions. See also 'basename' for the inverse.",
    "du": "Estimate file and directory space usage as JSON. Read-only. Use to find space-consuming directories. See also 'df' for filesystem-level overview, 'stat' for single files.",
    "echo": "Echo input text as JSON. Read-only. Use to output text values to stdout. Returns JSON by default, raw with --raw. See also 'printf' for formatted output.",
    "env": "Return environment variables as structured JSON. Read-only. Use to inspect available env vars in the execution context. Supports filtering by name. See also 'printenv'.",
    "expand": "Convert tabs to spaces in files or stdin. Read-only. Use to normalize indentation. Returns JSON by default, raw with --raw. See also 'unexpand' for the reverse.",
    "expr": "Evaluate arithmetic and comparison expressions in a safe AST subset. Read-only. Supports +, -, *, /, %, comparisons, and string ops. See also 'test' for predicates.",
    "factor": "Compute the prime factors of given integers. Read-only. Use to decompose numbers. Returns factor arrays as JSON. See also 'expr' for general arithmetic.",
    "false": "Exit with status 1, indicating failure. Idempotent — always fails, no arguments, no side effects. Use to signal error conditions. See also 'true'.",
    "fmt": "Reflow paragraphs to a fixed character width, preserving paragraph structure. Read-only. Use for text reformatting. Not for hard wrapping — use 'fold'. Returns JSON, raw with --raw.",
    "fold": "Wrap long input lines to a fixed character width. Read-only. Use for display formatting. Not for paragraph reflowing — use 'fmt'. Returns JSON by default, raw with --raw.",
    "ginstall": "Copy files and set attributes — alias for 'install'. Destructive. See also 'install'.",
    "groups": "Return group IDs and names for a user. Read-only. Use to check group membership. See also 'id', 'whoami'.",
    "hash": "Compute hash of files with selectable algorithm as JSON. Read-only. Use when you need flexible algorithm choice via one tool. See also individual hash tools.",
    "head": "Return the first N lines of files as JSON. Read-only. Use to preview file beginnings. See also 'tail', 'cat'.",
    "hostid": "Return a deterministic host identifier in hexadecimal. Read-only. Use for stable machine identification. See also 'hostname'.",
    "hostname": "Return the system hostname as JSON. Read-only. Use to identify the machine in network contexts. See also 'hostid', 'uname'.",
    "id": "Return user ID, group ID, and group membership as JSON. Read-only. Use for comprehensive user identity inspection. See also 'whoami', 'groups'.",
    "install": "Copy files and set attributes (permissions, ownership) with dry-run support. Destructive. Use for software deployment scripts. See also 'cp', 'ginstall'.",
    "join": "Join two sorted files on a common field (default: first whitespace-separated field). Read-only. Performs inner join. Requires sorted input. See also 'paste', 'comm'.",
    "kill": "Plan or send a signal to a process. Potentially destructive. Use --dry_run to preview. Requires --allow_signal to execute. Use to signal or terminate processes.",
    "link": "Create hard links with dry-run and overwrite protection. Destructive. Hard links cannot span filesystems. See also 'ln' for symbolic links.",
    "ln": "Create hard or symbolic links with dry-run and overwrite protection. Destructive. Use --symbolic for symlinks. Overwrite disabled by default. See also 'link', 'cp'.",
    "logname": "Return the current user's login name. Read-only. Use to get the original login identity unaffected by su/sudo. See also 'whoami', 'id'.",
    "ls": "List directory contents as structured JSON. Read-only. Supports recursive depth, streaming, and symlink following. See also 'dir', 'stat'.",
    "md5sum": "Compute MD5 hash of files as JSON. Read-only. Use for non-cryptographic integrity checks. Not for security — use 'sha256sum' or 'b2sum'. Returns per-file hashes.",
    "mkdir": "Create directories with dry-run and parent directory creation support. Destructive. Use to create new directories. Use --dry_run to preview. See also 'rmdir', 'touch'.",
    "mkfifo": "Create named pipes (FIFOs) with dry-run support. Destructive. Use for inter-process communication. Use --dry_run to preview. See also 'mknod'.",
    "mknod": "Create device nodes with dry-run support. Destructive, typically requires elevated privileges. Use --dry_run to preview. See also 'mkfifo'.",
    "mktemp": "Create temporary files or directories safely with unique names. Creates the path atomically to prevent race conditions. Returns the path as JSON. See also 'mkdir'.",
    "mv": "Move or rename files and directories with dry-run and overwrite protection. Destructive. Overwrite disabled by default. Use --dry_run to preview. See also 'cp', 'ln'.",
    "nice": "Run a command with a niceness adjustment. Executes the given command. Use to lower priority of background tasks. See also 'stdbuf'.",
    "nl": "Number input lines with configurable formatting. Read-only. Use to add line numbers to text. Returns JSON by default, raw with --raw. See also 'cat -n'.",
    "nohup": "Run a command immune to hangups (SIGHUP). Use for long-running background tasks. Requires --allow_nohup confirmation. See also 'timeout'.",
    "nproc": "Return the number of available CPU cores. Read-only. Use for parallelism decisions. Returns plain integer with --raw. See also 'uptime', 'arch'.",
    "numfmt": "Convert numbers between plain, SI (K, M, G), and IEC (Ki, Mi, Gi) unit systems. Read-only. Use to humanize raw byte counts or parse human-readable sizes. See also 'printf'.",
    "od": "Dump input bytes as structured rows (hex, octal, decimal). Read-only. Use to inspect raw binary content. Returns JSON by default, raw with --raw. See also 'cat'.",
    "paste": "Merge corresponding lines from multiple files side-by-side with configurable delimiter. Read-only. Use to combine columns into a table. See also 'join', 'cat'.",
    "pathchk": "Validate path name components for portability and correctness. Read-only. Use to verify paths before creation. See also 'realpath'.",
    "pinky": "Print detailed user account information (login name, home, shell). Read-only. Use to inspect specific user profiles. Not for session listing — use 'who' or 'users'. See also 'id', 'whoami'.",
    "pr": "Paginate text into deterministic pages with headers and footers. Read-only. Use for print-formatted output. Returns JSON by default, raw with --raw. See also 'fmt', 'fold'.",
    "printenv": "Return selected environment variables by name. Read-only. Use to query specific variable values. See also 'env' for full listing.",
    "printf": "Format and print text with printf-style conversion specifiers. Read-only. Use for precise string and number formatting. See also 'echo' for simple output.",
    "ptx": "Build a permuted (keyword-in-context) index from input text. Read-only. Use to create searchable cross-references. Returns JSON by default, raw with --raw.",
    "pwd": "Print the current working directory as JSON. Read-only. Use to determine active directory context before file operations. See also 'ls', 'realpath'.",
    "readlink": "Read symbolic link targets or canonicalize paths. Read-only. Use --canonicalize to resolve full paths. See also 'realpath' for always-resolved paths.",
    "realpath": "Resolve file paths to absolute canonical form following all symlinks. Read-only. Use to normalize paths for comparison. See also 'readlink'.",
    "rm": "Remove files and directories with dry-run support. Destructive and irreversible. Use --dry_run to preview. For secure deletion use 'shred'. See also 'rmdir', 'unlink'.",
    "rmdir": "Remove empty directories with dry-run support. Destructive. Fails on non-empty directories — use 'rm' for those. Use --dry_run to preview. See also 'rm'.",
    "runcon": "Plan or run a command under an SELinux security context. Use --dry_run to preview. Requires --allow_context to execute. See also 'chcon'.",
    "schema": "Print the aicoreutils JSON protocol and exit code conventions. Read-only. Use before invoking other tools to understand the response envelope.",
    "seq": "Print a sequence of numbers as JSON. Read-only. Accepts [FIRST [INCREMENT]] LAST via the 'number' parameter. See also 'yes' for string repetition, 'printf' for formatted output.",
    "sha1sum": "Compute SHA-1 hash of files as JSON. Read-only. Use for basic integrity verification. Not recommended for new security uses — prefer 'sha256sum'. Returns per-file hashes.",
    "sha224sum": "Compute SHA-224 hash of files as JSON. Read-only. Use for cryptographic integrity verification. See also 'hash' for multi-algorithm support.",
    "sha256sum": "Compute SHA-256 hash of files as JSON. Read-only. Use for cryptographic integrity verification — standard choice. See also 'hash' for multi-algorithm support.",
    "sha384sum": "Compute SHA-384 hash of files as JSON. Read-only. Use for higher security margin than SHA-256. See also 'hash' for multi-algorithm support.",
    "sha512sum": "Compute SHA-512 hash of files as JSON. Read-only. Use for the highest security margin hashing. See also 'hash' for multi-algorithm support.",
    "shred": "Overwrite file contents with random data then remove, with explicit confirmation. Destructive and irreversible — data unrecoverable. Requires --allow_destructive. See also 'rm'.",
    "shuf": "Shuffle input lines randomly, with optional deterministic seed. Read-only. Set seed for reproducible ordering. See also 'sort', 'uniq'.",
    "sleep": "Pause execution for a specified number of seconds, bounded by max_seconds for safety. Blocks. Use to introduce delays. Use --dry_run to preview duration. See also 'timeout'.",
    "sort": "Sort text lines from files or stdin deterministically. Read-only. Use --numeric for number sort, --reverse for descending. See also 'uniq', 'shuf'.",
    "split": "Split input into chunked files by line count or size with dry-run and overwrite protection. Destructive. Default: 1000 lines per chunk. Use --dry_run to preview. See also 'csplit'.",
    "stat": "Return file metadata (size, permissions, timestamps, owner) as structured JSON. Read-only. Use to inspect file attributes without reading contents. See also 'ls'.",
    "stdbuf": "Run a command with controlled stdout/stderr buffering modes (0=none, L=line, or byte size). Use to debug buffering issues. See also 'timeout'.",
    "stty": "Inspect or modify terminal settings. Can change terminal behavior if --allow_change is enabled. Use to query terminal configuration. See also 'tty' for simple TTY check.",
    "sum": "Return simple 16-bit byte sums for files or stdin. Read-only. Use for legacy BSD-style checks. Not for integrity — prefer 'cksum' or 'sha256sum'. Returns sum and block count.",
    "sync": "Flush cached writes to disk where supported. Read-only but may affect I/O performance. Use to ensure data persistence before critical operations.",
    "tac": "Reverse input lines from files or stdin. Read-only. Use to invert line order. Returns JSON by default, raw with --raw. See also 'sort -r'.",
    "tail": "Return the last N lines of files as JSON. Read-only. Use to preview file endings or check recent log entries. See also 'head', 'cat'.",
    "tee": "Read stdin and write to files and stdout simultaneously with dry-run support. Destructive (writes files). Supports append mode. See also 'cat', 'echo'.",
    "test": "Evaluate path predicates (file, is_dir, is_executable) returning structured JSON. Read-only. Use to check file existence, type, or permissions in scripts. See also 'stat'.",
    "timeout": "Run a command with a bounded time limit, capturing output as JSON. May terminate child processes on timeout. Use to prevent runaway commands. See also 'sleep'.",
    "tool-list": "Return a compact tool index for LLM function-calling context. Read-only. Supports --format=openai for OpenAI-compatible output. See also 'coreutils'.",
    "touch": "Update file timestamps or create empty files. Modifies timestamps, creates files if absent. See also 'mkdir', 'truncate'.",
    "tr": "Translate or delete literal characters from files or stdin. Read-only. Does NOT support regex. Returns JSON by default, raw with --raw. See also 'sed' for regex substitution.",
    "true": "Exit with status 0, indicating success. Idempotent — always succeeds, no arguments, no side effects. Use to signal successful completion. See also 'false'.",
    "truncate": "Shrink or extend file sizes with dry-run and overwrite protection. Destructive. Extending fills with null bytes. Use --dry_run to preview. See also 'touch', 'dd'.",
    "tsort": "Topologically sort whitespace-separated dependency pairs. Read-only. Use for dependency resolution — detects cycles and reports errors. See also 'sort'.",
    "tty": "Check if stdin is a terminal and report the terminal device name. Read-only. Use to detect interactive contexts. Returns non-zero exit code if not a TTY.",
    "uname": "Return system information (kernel, hostname, release, machine) as JSON. Read-only. Use for cross-platform system identification. See also 'arch', 'hostname'.",
    "unexpand": "Convert spaces to tabs in files or stdin. Read-only. Use to compress leading spaces. Returns JSON by default, raw with --raw. See also 'expand' for the reverse.",
    "uniq": "Collapse adjacent duplicate lines. Read-only. Does NOT sort — pipe through 'sort' first for full deduplication. Returns JSON by default, raw with --raw. See also 'sort'.",
    "unlink": "Remove a single file with dry-run support. Destructive and irreversible. Fails on directories. Use --dry_run to preview. See also 'rm', 'rmdir'.",
    "uptime": "Return system uptime in seconds. Read-only. Use to check how long the system has been running. Returns plain seconds with --raw. See also 'date'.",
    "users": "List currently logged-in users. Read-only. Use for quick session check. Not for detailed info — use 'who' for session details. See also 'who', 'pinky'.",
    "vdir": "List directory contents with verbose output — alias for 'ls'. Read-only. Use for extended file metadata. See also 'ls', 'dir'.",
    "wc": "Count bytes, characters, lines, and words in files, returning results as JSON. Read-only. Returns per-file counts plus totals. See also 'stat', 'du'.",
    "who": "Return logged-in user sessions with terminal, login time, and remote host. Read-only. Use to see active sessions. See also 'users', 'pinky'.",
    "whoami": "Return current user identity (username, UID, GID) as JSON. Read-only. Use to determine the effective process user. See also 'id', 'logname'.",
    "yes": "Repeatedly print a given string (default 'y') to stdout, bounded by count. Read-only. Use to auto-answer scripting prompts. See also 'seq', 'printf'.",
}


def _arg_to_schema(action: argparse.Action) -> dict[str, Any]:
    """Convert an argparse action to a JSON Schema property."""
    schema: dict[str, Any] = {"description": action.help or ""}
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


def _command_tools(parser: argparse.ArgumentParser) -> list[dict[str, Any]]:
    """Generate MCP-compatible tool list from all registered subcommands."""
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

        for action in subparser._actions:
            dest = action.dest
            if dest in ("help", "pretty", "command") or dest == argparse.SUPPRESS:
                continue
            prop_schema = _arg_to_schema(action)
            if action.option_strings is None or len(action.option_strings) == 0:
                if action.nargs in ("*", "+", "?"):
                    prop_schema["type"] = "array"
                    prop_schema["items"] = {"type": "string"}
                if action.required:
                    required.append(dest)
                properties[dest] = prop_schema
            else:
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


def tools_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool schemas to OpenAI function-calling format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"],
                },
            }
        )
    return result


def tools_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool schemas to Anthropic tool-use format."""
    result: list[dict[str, Any]] = []
    for tool in tools:
        result.append(
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["inputSchema"],
            }
        )
    return result
