from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import run_cli


class ErrorExitCodeTests(unittest.TestCase):
    def assert_error(self, result, exit_code: int, code: str) -> None:
        self.assertEqual(result.returncode, exit_code)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], code)

    def test_usage_error_is_json_exit_2(self) -> None:
        self.assert_error(run_cli("ls", "--bad-option"), 2, "usage")

    def test_not_found_is_json_exit_3(self) -> None:
        self.assert_error(run_cli("cat", "missing.txt"), 3, "not_found")

    def test_invalid_input_is_json_exit_5(self) -> None:
        self.assert_error(run_cli("cut", "--chars", "bad", input_text="abc\n"), 5, "invalid_input")

    def test_conflict_is_json_exit_6(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "existing").mkdir()
            self.assert_error(run_cli("mkdir", "existing", cwd=cwd), 6, "conflict")

    def test_unsafe_operation_is_json_exit_8(self) -> None:
        self.assert_error(run_cli("sleep", "1000", "--max-seconds", "1"), 8, "unsafe_operation")

    def test_false_uses_exit_1_but_success_envelope(self) -> None:
        result = run_cli("false")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["result"]["value"])


if __name__ == "__main__":
    unittest.main()
