"""Project consistency tests: verify catalog, tool_schema, and parser are in agreement."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _get_parser_commands() -> set[str]:
    sys.path.insert(0, str(SRC))
    from aicoreutils.parser._parser import build_parser  # noqa: E402

    parser = build_parser()
    # find subparsers
    for action in parser._actions:
        from argparse import _SubParsersAction

        if isinstance(action, _SubParsersAction):
            return {name for name in action.choices if not name.startswith("_")}
    return set()


def _get_read_only_tools() -> set[str]:
    sys.path.insert(0, str(SRC))
    from aicoreutils.registry.tool_schema import _READ_ONLY_TOOLS  # noqa: E402

    return _READ_ONLY_TOOLS


def _get_destructive_tools() -> set[str]:
    sys.path.insert(0, str(SRC))
    from aicoreutils.registry.tool_schema import _DESTRUCTIVE_TOOLS  # noqa: E402

    return _DESTRUCTIVE_TOOLS


def _get_catalog_commands() -> list[str]:
    sys.path.insert(0, str(SRC))
    from aicoreutils.registry.catalog import CATALOG  # noqa: E402

    all_cmds: list[str] = []
    for entry in CATALOG:
        all_cmds.extend(entry["tools"])
    return all_cmds


def test_tool_classification_no_overlap():
    """_READ_ONLY_TOOLS and _DESTRUCTIVE_TOOLS must not share any commands."""
    read_only = _get_read_only_tools()
    destructive = _get_destructive_tools()
    overlap = read_only & destructive
    assert not overlap, (
        f"Commands in BOTH _READ_ONLY_TOOLS and _DESTRUCTIVE_TOOLS: {sorted(overlap)}. "
        f"This is a security bug — commands in both sets are treated as read-only by MCP --read-only mode."
    )


def test_catalog_no_duplicate_commands():
    """Each command must appear in only ONE priority group in catalog.py."""
    commands = _get_catalog_commands()
    seen: dict[str, int] = {}
    for cmd in commands:
        seen[cmd] = seen.get(cmd, 0) + 1
    duplicates = {cmd: count for cmd, count in seen.items() if count > 1}
    assert not duplicates, (
        f"Commands appearing in multiple catalog priority groups: {duplicates}. "
        f"This causes the last group to silently overwrite the priority mapping."
    )


def test_all_parser_commands_are_classified():
    """Every parser-registered command must be in _READ_ONLY_TOOLS or _DESTRUCTIVE_TOOLS."""
    parser_cmds = _get_parser_commands()
    read_only = _get_read_only_tools()
    destructive = _get_destructive_tools()
    classified = read_only | destructive
    unclassified = parser_cmds - classified
    assert not unclassified, (
        f"Parser commands not in _READ_ONLY_TOOLS or _DESTRUCTIVE_TOOLS: {sorted(unclassified)}. "
        f"These commands will not get readOnlyHint/destructiveHint annotations."
    )


def test_catalog_commands_are_in_parser():
    """Every catalog command must be registered in the parser."""
    parser_cmds = _get_parser_commands()
    catalog_cmds = set(_get_catalog_commands())
    missing = catalog_cmds - parser_cmds
    assert not missing, f"Catalog commands not in parser: {sorted(missing)}"


def test_command_matrix_audit_passes():
    """The command risk/test matrix audit must pass."""
    result = subprocess.run(
        [sys.executable, "scripts/audit_command_matrix.py"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_command_spec_pilot_audit_passes():
    """The command spec pilot must stay consistent with the current parser."""
    result = subprocess.run(
        [sys.executable, "scripts/audit_command_specs.py"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_supply_chain_audit_passes():
    """Supply-chain and release hardening controls must stay in place."""
    result = subprocess.run(
        [sys.executable, "scripts/audit_supply_chain.py"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
