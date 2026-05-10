"""Unit tests for OO command base classes: CommandResult, BaseCommand, TextFilterCommand,
FileInfoCommand, MutatingCommand."""

from __future__ import annotations

import argparse
import unittest
from pathlib import Path
from typing import Any

from aicoreutils.core.command import (
    BaseCommand,
    CommandResult,
    FileInfoCommand,
    MutatingCommand,
    TextFilterCommand,
)


class TestCommandResult(unittest.TestCase):
    def test_data_mode(self) -> None:
        r = CommandResult(data={"key": "value"})
        self.assertFalse(r.is_raw)
        self.assertIsNone(r.raw_bytes)
        self.assertEqual(r.to_dict(), {"key": "value"})

    def test_raw_mode(self) -> None:
        r = CommandResult(raw_bytes=b"hello\n")
        self.assertTrue(r.is_raw)
        self.assertIsNone(r.data)
        self.assertEqual(r.raw_bytes, b"hello\n")

    def test_exit_code_in_dict(self) -> None:
        r = CommandResult(data={"ok": True}, exit_code=3)
        d = r.to_dict()
        self.assertEqual(d["_exit_code"], 3)
        self.assertEqual(d["ok"], True)

    def test_defaults(self) -> None:
        r = CommandResult()
        self.assertFalse(r.is_raw)
        self.assertEqual(r.exit_code, 0)
        self.assertIsNone(r.encoding_meta)
        self.assertEqual(r.warnings, [])
        self.assertEqual(r.to_dict(), {})


class TestBaseCommand(unittest.TestCase):
    def test_dict_return(self) -> None:
        class SimpleCmd(BaseCommand):
            name = "test"

            def execute(self, args: argparse.Namespace) -> CommandResult:
                return CommandResult(data={"val": 42})

        ns = argparse.Namespace()
        result = SimpleCmd()(ns)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["val"], 42)

    def test_raw_return(self) -> None:
        class RawCmd(BaseCommand):
            name = "test"

            def execute(self, args: argparse.Namespace) -> CommandResult:
                return CommandResult(raw_bytes=b"raw")

        ns = argparse.Namespace()
        result = RawCmd()(ns)
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b"raw")

    def test_encoding_meta_passthrough(self) -> None:
        class MetaCmd(BaseCommand):
            name = "test"

            def execute(self, args: argparse.Namespace) -> CommandResult:
                r = CommandResult(data={"x": 1})
                r.encoding_meta = {"detected": "utf-8", "confidence": 1.0}
                return r

        ns = argparse.Namespace()
        result = MetaCmd()(ns)
        self.assertIn("_encoding_info", result)
        self.assertEqual(result["_encoding_info"]["detected"], "utf-8")


class TestTextFilterCommand(unittest.TestCase):
    def test_transform(self) -> None:
        class UpperFilter(TextFilterCommand):
            name = "upper"

            def transform(self, lines: list[str], args: argparse.Namespace) -> list[str]:
                return [line.upper() for line in lines]

        import tempfile

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("hello\nworld\n", encoding="utf-8")
            ns = argparse.Namespace(paths=[str(d / "f.txt")], encoding="utf-8", raw=False, max_lines=10000)
            result = UpperFilter()(ns)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["lines"], ["HELLO", "WORLD"])
            self.assertEqual(result["source_paths"], [str((d / "f.txt").resolve())])
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_raw_mode(self) -> None:
        class ReversedFilter(TextFilterCommand):
            name = "rev"

            def transform(self, lines: list[str], args: argparse.Namespace) -> list[str]:
                return list(reversed(lines))

        import tempfile

        d = Path(tempfile.mkdtemp())
        try:
            (d / "f.txt").write_text("a\nb\nc\n", encoding="utf-8")
            ns = argparse.Namespace(paths=[str(d / "f.txt")], encoding="utf-8", raw=True, max_lines=10000)
            result = ReversedFilter()(ns)
            self.assertIsInstance(result, bytes)
            self.assertEqual(result.decode("utf-8"), "c\nb\na\n")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


class TestFileInfoCommand(unittest.TestCase):
    def test_process_path(self) -> None:
        class NameLength(FileInfoCommand):
            name = "namelen"

            def process_path(self, raw: str, args: argparse.Namespace) -> tuple[dict[str, Any], str]:
                name = Path(raw).name
                entry = {"input": raw, "name": name, "length": len(name)}
                return entry, f"{len(name)}\t{name}"

        import tempfile

        d = Path(tempfile.mkdtemp())
        try:
            (d / "abc.txt").touch()
            (d / "hello.md").touch()
            ns = argparse.Namespace(
                paths=[str(d / "abc.txt"), str(d / "hello.md")],
                raw=False,
            )
            result = NameLength()(ns)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["count"], 2)
            self.assertEqual(result["entries"][0]["name"], "abc.txt")
            self.assertEqual(result["entries"][1]["name"], "hello.md")
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


class TestMutatingCommand(unittest.TestCase):
    def test_execute_one(self) -> None:
        import tempfile

        d = Path(tempfile.mkdtemp())

        class FakeCreate(MutatingCommand):
            name = "fakecreate"

            def _execute_one(self, path: Any, args: argparse.Namespace, ops: list[dict[str, Any]]) -> None:
                ops.append({"operation": "create", "path": str(path), "dry_run": args.dry_run})
                if not args.dry_run:
                    path.touch(exist_ok=True)

        try:
            f = d / "newfile.txt"
            ns = argparse.Namespace(paths=[str(f)], dry_run=False, allow_outside_cwd=True)
            result = FakeCreate()(ns)
            self.assertIsInstance(result, dict)
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["operations"][0]["operation"], "create")
            self.assertTrue(f.exists())
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()

    def test_dry_run_no_side_effect(self) -> None:
        import tempfile

        d = Path(tempfile.mkdtemp())

        class FakeCreate(MutatingCommand):
            name = "fakecreate"

            def _execute_one(self, path: Any, args: argparse.Namespace, ops: list[dict[str, Any]]) -> None:
                ops.append({"operation": "create", "path": str(path), "dry_run": args.dry_run})
                if not args.dry_run:
                    path.touch(exist_ok=True)

        try:
            f = d / "dry_run_test.txt"
            ns = argparse.Namespace(paths=[str(f)], dry_run=True, allow_outside_cwd=True)
            result = FakeCreate()(ns)
            self.assertEqual(result["operations"][0]["dry_run"], True)
            self.assertFalse(f.exists())
        finally:
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


if __name__ == "__main__":
    unittest.main()
