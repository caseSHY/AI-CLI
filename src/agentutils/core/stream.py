"""Streaming NDJSON output for large dataset operations.

Provides StreamWriter for emitting newline-delimited JSON (NDJSON)
one entry at a time, enabling bounded-memory operations on large
directories, files, and pipelines.
"""

from __future__ import annotations

import json
from typing import Any, TextIO

from .envelope import _TOOL_VERSION


class StreamWriter:
    """Write NDJSON (one JSON object per line) to an output stream.

    Usage:
        writer = StreamWriter(sys.stdout, command="ls")
        for item in large_iterator:
            writer.write_item(item)
        writer.write_summary({"total": 1000, "truncated": False})
    """

    def __init__(
        self,
        stream: TextIO,
        *,
        command: str,
        max_items: int = 0,
    ) -> None:
        self._stream = stream
        self._command = command
        self._max_items = max_items
        self._count = 0
        self._truncated = False
        self._closed = False

    def write_item(self, item: dict[str, Any]) -> bool:
        """Write a single item as NDJSON line. Returns False if truncated."""
        if self._closed:
            return False
        if self._max_items and self._count >= self._max_items:
            self._truncated = True
            return False
        self._count += 1
        line = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self._stream.write(line + "\n")
        return True

    def write_summary(self, summary: dict[str, Any]) -> None:
        """Write the closing summary envelope."""
        if self._closed:
            return
        self._closed = True
        envelope = {
            "ok": True,
            "tool": "agentutils",
            "version": _TOOL_VERSION,
            "command": self._command,
            "stream": True,
            "count": self._count,
            "truncated": self._truncated,
            "summary": summary,
        }
        self._stream.write(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n")

    @property
    def count(self) -> int:
        return self._count

    @property
    def truncated(self) -> bool:
        return self._truncated


class NullStream:
    """No-op stream for dry-run operations that would otherwise stream."""

    def write_item(self, item: dict[str, Any]) -> bool:
        return True

    def write_summary(self, summary: dict[str, Any]) -> None:
        pass

    @property
    def count(self) -> int:
        return 0

    @property
    def truncated(self) -> bool:
        return False


def is_stream_mode(args: Any) -> bool:
    """Check if --stream flag is set on the args namespace."""
    return getattr(args, "stream", False)
