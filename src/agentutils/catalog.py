"""Priority catalog for GNU Coreutils commands in agent workflows.

This is the single authority for command priority classification.
All registry/priority functions are derived from CATALOG below.
"""

from __future__ import annotations

from typing import TypedDict


class CatalogEntry(TypedDict):
    priority: str
    urgency: str
    category: str
    why: str
    tools: list[str]


CATALOG: list[CatalogEntry] = [
    {
        "priority": "P0",
        "urgency": "critical",
        "category": "read_observe_and_decide",
        "why": "Agents need deterministic filesystem observation before taking action.",
        "tools": [
            "ls",
            "stat",
            "cat",
            "head",
            "tail",
            "wc",
            "pwd",
            "basename",
            "dirname",
            "realpath",
            "readlink",
            "test",
            "sha256sum",
            "md5sum",
        ],
    },
    {
        "priority": "P1",
        "urgency": "high",
        "category": "mutate_files_safely",
        "why": "These commands change state and need dry-run, explicit overwrite, and structured errors.",
        "tools": [
            "cp",
            "mv",
            "rm",
            "mkdir",
            "touch",
            "ln",
            "link",
            "chmod",
            "chown",
            "chgrp",
            "truncate",
            "mktemp",
            "mkfifo",
            "mknod",
            "tee",
            "rmdir",
            "unlink",
            "install",
            "ginstall",
        ],
    },
    {
        "priority": "P2",
        "urgency": "medium",
        "category": "transform_and_compose_text",
        "why": "These commands are useful in pipelines and should preserve stdin/stdout composability.",
        "tools": [
            "sort",
            "uniq",
            "cut",
            "tr",
            "comm",
            "join",
            "paste",
            "split",
            "csplit",
            "fmt",
            "fold",
            "nl",
            "od",
            "seq",
            "numfmt",
            "shuf",
            "tac",
            "pr",
            "ptx",
            "expand",
            "unexpand",
            "tsort",
            "base64",
            "base32",
            "basenc",
            "cksum",
            "sum",
            "b2sum",
            "sha1sum",
            "sha224sum",
            "sha384sum",
            "sha512sum",
            "hash",
        ],
    },
    {
        "priority": "P3",
        "urgency": "normal",
        "category": "system_context_and_execution",
        "why": "Useful, but often environment-specific, long-running, privileged, or less central to file work.",
        "tools": [
            "date",
            "coreutils",
            "df",
            "du",
            "env",
            "id",
            "groups",
            "whoami",
            "uname",
            "arch",
            "nproc",
            "timeout",
            "sleep",
            "tty",
            "true",
            "false",
            "yes",
            "printf",
            "echo",
            "printenv",
            "sync",
            "dd",
            "shred",
            "chroot",
            "nice",
            "nohup",
            "stdbuf",
            "stty",
            "kill",
            "who",
            "users",
            "uptime",
            "hostid",
            "hostname",
            "logname",
            "pinky",
            "dircolors",
            "dir",
            "vdir",
            "[",
            "expr",
            "factor",
            "pathchk",
            "mknod",
            "chcon",
            "runcon",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
#  Priority derivation (single authority: CATALOG above)
# ═══════════════════════════════════════════════════════════════════════

_COMMAND_PRIORITY_MAP: dict[str, str] = {}
for _entry in CATALOG:
    for _tool in _entry["tools"]:
        _COMMAND_PRIORITY_MAP[_tool] = _entry["priority"]


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


def priority_catalog() -> dict[str, object]:
    return {
        "source": "GNU Coreutils 9.10",
        "principles": [
            "json_by_default",
            "no_color_or_progress_noise",
            "stderr_for_errors",
            "semantic_exit_codes",
            "dry_run_for_mutation",
            "stdin_stdout_composable",
            "bounded_outputs",
            "self_describing_help_and_schema",
        ],
        "categories": CATALOG,
        "implemented": implemented_catalog(),
    }
