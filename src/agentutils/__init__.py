"""Agent-friendly CLI layer inspired by GNU Coreutils."""

from __future__ import annotations

__version__ = "0.2.0"

# Re-export main entry point and core protocol for backward compatibility
from .parser import main, build_parser, dispatch, command_catalog, command_schema
from .protocol import (
    AgentArgumentParser,
    AgentError,
    EXIT,
    HASH_ALGORITHMS,
    envelope,
    error_envelope,
    resolve_path,
    stat_entry,
    utc_iso,
    write_json,
)

# Core primitives (new in 0.2.0)
from .core import StreamWriter, is_stream_mode

# Plugin system (new in 0.2.0)
from .plugins import discover_plugins, register_plugin_command, get_plugin_commands

# Async interface (new in 0.2.0)
from .async_interface import run_async, run_async_many
