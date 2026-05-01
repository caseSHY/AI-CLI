"""Plugin discovery and registration system for agentutils.

Phase 3 foundation: discovers agentutils_* namespace packages and
registers their command functions automatically.

Usage in a plugin package (e.g., agentutils_extra):

    # agentutils_extra/__init__.py
    COMMANDS = {
        "mycommand": my_command_function,
    }

Then agentutils will discover and register "mycommand" automatically.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from typing import Any

from .catalog import CATALOG as _BUILTIN_CATALOG

# Type alias for a command function
CommandFunc = Callable[..., Any]

# Registry of plugin-discovered commands: name -> function
_PLUGIN_COMMANDS: dict[str, CommandFunc] = {}


def discover_plugins() -> dict[str, CommandFunc]:
    """Discover agentutils plugin packages and return their commands.

    Scans for packages matching 'agentutils_*' and collects COMMANDS
    dictionaries from each.
    """
    global _PLUGIN_COMMANDS
    discovered: dict[str, CommandFunc] = {}

    for _finder, name, ispkg in pkgutil.iter_modules():
        if not name.startswith("agentutils_") or not ispkg:
            continue
        try:
            module = importlib.import_module(name)
            commands = getattr(module, "COMMANDS", None)
            if isinstance(commands, dict):
                for cmd_name, cmd_func in commands.items():
                    if callable(cmd_func):
                        discovered[cmd_name] = cmd_func
        except ImportError:
            continue

    _PLUGIN_COMMANDS = discovered
    return discovered


def get_plugin_commands() -> dict[str, CommandFunc]:
    """Return currently registered plugin commands."""
    return dict(_PLUGIN_COMMANDS)


def register_plugin_command(name: str, func: CommandFunc, priority: str = "P3") -> None:
    """Register a single plugin command programmatically."""
    _PLUGIN_COMMANDS[name] = func
    # Add to catalog if not already present
    for entry in _BUILTIN_CATALOG:
        if entry["priority"] == priority:
            if name not in entry["tools"]:
                entry["tools"].append(name)
            return
    # If priority not found, create a new entry
    _BUILTIN_CATALOG.append(
        {
            "priority": priority,
            "urgency": "normal",
            "category": "plugin",
            "why": "User-installed plugin command.",
            "tools": [name],
        }
    )


def has_plugins() -> bool:
    """Return True if any plugins are registered."""
    return len(_PLUGIN_COMMANDS) > 0
