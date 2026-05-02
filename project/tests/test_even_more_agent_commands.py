from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class EvenMoreAgentCommandsTests(unittest.TestCase):
    def test_nl_fold_and_fmt_raw_output(self) -> None:
        numbered = run_cli("nl", "--raw", "--width", "2", input_text="alpha\n\nbeta\n")
        self.assertEqual(numbered.returncode, 0, numbered.stderr)
        self.assertEqual(numbered.stdout, " 1\talpha\n\n 2\tbeta\n")

        folded = run_cli("fold", "--width", "5", "--break-words", "--raw", input_text="abcdefghij\n")
        self.assertEqual(folded.returncode, 0, folded.stderr)
        self.assertEqual(folded.stdout, "abcde\nfghij\n")

        formatted = run_cli("fmt", "--width", "12", "--raw", input_text="alpha beta gamma\n\ndelta epsilon\n")
        self.assertEqual(formatted.returncode, 0, formatted.stderr)
        self.assertEqual(formatted.stdout, "alpha beta\ngamma\n\ndelta\nepsilon\n")

    def test_split_dry_run_and_real_outputs(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            source = cwd / "rows.txt"
            source.write_text("a\nb\nc\n", encoding="utf-8")

            dry = parse_stdout(run_cli("split", "rows.txt", "--lines", "2", "--prefix", "part-", "--dry-run", cwd=cwd))
            self.assertEqual(dry["result"]["chunks"], 2)
            self.assertFalse((cwd / "part-aa").exists())

            payload = parse_stdout(run_cli("split", "rows.txt", "--lines", "2", "--prefix", "part-", cwd=cwd))
            self.assertEqual(payload["result"]["chunks"], 2)
            self.assertEqual((cwd / "part-aa").read_text(encoding="utf-8"), "a\nb\n")
            self.assertEqual((cwd / "part-ab").read_text(encoding="utf-8"), "c\n")

            conflict = run_cli("split", "rows.txt", "--lines", "2", "--prefix", "part-", cwd=cwd)
            self.assertEqual(conflict.returncode, 6)
            self.assertEqual(json.loads(conflict.stderr)["error"]["code"], "conflict")

    def test_od_numfmt_factor_expr_and_pathchk(self) -> None:
        dump = run_cli("od", "--format", "hex", "--max-bytes", "3", "--raw", input_text="ABCDEF")
        self.assertEqual(dump.returncode, 0, dump.stderr)
        self.assertEqual(dump.stdout, "000000 41 42 43\n")

        numfmt = run_cli("numfmt", "1536", "--to-unit", "iec", "--precision", "1", "--raw")
        self.assertEqual(numfmt.returncode, 0, numfmt.stderr)
        self.assertEqual(numfmt.stdout, "1.5Ki\n")

        factor = run_cli("factor", "84", "--raw")
        self.assertEqual(factor.returncode, 0, factor.stderr)
        self.assertEqual(factor.stdout, "84: 2 2 3 7\n")

        expr = parse_stdout(run_cli("expr", "3", ">", "2"))
        self.assertTrue(expr["result"]["value"])

        bad_expr = run_cli("expr", "'a'", "-", "1")
        self.assertEqual(bad_expr.returncode, 5)
        self.assertEqual(json.loads(bad_expr.stderr)["error"]["code"], "invalid_input")

        invalid_path = run_cli("pathchk", "bad name", "--portable", "--exit-code")
        self.assertEqual(invalid_path.returncode, 1)
        self.assertFalse(json.loads(invalid_path.stdout)["result"]["valid"])


if __name__ == "__main__":
    unittest.main()
