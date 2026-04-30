"""Unified command registry with auto-discovery from the parser.

Provides ALL_COMMANDS, COMMAND_TO_PRIORITY, and helper functions
derived from the parser's registered subcommands.
"""

from __future__ import annotations

# Static priority classification derived from CATALOG in catalog.py.
# Priority order: P0, P1, P2, P3 — everything else is unknown.
_COMMAND_PRIORITY_MAP: dict[str, str] = {
    # P0 – read / observe / decide
    "ls": "P0", "stat": "P0", "cat": "P0", "head": "P0", "tail": "P0",
    "wc": "P0", "pwd": "P0", "basename": "P0", "dirname": "P0",
    "realpath": "P0", "readlink": "P0", "test": "P0",
    "sha256sum": "P0", "md5sum": "P0",
    # P1 – mutate files safely
    "cp": "P1", "mv": "P1", "rm": "P1", "mkdir": "P1", "touch": "P1",
    "ln": "P1", "link": "P1", "chmod": "P1", "chown": "P1",
    "chgrp": "P1", "truncate": "P1", "mktemp": "P1", "mkfifo": "P1",
    "mknod": "P1", "install": "P1", "ginstall": "P1", "tee": "P1",
    "rmdir": "P1", "unlink": "P1", "shred": "P1",
    # P2 – transform / compose text
    "sort": "P2", "comm": "P2", "join": "P2", "paste": "P2",
    "shuf": "P2", "tac": "P2", "nl": "P2", "fold": "P2", "fmt": "P2",
    "csplit": "P2", "split": "P2", "od": "P2", "pr": "P2", "ptx": "P2",
    "numfmt": "P2", "uniq": "P2", "cut": "P2", "tr": "P2",
    "expand": "P2", "unexpand": "P2", "tsort": "P2",
    "base64": "P2", "base32": "P2", "basenc": "P2", "seq": "P2",
    "cksum": "P2", "sum": "P2", "b2sum": "P2",
    "sha1sum": "P2", "sha224sum": "P2", "sha384sum": "P2", "sha512sum": "P2",
    # P3 – system context / execution
    "date": "P3", "env": "P3", "printenv": "P3", "whoami": "P3",
    "groups": "P3", "id": "P3", "uname": "P3", "arch": "P3",
    "hostname": "P3", "hostid": "P3", "logname": "P3", "uptime": "P3",
    "tty": "P3", "users": "P3", "who": "P3", "nproc": "P3",
    "df": "P3", "du": "P3", "dd": "P3", "sync": "P3",
    "dircolors": "P3", "timeout": "P3", "nice": "P3", "nohup": "P3",
    "kill": "P3", "dir": "P3", "vdir": "P3", "[": "P3",
    "printf": "P3", "echo": "P3", "pathchk": "P3", "factor": "P3",
    "expr": "P3", "true": "P3", "false": "P3", "sleep": "P3", "yes": "P3",
}


def get_priority(command_name: str) -> str:
    """Return the priority level for a command name, or 'unknown'."""
    return _COMMAND_PRIORITY_MAP.get(command_name, "unknown")


def get_all_commands() -> set[str]:
    """Return the set of all known command names."""
    return set(_COMMAND_PRIORITY_MAP)


def get_commands_by_priority() -> dict[str, list[str]]:
    """Return commands grouped by priority (P0, P1, P2, P3)."""
    grouped: dict[str, list[str]] = {}
    for cmd, pri in _COMMAND_PRIORITY_MAP.items():
        grouped.setdefault(pri, []).append(cmd)
    for pri in grouped:
        grouped[pri].sort()
    return grouped


def implemented_catalog() -> dict[str, list[str]]:
    """Return IMPLEMENTED dict compatible with priority_catalog()."""
    return get_commands_by_priority()
