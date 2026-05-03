"""Unit tests for path_utils and sandbox modules."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agentutils.core.exceptions import AgentError
from agentutils.core.path_utils import ensure_exists, ensure_parent, path_type, resolve_path, stat_entry
from agentutils.core.sandbox import (
    dangerous_delete_target,
    destination_inside_directory,
    refuse_overwrite,
    require_inside_cwd,
)

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


if __name__ == "__main__":
    unittest.main()
