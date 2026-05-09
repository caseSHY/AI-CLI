"""Unit tests for utils/_path.py — disk usage, directory size, test predicates,
path validation, expression truthiness, and directory iteration."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aicoreutils.core.exceptions import AgentError
from aicoreutils.utils._path import (
    directory_size,
    disk_usage_entry,
    evaluate_test_predicates,
    expression_truthy,
    iter_directory,
    path_issues,
    prime_factors,
)


class DiskUsageEntryTests(unittest.TestCase):
    def test_returns_usage_for_directory(self) -> None:
        with TemporaryDirectory() as raw:
            result = disk_usage_entry(Path(raw))
            self.assertEqual(result["path"], str(Path(raw).resolve()))
            self.assertGreater(result["total_bytes"], 0)
            self.assertGreaterEqual(result["used_bytes"], 0)
            self.assertGreaterEqual(result["free_bytes"], 0)
            self.assertIsInstance(result["used_ratio"], float)

    def test_raises_not_found_for_missing_path(self) -> None:
        with self.assertRaises(AgentError) as ctx:
            disk_usage_entry(Path("/nonexistent_path_xyz_12345"))
        self.assertEqual(ctx.exception.code, "not_found")


class DirectorySizeTests(unittest.TestCase):
    def test_empty_directory_zero_size(self) -> None:
        with TemporaryDirectory() as raw:
            total, count, truncated = directory_size(Path(raw), max_depth=10, follow_symlinks=False)
            # Total includes directory entry size (fs-dependent), just check >= 0
            self.assertGreaterEqual(total, 0)
            self.assertEqual(count, 1)  # The directory itself counts
            self.assertFalse(truncated)

    def test_counts_files_recursively(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("12345", encoding="utf-8")  # 5 bytes content
            sub = root / "sub"
            sub.mkdir()
            (sub / "b.txt").write_text("1234567890", encoding="utf-8")  # 10 bytes content
            total, count, truncated = directory_size(root, max_depth=10, follow_symlinks=False)
            self.assertGreaterEqual(total, 15)  # At least file content bytes
            self.assertGreaterEqual(count, 3)  # root + sub dir + 2 files
            self.assertFalse(truncated)

    def test_max_depth_truncation(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sub = root / "sub"
            sub.mkdir()
            (sub / "deep.txt").write_text("x", encoding="utf-8")
            total, count, truncated = directory_size(root, max_depth=0, follow_symlinks=False)
            self.assertTrue(truncated)

    def test_follow_symlinks_resolves_links(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target.txt"
            target.write_text("hello", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            total, count, truncated = directory_size(root, max_depth=10, follow_symlinks=True)
            # Should count both the link and the target
            self.assertGreaterEqual(total, 5)


class EvaluateTestPredicatesTests(unittest.TestCase):
    def test_exists_true_for_file(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            results = evaluate_test_predicates(f, ["exists"])
            self.assertTrue(results[0]["matches"])

    def test_exists_true_for_broken_symlink(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "target"
            target.write_text("x", encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to("target")
            except OSError:
                self.skipTest("symlink requires admin on Windows")
            target.unlink()
            results = evaluate_test_predicates(link, ["exists"])
            self.assertTrue(results[0]["matches"])

    def test_file_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            results = evaluate_test_predicates(f, ["file"])
            self.assertTrue(results[0]["matches"])

    def test_directory_predicate(self) -> None:
        with TemporaryDirectory() as raw:
            results = evaluate_test_predicates(Path(raw), ["directory"])
            self.assertTrue(results[0]["matches"])

    def test_empty_and_non_empty(self) -> None:
        with TemporaryDirectory() as raw:
            empty = Path(raw) / "empty.txt"
            empty.write_text("", encoding="utf-8")
            nonempty = Path(raw) / "nonempty.txt"
            nonempty.write_text("data", encoding="utf-8")
            self.assertTrue(evaluate_test_predicates(empty, ["empty"])[0]["matches"])
            self.assertTrue(evaluate_test_predicates(nonempty, ["non_empty"])[0]["matches"])

    def test_multiple_predicates(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("hello", encoding="utf-8")
            results = evaluate_test_predicates(f, ["exists", "file", "readable", "non_empty"])
            self.assertEqual(len(results), 4)
            self.assertTrue(all(r["matches"] for r in results))

    def test_unsupported_predicate_raises(self) -> None:
        with TemporaryDirectory() as raw:
            f = Path(raw) / "f.txt"
            f.write_text("x", encoding="utf-8")
            with self.assertRaises(AgentError) as ctx:
                evaluate_test_predicates(f, ["nonexistent_predicate"])
            self.assertEqual(ctx.exception.code, "invalid_input")

    def test_predicates_on_nonexistent_path(self) -> None:
        results = evaluate_test_predicates(Path("/nonexistent_xyz_12345"), ["exists"])
        self.assertFalse(results[0]["matches"])


class PrimeFactorsTests(unittest.TestCase):
    def test_prime_factors_of_prime(self) -> None:
        self.assertEqual(prime_factors(7), [7])

    def test_prime_factors_of_composite(self) -> None:
        self.assertEqual(prime_factors(12), [2, 2, 3])

    def test_prime_factors_of_one(self) -> None:
        self.assertEqual(prime_factors(1), [])

    def test_prime_factors_of_zero(self) -> None:
        self.assertEqual(prime_factors(0), [])

    def test_prime_factors_of_negative(self) -> None:
        self.assertEqual(prime_factors(-12), [2, 2, 3])

    def test_prime_factors_large_number(self) -> None:
        self.assertEqual(prime_factors(97 * 97), [97, 97])


class PathIssuesTests(unittest.TestCase):
    def test_valid_path_no_issues(self) -> None:
        issues = path_issues("hello.txt", max_path_length=255, max_component_length=255, portable=False)
        self.assertEqual(issues, [])

    def test_empty_path(self) -> None:
        issues = path_issues("", max_path_length=255, max_component_length=255, portable=False)
        self.assertIn("empty_path", issues)

    def test_nul_byte(self) -> None:
        issues = path_issues("file\0name.txt", max_path_length=255, max_component_length=255, portable=False)
        self.assertIn("nul_byte", issues)

    def test_path_too_long(self) -> None:
        issues = path_issues("a" * 300, max_path_length=255, max_component_length=255, portable=False)
        self.assertIn("path_too_long", issues)

    def test_component_too_long(self) -> None:
        issues = path_issues(
            "dir/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/file.txt",
            max_path_length=4096,
            max_component_length=255,
            portable=False,
        )
        self.assertIn("component_too_long", issues)

    def test_non_portable_character(self) -> None:
        issues = path_issues("file name.txt", max_path_length=255, max_component_length=255, portable=True)
        self.assertIn("non_portable_character", issues)

    def test_portable_allows_safe_chars(self) -> None:
        issues = path_issues("abc_123.XYZ-0", max_path_length=255, max_component_length=255, portable=True)
        self.assertEqual(issues, [])


class ExpressionTruthyTests(unittest.TestCase):
    def test_bool_true(self) -> None:
        self.assertTrue(expression_truthy(True))

    def test_bool_false(self) -> None:
        self.assertFalse(expression_truthy(False))

    def test_nonzero_int(self) -> None:
        self.assertTrue(expression_truthy(42))

    def test_zero_int(self) -> None:
        self.assertFalse(expression_truthy(0))

    def test_nonzero_float(self) -> None:
        self.assertTrue(expression_truthy(3.14))

    def test_zero_float(self) -> None:
        self.assertFalse(expression_truthy(0.0))

    def test_nonempty_string(self) -> None:
        self.assertTrue(expression_truthy("hello"))

    def test_empty_string(self) -> None:
        self.assertFalse(expression_truthy(""))

    def test_none(self) -> None:
        self.assertFalse(expression_truthy(None))

    def test_empty_list(self) -> None:
        self.assertFalse(expression_truthy([]))


class IterDirectoryTests(unittest.TestCase):
    def test_single_file_returns_one_entry(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "test.txt"
            f.write_text("content", encoding="utf-8")
            entries, truncated = iter_directory(
                f,
                include_hidden=False,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["name"], "test.txt")
            self.assertFalse(truncated)

    def test_directory_lists_children(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "b.txt").write_text("b", encoding="utf-8")
            entries, truncated = iter_directory(
                root,
                include_hidden=False,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            self.assertEqual(len(entries), 2)
            self.assertFalse(truncated)

    def test_limit_truncation(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            for i in range(10):
                (root / f"file_{i:02d}.txt").write_text(f"{i}", encoding="utf-8")
            entries, truncated = iter_directory(
                root,
                include_hidden=False,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=3,
            )
            self.assertEqual(len(entries), 3)
            self.assertTrue(truncated)

    def test_include_hidden_shows_dotfiles(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".hidden").write_text("secret", encoding="utf-8")
            (root / "visible.txt").write_text("hello", encoding="utf-8")
            entries, _ = iter_directory(
                root,
                include_hidden=True,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            names = {e["name"] for e in entries}
            self.assertIn(".hidden", names)
            self.assertIn("visible.txt", names)

    def test_exclude_hidden_hides_dotfiles(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".hidden").write_text("secret", encoding="utf-8")
            (root / "visible.txt").write_text("hello", encoding="utf-8")
            entries, _ = iter_directory(
                root,
                include_hidden=False,
                recursive=False,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            names = {e["name"] for e in entries}
            self.assertNotIn(".hidden", names)
            self.assertIn("visible.txt", names)

    def test_recursive_traverses_subdirs(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sub = root / "sub"
            sub.mkdir()
            (sub / "deep.txt").write_text("deep", encoding="utf-8")
            entries, truncated = iter_directory(
                root,
                include_hidden=False,
                recursive=True,
                max_depth=10,
                follow_symlinks=False,
                limit=100,
            )
            self.assertEqual(len(entries), 2)  # sub entry + deep.txt
            self.assertFalse(truncated)


if __name__ == "__main__":
    unittest.main()
