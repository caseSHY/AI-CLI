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


class TestPhase1ImportsStillWork(unittest.TestCase):
    """Phase 1 command_* functions still importable and callable."""

    def test_import_command_coreutils(self) -> None:
        from aicoreutils.commands.system import command_coreutils

        self.assertTrue(callable(command_coreutils))

    def test_import_command_pinky(self) -> None:
        from aicoreutils.commands.system import command_pinky

        self.assertTrue(callable(command_pinky))

    def test_import_command_hash(self) -> None:
        from aicoreutils.commands.fs import command_hash

        self.assertTrue(callable(command_hash))

    def test_import_command_install(self) -> None:
        from aicoreutils.commands.fs import command_install

        self.assertTrue(callable(command_install))

    def test_import_command_dir(self) -> None:
        from aicoreutils.commands.fs import command_dir

        self.assertTrue(callable(command_dir))

    def test_import_command_vdir(self) -> None:
        from aicoreutils.commands.fs import command_vdir

        self.assertTrue(callable(command_vdir))


class TestPhase2ImportsStillWork(unittest.TestCase):
    """Phase 2 command_* functions still importable and callable."""

    def test_import_command_cp(self) -> None:
        from aicoreutils.commands.fs import command_cp

        self.assertTrue(callable(command_cp))

    def test_import_command_mv(self) -> None:
        from aicoreutils.commands.fs import command_mv

        self.assertTrue(callable(command_mv))

    def test_import_command_ln(self) -> None:
        from aicoreutils.commands.fs import command_ln

        self.assertTrue(callable(command_ln))

    def test_import_command_link(self) -> None:
        from aicoreutils.commands.fs import command_link

        self.assertTrue(callable(command_link))

    def test_import_command_chown(self) -> None:
        from aicoreutils.commands.fs import command_chown

        self.assertTrue(callable(command_chown))

    def test_import_command_chgrp(self) -> None:
        from aicoreutils.commands.fs import command_chgrp

        self.assertTrue(callable(command_chgrp))

    def test_import_command_kill(self) -> None:
        from aicoreutils.commands.system import command_kill

        self.assertTrue(callable(command_kill))


class TestExitCodePassthrough(unittest.TestCase):
    """CommandResult.exit_code flows through BaseCommand.__call__ into the result dict."""

    def test_exit_code_zero_is_absent(self) -> None:
        import argparse

        from aicoreutils.commands.system import command_true

        ns = argparse.Namespace()
        result = command_true(ns)
        self.assertIsInstance(result, dict)
        self.assertNotIn("_exit_code", result)

    def test_exit_code_nonzero_included(self) -> None:
        import argparse

        from aicoreutils.commands.system import command_false

        ns = argparse.Namespace()
        result = command_false(ns)
        self.assertIsInstance(result, dict)
        self.assertIn("_exit_code", result)
        self.assertGreater(result["_exit_code"], 0)


class TestEncodingMetaPassthrough(unittest.TestCase):
    """--show-encoding metadata flows through CommandResult into the JSON output."""

    def test_cat_show_encoding(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            (d / "f.txt").write_text("hello", encoding="utf-8")
            stdout = _cli("cat", "--show-encoding", str(d / "f.txt"))
            data = json.loads(stdout)
            self.assertIn("encoding_meta", data["result"])
            self.assertEqual(data["result"]["encoding_meta"]["declared"], "utf-8")
            self.assertIn("detected", data["result"]["encoding_meta"])
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)

    def test_cat_no_show_encoding_omits_meta(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            (d / "f.txt").write_text("hello", encoding="utf-8")
            stdout = _cli("cat", str(d / "f.txt"))
            data = json.loads(stdout)
            self.assertNotIn("encoding_meta", data["result"])
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)


class TestPhase1CliShape(unittest.TestCase):
    """Phase 1 commands produce correct JSON envelope shapes."""

    def test_coreutils_shape(self) -> None:
        import json

        stdout = _cli("coreutils")
        data = json.loads(stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "coreutils")
        self.assertIn("commands", data["result"])
        self.assertIn("count", data["result"])

    def test_hash_shape(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            (d / "data.bin").write_bytes(b"test")
            stdout = _cli("hash", "--algorithm", "sha256", str(d / "data.bin"))
            data = json.loads(stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["command"], "hash")
            self.assertEqual(data["result"]["count"], 1)
            self.assertIn("digest", data["result"]["entries"][0])
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)

    def test_install_dir_shape(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            target = d / "test-install-dir"
            stdout = _cli("install", "--dry-run", "--directory", str(target))
            data = json.loads(stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["command"], "install")
            self.assertEqual(data["result"]["operations"][0]["directory"], True)
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)


class TestPhase2CliShape(unittest.TestCase):
    """Phase 2 commands produce correct JSON envelope shapes."""

    def test_cp_shape(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            src = d / "src.txt"
            src.write_text("test")
            stdout = _cli("cp", "--dry-run", str(src), str(d / "dest.txt"))
            data = json.loads(stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["command"], "cp")
            self.assertEqual(data["result"]["operations"][0]["operation"], "cp")
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)

    def test_mv_shape(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        d = Path(tempfile.mkdtemp(dir=Path.cwd()))
        try:
            src = d / "src.txt"
            src.write_text("test")
            stdout = _cli("mv", "--dry-run", str(src), str(d / "dest.txt"))
            data = json.loads(stdout)
            self.assertTrue(data["ok"])
            self.assertEqual(data["command"], "mv")
            self.assertEqual(data["result"]["operations"][0]["operation"], "mv")
        finally:
            import shutil

            shutil.rmtree(d, ignore_errors=True)

    def test_kill_shape(self) -> None:
        import json

        stdout = _cli("kill", "--dry-run", "--signal", "TERM", "1234")
        data = json.loads(stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["command"], "kill")
        self.assertEqual(data["result"]["count"], 1)
        self.assertEqual(data["result"]["operations"][0]["pid"], 1234)
        self.assertEqual(data["result"]["operations"][0]["signal"], 15)


if __name__ == "__main__":
    unittest.main()
