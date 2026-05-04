"""Parser subpackage: CLI argument parsing, command dispatch, and main entry point."""

from __future__ import annotations

from ..core import EXIT
from ..protocol import AgentArgumentParser, AgentError
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
    "command_schema",
    "command_tool_list",
    "dispatch",
    "main",
    "parser_command_names",
]
