from __future__ import annotations

import json
import unittest
from typing import Any

from support import ROOT, run_cli


def _normalize_output(obj: Any) -> Any:
    """Normalize platform-dependent values (paths, timestamps) in JSON output."""
    root_str = str(ROOT).replace("\\", "/")
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            # Skip timestamp fields (platform-dependent)
            if key.endswith("_at"):
                result[key] = "{{TIMESTAMP}}"
            elif isinstance(value, str):
                # Normalize absolute paths to {{ROOT}}/relative
                normalized = value.replace("\\", "/")
                if normalized.startswith(root_str):
                    result[key] = "{{ROOT}}" + normalized[len(root_str) :]
                else:
                    result[key] = value
            else:
                result[key] = _normalize_output(value)
        return result
    elif isinstance(obj, list):
        return [_normalize_output(item) for item in obj]
    elif isinstance(obj, str):
        normalized = obj.replace("\\", "/")
        if normalized.startswith(root_str):
            return "{{ROOT}}" + normalized[len(root_str) :]
        return obj
    return obj


class GoldenOutputTests(unittest.TestCase):
    def assert_matches_golden(self, golden_name: str, result_stdout: str) -> None:
        expected = json.loads((ROOT / "project" / "tests" / "golden" / golden_name).read_text(encoding="utf-8"))
        actual = json.loads(result_stdout)
        self.assertEqual(_normalize_output(actual), _normalize_output(expected))

    def test_seq_output_matches_golden_file(self) -> None:
        result = run_cli("seq", "1", "2", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("seq_1_2_5.json", result.stdout)

    def test_base64_stdin_output_matches_golden_file(self) -> None:
        result = run_cli("base64", input_text="hello")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("base64_hello.json", result.stdout)

    def test_stat_output_matches_golden_file(self) -> None:
        result = run_cli("stat", "project/docs/README.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("stat_readme.json", result.stdout)

    def test_wc_output_matches_golden_file(self) -> None:
        result = run_cli("wc", "project/tests/golden/base64_hello.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("wc_counts.json", result.stdout)

    def test_cp_dry_run_does_not_create_files(self) -> None:
        result = run_cli(
            "cp", "project/tests/golden/base64_hello.json", "project/tests/golden/_copy_target.json", "--dry-run"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_matches_golden("cp_dryrun.json", result.stdout)


if __name__ == "__main__":
    unittest.main()
