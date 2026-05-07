#!/usr/bin/env python3
"""Audit command risk classification and expected test coverage lanes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aicoreutils.parser._parser import build_parser  # noqa: E402
from aicoreutils.registry.tool_schema import (  # noqa: E402
    _DESTRUCTIVE_TOOLS,
    _READ_ONLY_TOOLS,
    _WORKSPACE_WRITE_TOOLS,
    tool_risk_categories,
    tool_risk_level,
)

TEST_LANES: dict[str, list[str]] = {
    "read-only": [
        "tests/test_cli_black_box.py",
        "tests/test_golden_outputs.py",
        "tests/test_property_based_cli.py",
    ],
    "write": [
        "tests/test_sandbox_and_side_effects.py",
        "tests/test_sandbox_escape_hardening.py",
        "tests/test_file_admin_commands.py",
    ],
    "destructive": [
        "tests/test_sandbox_escape_hardening.py",
        "tests/test_error_exit_codes.py",
    ],
    "process-exec": [
        "tests/test_execution_and_page_commands.py",
        "tests/test_remaining_coreutils_commands.py",
        "tests/test_mcp_security.py",
    ],
    "platform-sensitive": [
        "tests/test_remaining_coreutils_commands.py",
        "tests/test_system_alias_and_encoding_commands.py",
        "tests/test_gnu_differential.py",
    ],
}


def parser_commands() -> list[str]:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return sorted(name for name in action.choices if not name.startswith("_"))
    return []


def command_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command in parser_commands():
        categories = tool_risk_categories(command)
        lanes: list[str] = []
        for category in categories:
            for lane in TEST_LANES.get(category, []):
                if lane not in lanes:
                    lanes.append(lane)
        rows.append(
            {
                "command": command,
                "risk_level": tool_risk_level(command),
                "risk_categories": categories,
                "test_lanes": lanes,
                "workspace_write_profile": command in _WORKSPACE_WRITE_TOOLS,
            }
        )
    return rows


def audit() -> list[str]:
    commands = set(parser_commands())
    issues: list[str] = []

    overlap = _READ_ONLY_TOOLS & _DESTRUCTIVE_TOOLS
    if overlap:
        issues.append(f"read-only/destructive overlap: {sorted(overlap)}")

    classified = _READ_ONLY_TOOLS | _DESTRUCTIVE_TOOLS
    missing = commands - classified
    if missing:
        issues.append(f"unclassified parser commands: {sorted(missing)}")

    unknown = [row["command"] for row in command_rows() if row["risk_level"] == "unknown"]
    if unknown:
        issues.append(f"commands with unknown risk level: {unknown}")

    missing_lanes = [row["command"] for row in command_rows() if not row["test_lanes"]]
    if missing_lanes:
        issues.append(f"commands without test lanes: {missing_lanes}")

    missing_files = sorted({lane for lanes in TEST_LANES.values() for lane in lanes if not (ROOT / lane).exists()})
    if missing_files:
        issues.append(f"declared test lane files do not exist: {missing_files}")

    return issues


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Command | Risk Level | Risk Categories | Test Lanes |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| `{command}` | `{risk_level}` | {categories} | {lanes} |".format(
                command=row["command"],
                risk_level=row["risk_level"],
                categories=", ".join(f"`{item}`" for item in row["risk_categories"]),
                lanes="<br>".join(f"`{lane}`" for lane in row["test_lanes"]),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit aicoreutils command risk/test matrix.")
    parser.add_argument("--format", choices=["summary", "json", "markdown"], default="summary")
    args = parser.parse_args(argv)

    rows = command_rows()
    issues = audit()

    if args.format == "json":
        print(json.dumps({"ok": not issues, "issues": issues, "commands": rows}, ensure_ascii=False, indent=2))
    elif args.format == "markdown":
        print(render_markdown(rows))
    else:
        print(f"commands={len(rows)} risk_lanes={len(TEST_LANES)}")
        if issues:
            for issue in issues:
                print(f"ISSUE: {issue}")
        else:
            print("Command risk/test matrix is complete.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
