from __future__ import annotations

import json
import os
import unittest
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class MoreAgentCommandsTests(unittest.TestCase):
    def test_echo_and_printf_raw_output(self) -> None:
        echo = run_cli("echo", "hello", "agent", "--raw")
        self.assertEqual(echo.returncode, 0, echo.stderr)
        self.assertEqual(echo.stdout, "hello agent\n")

        printf = run_cli("printf", "row:%s:%03d\\n", "alpha", "7", "--raw")
        self.assertEqual(printf.returncode, 0, printf.stderr)
        self.assertEqual(printf.stdout, "row:alpha:007\n")

        bad = run_cli("printf", "%d", "not-a-number")
        self.assertEqual(bad.returncode, 5)
        self.assertEqual(json.loads(bad.stderr)["error"]["code"], "invalid_input")

    def test_comm_join_and_paste(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "left.txt").write_text("a\nb\nc\n", encoding="utf-8")
            (cwd / "right.txt").write_text("b\nd\n", encoding="utf-8")

            comm = parse_stdout(run_cli("comm", "left.txt", "right.txt", cwd=cwd))
            self.assertEqual(comm["result"]["counts"], {"common": 1, "only_first": 2, "only_second": 1})

            (cwd / "people.txt").write_text("1 Alice\n2 Bob\n", encoding="utf-8")
            (cwd / "roles.txt").write_text("1 Dev\n2 Ops\n", encoding="utf-8")
            joined = run_cli("join", "people.txt", "roles.txt", "--raw", cwd=cwd)
            self.assertEqual(joined.returncode, 0, joined.stderr)
            self.assertEqual(joined.stdout, "1 Alice Dev\n2 Bob Ops\n")

            pasted = run_cli("paste", "people.txt", "roles.txt", "--delimiter", "|", "--raw", cwd=cwd)
            self.assertEqual(pasted.returncode, 0, pasted.stderr)
            self.assertEqual(pasted.stdout.splitlines()[0], "1 Alice|1 Dev")

    def test_shuf_tac_expand_and_unexpand(self) -> None:
        first = run_cli("shuf", "--seed", "11", "--raw", input_text="a\nb\nc\nd\n")
        second = run_cli("shuf", "--seed", "11", "--raw", input_text="a\nb\nc\nd\n")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(sorted(first.stdout.splitlines()), ["a", "b", "c", "d"])

        tac = run_cli("tac", "--raw", input_text="one\ntwo\nthree\n")
        self.assertEqual(tac.returncode, 0, tac.stderr)
        self.assertEqual(tac.stdout, "three\ntwo\none\n")

        expanded = run_cli("expand", "--tabs", "4", "--raw", input_text="a\tb\n")
        self.assertEqual(expanded.returncode, 0, expanded.stderr)
        self.assertEqual(expanded.stdout, "a   b\n")

        unexpanded = run_cli("unexpand", "--tabs", "4", "--raw", input_text="    value\n")
        self.assertEqual(unexpanded.returncode, 0, unexpanded.stderr)
        self.assertEqual(unexpanded.stdout, "\tvalue\n")

    def test_cksum_sum_groups_link_and_mkfifo(self) -> None:
        cksum = parse_stdout(run_cli("cksum", input_text="abc"))
        self.assertEqual(cksum["result"]["entries"][0]["checksum"], zlib.crc32(b"abc") & 0xFFFFFFFF)

        byte_sum = parse_stdout(run_cli("sum", "--block-size", "2", input_text="abc"))
        self.assertEqual(byte_sum["result"]["entries"][0]["checksum"], sum(b"abc") & 0xFFFF)
        self.assertEqual(byte_sum["result"]["entries"][0]["blocks"], 2)

        groups = parse_stdout(run_cli("groups"))
        self.assertIn("groups", groups["result"])

        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            source = cwd / "source.txt"
            source.write_text("payload", encoding="utf-8")
            link = parse_stdout(run_cli("link", "source.txt", "hard.txt", cwd=cwd))
            self.assertFalse(link["result"]["operations"][0]["dry_run"])
            self.assertEqual((cwd / "hard.txt").read_text(encoding="utf-8"), "payload")
            if hasattr(os, "stat"):
                self.assertTrue((cwd / "hard.txt").exists())

            fifo = parse_stdout(run_cli("mkfifo", "pipe", "--dry-run", cwd=cwd))
            self.assertTrue(fifo["result"]["operations"][0]["dry_run"])
            self.assertFalse((cwd / "pipe").exists())


if __name__ == "__main__":
    unittest.main()
