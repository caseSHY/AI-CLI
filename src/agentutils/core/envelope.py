"""JSON envelope helpers for agentutils."""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from .exceptions import AgentError

_TOOL_VERSION = "0.2.0"


def utc_iso(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).isoformat().replace("+00:00", "Z")


def write_json(stream: TextIO, payload: dict[str, Any], *, pretty: bool = False) -> None:
    kwargs: dict[str, Any] = {"ensure_ascii": False, "sort_keys": True}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    stream.write(json.dumps(payload, **kwargs))
    stream.write("\n")


def envelope(command: str, result: Any, *, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "tool": "agentutils",
        "version": _TOOL_VERSION,
        "command": command,
        "result": result,
        "warnings": warnings or [],
    }


def error_envelope(command: str | None, error: AgentError) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": "agentutils",
        "version": _TOOL_VERSION,
        "command": command,
        "error": error.to_dict(),
    }
