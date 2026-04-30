from __future__ import annotations

import base64
import json
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from support import parse_stdout, run_cli


class CliBlackBoxTests(unittest.TestCase):
    def test_cli_success_stdout_is_json_and_stderr_is_empty(self) -> None:
        result = run_cli("schema")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("implemented_commands", payload["result"])

    def test_pretty_flag_works_after_subcommand(self) -> None:
        result = run_cli("schema", "--pretty")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertTrue(result.stdout.replace("\r\n", "\n").startswith("{\n  "))

    def test_pretty_flag_is_preserved_for_remainder_commands(self) -> None:
        result = run_cli(
            "timeout",
            "5",
            "--",
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1])",
            "--pretty",
        )
        payload = parse_stdout(result)
        stdout = base64.b64decode(payload["result"]["stdout_base64"]).decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(stdout, "--pretty\n")

    def test_raw_output_opt_in_removes_json_envelope(self) -> None:
        result = run_cli("sort", "--raw", input_text="b\na\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "a\nb\n")

    def test_cli_reads_relative_paths_from_cwd(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "note.txt").write_bytes(b"hello\n")
            payload = parse_stdout(run_cli("cat", "note.txt", cwd=cwd))
            self.assertEqual(payload["result"]["content"], "hello\n")


if __name__ == "__main__":
    unittest.main()
