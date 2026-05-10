"""Safe stdout/stderr output layer — bypass text I/O encoding on all platforms.

On Windows with Chinese locale, sys.stdout.encoding is gbk/cp936.
Writing a Unicode str containing emoji, Korean, math symbols, etc. through
the text I/O layer (stream.write(str)) triggers UnicodeEncodeError because
GBK cannot represent those codepoints.

This module routes ALL output through sys.stdout.buffer / sys.stderr.buffer
(bytes), bypassing the platform text encoding layer entirely.  JSON output
is serialized with ensure_ascii=False (human-readable Unicode), then encoded
as UTF-8 with errors="backslashreplace" as the ultimate safety net.

When stream.buffer is not available (e.g. StringIO in tests), falls back to
text-mode writing — safe because StringIO has no encoding constraints.

Usage:
    from aicoreutils.core.output import safe_write_json, safe_write_bytes

    safe_write_json(sys.stdout, {"ok": True, "result": ...})
    safe_write_bytes(sys.stdout, b"raw output")
    safe_write_error({"ok": False, "error": ...})
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, TextIO

_DEFAULT_ENCODING = "utf-8"
_DEFAULT_ERRORS = "backslashreplace"


def _has_buffer(stream: TextIO) -> bool:
    """Check whether the stream has a .buffer attribute for binary I/O.

    Real sys.stdout / sys.stderr always have .buffer.  StringIO and other
    test doubles do not, so we fall back to text-mode writes for those.
    """
    return getattr(stream, "buffer", None) is not None


def _write_bytes_or_text(stream: TextIO, data: bytes, *, text: str) -> None:
    """Write bytes to stream.buffer when available, otherwise write text.

    On real stdout/stderr, UTF-8 bytes go to stream.buffer, bypassing the
    platform text encoding layer entirely (prevents cp936/gbk crashes).
    When .buffer is missing (e.g. StringIO in tests), write the text
    string directly — StringIO has no encoding constraints.
    """
    buf: Any = getattr(stream, "buffer", None)
    if buf is not None:
        buf.write(data)
    else:
        stream.write(text)


def _json_text(payload: dict[str, Any], *, pretty: bool = False) -> str:
    """Serialize a dict to a JSON string (no trailing newline)."""
    kwargs: dict[str, Any] = {"ensure_ascii": False, "sort_keys": True}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(payload, **kwargs)


def safe_write_json(
    stream: TextIO,
    payload: dict[str, Any],
    *,
    pretty: bool = False,
) -> None:
    """Write a dict as UTF-8 JSON bytes to stream.buffer.

    On Windows cp936, this bypasses the text encoding layer so characters
    outside the console codepage (emoji, Korean, math symbols) don't crash.
    Falls back to text-mode write when .buffer is unavailable (tests).
    """
    text = _json_text(payload, pretty=pretty)
    data = (text + "\n").encode(_DEFAULT_ENCODING, errors=_DEFAULT_ERRORS)
    _write_bytes_or_text(stream, data, text=text + "\n")


def safe_write_text(
    stream: TextIO,
    text: str,
    *,
    encoding: str = _DEFAULT_ENCODING,
    errors: str = _DEFAULT_ERRORS,
) -> None:
    """Write a text string as encoded bytes, bypassing the text I/O layer."""
    data = text.encode(encoding, errors=errors)
    _write_bytes_or_text(stream, data, text=text)


def safe_write_bytes(stream: TextIO, data: bytes) -> None:
    """Write raw bytes to stream.buffer (for --raw binary mode).

    When .buffer is unavailable, writes text via latin-1 (which round-trips
    every byte value 0-255 as a single Unicode codepoint).
    """
    buf: Any = getattr(stream, "buffer", None)
    if buf is not None:
        buf.write(data)
    else:
        # Fallback: latin-1 encodes every byte as U+0000-U+00FF,
        # so the bytes survive intact through the text layer.
        stream.write(data.decode("latin-1"))


def safe_write_error(payload: dict[str, Any]) -> None:
    """Write an error envelope to stderr as UTF-8 JSON bytes."""
    safe_write_json(sys.stderr, payload)


def safe_flush(stream: TextIO) -> None:
    """Flush the underlying buffer or stream."""
    buf: Any = getattr(stream, "buffer", None)
    if buf is not None:
        buf.flush()
    else:
        stream.flush()


def configure_stdio() -> None:
    """Ensure stdio uses UTF-8 on platforms where Python may default to locale encoding.

    On Python 3.11+, UTF-8 mode is the default, so this is normally a no-op.
    On older Python or when PYTHONIOENCODING is overridden, this forces UTF-8.
    """
    for name in ("PYTHONIOENCODING", "PYTHONUTF8"):
        if os.environ.get(name) in (None, ""):
            os.environ[name] = "utf-8" if name == "PYTHONIOENCODING" else "1"
