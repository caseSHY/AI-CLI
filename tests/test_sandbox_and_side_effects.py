from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class SandboxAndSideEffectTests(unittest.TestCase):
    def test_recursive_rm_outside_cwd_is_blocked(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sandbox = root / "sandbox"
            outside = root / "outside"
            sandbox.mkdir()
            outside.mkdir()
            (outside / "keep.txt").write_text("keep", encoding="utf-8")

            result = run_cli("rm", str(outside), "--recursive", cwd=sandbox)

            self.assertEqual(result.returncode, 8)
            self.assertEqual(result.stdout, "")
            payload = json.loads(result.stderr)
            self.assertEqual(payload["error"]["code"], "unsafe_operation")
            self.assertTrue((outside / "keep.txt").exists())

    def test_dry_run_does_not_create_or_delete_files(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "created.txt"
            parse_stdout(run_cli("touch", "created.txt", "--dry-run", cwd=cwd))
            self.assertFalse(target.exists())

            existing = cwd / "existing.txt"
            existing.write_text("data", encoding="utf-8")
            parse_stdout(run_cli("rm", "existing.txt", "--dry-run", cwd=cwd))
            self.assertEqual(existing.read_text(encoding="utf-8"), "data")

    def test_write_commands_have_expected_side_effects(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            payload = parse_stdout(run_cli("tee", "out.txt", cwd=cwd, input_text="abc"))
            self.assertEqual(payload["result"]["input_bytes"], 3)
            self.assertEqual((cwd / "out.txt").read_text(encoding="utf-8"), "abc")

            parse_stdout(run_cli("truncate", "out.txt", "--size", "1", cwd=cwd))
            self.assertEqual((cwd / "out.txt").read_text(encoding="utf-8"), "a")


if __name__ == "__main__":
    unittest.main()
