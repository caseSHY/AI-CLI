"""Command specification prototype for parser/schema convergence.

This module defines the data shape for a future schema-first command registry.
During the transition, all command specs can be derived from the current
argparse parser and risk metadata, while a small hand-written pilot remains as
the promotion target for parser generation.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Literal

RiskLevel = Literal["read-only", "write", "destructive", "process-exec", "platform-sensitive"]
StabilityLevel = Literal["stable", "experimental", "platform-limited"]
ArgumentKind = Literal["positional", "option"]


@dataclass(frozen=True)
class ArgumentSpec:
    """Minimal command argument specification."""

    name: str
    kind: ArgumentKind
    required: bool
    help: str
    nargs: str | None = None


@dataclass(frozen=True)
class CommandSpec:
    """Minimal command specification shared by parser, MCP, docs, and audits."""

    name: str
    category: str
    stability: StabilityLevel
    risk_level: RiskLevel
    handler_name: str
    summary: str
    gnu_compatibility: str
    arguments: tuple[ArgumentSpec, ...] = ()


PILOT_COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="pwd",
        category="fs",
        stability="stable",
        risk_level="read-only",
        handler_name="command_pwd",
        summary="Return the current working directory as structured JSON.",
        gnu_compatibility="Agent JSON envelope; not GNU raw stdout by default.",
    ),
    CommandSpec(
        name="basename",
        category="fs",
        stability="stable",
        risk_level="read-only",
        handler_name="command_basename",
        summary="Return final path components, optionally stripping a suffix.",
        gnu_compatibility="Effective subset; zero-byte delimiters are not supported.",
        arguments=(
            ArgumentSpec("paths", "positional", True, "Paths to transform.", nargs="+"),
            ArgumentSpec("suffix", "option", False, "Remove suffix from each basename when present."),
            ArgumentSpec("raw", "option", False, "Write one basename per line without a JSON envelope."),
        ),
    ),
    CommandSpec(
        name="seq",
        category="text",
        stability="stable",
        risk_level="read-only",
        handler_name="command_seq",
        summary="Generate a bounded numeric sequence.",
        gnu_compatibility="Effective subset with bounded output and JSON by default.",
        arguments=(
            ArgumentSpec("numbers", "positional", True, "[FIRST [INCREMENT]] LAST.", nargs="+"),
            ArgumentSpec("increment", "option", False, "Increment used with one or two positional numbers."),
            ArgumentSpec("separator", "option", False, "Raw output separator."),
            ArgumentSpec("format", "option", False, "printf-style numeric format."),
            ArgumentSpec("max_items", "option", False, "Maximum items to generate."),
            ArgumentSpec("raw", "option", False, "Write sequence text without a JSON envelope."),
        ),
    ),
)


def pilot_spec_names() -> set[str]:
    """Return the commands covered by the command spec pilot."""
    return {spec.name for spec in PILOT_COMMAND_SPECS}


def _handler_name(subparser: argparse.ArgumentParser) -> str:
    handler = subparser.get_default("func")
    return getattr(handler, "__name__", "")


def _argument_kind(action: argparse.Action) -> ArgumentKind:
    return "option" if action.option_strings else "positional"


def _argument_required(action: argparse.Action) -> bool:
    if action.option_strings:
        return bool(getattr(action, "required", False))
    return action.nargs not in ("?", "*")


def _argument_nargs(action: argparse.Action) -> str | None:
    if action.nargs is None:
        return None
    return str(action.nargs)


def _argument_specs(subparser: argparse.ArgumentParser) -> tuple[ArgumentSpec, ...]:
    specs: list[ArgumentSpec] = []
    for action in subparser._actions:
        if action.dest in ("help", "pretty", "command") or action.dest == argparse.SUPPRESS:
            continue
        specs.append(
            ArgumentSpec(
                name=str(action.dest),
                kind=_argument_kind(action),
                required=_argument_required(action),
                help=action.help or "",
                nargs=_argument_nargs(action),
            )
        )
    return tuple(specs)


def _stability_for_risk(risk_level: str) -> StabilityLevel:
    if risk_level == "platform-sensitive":
        return "platform-limited"
    return "stable"


def _summary(subparser: argparse.ArgumentParser) -> str:
    return subparser.description or subparser.get_default("help") or ""


def _parser_subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return {name: subparser for name, subparser in action.choices.items() if not name.startswith("_")}
    return {}


def command_specs_from_parser(parser: argparse.ArgumentParser) -> tuple[CommandSpec, ...]:
    """Build transitional specs for every registered parser command."""
    from .catalog import get_priority
    from .tool_schema import tool_risk_level

    specs: list[CommandSpec] = []
    for name, subparser in sorted(_parser_subcommands(parser).items()):
        risk_level = tool_risk_level(name)
        specs.append(
            CommandSpec(
                name=name,
                category=get_priority(name),
                stability=_stability_for_risk(risk_level),
                risk_level=risk_level,  # type: ignore[arg-type]
                handler_name=_handler_name(subparser),
                summary=_summary(subparser),
                gnu_compatibility="Transitional parser-derived spec; see GNU compatibility audit for command gaps.",
                arguments=_argument_specs(subparser),
            )
        )
    return tuple(specs)


def all_command_specs() -> tuple[CommandSpec, ...]:
    """Return parser-derived specs for all registered commands."""
    from .parser._parser import build_parser

    return command_specs_from_parser(build_parser())


def specs_by_name(specs: tuple[CommandSpec, ...] | None = None) -> dict[str, CommandSpec]:
    """Return command specs keyed by command name."""
    chosen_specs = specs if specs is not None else all_command_specs()
    return {spec.name: spec for spec in chosen_specs}
