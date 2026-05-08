from __future__ import annotations

import json
import re
import unittest
from typing import Any

from support import ROOT, run_cli

_PATH_PREFIX_RE = re.compile(
    r"^([A-Za-z]:[/\\])"  # Drive letter (Windows)
    r".*?[/\\]AI-CLI[/\\]"  # Up to repo root
)
_UNIX_PATH_PREFIX_RE = re.compile(
    r"^/"
    r".*?/AI-CLI/"  # Up to repo root
)


# Platform-dependent fields that should be normalized in golden comparisons
_NORMALIZE_FIELDS = frozenset({"size_bytes", "mode_octal", "version", "tool"})


def _normalize_output(obj: Any) -> Any:
    """Normalize platform-dependent values (paths, timestamps, file metadata) in JSON output."""

    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key.endswith("_at"):
                result[key] = "{{TIMESTAMP}}"
            elif key in _NORMALIZE_FIELDS:
                result[key] = "{{VARIES}}"
            elif isinstance(value, str):
                result[key] = _normalize_path(value)
            else:
                result[key] = _normalize_output(value)
        return result
    elif isinstance(obj, list):
        return [_normalize_output(item) for item in obj]
    elif isinstance(obj, str):
        return _normalize_path(obj)
    return obj


def _normalize_path(text: str) -> str:
    """Replace absolute path prefix up to project root with {{ROOT}}/."""
    normalized = text.replace("\\", "/")
    for pattern in (_PATH_PREFIX_RE, _UNIX_PATH_PREFIX_RE):
        m = pattern.match(normalized)
        if m:
            return "{{ROOT}}/" + normalized[m.end() :]
    return text


class GoldenOutputTests(unittest.TestCase):
    def assert_matches_golden(self, golden_name: str, result_stdout: str) -> None:
        expected = json.loads((ROOT / "tests" / "golden" / golden_name).read_text(encoding="utf-8"))
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
