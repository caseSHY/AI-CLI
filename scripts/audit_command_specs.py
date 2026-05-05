#!/usr/bin/env python3
"""Audit the command spec pilot against the current argparse parser."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aicoreutils.command_specs import PILOT_COMMAND_SPECS, all_command_specs, specs_by_name  # noqa: E402
from aicoreutils.parser._parser import build_parser  # noqa: E402
from aicoreutils.tool_schema import tool_risk_level  # noqa: E402


def parser_subcommands() -> dict[str, argparse.ArgumentParser]:
    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return {name: subparser for name, subparser in action.choices.items() if not name.startswith("_")}
    return {}


def parser_argument_dests(subparser: argparse.ArgumentParser) -> set[str]:
    return {
        action.dest
        for action in subparser._actions
        if action.dest not in ("help", "pretty", "command") and action.dest != argparse.SUPPRESS
    }


def audit() -> list[str]:
    issues: list[str] = []
    subcommands = parser_subcommands()
    all_specs = all_command_specs()
    all_specs_by_name = specs_by_name(all_specs)

    missing_specs = set(subcommands) - set(all_specs_by_name)
    if missing_specs:
        issues.append(f"parser commands missing all-command specs: {sorted(missing_specs)}")

    extra_specs = set(all_specs_by_name) - set(subcommands)
    if extra_specs:
        issues.append(f"all-command specs not present in parser: {sorted(extra_specs)}")

    for name, spec in all_specs_by_name.items():
        subparser = subcommands.get(name)
        if subparser is None:
            continue

        parser_risk = tool_risk_level(name)
        if spec.risk_level != parser_risk:
            issues.append(f"{name}: generated spec risk {spec.risk_level} != tool risk {parser_risk}")

        handler = subparser.get_default("func")
        handler_name = getattr(handler, "__name__", "")
        if spec.handler_name != handler_name:
            issues.append(f"{name}: generated spec handler {spec.handler_name} != parser handler {handler_name}")

    for spec in PILOT_COMMAND_SPECS:
        subparser = subcommands.get(spec.name)
        if subparser is None:
            issues.append(f"pilot spec command is missing from parser: {spec.name}")
            continue

        parser_risk = tool_risk_level(spec.name)
        if spec.risk_level != parser_risk:
            issues.append(f"{spec.name}: spec risk {spec.risk_level} != tool risk {parser_risk}")

        parser_args = parser_argument_dests(subparser)
        spec_args = {argument.name for argument in spec.arguments}
        missing_args = spec_args - parser_args
        if missing_args:
            issues.append(f"{spec.name}: spec args missing from parser: {sorted(missing_args)}")

    return issues


def main() -> int:
    issues = audit()
    if issues:
        for issue in issues:
            print(f"ISSUE: {issue}")
        return 1
    print(
        "Command specs are consistent "
        f"({len(all_command_specs())} parser-derived commands, {len(PILOT_COMMAND_SPECS)} pilot commands)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
