from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class SystemAliasAndEncodingCommandsTests(unittest.TestCase):
    def test_dir_and_vdir_alias_ls(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "b.txt").write_text("b", encoding="utf-8")
            (cwd / "a.txt").write_text("a", encoding="utf-8")

            directory = parse_stdout(run_cli("dir", ".", cwd=cwd))
            self.assertEqual(directory["result"]["alias"], "dir")
            self.assertEqual([entry["name"] for entry in directory["result"]["entries"]], ["a.txt", "b.txt"])

            verbose = parse_stdout(run_cli("vdir", ".", cwd=cwd))
            self.assertEqual(verbose["result"]["alias"], "vdir")
            self.assertTrue(verbose["result"]["verbose"])

    def test_basenc_and_tsort_raw_output(self) -> None:
        encoded = run_cli("basenc", "--base", "base16", "--raw", input_text="hello")
        self.assertEqual(encoded.returncode, 0, encoded.stderr)
        self.assertEqual(encoded.stdout, "68656C6C6F")

        decoded = run_cli("basenc", "--base", "base64url", "--decode", "--raw", input_text="aGVsbG8")
        self.assertEqual(decoded.returncode, 0, decoded.stderr)
        self.assertEqual(decoded.stdout, "hello")

        sorted_nodes = run_cli("tsort", "--raw", input_text="a b\nb c\n")
        self.assertEqual(sorted_nodes.returncode, 0, sorted_nodes.stderr)
        self.assertEqual(sorted_nodes.stdout, "a\nb\nc\n")

        cycle = run_cli("tsort", input_text="a b\nb a\n")
        self.assertEqual(cycle.returncode, 6)
        self.assertEqual(json.loads(cycle.stderr)["error"]["code"], "conflict")

    def test_system_context_commands(self) -> None:
        for command in ("arch", "hostname", "hostid", "logname", "uptime", "users", "who"):
            payload = parse_stdout(run_cli(command))
            self.assertTrue(payload["ok"], command)

        hostid = run_cli("hostid", "--raw")
        self.assertEqual(hostid.returncode, 0, hostid.stderr)
        self.assertRegex(hostid.stdout.strip(), r"^[0-9a-f]{8}$")

        uptime = parse_stdout(run_cli("uptime"))
        self.assertGreaterEqual(uptime["result"]["uptime_seconds"], 0)

        tty = run_cli("tty", "--exit-code")
        tty_payload = json.loads(tty.stdout)
        self.assertIn("stdin_is_tty", tty_payload["result"])
        self.assertEqual(tty.returncode, 0 if tty_payload["result"]["stdin_is_tty"] else 1)

        arch = run_cli("arch", "--raw")
        self.assertEqual(arch.returncode, 0, arch.stderr)
        self.assertTrue(re.search(r"\S", arch.stdout))


if __name__ == "__main__":
    unittest.main()
