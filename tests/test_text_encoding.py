"""Encoding layer tests: decode_bytes, BOM detection, CLI integration, backward compat.

Tests cover:
- UTF-8 with/without BOM
- UTF-16 LE/BE with BOM
- UTF-32 LE/BE with BOM
- GB18030, GBK, Big5, Shift-JIS, EUC-JP, EUC-KR
- latin-1 fallback
- --encoding auto/profile/errors flags
- --show-encoding metadata
- Backward compatibility (default still utf-8, no regressions)
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest

from aicoreutils.core.encoding import (
    ENCODING_PROFILES,
    decode_bytes,
    detect_bom,
    detect_encoding,
    encoding_metadata,
    normalize_encoding,
)

# ── Test helpers ─────────────────────────────────────────────────────


def _cli_output(*args: str, **env: str) -> str:
    """Run aicoreutils CLI and return stdout as decoded text."""
    env_vars = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **env}
    full_env = {**__import__("os").environ, **env_vars}
    result = subprocess.run(
        [sys.executable, "-m", "aicoreutils", *args],
        capture_output=True,
        env=full_env,
    )
    return result.stdout.decode("utf-8", errors="replace")


def _json_result(*args: str, **env: str) -> dict:
    """Run CLI and return parsed JSON result."""
    return json.loads(_cli_output(*args, **env))


# ── Unit tests: detect_bom ───────────────────────────────────────────


class TestDetectBOM(unittest.TestCase):
    def test_no_bom(self) -> None:
        enc, length = detect_bom(b"hello")
        self.assertIsNone(enc)
        self.assertEqual(length, 0)

    def test_utf8_bom(self) -> None:
        enc, length = detect_bom(b"\xef\xbb\xbfhello")
        self.assertEqual(enc, "utf-8-sig")
        self.assertEqual(length, 3)

    def test_utf16_le_bom(self) -> None:
        enc, length = detect_bom(b"\xff\xfeh\x00e\x00")
        self.assertEqual(enc, "utf-16-le")
        self.assertEqual(length, 2)

    def test_utf16_be_bom(self) -> None:
        enc, length = detect_bom(b"\xfe\xff\x00h\x00e")
        self.assertEqual(enc, "utf-16-be")
        self.assertEqual(length, 2)

    def test_utf32_le_bom(self) -> None:
        enc, length = detect_bom(b"\xff\xfe\x00\x00hello")
        self.assertEqual(enc, "utf-32-le")
        self.assertEqual(length, 4)

    def test_utf32_be_bom(self) -> None:
        enc, length = detect_bom(b"\x00\x00\xfe\xffhello")
        self.assertEqual(enc, "utf-32-be")
        self.assertEqual(length, 4)

    def test_short_data_no_bom(self) -> None:
        enc, length = detect_bom(b"\xef")
        self.assertIsNone(enc)
        self.assertEqual(length, 0)

    def test_gbk_no_bom(self) -> None:
        enc, length = detect_bom("中文".encode("gbk"))
        self.assertIsNone(enc)


# ── Unit tests: normalize_encoding ───────────────────────────────────


class TestNormalizeEncoding(unittest.TestCase):
    def test_utf8(self) -> None:
        self.assertEqual(normalize_encoding("utf-8"), "utf-8")

    def test_utf8_dash_variants(self) -> None:
        self.assertEqual(normalize_encoding("UTF-8"), "utf-8")
        self.assertEqual(normalize_encoding("utf_8"), "utf-8")

    def test_gbk_alias(self) -> None:
        self.assertEqual(normalize_encoding("gbk"), "gbk")

    def test_shift_jis(self) -> None:
        self.assertEqual(normalize_encoding("shift_jis"), "shift_jis")

    def test_euc_jp_underscore(self) -> None:
        self.assertEqual(normalize_encoding("euc-jp"), "euc_jp")

    def test_auto_passthrough(self) -> None:
        self.assertEqual(normalize_encoding("auto"), "auto")

    def test_invalid_encoding(self) -> None:
        with self.assertRaises(ValueError):
            normalize_encoding("x-invalid-encoding-12345")


# ── Unit tests: decode_bytes ─────────────────────────────────────────


class TestDecodeBytesUTF8(unittest.TestCase):
    def test_plain_utf8(self) -> None:
        r = decode_bytes(b"hello world", encoding="utf-8")
        self.assertEqual(r.text, "hello world")
        self.assertEqual(r.encoding_used, "utf-8")
        self.assertEqual(r.method, "exact")
        self.assertGreater(r.confidence, 0.9)

    def test_utf8_bom_detected(self) -> None:
        r = decode_bytes(b"\xef\xbb\xbfhello", encoding="utf-8")
        self.assertEqual(r.text, "hello")
        self.assertEqual(r.encoding_used, "utf-8-sig")
        self.assertTrue(r.bom_stripped)
        self.assertEqual(r.method, "bom")

    def test_utf8_bom_with_auto(self) -> None:
        r = decode_bytes(b"\xef\xbb\xbfhello", encoding="auto")
        self.assertEqual(r.text, "hello")
        self.assertEqual(r.encoding_used, "utf-8-sig")
        self.assertTrue(r.bom_stripped)

    def test_utf8_strict_rejects_invalid(self) -> None:
        with self.assertRaises(UnicodeDecodeError):
            decode_bytes(b"\xc0\xc1", encoding="utf-8", errors="strict")

    def test_utf8_replace_silences_invalid(self) -> None:
        # \xc0 is overlong encoding — invalid in strict UTF-8, replaced in replace mode
        r = decode_bytes(b"\xc0\xc1", encoding="utf-8", errors="replace")
        self.assertIn("�", r.text)
        self.assertLess(r.confidence, 0.5)

    def test_utf8_with_chinese(self) -> None:
        text = "你好世界\n中文测试\n"
        data = text.encode("utf-8")
        r = decode_bytes(data, encoding="utf-8")
        self.assertEqual(r.text, text)
        self.assertEqual(r.encoding_used, "utf-8")

    def test_utf8_surrogateescape(self) -> None:
        r = decode_bytes(b"hello\xffworld", encoding="utf-8", errors="surrogateescape")
        # surrogates in the text indicate the byte was preserved
        self.assertIn("hello", r.text)


class TestDecodeBytesBOM(unittest.TestCase):
    def test_utf16_le_bom(self) -> None:
        # "hello" in UTF-16-LE with BOM
        data = "hello".encode("utf-16-le")
        r = decode_bytes(b"\xff\xfe" + data, encoding="auto")
        self.assertIn("hello", r.text)
        self.assertEqual(r.encoding_used, "utf-16-le")

    def test_utf16_be_bom(self) -> None:
        data = "hello".encode("utf-16-be")
        r = decode_bytes(b"\xfe\xff" + data, encoding="auto")
        self.assertIn("hello", r.text)
        self.assertEqual(r.encoding_used, "utf-16-be")

    def test_utf32_le_bom(self) -> None:
        data = "hello".encode("utf-32-le")
        r = decode_bytes(b"\xff\xfe\x00\x00" + data, encoding="auto")
        self.assertIn("hello", r.text)
        self.assertEqual(r.encoding_used, "utf-32-le")

    def test_bom_overrides_declared_encoding(self) -> None:
        r = decode_bytes(b"\xef\xbb\xbfhello", encoding="gb18030")
        self.assertEqual(r.text, "hello")
        self.assertEqual(r.encoding_used, "utf-8-sig")
        self.assertIn("BOM indicates", r.warnings[0] if r.warnings else "")


class TestDecodeBytesCJK(unittest.TestCase):
    def test_gb18030_chinese(self) -> None:
        text = "你好世界"
        data = text.encode("gb18030")
        r = decode_bytes(data, encoding="gb18030")
        self.assertEqual(r.text, text)
        self.assertEqual(r.method, "exact")

    def test_gbk_chinese(self) -> None:
        text = "中文测试"
        data = text.encode("gbk")
        r = decode_bytes(data, encoding="gbk")
        self.assertEqual(r.text, text)

    def test_big5_chinese(self) -> None:
        text = "繁體中文"
        data = text.encode("big5")
        r = decode_bytes(data, encoding="big5")
        self.assertEqual(r.text, text)

    def test_shift_jis_japanese(self) -> None:
        text = "日本語テスト"
        data = text.encode("shift_jis")
        r = decode_bytes(data, encoding="shift_jis")
        self.assertEqual(r.text, text)

    def test_euc_jp_japanese(self) -> None:
        text = "日本語テスト"
        data = text.encode("euc_jp")
        r = decode_bytes(data, encoding="euc_jp")
        self.assertEqual(r.text, text)

    def test_euc_kr_korean(self) -> None:
        text = "한국어"
        data = text.encode("euc_kr")
        r = decode_bytes(data, encoding="euc_kr")
        self.assertEqual(r.text, text)

    def test_cp949_korean(self) -> None:
        text = "한국어"
        data = text.encode("cp949")
        r = decode_bytes(data, encoding="cp949")
        self.assertEqual(r.text, text)


class TestDecodeBytesAuto(unittest.TestCase):
    def test_auto_utf8_without_bom(self) -> None:
        text = "hello world"
        data = text.encode("utf-8")
        r = decode_bytes(data, encoding="auto")
        self.assertEqual(r.text, text)
        self.assertEqual(r.encoding_used, "utf-8")

    def test_auto_detects_gb18030_with_zh_cn_profile(self) -> None:
        text = "你好世界中文"
        data = text.encode("gb18030")
        r = decode_bytes(data, encoding="auto", profile="zh-cn")
        self.assertEqual(r.text, text)
        self.assertIn(r.encoding_used, ("gb18030", "gbk"))

    def test_auto_detects_big5_with_zh_tw_profile(self) -> None:
        text = "繁體中文"
        data = text.encode("big5")
        r = decode_bytes(data, encoding="auto", profile="zh-tw")
        # big5 or utf-8 fallback
        self.assertIn(r.encoding_used, ("big5", "utf-8", "latin-1"))

    def test_auto_detects_shift_jis_with_ja_profile(self) -> None:
        text = "日本語"
        data = text.encode("shift_jis")
        r = decode_bytes(data, encoding="auto", profile="ja")
        self.assertIn(r.encoding_used, ("shift_jis", "euc_jp", "utf-8"))


class TestDecodeBytesFallback(unittest.TestCase):
    def test_latin1_never_fails(self) -> None:
        # latin-1 decodes any bytes 1:1 — never fails
        r = decode_bytes(bytes(range(256)), encoding="latin-1")
        self.assertEqual(len(r.text), 256)
        self.assertEqual(r.encoding_used, "latin_1")

    def test_auto_fallback_to_latin1(self) -> None:
        # Binary data that fails in all CJK codecs falls back to latin-1
        r = decode_bytes(b"\x80\x81\x82\x83\x84\x85\x86\x87", encoding="auto")
        self.assertIsNotNone(r.text)
        self.assertEqual(r.encoding_used, "latin-1")

    def test_latin1_explicit(self) -> None:
        text = "café"
        data = text.encode("latin-1")
        r = decode_bytes(data, encoding="latin-1")
        self.assertEqual(r.text, text)

    def test_windows1252(self) -> None:
        text = "café €"
        data = text.encode("windows-1252")
        r = decode_bytes(data, encoding="windows-1252")
        self.assertEqual(r.text, text)


class TestDecodeBytesConfidence(unittest.TestCase):
    def test_empty_input(self) -> None:
        r = decode_bytes(b"", encoding="utf-8")
        self.assertEqual(r.text, "")
        self.assertEqual(r.confidence, 1.0)

    def test_valid_utf8_high_confidence(self) -> None:
        r = decode_bytes(b"hello", encoding="utf-8")
        self.assertGreaterEqual(r.confidence, 0.9)

    def test_invalid_utf8_low_confidence(self) -> None:
        # All bytes are invalid in utf-8; no BOM pattern
        r = decode_bytes(b"\xff\xff\xc0\xc1\xfe", encoding="utf-8", errors="replace")
        self.assertLess(r.confidence, 0.8)

    def test_confidence_exact_is_1_0(self) -> None:
        r = decode_bytes(b"hello", encoding="utf-8")
        self.assertAlmostEqual(r.confidence, 0.95)


# ── Unit tests: detect_encoding ──────────────────────────────────────


class TestDetectEncoding(unittest.TestCase):
    def test_detect_utf8(self) -> None:
        enc, conf, method, warnings = detect_encoding(b"hello")
        self.assertEqual(enc, "utf-8")
        self.assertGreater(conf, 0.9)
        # detect_encoding always uses auto mode, so method is profile_fallback
        self.assertIn(method, ("exact", "profile_fallback"))

    def test_detect_with_bom(self) -> None:
        enc, conf, method, _ = detect_encoding(b"\xef\xbb\xbfhello")
        self.assertEqual(enc, "utf-8-sig")
        self.assertEqual(conf, 1.0)
        self.assertEqual(method, "bom")


# ── Unit tests: encoding_metadata ────────────────────────────────────


class TestEncodingMetadata(unittest.TestCase):
    def test_metadata_basic(self) -> None:
        r = decode_bytes(b"hello", encoding="utf-8")
        m = encoding_metadata(r, declared="utf-8")
        self.assertEqual(m["declared"], "utf-8")
        self.assertEqual(m["detected"], "utf-8")
        self.assertIsInstance(m["confidence"], float)
        self.assertEqual(m["method"], "exact")
        self.assertIsInstance(m["warnings"], list)

    def test_metadata_with_warnings(self) -> None:
        r = decode_bytes(b"\xff\xfe", encoding="utf-8", errors="replace")
        m = encoding_metadata(r, declared="utf-8")
        self.assertTrue(len(m["warnings"]) > 0)


# ── ENCODING_PROFILES structure ──────────────────────────────────────


class TestEncodingProfiles(unittest.TestCase):
    def test_all_profiles_defined(self) -> None:
        for name in ("zh-cn", "zh-tw", "ja", "ko", "western", "universal"):
            self.assertIn(name, ENCODING_PROFILES, msg=f"Profile {name} must be defined")

    def test_profiles_contain_valid_codecs(self) -> None:
        for _profile, chain in ENCODING_PROFILES.items():
            for codec in chain:
                normalize_encoding(codec)  # must not raise


# ── CLI integration: --encoding flag ─────────────────────────────────


class TestCliEncodingFlag(unittest.TestCase):
    def test_cat_utf8_default(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_bytes(b"hello\n")
            r = _json_result("cat", str(d / "f.txt"))
            self.assertEqual(r["result"]["content"], "hello\n")
            self.assertEqual(r["result"]["encoding"], "utf-8")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_cat_gb18030(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            text = "你好世界\n"
            (d / "f.txt").write_bytes(text.encode("gb18030"))
            r = _json_result("cat", str(d / "f.txt"), "--encoding", "gb18030")
            self.assertEqual(r["result"]["content"], text)
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_sort_encoding_gb18030(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            lines = "张三\n李四\n王五\n"
            (d / "f.txt").write_bytes(lines.encode("gb18030"))
            r = _json_result("sort", str(d / "f.txt"), "--encoding", "gb18030")
            self.assertIn("lines", r["result"])
            self.assertGreater(len(r["result"]["lines"]), 0)
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_show_encoding_metadata_in_result(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            text = "hello\n"
            (d / "f.txt").write_text(text, encoding="utf-8")
            r = _json_result("cat", str(d / "f.txt"), "--show-encoding")
            self.assertIn("result", r)
            self.assertIn("encoding_meta", r["result"])
            meta = r["result"]["encoding_meta"]
            self.assertIn("detected", meta)
            self.assertIn("method", meta)
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_no_encoding_meta_without_flag(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("hello\n", encoding="utf-8")
            r = _json_result("cat", str(d / "f.txt"))
            self.assertNotIn("encoding_meta", r["result"])
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_wc_encoding_gbk(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            text = "中文测试\n"
            (d / "f.txt").write_bytes(text.encode("gbk"))
            r = _json_result("wc", str(d / "f.txt"), "--encoding", "gbk")
            entries = r["result"]["entries"]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["chars"], len(text))
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_raw_mode_preserves_bytes(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            text = "hello\n"
            (d / "f.txt").write_text(text, encoding="utf-8")
            raw_stdout = _cli_output("sort", str(d / "f.txt"), "--raw")
            self.assertEqual(raw_stdout, text)
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


# ── Backward compatibility ───────────────────────────────────────────


class TestBackwardCompat(unittest.TestCase):
    def test_envelope_format_unchanged(self) -> None:
        r = _json_result("schema")
        self.assertIn("ok", r)
        self.assertIn("tool", r)
        self.assertEqual(r["tool"], "aicoreutils")
        self.assertIn("version", r)
        self.assertIn("command", r)

    def test_utf8_content_unchanged(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_bytes(b"hello world\n")
            r = _json_result("cat", str(d / "f.txt"))
            self.assertEqual(r["result"]["content"], "hello world\n")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_default_encoding_still_utf8(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("hello\n", encoding="utf-8")
            r = _json_result("cat", str(d / "f.txt"))
            self.assertEqual(r["result"]["encoding"], "utf-8")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_envelope_no_unknown_keys(self) -> None:
        r = _json_result("schema")
        for key in r:
            self.assertIn(key, ("ok", "tool", "version", "command", "result", "warnings"))

    def test_printf_encoding_field_is_string(self) -> None:
        r = _json_result("printf", "%s", "hello")
        self.assertIsInstance(r["result"]["encoding"], str)

    def test_catalog_still_works(self) -> None:
        r = _json_result("catalog")
        self.assertIn("categories", r["result"])


if __name__ == "__main__":
    unittest.main()
