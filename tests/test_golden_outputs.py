from __future__ import annotations

import json
import unittest

from support import ROOT, run_cli


class GoldenOutputTests(unittest.TestCase):
    def assert_matches_golden(self, golden_name: str, result_stdout: str) -> None:
        expected = json.loads((ROOT / "tests" / "golden" / golden_name).read_text(encoding="utf-8"))
        actual = json.loads(result_stdout)
        self.assertEqual(actual, expected)

    def test_seq_output_matches_golden_file(self) -> None:
        result = run_cli("seq", "1", "2", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("seq_1_2_5.json", result.stdout)

    def test_base64_stdin_output_matches_golden_file(self) -> None:
        result = run_cli("base64", input_text="hello")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("base64_hello.json", result.stdout)

    def test_stat_output_matches_golden_file(self) -> None:
        result = run_cli("stat", "docs/README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("stat_readme.json", result.stdout)

    def test_wc_output_matches_golden_file(self) -> None:
        result = run_cli("wc", "tests/golden/base64_hello.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("wc_counts.json", result.stdout)

    def test_cp_dry_run_does_not_create_files(self) -> None:
        result = run_cli("cp", "tests/golden/base64_hello.json", "tests/golden/_copy_target.json", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("cp_dryrun.json", result.stdout)


if __name__ == "__main__":
    unittest.main()
