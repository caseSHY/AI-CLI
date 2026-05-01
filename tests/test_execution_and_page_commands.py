from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class ExecutionAndPageCommandsTests(unittest.TestCase):
    def test_timeout_captures_output_and_reports_timeout(self) -> None:
        payload = parse_stdout(run_cli("timeout", "5", "--", sys.executable, "-c", "print('ok')"))
        self.assertEqual(payload["result"]["returncode"], 0)
        stdout = base64.b64decode(payload["result"]["stdout_base64"]).decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(stdout, "ok\n")

        timed_out = run_cli("timeout", "0.1", sys.executable, "-c", "import time; time.sleep(2)")
        self.assertEqual(timed_out.returncode, 8)
        self.assertTrue(json.loads(timed_out.stdout)["result"]["timed_out"])

    def test_nice_kill_nohup_and_bracket_safe_modes(self) -> None:
        nice = parse_stdout(run_cli("nice", "--dry-run", "--", sys.executable, "-c", "print('ok')"))
        self.assertTrue(nice["result"]["dry_run"])

        kill = parse_stdout(run_cli("kill", "12345", "--signal", "TERM", "--dry-run"))
        self.assertEqual(kill["result"]["operations"][0]["signal"], 15)

        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            nohup = parse_stdout(
                run_cli("nohup", "--output", "out.log", "--dry-run", "--", sys.executable, "-c", "print('ok')", cwd=cwd)
            )
            self.assertEqual(nohup["result"]["operation"]["output"], str((cwd / "out.log").resolve()))
            self.assertFalse((cwd / "out.log").exists())

            target = cwd / "file.txt"
            target.write_text("x", encoding="utf-8")
            bracket = run_cli("[", "--exit-code", "-f", "file.txt", "]", cwd=cwd)
            self.assertEqual(bracket.returncode, 0, bracket.stderr)
            self.assertTrue(json.loads(bracket.stdout)["result"]["matches"])

    def test_csplit_pr_and_ptx(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            source = cwd / "doc.txt"
            source.write_text("alpha\n--\nbeta\n--\ngamma\n", encoding="utf-8")

            dry = parse_stdout(run_cli("csplit", "doc.txt", "--pattern", "^--$", "--dry-run", cwd=cwd))
            self.assertEqual(dry["result"]["chunks"], 3)
            self.assertFalse((cwd / "xx00").exists())

            written = parse_stdout(run_cli("csplit", "doc.txt", "--pattern", "^--$", "--prefix", "part-", cwd=cwd))
            self.assertEqual(written["result"]["chunks"], 3)
            self.assertTrue((cwd / "part-00").exists())

        paged = run_cli("pr", "--page-length", "2", "--header", "Report", "--raw", input_text="one\ntwo\nthree\n")
        self.assertEqual(paged.returncode, 0, paged.stderr)
        self.assertIn("Report  Page 1", paged.stdout)
        self.assertIn("Report  Page 2", paged.stdout)

        index = parse_stdout(
            run_cli("ptx", "--ignore-case", "--only", "beta", input_text="alpha beta gamma\nbeta delta\n")
        )
        self.assertEqual(index["result"]["total_records"], 2)
        self.assertEqual(index["result"]["records"][0]["keyword"].lower(), "beta")


if __name__ == "__main__":
    unittest.main()
