"""Unit tests for commands/text/_core.py — via real parser for proper args."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aicoreutils.parser._parser import build_parser

_parser = build_parser()


class SortCommandTests(unittest.TestCase):
    def test_sort_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("c\na\nb\n", encoding="utf-8")
            args = _parser.parse_args(["sort", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["a", "b", "c"])

    def test_sort_reverse(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            args = _parser.parse_args(["sort", "--reverse", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["c", "b", "a"])

    def test_sort_unique(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\na\nb\n", encoding="utf-8")
            args = _parser.parse_args(["sort", "--unique", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["a", "b"])

    def test_sort_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("b\na\n", encoding="utf-8")
            args = _parser.parse_args(["sort", "--raw", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)


class UniqCommandTests(unittest.TestCase):
    def test_uniq_adjacent(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\na\nb\n", encoding="utf-8")
            args = _parser.parse_args(["uniq", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(len(result["records"]), 2)

    def test_uniq_count(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\na\nb\n", encoding="utf-8")
            args = _parser.parse_args(["uniq", "--count", str(root / "f.txt")])
            result = args.func(args)
            self.assertTrue(result["counted"])


class ShufCommandTests(unittest.TestCase):
    def test_shuf_line_count(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
            args = _parser.parse_args(["shuf", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(len(result["lines"]), 5)


class TacCommandTests(unittest.TestCase):
    def test_tac_reverses(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            args = _parser.parse_args(["tac", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["c", "b", "a"])


class CutCommandTests(unittest.TestCase):
    def test_cut_chars(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("abcdef\n", encoding="utf-8")
            args = _parser.parse_args(["cut", "--chars", "1-3", str(root / "f.txt")])
            result = args.func(args)
            self.assertIn("abc", result["lines"][0])

    def test_cut_fields(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\tb\tc\n", encoding="utf-8")
            args = _parser.parse_args(["cut", "--fields", "1,3", str(root / "f.txt")])
            result = args.func(args)
            self.assertIn("a\tc", result["lines"][0])


class TrCommandTests(unittest.TestCase):
    def test_tr_translate(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("abc\n", encoding="utf-8")
            args = _parser.parse_args(["tr", "a-c", "A-C", "--path", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["ABC"])

    def test_tr_delete(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello\n", encoding="utf-8")
            args = _parser.parse_args(["tr", "--delete", "aeiou", "--path", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["hll"])


class CodecCommandTests(unittest.TestCase):
    def test_base64_encode(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_bytes(b"hello")
            args = _parser.parse_args(["base64", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["operation"], "encode")
            self.assertIn("content", result)

    def test_base64_decode(self) -> None:
        import base64 as b64

        with TemporaryDirectory() as raw:
            root = Path(raw)
            encoded = b64.b64encode(b"hello").decode()
            (root / "f.txt").write_text(encoded, encoding="utf-8")
            args = _parser.parse_args(["base64", "--decode", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["operation"], "decode")
            self.assertEqual(result["content_text"], "hello")


class NlCommandTests(unittest.TestCase):
    def test_nl_numbers(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            args = _parser.parse_args(["nl", str(root / "f.txt")])
            result = args.func(args)
            self.assertGreaterEqual(len(result["records"]), 3)


class FoldCommandTests(unittest.TestCase):
    def test_fold_wraps(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("0123456789\n", encoding="utf-8")
            args = _parser.parse_args(["fold", "--width", "5", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class EchoCommandTests(unittest.TestCase):
    def test_echo_text(self) -> None:
        args = _parser.parse_args(["echo", "hello", "world"])
        result = args.func(args)
        self.assertIn("hello world", result["text"])

    def test_echo_raw(self) -> None:
        args = _parser.parse_args(["echo", "--raw", "hello"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class ExpandCommandTests(unittest.TestCase):
    def test_expand_tabs(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\tb\n", encoding="utf-8")
            args = _parser.parse_args(["expand", str(root / "f.txt")])
            result = args.func(args)
            self.assertIn(" ", result["lines"][0])


class UnexpandCommandTests(unittest.TestCase):
    def test_unexpand(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a       b\n", encoding="utf-8")
            args = _parser.parse_args(["unexpand", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class CommJoinPasteTests(unittest.TestCase):
    def test_comm_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("a\nc\n", encoding="utf-8")
            (root / "b.txt").write_text("b\nc\n", encoding="utf-8")
            args = _parser.parse_args(["comm", str(root / "a.txt"), str(root / "b.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertIn("records", result)

    def test_join_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("1 x\n2 y\n", encoding="utf-8")
            (root / "b.txt").write_text("1 A\n3 B\n", encoding="utf-8")
            args = _parser.parse_args(["join", str(root / "a.txt"), str(root / "b.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)

    def test_paste_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("a\nb\n", encoding="utf-8")
            (root / "b.txt").write_text("1\n2\n", encoding="utf-8")
            args = _parser.parse_args(["paste", str(root / "a.txt"), str(root / "b.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertIn("lines", result)


class SplitCsplitTests(unittest.TestCase):
    def test_split_basic(self) -> None:
        import os as _os

        with TemporaryDirectory() as raw:
            root = Path(raw)
            _orig = _os.getcwd()
            _os.chdir(str(root))
            try:
                (root / "f.txt").write_text("a\nb\nc\nd\n", encoding="utf-8")
                args = _parser.parse_args(["split", "--lines", "2", str(root / "f.txt"), "--prefix", "xx_"])
                result = args.func(args)
                self.assertIsInstance(result, dict)
            finally:
                _os.chdir(_orig)

    def test_csplit_basic(self) -> None:
        import os as _os

        with TemporaryDirectory() as raw:
            root = Path(raw)
            _orig = _os.getcwd()
            _os.chdir(str(root))
            try:
                (root / "f.txt").write_text("a\n%\nb\n%\nc\n", encoding="utf-8")
                args = _parser.parse_args(["csplit", "--pattern", "%", str(root / "f.txt"), "--prefix", "cs_"])
                result = args.func(args)
                self.assertIsInstance(result, dict)
            finally:
                _os.chdir(_orig)


class FmtPrPtxTests(unittest.TestCase):
    def test_fmt_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("this is a long line that should be wrapped by fmt\n", encoding="utf-8")
            args = _parser.parse_args(["fmt", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)

    def test_pr_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\n", encoding="utf-8")
            args = _parser.parse_args(["pr", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)

    def test_ptx_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello world\nfoo bar\n", encoding="utf-8")
            args = _parser.parse_args(["ptx", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class OdCommandTests(unittest.TestCase):
    def test_od_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_bytes(b"hello")
            args = _parser.parse_args(["od", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class NumfmtSeqYesTests(unittest.TestCase):
    def test_numfmt_basic(self) -> None:
        args = _parser.parse_args(["numfmt", "1024"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_seq_basic(self) -> None:
        args = _parser.parse_args(["seq", "1", "3"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_printf_basic(self) -> None:
        args = _parser.parse_args(["printf", "%s", "hello"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_yes_basic(self) -> None:
        args = _parser.parse_args(["yes", "--count", "3"])
        result = args.func(args)
        self.assertIsInstance(result, dict)
        self.assertIn("lines", result)


class TsortDircolorsTests(unittest.TestCase):
    def test_tsort_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a b\nb c\n", encoding="utf-8")
            args = _parser.parse_args(["tsort", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)

    def test_dircolors_basic(self) -> None:
        args = _parser.parse_args(["dircolors"])
        result = args.func(args)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
