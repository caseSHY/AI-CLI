from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class FileAdminCommandsTests(unittest.TestCase):
    def test_chown_chgrp_mknod_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "target.txt"
            target.write_text("data", encoding="utf-8")

            chown = parse_stdout(run_cli("chown", "0:0", "target.txt", "--dry-run", cwd=cwd))
            self.assertEqual(chown["result"]["operations"][0]["uid"], 0)
            self.assertTrue(chown["result"]["operations"][0]["dry_run"])

            chgrp = parse_stdout(run_cli("chgrp", "0", "target.txt", "--dry-run", cwd=cwd))
            self.assertEqual(chgrp["result"]["operations"][0]["gid"], 0)

            node = parse_stdout(run_cli("mknod", "placeholder", "--type", "regular", "--dry-run", cwd=cwd))
            self.assertEqual(node["result"]["operations"][0]["type"], "regular")
            self.assertFalse((cwd / "placeholder").exists())

    def test_dd_install_sync_and_dircolors(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            source = cwd / "source.txt"
            source.write_text("abcdef", encoding="utf-8")

            copied = parse_stdout(
                run_cli("dd", "--input", "source.txt", "--output", "copy.bin", "--bs", "2", "--count", "2", cwd=cwd)
            )
            self.assertEqual(copied["result"]["copied_bytes"], 4)
            self.assertEqual((cwd / "copy.bin").read_text(encoding="utf-8"), "abcd")

            conflict = run_cli("dd", "--input", "source.txt", "--output", "copy.bin", cwd=cwd)
            self.assertEqual(conflict.returncode, 6)
            self.assertEqual(json.loads(conflict.stderr)["error"]["code"], "conflict")

            installed = parse_stdout(run_cli("install", "source.txt", "bin/tool.txt", "--parents", "--mode", "600", cwd=cwd))
            self.assertEqual(installed["result"]["operations"][0]["mode_octal"], "0o600")
            self.assertEqual((cwd / "bin" / "tool.txt").read_text(encoding="utf-8"), "abcdef")

            made_dir = parse_stdout(run_cli("ginstall", "--directory", "created/dir", "--dry-run", cwd=cwd))
            self.assertTrue(made_dir["result"]["operations"][0]["directory"])
            self.assertFalse((cwd / "created" / "dir").exists())

            colors = run_cli("dircolors", "--raw")
            self.assertEqual(colors.returncode, 0, colors.stderr)
            self.assertIn("LS_COLORS", colors.stdout)

            sync = parse_stdout(run_cli("sync", "--dry-run"))
            self.assertTrue(sync["result"]["dry_run"])

    def test_shred_requires_explicit_confirmation(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "secret.txt"
            target.write_text("secret", encoding="utf-8")

            dry = parse_stdout(run_cli("shred", "secret.txt", "--dry-run", cwd=cwd))
            self.assertTrue(dry["result"]["operations"][0]["dry_run"])
            self.assertEqual(target.read_text(encoding="utf-8"), "secret")

            refused = run_cli("shred", "secret.txt", cwd=cwd)
            self.assertEqual(refused.returncode, 8)
            self.assertEqual(json.loads(refused.stderr)["error"]["code"], "unsafe_operation")
            self.assertEqual(target.read_text(encoding="utf-8"), "secret")


if __name__ == "__main__":
    unittest.main()
