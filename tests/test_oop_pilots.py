"""Golden tests: verify pilot OOP commands produce identical output to pre-refactor behavior.

Each test runs the CLI subcommand and asserts specific JSON result fields and values.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest


def _cli_json(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "aicoreutils", *args],
        capture_output=True,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    return json.loads(result.stdout.decode("utf-8", errors="replace"))


def _cli_raw(*args: str) -> bytes:
    result = subprocess.run(
        [sys.executable, "-m", "aicoreutils", *args],
        capture_output=True,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    return result.stdout


class TestEchoPilot(unittest.TestCase):
    def test_plain(self) -> None:
        r = _cli_json("echo", "hello")
        self.assertEqual(r["result"]["text"], "hello")
        self.assertTrue(r["result"]["newline"])
        self.assertFalse(r["result"]["escapes"])
        self.assertEqual(r["result"]["encoding"], "utf-8")

    def test_no_newline(self) -> None:
        r = _cli_json("echo", "-n", "test")
        self.assertFalse(r["result"]["newline"])

    def test_escapes(self) -> None:
        r = _cli_json("echo", "-e", "hello\\nworld")
        self.assertTrue(r["result"]["escapes"])
        self.assertIn("\n", r["result"]["text"])

    def test_raw_output(self) -> None:
        raw = _cli_raw("echo", "--raw", "hello")
        self.assertEqual(raw, b"hello\n")

    def test_raw_no_newline(self) -> None:
        raw = _cli_raw("echo", "--raw", "-n", "hello")
        self.assertEqual(raw, b"hello")

    def test_empty(self) -> None:
        r = _cli_json("echo")
        self.assertEqual(r["result"]["text"], "")


class TestTacPilot(unittest.TestCase):
    def test_reverses_lines(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            r = _cli_json("tac", str(d / "f.txt"))
            self.assertEqual(r["result"]["lines"], ["c", "b", "a"])
            self.assertEqual(r["result"]["source_paths"], [str((d / "f.txt").resolve())])
            self.assertEqual(r["result"]["returned_lines"], 3)
            self.assertFalse(r["result"]["truncated"])
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_raw_output(self) -> None:
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("1\n2\n3\n", encoding="utf-8")
            raw = _cli_raw("tac", "--raw", str(d / "f.txt"))
            self.assertEqual(raw, b"3\n2\n1\n")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


class TestTouchPilot(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        from pathlib import Path

        self._tmp = Path(tempfile.mkdtemp(dir=Path.cwd()))

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_creates_file(self) -> None:
        f = self._tmp / "new.txt"
        r = _cli_json("touch", str(f))
        self.assertEqual(r["result"]["count"], 1)
        self.assertEqual(r["result"]["operations"][0]["operation"], "touch")
        self.assertTrue(r["result"]["operations"][0]["created"])
        self.assertTrue(f.exists())

    def test_dry_run(self) -> None:
        f = self._tmp / "dry.txt"
        r = _cli_json("touch", "--dry-run", str(f))
        self.assertTrue(r["result"]["operations"][0]["dry_run"])
        self.assertFalse(f.exists())

    def test_existing_file(self) -> None:
        f = self._tmp / "existing.txt"
        f.touch()
        r = _cli_json("touch", str(f))
        self.assertFalse(r["result"]["operations"][0]["created"])

    def test_with_parents(self) -> None:
        f = self._tmp / "subdir" / "file.txt"
        _cli_json("touch", "--parents", str(f))
        self.assertTrue(f.exists())
        self.assertTrue(f.parent.exists())


if __name__ == "__main__":
    unittest.main()
