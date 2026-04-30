from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class AgentCallFlowTests(unittest.TestCase):
    def test_agent_can_observe_decide_and_mutate_with_json(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "input.txt").write_text("beta\nalpha\n", encoding="utf-8")

            listing = parse_stdout(run_cli("ls", ".", cwd=cwd))
            names = {entry["name"] for entry in listing["result"]["entries"]}
            self.assertIn("input.txt", names)

            sorted_raw = run_cli("sort", "input.txt", "--raw", cwd=cwd)
            self.assertEqual(sorted_raw.stdout, "alpha\nbeta\n")

            dry_run = parse_stdout(run_cli("tee", "sorted.txt", "--dry-run", cwd=cwd, input_text=sorted_raw.stdout))
            self.assertTrue(dry_run["result"]["operations"][0]["dry_run"])
            self.assertFalse((cwd / "sorted.txt").exists())

            parse_stdout(run_cli("tee", "sorted.txt", cwd=cwd, input_text=sorted_raw.stdout))
            test_result = parse_stdout(run_cli("test", "sorted.txt", "--file", "--non-empty", cwd=cwd))
            self.assertTrue(test_result["result"]["matches"])

            checksum = parse_stdout(run_cli("sha256sum", "sorted.txt", cwd=cwd))
            self.assertEqual(len(checksum["result"]["entries"][0]["digest"]), 64)


if __name__ == "__main__":
    unittest.main()
