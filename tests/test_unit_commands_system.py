"""Unit tests for commands/system/_core.py — via real parser for proper args."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from aicoreutils.parser._parser import build_parser

_parser = build_parser()


class DateCommandTests(unittest.TestCase):
    def test_date_default(self) -> None:
        args = _parser.parse_args(["date"])
        result = args.func(args)
        self.assertIn("iso", result)
        self.assertIn("formatted", result)

    def test_date_utc(self) -> None:
        args = _parser.parse_args(["date", "--utc"])
        result = args.func(args)
        self.assertTrue(result["utc"])

    def test_date_raw(self) -> None:
        args = _parser.parse_args(["date", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class TrueFalseCommandTests(unittest.TestCase):
    def test_true(self) -> None:
        args = _parser.parse_args(["true"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_false(self) -> None:
        args = _parser.parse_args(["false"])
        result = args.func(args)
        self.assertFalse(result["value"])


class WhoamiCommandTests(unittest.TestCase):
    def test_whoami(self) -> None:
        args = _parser.parse_args(["whoami"])
        result = args.func(args)
        self.assertIn("user", result)
        self.assertGreater(len(result["user"]), 0)


class EnvCommandTests(unittest.TestCase):
    def test_env_all(self) -> None:
        args = _parser.parse_args(["env"])
        result = args.func(args)
        self.assertGreater(result["count"], 0)

    def test_env_filter(self) -> None:
        args = _parser.parse_args(["env", "PATH"])
        result = args.func(args)
        self.assertIn("PATH", result["environment"])

    def test_env_raw(self) -> None:
        args = _parser.parse_args(["env", "--raw", "PATH"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class PrintenvCommandTests(unittest.TestCase):
    def test_printenv_all(self) -> None:
        args = _parser.parse_args(["printenv"])
        result = args.func(args)
        self.assertIn("values", result)


class SleepCommandTests(unittest.TestCase):
    def test_sleep_zero(self) -> None:
        args = _parser.parse_args(["sleep", "0"])
        result = args.func(args)
        self.assertTrue(result["slept"])


class PathchkCommandTests(unittest.TestCase):
    def test_pathchk_valid(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "valid.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["pathchk", str(root / "valid.txt")])
            result = args.func(args)
            self.assertIn("entries", result)

    def test_pathchk_nonexistent(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["pathchk", str(root / "nope")])
            result = args.func(args)
            self.assertIn("entries", result)


class CoreutilsCommandTests(unittest.TestCase):
    def test_coreutils_list(self) -> None:
        args = _parser.parse_args(["coreutils", "--list"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)


class UnameCommandTests(unittest.TestCase):
    def test_uname(self) -> None:
        args = _parser.parse_args(["uname"])
        result = args.func(args)
        self.assertIn("system", result)


class IdCommandTests(unittest.TestCase):
    def test_id(self) -> None:
        args = _parser.parse_args(["id"])
        result = args.func(args)
        self.assertIn("uid", result)


class GroupsCommandTests(unittest.TestCase):
    def test_groups(self) -> None:
        args = _parser.parse_args(["groups"])
        result = args.func(args)
        self.assertIsInstance(result, dict)


class TtyCommandTests(unittest.TestCase):
    def test_tty(self) -> None:
        args = _parser.parse_args(["tty"])
        result = args.func(args)
        self.assertIn("stdin_is_tty", result)


class UptimeCommandTests(unittest.TestCase):
    def test_uptime(self) -> None:
        args = _parser.parse_args(["uptime"])
        result = args.func(args)
        self.assertIn("uptime_seconds", result)


class NprocCommandTests(unittest.TestCase):
    def test_nproc(self) -> None:
        args = _parser.parse_args(["nproc"])
        result = args.func(args)
        self.assertIn("count", result)


class HostnameCommandTests(unittest.TestCase):
    def test_hostname(self) -> None:
        args = _parser.parse_args(["hostname"])
        result = args.func(args)
        self.assertIn("hostname", result)


class ArchLognameHostidTests(unittest.TestCase):
    def test_arch(self) -> None:
        args = _parser.parse_args(["arch"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_logname(self) -> None:
        args = _parser.parse_args(["logname"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_hostid(self) -> None:
        args = _parser.parse_args(["hostid"])
        result = args.func(args)
        self.assertIsInstance(result, dict)


class UsersWhoPinkyTests(unittest.TestCase):
    def test_users(self) -> None:
        args = _parser.parse_args(["users"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_who(self) -> None:
        args = _parser.parse_args(["who"])
        result = args.func(args)
        self.assertIsInstance(result, dict)

    def test_pinky(self) -> None:
        args = _parser.parse_args(["pinky"])
        result = args.func(args)
        self.assertIsInstance(result, dict)


class DfDuTests(unittest.TestCase):
    def test_df(self) -> None:
        with TemporaryDirectory() as raw:
            args = _parser.parse_args(["df", raw])
            result = args.func(args)
            self.assertIsInstance(result, dict)

    def test_du(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "f.txt").write_text("hello", encoding="utf-8")
            args = _parser.parse_args(["du", raw])
            result = args.func(args)
            self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
