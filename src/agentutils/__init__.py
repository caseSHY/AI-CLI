"""Agent-friendly CLI layer inspired by GNU Coreutils."""

from __future__ import annotations

__version__ = "0.2.0"

# Re-export main entry point and core protocol for backward compatibility
# Async interface (new in 0.2.0)
from .async_interface import run_async, run_async_many

# Core primitives (new in 0.2.0)
from .core import StreamWriter, is_stream_mode
from .parser import build_parser, command_catalog, command_schema, dispatch, main

# Plugin system (new in 0.2.0)
from .plugins import discover_plugins, get_plugin_commands, register_plugin_command
from .protocol import (
    EXIT,
    HASH_ALGORITHMS,
    AgentArgumentParser,
    AgentError,
    envelope,
    error_envelope,
    resolve_path,
    stat_entry,
    utc_iso,
    write_json,
)

__all__ = [
    "AgentArgumentParser",
    "AgentError",
    "EXIT",
    "HASH_ALGORITHMS",
    "StreamWriter",
    "__version__",
    "build_parser",
    "command_catalog",
    "command_schema",
    "discover_plugins",
    "dispatch",
    "envelope",
    "error_envelope",
    "get_plugin_commands",
    "is_stream_mode",
    "main",
    "register_plugin_command",
    "resolve_path",
    "run_async",
    "run_async_many",
    "stat_entry",
    "utc_iso",
    "write_json",
]
