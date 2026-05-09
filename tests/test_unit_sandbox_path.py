"""Unit tests for path_utils and sandbox modules."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aicoreutils.core.exceptions import AgentError
from aicoreutils.core.path_utils import (
    directory_size,
    disk_usage_entry,
    ensure_exists,
    ensure_parent,
    iter_directory,
    path_type,
    resolve_path,
    stat_entry,
)
from aicoreutils.core.sandbox import (
    dangerous_delete_target,
    destination_inside_directory,
    refuse_overwrite,
    remove_one,
    remove_recursive,
    require_inside_cwd,
)
from aicoreutils.utils._path import evaluate_test_predicates

# ── path_utils ──


class ResolvePathTests(unittest.TestCase):
    def test_resolves_relative_to_absolute(self) -> None:
        result = resolve_path("project")
        self.assertTrue(result.is_absolute())

    def test_resolve_expands_user(self) -> None:
        result = resolve_path("~")
        self.assertEqual(result, Path.home().resolve())

    def test_resolve_accepts_path_object(self) -> None:
        result = resolve_path(Path("project"))
        self.assertTrue(result.is_absolute())

    def test_resolve_strict_raises_for_missing(self) -> None:
        with self.assertRaises(AgentError) as ctx:
            resolve_path("/nonexistent/path/12345", strict=True)
        self.assertEqual(ctx.exception.code, "not_found")

    def test_resolve_non_strict_allows_missing(self) -> None:
        result = resolve_path("nonexistent_file_xyz", strict=False)
        self.assertTrue(result.is_absolute())


class PathTypeTests(unittest.TestCase):
    def test_file_type(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "file.txt").write_text("hello", encoding="utf-8")
            self.assertEqual(path_type(cwd / "file.txt"), "file")

    def test_directory_type(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            self.assertEqual(path_type(cwd), "directory")

    def test_not_found_raises(self) -> None:
        with TemporaryDirectory() as raw:
            with self.assertRaises(AgentError) as ctx:
                path_type(Path(raw) / "nope")
            self.assertEqual(ctx.exception.code, "not_found")


class EnsureExistsTests(unittest.TestCase):
    def test_existing_file_passes(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text("x", encoding="utf-8")
            ensure_exists(cwd / "f.txt")

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(AgentError) as ctx:
            ensure_exists(Path("/nonexistent_file_abc_xyz"))
        self.assertEqual(ctx.exception.code, "not_found")

    def test_broken_symlink_passes(self) -> None:
        # ensure_exists should pass for broken symlinks (is_symlink returns True)
        # Windows requires admin for symlinks; skip gracefully
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "target"
            target.write_text("content", encoding="utf-8")
            link = cwd / "link"
            try:
                link.symlink_to("target")
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            target.unlink()
            ensure_exists(link)


class EnsureParentTests(unittest.TestCase):
    def test_exists_passes(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "sub").mkdir()
            ensure_parent(cwd / "sub" / "file.txt", create=False, dry_run=False)

    def test_missing_parent_raises(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            with self.assertRaises(AgentError) as ctx:
                ensure_parent(cwd / "missing" / "child.txt", create=False, dry_run=False)
            self.assertEqual(ctx.exception.code, "not_found")

    def test_create_parent(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            child = cwd / "new_dir" / "child.txt"
            ensure_parent(child, create=True, dry_run=False)
            self.assertTrue(cwd.joinpath("new_dir").is_dir())

    def test_create_parent_dry_run_no_fs_change(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            child = cwd / "new_dir" / "child.txt"
            ensure_parent(child, create=True, dry_run=True)
            self.assertFalse(cwd.joinpath("new_dir").exists())


class StatEntryTests(unittest.TestCase):
    def test_stat_entry_basic(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            f = cwd / "f.txt"
            f.write_text("hello", encoding="utf-8")
            entry = stat_entry(f)
            self.assertEqual(entry["name"], "f.txt")
            self.assertEqual(entry["type"], "file")
            self.assertEqual(entry["size_bytes"], len(b"hello"))
            self.assertGreater(len(entry["path"]), 0)

    def test_stat_entry_with_base(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            f = cwd / "sub" / "f.txt"
            f.parent.mkdir()
            f.write_text("x", encoding="utf-8")
            entry = stat_entry(f, base=cwd)
            self.assertIn("relative_path", entry)

    def test_stat_entry_with_depth(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            f = cwd / "f.txt"
            f.write_text("x", encoding="utf-8")
            entry = stat_entry(f, depth=3)
            self.assertEqual(entry["depth"], 3)


# ── sandbox ──


class DangerousDeleteTests(unittest.TestCase):
    def test_cwd_is_dangerous(self) -> None:
        cwd = Path.cwd().resolve()
        result = dangerous_delete_target(cwd, cwd)
        self.assertIsNotNone(result)

    def test_home_is_dangerous(self) -> None:
        cwd = Path.cwd().resolve()
        home = Path.home().resolve()
        result = dangerous_delete_target(home, cwd)
        self.assertIsNotNone(result)

    def test_random_file_is_safe(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            result = dangerous_delete_target(cwd / "file.txt", cwd)
            self.assertIsNone(result)


class RequireInsideCwdTests(unittest.TestCase):
    def test_path_inside_cwd_passes(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw).resolve()
            child = cwd / "child.txt"
            child.write_text("x", encoding="utf-8")
            require_inside_cwd(child, cwd, allow_outside_cwd=False)

    def test_path_outside_cwd_raises(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw).resolve()
            outside = cwd.parent
            with self.assertRaises(AgentError) as ctx:
                require_inside_cwd(outside, cwd, allow_outside_cwd=False)
            self.assertEqual(ctx.exception.code, "unsafe_operation")

    def test_allow_outside_cwd_bypasses(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw).resolve()
            outside = cwd.parent
            require_inside_cwd(outside, cwd, allow_outside_cwd=True)


class RefuseOverwriteTests(unittest.TestCase):
    def test_existing_file_without_allow_raises(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            f = cwd / "existing.txt"
            f.write_text("x", encoding="utf-8")
            with self.assertRaises(AgentError) as ctx:
                refuse_overwrite(f, allow_overwrite=False)
            self.assertEqual(ctx.exception.code, "conflict")

    def test_existing_file_with_allow_passes(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            f = cwd / "existing.txt"
            f.write_text("x", encoding="utf-8")
            refuse_overwrite(f, allow_overwrite=True)

    def test_non_existing_file_passes(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            refuse_overwrite(cwd / "nonexistent.txt", allow_overwrite=False)


class DestinationInsideDirectoryTests(unittest.TestCase):
    def test_dest_is_dir_returns_subpath(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            src = cwd / "file.txt"
            dest_dir = cwd / "mydir"
            dest_dir.mkdir()
            result = destination_inside_directory(src, dest_dir)
            self.assertEqual(result, dest_dir / "file.txt")

    def test_dest_is_file_returns_dest(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            src = cwd / "file.txt"
            dest = cwd / "other.txt"
            dest.write_text("x", encoding="utf-8")
            result = destination_inside_directory(src, dest)
            self.assertEqual(result, dest)

    def test_non_existing_dest_returns_dest(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            src = cwd / "file.txt"
            dest = cwd / "nonexistent"
            result = destination_inside_directory(src, dest)
            self.assertEqual(result, dest)


# ── sandbox: remove_one and remove_recursive ──


class RemoveOneTests(unittest.TestCase):
    def test_remove_file(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "file.txt"
            f.write_text("hello", encoding="utf-8")
            status = remove_one(f)
            self.assertEqual(status, "removed")
            self.assertFalse(f.exists())

    def test_remove_symlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            status = remove_one(link)
            self.assertEqual(status, "removed")
            self.assertTrue(target.exists())  # Only the link, not the target

    def test_remove_directory_recursive(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sub = root / "sub"
            sub.mkdir()
            (sub / "f.txt").write_text("x", encoding="utf-8")
            status = remove_one(sub, recursive=True)
            self.assertEqual(status, "directory_removed")
            self.assertFalse(sub.exists())

    def test_remove_directory_non_recursive_raises(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sub = root / "sub"
            sub.mkdir()
            with self.assertRaises(AgentError) as ctx:
                remove_one(sub, recursive=False)
            self.assertEqual(ctx.exception.code, "invalid_input")

    def test_remove_missing_raises_not_found(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(AgentError) as ctx:
                remove_one(root / "nonexistent")
            self.assertEqual(ctx.exception.code, "not_found")

    def test_remove_missing_with_force_ignores(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            status = remove_one(root / "nonexistent", force=True)
            self.assertEqual(status, "missing_ignored")

    def test_remove_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "file.txt"
            f.write_text("hello", encoding="utf-8")
            status = remove_one(f, dry_run=True)
            self.assertEqual(status, "would_remove")
            self.assertTrue(f.exists())  # Not actually removed


class RemoveRecursiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = os.getcwd()

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)

    def test_dry_run_inside_cwd(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))  # cwd = temp dir
            sub = root / "sub"
            sub.mkdir()
            ops = remove_recursive(sub, dry_run=True, allow_outside_cwd=False)
            self.assertEqual(len(ops), 1)
            self.assertTrue(ops[0]["dry_run"])
            self.assertTrue(sub.exists())

    def test_remove_symlink_uses_unlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            target = root / "target.txt"
            target.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            ops = remove_recursive(link, dry_run=False, allow_outside_cwd=False)
            self.assertEqual(ops[0]["status"], "removed")
            self.assertTrue(target.exists())

    def test_inside_cwd_works(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            sub = root / "sub"
            sub.mkdir()
            (sub / "f.txt").write_text("x", encoding="utf-8")
            ops = remove_recursive(sub, dry_run=False, allow_outside_cwd=False)
            self.assertEqual(ops[0]["status"], "removed")
            self.assertFalse(sub.exists())

    def test_outside_cwd_raises_without_allow(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            os.chdir(str(root))
            outside = root.parent
            with self.assertRaises(AgentError) as ctx:
                remove_recursive(outside, dry_run=True, allow_outside_cwd=False)
            self.assertEqual(ctx.exception.code, "unsafe_operation")


# ── path_utils: edge cases ──


class ResolvePathEdgeTests(unittest.TestCase):
    def test_symlink_chain_resolves_to_real_path(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "real"
            target.mkdir()
            link1 = root / "link1"
            link2 = root / "link2"
            try:
                link1.symlink_to(target)
                link2.symlink_to(link1)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            result = resolve_path(link2)
            self.assertEqual(result, target.resolve())

    def test_resolve_with_tilde_and_dots(self) -> None:
        home_name = Path.home().name
        # ~/.. goes to /home, then home_name goes back to /home/<user>
        result = resolve_path(f"~/../{home_name}")
        self.assertEqual(result, Path.home().resolve())


class PathTypeEdgeTests(unittest.TestCase):
    def test_symlink_type_returns_symlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.write_text("x", encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            self.assertEqual(path_type(link), "symlink")

    def test_fifo_type(self) -> None:
        with TemporaryDirectory() as raw:
            fifo_path = Path(raw) / "test_fifo"
            try:
                os.mkfifo(fifo_path)
            except OSError:
                self.skipTest("mkfifo not supported on this platform")
            self.assertEqual(path_type(fifo_path), "fifo")

    def test_broken_symlink_is_symlink_type(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.write_text("x", encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            target.unlink()
            self.assertEqual(path_type(link), "symlink")


class StatEntryEdgeTests(unittest.TestCase):
    def test_stat_entry_symlink_includes_link_target(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("hello", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            entry = stat_entry(link)
            self.assertTrue(entry["is_symlink"])
            self.assertIn("link_target", entry)

    def test_stat_entry_base_outside_path(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            # Use /dev as base — tempdir is under /tmp, not /dev
            entry = stat_entry(f, base=Path("/dev"))
            self.assertEqual(entry["relative_path"], str(f))


class DiskUsageEntryPathUtilsTests(unittest.TestCase):
    def test_returns_size_bytes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("12345", encoding="utf-8")
            result = disk_usage_entry(root)
            self.assertEqual(result["path"], str(root))
            self.assertGreater(result["size_bytes"], 0)


class DirectorySizePathUtilsTests(unittest.TestCase):
    def test_counts_all_files(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("12345", encoding="utf-8")
            (root / "b.txt").write_text("1234567890", encoding="utf-8")
            total = directory_size(root)
            self.assertGreaterEqual(total, 15)  # At least file content bytes


class EvaluateTestPredicatesEdgeTests(unittest.TestCase):
    def test_symlink_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("x", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            results = evaluate_test_predicates(link, ["symlink"])
            self.assertTrue(results[0]["matches"])

    def test_readable_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            results = evaluate_test_predicates(f, ["readable"])
            self.assertTrue(results[0]["matches"])

    def test_writable_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            results = evaluate_test_predicates(f, ["writable"])
            self.assertTrue(results[0]["matches"])

    def test_executable_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            results = evaluate_test_predicates(f, ["executable"])
            # The file is readable/writable by owner, executable depends on umask
            self.assertIsInstance(results[0]["matches"], bool)


class IterDirectoryPathUtilsTests(unittest.TestCase):
    def test_recursive_with_depth_limit(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sub = root / "sub"
            sub.mkdir()
            (sub / "deep.txt").write_text("x", encoding="utf-8")
            entries, truncated = iter_directory(
                root,
                include_hidden=False,
                recursive=True,
                max_depth=0,
                follow_symlinks=False,
                limit=100,
            )
            # Should show sub but not its children
            self.assertGreaterEqual(len(entries), 1)
            self.assertFalse(truncated)

    def test_single_file_root(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "only.txt"
            f.write_text("hello", encoding="utf-8")
            entries, truncated = iter_directory(
                f,
                include_hidden=False,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "only.txt")
            self.assertEqual(entries[0]["depth"], 0)
            self.assertFalse(truncated)


if __name__ == "__main__":
    unittest.main()
