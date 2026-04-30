"""Backward-compatible re-export module.

All code has been refactored into modular files under agentutils/.
This module exists only for backward compatibility (e.g., the
pyproject.toml entry_point references agentutils.cli:main).
"""

from __future__ import annotations

# Re-export main entry point
from .parser import main, build_parser, dispatch, command_catalog, command_schema

# Re-export protocol essentials for backward compatibility
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
