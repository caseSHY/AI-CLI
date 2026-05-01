"""Unified command registry with auto-discovery from the parser.

Provides helper functions re-exported from catalog (single authority).
"""

from __future__ import annotations

# Re-export priority functions from the single authority (catalog.py)
from .catalog import (
    _COMMAND_PRIORITY_MAP,
    get_priority,
    get_all_commands,
    get_commands_by_priority,
    implemented_catalog,
)
