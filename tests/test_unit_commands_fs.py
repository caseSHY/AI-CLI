"""Unit tests for commands/fs/_core.py — via real parser for proper args."""

from __future__ import annotations

import os
import sys
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
        self.assertIn("foo", result["entries"][0]["dirname"])
        self.assertTrue(result["entries"][0]["dirname"].endswith("foo"))


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

    def test_touch_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "new.txt"
                args = _parser.parse_args(["touch", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["created"])
                self.assertTrue(f.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_touch_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "new.txt"
                args = _parser.parse_args(["touch", "--dry-run", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(f.exists())
            finally:
                os.chdir(self._orig_cwd)


class MkdirCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_mkdir_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                sub = root / "newdir"
                args = _parser.parse_args(["mkdir", str(sub)])
                result = args.func(args)
                self.assertIn("operations", result)
                self.assertTrue(result["operations"][0]["created"])
                self.assertTrue(sub.is_dir())
            finally:
                os.chdir(self._orig_cwd)

    def test_mkdir_parents(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                sub = root / "a" / "b"
                args = _parser.parse_args(["mkdir", "--parents", str(sub)])
                args.func(args)
                self.assertTrue(sub.is_dir())
            finally:
                os.chdir(self._orig_cwd)

    def test_mkdir_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                sub = root / "newdir"
                args = _parser.parse_args(["mkdir", "--dry-run", str(sub)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(sub.exists())
            finally:
                os.chdir(self._orig_cwd)


class CpMvLnTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_cp_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                (root / "src.txt").write_text("data", encoding="utf-8")
                args = _parser.parse_args(["cp", str(root / "src.txt"), str(root / "dst.txt")])
                result = args.func(args)
                self.assertIsInstance(result, dict)
                self.assertTrue((root / "dst.txt").exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_cp_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                (root / "src.txt").write_text("data", encoding="utf-8")
                args = _parser.parse_args(["cp", "--dry-run", str(root / "src.txt"), str(root / "dst.txt")])
                args.func(args)
                self.assertFalse((root / "dst.txt").exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_mv_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                (root / "old.txt").write_text("data", encoding="utf-8")
                args = _parser.parse_args(["mv", str(root / "old.txt"), str(root / "new.txt")])
                result = args.func(args)
                self.assertIsInstance(result, dict)
                self.assertFalse((root / "old.txt").exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_mv_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                (root / "old.txt").write_text("data", encoding="utf-8")
                args = _parser.parse_args(["mv", "--dry-run", str(root / "old.txt"), str(root / "new.txt")])
                args.func(args)
                self.assertTrue((root / "old.txt").exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_ln_symlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                (root / "target.txt").write_text("data", encoding="utf-8")
                args = _parser.parse_args(["ln", "--symbolic", str(root / "target.txt"), str(root / "link.txt")])
                result = args.func(args)
                self.assertIsInstance(result, dict)
            finally:
                os.chdir(self._orig_cwd)


class RmRmdirUnlinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_rm_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "del.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["rm", str(f)])
                args.func(args)
                self.assertFalse(f.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_rm_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "del.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["rm", "--dry-run", str(f)])
                args.func(args)
                self.assertTrue(f.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_rmdir(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                sub = root / "emptydir"
                sub.mkdir()
                args = _parser.parse_args(["rmdir", str(sub)])
                args.func(args)
                self.assertFalse(sub.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_unlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "unlinkme.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["unlink", str(f)])
                args.func(args)
                self.assertFalse(f.exists())
            finally:
                os.chdir(self._orig_cwd)


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


class DirVdirCommandTests(unittest.TestCase):
    def test_dir_delegates_to_ls(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["dir", str(root)])
            result = args.func(args)
            self.assertEqual(result["alias"], "dir")
            self.assertIn("entries", result)

    def test_vdir_delegates_to_ls(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["vdir", str(root)])
            result = args.func(args)
            self.assertEqual(result["alias"], "vdir")
            self.assertTrue(result["verbose"])


class CksumSumCommandTests(unittest.TestCase):
    def test_cksum_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["cksum", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["entries"][0]["algorithm"], "crc32")

    def test_cksum_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["cksum", "--raw", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)

    def test_sum_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["sum", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["entries"][0]["algorithm"], "byte-sum-16")

    def test_sum_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["sum", "--raw", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)


class SyncTruncateMktempTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_sync(self) -> None:
        args = _parser.parse_args(["sync"])
        result = args.func(args)
        self.assertEqual(result["operation"], "sync")

    def test_sync_dry_run(self) -> None:
        args = _parser.parse_args(["sync", "--dry-run"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_truncate_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "new.txt"
                args = _parser.parse_args(["truncate", "--size", "10", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["created"])
                self.assertEqual(f.stat().st_size, 10)
            finally:
                os.chdir(self._orig_cwd)

    def test_truncate_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "new.txt"
                args = _parser.parse_args(["truncate", "--size", "10", "--dry-run", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(f.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_mktemp_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                args = _parser.parse_args(["mktemp"])
                result = args.func(args)
                self.assertIn("path", result)
                self.assertTrue(Path(result["path"]).exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_mktemp_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                args = _parser.parse_args(["mktemp", "--dry-run"])
                result = args.func(args)
                self.assertTrue(result["dry_run"])
                self.assertIn("path", result)
            finally:
                os.chdir(self._orig_cwd)

    def test_mktemp_directory(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                args = _parser.parse_args(["mktemp", "--directory"])
                result = args.func(args)
                self.assertIn("path", result)
                self.assertTrue(Path(result["path"]).is_dir())
            finally:
                os.chdir(self._orig_cwd)


class RawModeTests(unittest.TestCase):
    def test_readlink_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            args = _parser.parse_args(["readlink", "--raw", "--canonicalize", str(root / "target.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)

    def test_head_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("line1\nline2\nline3\n", encoding="utf-8")
            args = _parser.parse_args(["head", "--raw", "--lines", "2", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)

    def test_tail_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("line1\nline2\nline3\n", encoding="utf-8")
            args = _parser.parse_args(["tail", "--raw", "--lines", "2", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)

    def test_wc_raw(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello world\n", encoding="utf-8")
            args = _parser.parse_args(["wc", "--raw", str(root / "f.txt")])
            result = args.func(args)
            self.assertIsInstance(result, bytes)


class ChmodChownChgrpReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_chmod_reference(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                ref = root / "ref.txt"
                ref.write_text("x", encoding="utf-8")
                ref.chmod(0o600)
                f = root / "f.txt"
                f.write_text("y", encoding="utf-8")
                args = _parser.parse_args(["chmod", "--reference", str(ref), str(f)])
                result = args.func(args)
                self.assertIn("operations", result)
            finally:
                os.chdir(self._orig_cwd)

    def test_chmod_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "f.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["chmod", "--dry-run", "644", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
            finally:
                os.chdir(self._orig_cwd)

    def test_chown_reference(self) -> None:
        if sys.platform == "win32":
            self.skipTest("chown is not supported on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                ref = root / "ref.txt"
                ref.write_text("x", encoding="utf-8")
                f = root / "f.txt"
                f.write_text("y", encoding="utf-8")
                args = _parser.parse_args(["chown", "--reference", str(ref), str(f)])
                result = args.func(args)
                self.assertIn("operations", result)
            finally:
                os.chdir(self._orig_cwd)

    def test_chown_dry_run(self) -> None:
        if sys.platform == "win32":
            self.skipTest("chown is not supported on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "f.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["chown", "--dry-run", "0:0", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
            finally:
                os.chdir(self._orig_cwd)

    def test_chgrp_reference(self) -> None:
        if sys.platform == "win32":
            self.skipTest("chgrp is not supported on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                ref = root / "ref.txt"
                ref.write_text("x", encoding="utf-8")
                f = root / "f.txt"
                f.write_text("y", encoding="utf-8")
                args = _parser.parse_args(["chgrp", "--reference", str(ref), str(f)])
                result = args.func(args)
                self.assertIn("operations", result)
            finally:
                os.chdir(self._orig_cwd)

    def test_chgrp_dry_run(self) -> None:
        if sys.platform == "win32":
            self.skipTest("chgrp is not supported on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "f.txt"
                f.write_text("x", encoding="utf-8")
                args = _parser.parse_args(["chgrp", "--dry-run", "0", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
            finally:
                os.chdir(self._orig_cwd)


class HashCheckModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_hash_check_valid(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "f.txt"
                f.write_text("hello", encoding="utf-8")
                import hashlib

                digest = hashlib.md5(f.read_bytes()).hexdigest()
                check_file = root / "checksums.md5"
                check_file.write_text(f"{digest}  {f}\n", encoding="utf-8")
                args = _parser.parse_args(["hash", "--algorithm", "md5", "--check", str(check_file)])
                result = args.func(args)
                self.assertEqual(result["failed"], 0)
                self.assertGreaterEqual(result["ok"], 1)
            finally:
                os.chdir(self._orig_cwd)

    def test_hash_check_invalid(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "f.txt"
                f.write_text("hello", encoding="utf-8")
                check_file = root / "checksums.md5"
                check_file.write_text(f"deadbeef000000000000000000000000  {f}\n", encoding="utf-8")
                args = _parser.parse_args(["hash", "--algorithm", "md5", "--check", str(check_file)])
                result = args.func(args)
                self.assertGreaterEqual(result["failed"], 1)
            finally:
                os.chdir(self._orig_cwd)


class TeeCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_tee_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "out.txt"
                args = _parser.parse_args(["tee", "--dry-run", str(f)])
                self.assertTrue(args.dry_run)
                self.assertEqual(args.paths, [str(f)])
            finally:
                os.chdir(self._orig_cwd)


class HardLinkCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_link_create(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                src = root / "src.txt"
                src.write_text("data", encoding="utf-8")
                dst = root / "linked.txt"
                args = _parser.parse_args(["link", str(src), str(dst)])
                result = args.func(args)
                self.assertIn("operations", result)
                self.assertTrue(dst.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_link_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                src = root / "src.txt"
                src.write_text("data", encoding="utf-8")
                dst = root / "linked.txt"
                args = _parser.parse_args(["link", "--dry-run", str(src), str(dst)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(dst.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_link_destination_exists_raises(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                src = root / "src.txt"
                src.write_text("data", encoding="utf-8")
                dst = root / "dst.txt"
                dst.write_text("existing", encoding="utf-8")
                args = _parser.parse_args(["link", str(src), str(dst)])
                from aicoreutils.core.exceptions import AgentError

                with self.assertRaises(AgentError) as ctx:
                    args.func(args)
                self.assertEqual(ctx.exception.code, "conflict")
            finally:
                os.chdir(self._orig_cwd)


class InstallCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_install_directory(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                d = root / "newdir"
                args = _parser.parse_args(["install", "--directory", str(d)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["directory"])
                self.assertTrue(d.is_dir())
            finally:
                os.chdir(self._orig_cwd)

    def test_install_directory_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                d = root / "newdir"
                args = _parser.parse_args(["install", "--directory", "--dry-run", str(d)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(d.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_install_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                src = root / "src.txt"
                src.write_text("hello", encoding="utf-8")
                dst = root / "installed.txt"
                args = _parser.parse_args(["install", str(src), str(dst)])
                result = args.func(args)
                self.assertFalse(result["operations"][0]["directory"])
                self.assertTrue(dst.exists())
            finally:
                os.chdir(self._orig_cwd)


class ShredCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_shred_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "secret.txt"
                f.write_text("secret data", encoding="utf-8")
                args = _parser.parse_args(["shred", "--dry-run", str(f)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertTrue(f.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_shred_requires_allow_destructive(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                f = root / "secret.txt"
                f.write_text("secret data", encoding="utf-8")
                args = _parser.parse_args(["shred", str(f)])
                from aicoreutils.core.exceptions import AgentError

                with self.assertRaises(AgentError) as ctx:
                    args.func(args)
                self.assertEqual(ctx.exception.code, "unsafe_operation")
            finally:
                os.chdir(self._orig_cwd)


class TestBracketCommandTests(unittest.TestCase):
    def test_test_exists(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["test", "--exists", str(f)])
            result = args.func(args)
            self.assertTrue(result["matches"])

    def test_test_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["test", "--file", str(f)])
            result = args.func(args)
            self.assertTrue(result["matches"])

    def test_test_directory(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            d = root / "dir"
            d.mkdir()
            args = _parser.parse_args(["test", "--directory", str(d)])
            result = args.func(args)
            self.assertTrue(result["matches"])

    def test_test_nonexistent(self) -> None:
        args = _parser.parse_args(["test", "--exists", "/nonexistent/path/xyz"])
        result = args.func(args)
        self.assertFalse(result["matches"])

    def test_bracket_single_arg(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["[", str(f), "]"])
            result = args.func(args)
            self.assertIn("matches", result)

    def test_bracket_flag(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["[", "-f", str(f), "]"])
            result = args.func(args)
            self.assertIn("matches", result)

    def test_bracket_string_equality(self) -> None:
        args = _parser.parse_args(["[", "abc", "=", "abc", "]"])
        result = args.func(args)
        self.assertTrue(result["matches"])


class DdConvMkfifoMknodTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def test_dd_argument_validation(self) -> None:
        args = _parser.parse_args(["dd", "--bs=1", "--count=0"])
        self.assertEqual(args.bs, 1)
        self.assertEqual(args.count, 0)

    def test_mkfifo_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                fifo = root / "test.fifo"
                args = _parser.parse_args(["mkfifo", "--dry-run", str(fifo)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
                self.assertFalse(fifo.exists())
            finally:
                os.chdir(self._orig_cwd)

    def test_mknod_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            try:
                node = root / "test.node"
                args = _parser.parse_args(["mknod", "--dry-run", str(node)])
                result = args.func(args)
                self.assertTrue(result["operations"][0]["dry_run"])
            finally:
                os.chdir(self._orig_cwd)


if __name__ == "__main__":
    unittest.main()
