"""Unit tests for commands/fs/_core.py — via real parser for proper args."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aicoreutils.parser._parser import build_parser

_parser = build_parser()


class PwdCommandTests(unittest.TestCase):
    def test_pwd(self) -> None:
        args = _parser.parse_args(["pwd"])
        result = args.func(args)
        self.assertTrue(Path(result["path"]).is_absolute())


class BasenameCommandTests(unittest.TestCase):
    def test_basename(self) -> None:
        args = _parser.parse_args(["basename", "/foo/bar.txt"])
        result = args.func(args)
        self.assertEqual(result["entries"][0]["basename"], "bar.txt")

    def test_basename_suffix(self) -> None:
        args = _parser.parse_args(["basename", "--suffix", ".txt", "/foo/bar.txt"])
        result = args.func(args)
        self.assertEqual(result["entries"][0]["basename"], "bar")

    def test_basename_raw(self) -> None:
        args = _parser.parse_args(["basename", "--raw", "/foo/bar.txt"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class DirnameCommandTests(unittest.TestCase):
    def test_dirname(self) -> None:
        args = _parser.parse_args(["dirname", "/foo/bar.txt"])
        result = args.func(args)
        self.assertEqual(result["entries"][0]["dirname"], "/foo")


class RealpathCommandTests(unittest.TestCase):
    def test_realpath(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "file.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["realpath", str(root / "file.txt")])
            result = args.func(args)
            self.assertIn("path", result["paths"][0])
            self.assertTrue(Path(result["paths"][0]["path"]).is_absolute())


class StatCommandTests(unittest.TestCase):
    def test_stat_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "test.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["stat", str(root / "test.txt")])
            result = args.func(args)
            self.assertEqual(result["entries"][0]["type"], "file")
            self.assertEqual(result["entries"][0]["size_bytes"], 5)


class LsCommandTests(unittest.TestCase):
    def test_ls_dir(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("a", encoding="utf-8")
            args = _parser.parse_args(["ls", str(root)])
            result = args.func(args)
            self.assertGreaterEqual(len(result["entries"]), 1)

    def test_ls_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "only.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["ls", str(root / "only.txt")])
            result = args.func(args)
            self.assertIn("entries", result)


class CatCommandTests(unittest.TestCase):
    def test_cat_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello world", encoding="utf-8")
            args = _parser.parse_args(["cat", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["content"], "hello world")

    def test_cat_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["cat", "--raw", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)

    def test_cat_max_bytes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("0123456789", encoding="utf-8")
            args = _parser.parse_args(["cat", "--max-bytes", "3", str(root / "f.txt")])
            result = args.func(args)
            self.assertTrue(result["truncated"])
            self.assertEqual(len(result["content"]), 3)


class HeadCommandTests(unittest.TestCase):
    def test_head_lines(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
            args = _parser.parse_args(["head", "--lines", "3", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["a", "b", "c"])

    def test_head_default(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\n", encoding="utf-8")
            args = _parser.parse_args(["head", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(len(result["lines"]), 2)


class TailCommandTests(unittest.TestCase):
    def test_tail_lines(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            args = _parser.parse_args(["tail", "--lines", "2", str(root / "f.txt")])
            result = args.func(args)
            self.assertEqual(result["lines"], ["b", "c"])


class WcCommandTests(unittest.TestCase):
    def test_wc(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello world\nfoo\n", encoding="utf-8")
            args = _parser.parse_args(["wc", str(root / "f.txt")])
            result = args.func(args)
            entry = result["entries"][0]
            self.assertEqual(entry["lines"], 2)
            self.assertEqual(entry["words"], 3)


class TouchCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)

    def test_touch_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            f = root / "new.txt"
            args = _parser.parse_args(["touch", str(f)])
            result = args.func(args)
            self.assertTrue(result["operations"][0]["created"])
            self.assertTrue(f.exists())

    def test_touch_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            f = root / "new.txt"
            args = _parser.parse_args(["touch", "--dry-run", str(f)])
            result = args.func(args)
            self.assertTrue(result["operations"][0]["dry_run"])
            self.assertFalse(f.exists())


class MkdirCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)

    def test_mkdir_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            sub = root / "newdir"
            args = _parser.parse_args(["mkdir", str(sub)])
            result = args.func(args)
            self.assertIn("operations", result)
            self.assertTrue(result["operations"][0]["created"])
            self.assertTrue(sub.is_dir())

    def test_mkdir_parents(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            sub = root / "a" / "b"
            args = _parser.parse_args(["mkdir", "--parents", str(sub)])
            args.func(args)
            self.assertTrue(sub.is_dir())

    def test_mkdir_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            sub = root / "newdir"
            args = _parser.parse_args(["mkdir", "--dry-run", str(sub)])
            result = args.func(args)
            self.assertTrue(result["operations"][0]["dry_run"])
            self.assertFalse(sub.exists())


class CpMvLnTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)

    def test_cp_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            (root / "src.txt").write_text("data", encoding="utf-8")
            args = _parser.parse_args(["cp", str(root / "src.txt"), str(root / "dst.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertTrue((root / "dst.txt").exists())

    def test_cp_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            (root / "src.txt").write_text("data", encoding="utf-8")
            args = _parser.parse_args(["cp", "--dry-run", str(root / "src.txt"), str(root / "dst.txt")])
            args.func(args)
            self.assertFalse((root / "dst.txt").exists())

    def test_mv_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            (root / "old.txt").write_text("data", encoding="utf-8")
            args = _parser.parse_args(["mv", str(root / "old.txt"), str(root / "new.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertFalse((root / "old.txt").exists())

    def test_mv_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            (root / "old.txt").write_text("data", encoding="utf-8")
            args = _parser.parse_args(["mv", "--dry-run", str(root / "old.txt"), str(root / "new.txt")])
            args.func(args)
            self.assertTrue((root / "old.txt").exists())

    def test_ln_symlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            (root / "target.txt").write_text("data", encoding="utf-8")
            args = _parser.parse_args(["ln", "--symbolic", str(root / "target.txt"), str(root / "link.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class RmRmdirUnlinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)

    def test_rm_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            f = root / "del.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["rm", str(f)])
            args.func(args)
            self.assertFalse(f.exists())

    def test_rm_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            f = root / "del.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["rm", "--dry-run", str(f)])
            args.func(args)
            self.assertTrue(f.exists())

    def test_rmdir(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            sub = root / "emptydir"
            sub.mkdir()
            args = _parser.parse_args(["rmdir", str(sub)])
            args.func(args)
            self.assertFalse(sub.exists())

    def test_unlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            f = root / "unlinkme.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["unlink", str(f)])
            args.func(args)
            self.assertFalse(f.exists())


class ReadlinkTests(unittest.TestCase):
    def test_readlink_canonicalize(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            args = _parser.parse_args(["readlink", "--canonicalize", str(link)])
            result = args.func(args)
            self.assertIsInstance(result, dict)


class DdDfDuTests(unittest.TestCase):
    def test_du_basic(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["du", raw])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertIn("entries", result)

    def test_df_basic(self) -> None:
        with TemporaryDirectory() as raw:
            args = _parser.parse_args(["df", raw])
            result = args.func(args)
            self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
