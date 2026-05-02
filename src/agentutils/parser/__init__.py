"""Parser subpackage: CLI argument parsing, command dispatch, and main entry point.

Replaces the monolithic parser.py (~3000 lines) with focused modules:
    _parser.py        — build_parser() + all 114 subcommand imports
    _dispatch.py      — dispatch() routing (forwarded from _parser)
    _introspection.py — catalog/schema/coreutils/tool-list (forwarded)

All real code still lives in _parser.py for now (Phase 1 relay pattern).
Phase 2 will extract command specs into declarative COMMAND_SPECS.
"""

from __future__ import annotations

# These are re-exported from _parser but sourced from protocol/core;
# import them directly so mypy can trace the types.
from ..commands.system import command_coreutils
from ..core import EXIT
from ..protocol import AgentArgumentParser, AgentError

# Re-export everything from the bulk module (_parser.py)
from ._parser import (
    build_parser,
    command_catalog,
    command_schema,
    command_tool_list,
    dispatch,
    main,
    parser_command_names,
)

__all__ = [
    "AgentArgumentParser",
    "AgentError",
    "EXIT",
    "build_parser",
    "command_catalog",
    "command_coreutils",
    "command_schema",
    "command_tool_list",
    "dispatch",
    "main",
    "parser_command_names",
]
