"""Backward-compatibility tests: old function entries still work, old imports still resolve."""

from __future__ import annotations

import subprocess
import sys
import unittest


def _cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "aicoreutils", *args],
        capture_output=True,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    return result.stdout.decode("utf-8", errors="replace")


class TestOldImportsStillWork(unittest.TestCase):
    def test_import_command_echo(self) -> None:
        from aicoreutils.commands.text import command_echo

        self.assertTrue(callable(command_echo))

    def test_import_command_tac(self) -> None:
        from aicoreutils.commands.text import command_tac

        self.assertTrue(callable(command_tac))

    def test_import_command_touch(self) -> None:
        from aicoreutils.commands.fs import command_touch

        self.assertTrue(callable(command_touch))


class TestOldFunctionEntryPoints(unittest.TestCase):
    """Verify the old command_* functions still work as callable entry points."""

    def test_command_echo_dict(self) -> None:
        import argparse

        from aicoreutils.commands.text import command_echo

        ns = argparse.Namespace(words=["hello"], escapes=False, no_newline=False, encoding="utf-8", raw=False)
        result = command_echo(ns)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["text"], "hello")
        self.assertEqual(result["encoding"], "utf-8")

    def test_command_echo_raw(self) -> None:
        import argparse

        from aicoreutils.commands.text import command_echo

        ns = argparse.Namespace(words=["hello"], escapes=False, no_newline=False, encoding="utf-8", raw=True)
        result = command_echo(ns)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b"hello\n")

    def test_command_tac_dict(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path

        from aicoreutils.commands.text import command_tac

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("c\nb\na\n", encoding="utf-8")
            ns = argparse.Namespace(paths=[str(d / "f.txt")], encoding="utf-8", raw=False, max_lines=10000)
            result = command_tac(ns)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["lines"], ["a", "b", "c"])
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_command_tac_raw(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path

        from aicoreutils.commands.text import command_tac

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("c\nb\na\n", encoding="utf-8")
            ns = argparse.Namespace(paths=[str(d / "f.txt")], encoding="utf-8", raw=True, max_lines=10000)
            result = command_tac(ns)
            self.assertIsInstance(result, bytes)
            self.assertEqual(result, b"a\nb\nc\n")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_command_touch_dict(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path

        from aicoreutils.commands.fs import command_touch

        d = Path(tempfile.mkdtemp())
        try:
            f = d / "test.txt"
            ns = argparse.Namespace(paths=[str(f)], parents=False, dry_run=False, allow_outside_cwd=True)
            result = command_touch(ns)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["operations"][0]["operation"], "touch")
            self.assertTrue(f.exists())
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)

    def test_command_touch_dry_run(self) -> None:
        import argparse
        import tempfile
        from pathlib import Path

        from aicoreutils.commands.fs import command_touch

        d = Path(tempfile.mkdtemp())
        try:
            f = d / "no_create.txt"
            ns = argparse.Namespace(paths=[str(f)], parents=False, dry_run=True, allow_outside_cwd=True)
            result = command_touch(ns)
            self.assertEqual(result["operations"][0]["dry_run"], True)
            self.assertFalse(f.exists())
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)


class TestCliBehaviorUnchanged(unittest.TestCase):
    """Smoke tests verifying CLI JSON output shape unchanged after OOP refactoring."""

    def test_echo_json_shape(self) -> None:
        import json

        stdout = _cli("echo", "hello", "world")
        data = json.loads(stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "echo")
        self.assertEqual(data["result"]["text"], "hello world")
        self.assertIn("encoding", data["result"])
        self.assertFalse(data["result"]["escapes"])

    def test_tac_json_shape(self) -> None:
        import json

        stdout = _cli("tac")
        # stdin closed → empty input
        data = json.loads(stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "tac")
        self.assertIn("lines", data["result"])
        self.assertIn("source_paths", data["result"])

    def test_envelope_keys_unchanged(self) -> None:
        import json

        stdout = _cli("echo", "test")
        data = json.loads(stdout)
        for key in data:
            self.assertIn(key, ("ok", "tool", "version", "command", "result", "warnings"))


if __name__ == "__main__":
    unittest.main()
