"""Tests for safe output encoding layer (core/output.py).

Verifies that stdout/stderr output is safe on Windows cp936/gbk locales
where the text I/O layer cannot encode emoji, Korean, math symbols, etc.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
from typing import Any

from aicoreutils.core.output import (
    _has_buffer,
    safe_flush,
    safe_write_bytes,
    safe_write_error,
    safe_write_json,
    safe_write_text,
)


class SafeWriteJsonTests(unittest.TestCase):
    """JSON output safety regardless of platform encoding."""

    def test_json_with_emoji(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"ok": True, "msg": "hello \U0001f600 world"})
        result = json.loads(buf.getvalue())
        self.assertTrue(result["ok"])
        self.assertIn("\U0001f600", result["msg"])

    def test_json_with_korean(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"ok": True, "text": "안녕하세요"})
        result = json.loads(buf.getvalue())
        self.assertEqual(result["text"], "안녕하세요")

    def test_json_with_math_symbols(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"ok": True, "symbols": "∞ ≠ π √"})
        result = json.loads(buf.getvalue())
        self.assertIn("∞", result["symbols"])

    def test_json_compact_format(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"a": 1, "b": 2})
        raw = buf.getvalue()
        self.assertNotIn("  ", raw)  # no pretty-print indent
        self.assertTrue(raw.endswith("\n"))

    def test_json_pretty_format(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"a": 1, "b": 2}, pretty=True)
        raw = buf.getvalue()
        self.assertIn("  ", raw)  # has indent
        self.assertIn('"a"', raw)

    def test_ensure_ascii_false_no_crash(self) -> None:
        # ensure_ascii=False should not crash even with characters
        # outside the ASCII range
        buf = io.StringIO()
        chars = "\U0001f600 ☃ é 世界"
        safe_write_json(buf, {"ok": True, "text": chars})
        result = json.loads(buf.getvalue())
        self.assertEqual(result["text"], chars)

    def test_empty_payload(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {})
        result = json.loads(buf.getvalue())
        self.assertEqual(result, {})

    def test_nested_unicode(self) -> None:
        buf = io.StringIO()
        payload: dict[str, Any] = {
            "ok": True,
            "files": [
                {"name": "유코스 파일.txt"},
                {"name": "\U0001f4c4 document.pdf"},
            ],
        }
        safe_write_json(buf, payload)
        result = json.loads(buf.getvalue())
        self.assertEqual(len(result["files"]), 2)

    def test_cp936_stdout_simulation(self) -> None:
        """Simulate Windows cp936: mock stdout where .buffer writes bytes."""
        buf = io.BytesIO()

        class FakeStdout:
            buffer = buf
            encoding = "cp936"

        safe_write_json(FakeStdout(), {"ok": True, "msg": "\U0001f600 안녕"})
        raw_bytes = buf.getvalue()
        # Decode back as UTF-8 to verify no backslashreplace was needed
        text = raw_bytes.decode("utf-8")
        self.assertIn("\U0001f600", text)
        self.assertIn("안녕", text)

    def test_no_buffer_fallback(self) -> None:
        """When .buffer is missing, falls back to text write."""
        self.assertFalse(_has_buffer(io.StringIO()))
        buf = io.StringIO()
        safe_write_json(buf, {"ok": True, "text": "hello"})
        self.assertIn("hello", buf.getvalue())

    def test_backslashreplace_fallback(self) -> None:
        """UTF-8 encoding with backslashreplace should never fail."""
        text = "valid text \U0001f600"
        data = text.encode("utf-8", errors="backslashreplace")
        decoded = data.decode("utf-8")
        self.assertIn("\U0001f600", decoded)


class SafeWriteTextTests(unittest.TestCase):
    """Text output with configurable encoding."""

    def test_default_utf8_output(self) -> None:
        buf = io.StringIO()
        safe_write_text(buf, "hello world")
        self.assertEqual(buf.getvalue(), "hello world")

    def test_unicode_text_utf8(self) -> None:
        buf = io.StringIO()
        safe_write_text(buf, "CJK: 世界, emoji: \U0001f600")
        self.assertIn("世界", buf.getvalue())

    def test_custom_encoding(self) -> None:
        buf = io.StringIO()
        safe_write_text(buf, "hello", encoding="ascii", errors="replace")
        self.assertEqual(buf.getvalue(), "hello")


class SafeWriteBytesTests(unittest.TestCase):
    """Binary raw output passthrough."""

    def test_raw_bytes_passthrough(self) -> None:
        buf = io.BytesIO()

        class FakeStdout:
            buffer = buf

        data = b"\x00\x01\x02\xff\xfe\xfd"
        safe_write_bytes(FakeStdout(), data)
        self.assertEqual(buf.getvalue(), data)

    def test_raw_bytes_no_buffer_fallback(self) -> None:
        """With StringIO fallback, bytes survive via latin-1 round-trip."""
        buf = io.StringIO()
        data = b"hello\xffworld"
        safe_write_bytes(buf, data)
        # latin-1 encodes \xff as U+00FF
        self.assertEqual(buf.getvalue(), "helloÿworld")

    def test_binary_not_reencoded(self) -> None:
        """Binary data must not go through UTF-8 encode/decode."""
        buf = io.BytesIO()

        class FakeStdout:
            buffer = buf

        original = bytes(range(256))
        safe_write_bytes(FakeStdout(), original)
        self.assertEqual(buf.getvalue(), original)


class SafeWriteErrorTests(unittest.TestCase):
    """stderr error output safety."""

    def test_stderr_with_emoji(self) -> None:
        """Error messages containing emoji must not crash on stderr."""
        buf = io.StringIO()
        with unittest.mock.patch("sys.stderr", buf):
            safe_write_error({"ok": False, "error": {"code": "test", "message": "Failed \U0001f600 안녕"}})
        result = json.loads(buf.getvalue())
        self.assertFalse(result["ok"])
        self.assertIn("\U0001f600", result["error"]["message"])

    def test_stderr_error_structure(self) -> None:
        buf = io.StringIO()
        with unittest.mock.patch("sys.stderr", buf):
            safe_write_error({"ok": False, "error": {"code": "not_found", "message": "Path does not exist."}})
        result = json.loads(buf.getvalue())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "not_found")


class SafeFlushTests(unittest.TestCase):
    """Flush behavior."""

    def test_flush_called(self) -> None:
        flushed = []

        class FakeStream:
            buffer = None

            def flush(self):
                flushed.append(True)

        safe_flush(FakeStream())
        self.assertTrue(flushed)

    def test_flush_buffer(self) -> None:
        flushed = []

        class FakeBuffer:
            @staticmethod
            def flush():
                flushed.append(True)

        class FakeStream:
            buffer = FakeBuffer()

        safe_flush(FakeStream())
        self.assertTrue(flushed)


class RealStdoutTests(unittest.TestCase):
    """Verify safe_write_json works with real sys.stdout (smoke test)."""

    def test_real_stdout_has_buffer(self) -> None:
        self.assertTrue(_has_buffer(sys.stdout))

    def test_real_stderr_has_buffer(self) -> None:
        self.assertTrue(_has_buffer(sys.stderr))

    def test_safe_write_json_real_stdout_no_crash(self) -> None:
        """Must not raise any exception."""
        safe_write_json(sys.stdout, {"ok": True, "test": "smoke \U0001f600"})

    def test_safe_write_text_real_stdout_no_crash(self) -> None:
        safe_write_text(sys.stdout, "smoke test\n")

    def test_safe_write_bytes_real_stdout_no_crash(self) -> None:
        safe_write_bytes(sys.stdout, b"smoke bytes\n")


class Utf8EnvUnchangedTests(unittest.TestCase):
    """Linux/macOS UTF-8 environment behavior must not change."""

    def test_json_roundtrip_utf8(self) -> None:
        buf = io.StringIO()
        payload = {"ok": True, "result": {"path": "/home/été.txt"}}
        safe_write_json(buf, payload)
        roundtripped = json.loads(buf.getvalue())
        self.assertEqual(roundtripped["result"]["path"], "/home/été.txt")

    def test_sort_keys_deterministic(self) -> None:
        buf1 = io.StringIO()
        buf2 = io.StringIO()
        safe_write_json(buf1, {"b": 1, "a": 2})
        safe_write_json(buf2, {"a": 2, "b": 1})
        self.assertEqual(buf1.getvalue(), buf2.getvalue())

    def test_trailing_newline_consistent(self) -> None:
        buf = io.StringIO()
        safe_write_json(buf, {"ok": True})
        self.assertTrue(buf.getvalue().endswith("\n"))


if __name__ == "__main__":
    unittest.main()
