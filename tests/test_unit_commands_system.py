"""Unit tests for commands/system/_core.py — via real parser for proper args."""

from __future__ import annotations

import os
import sys
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


class FactorCommandTests(unittest.TestCase):
    def test_factor_basic(self) -> None:
        args = _parser.parse_args(["factor", "12"])
        result = args.func(args)
        self.assertIn("entries", result)
        factors_text = " ".join(str(f) for f in result["entries"][0]["factors"])
        self.assertIn("2", factors_text)
        self.assertIn("3", factors_text)

    def test_factor_prime(self) -> None:
        args = _parser.parse_args(["factor", "7"])
        result = args.func(args)
        self.assertEqual(result["entries"][0]["input"], "7")
        self.assertEqual(result["entries"][0]["factors"], [7])

    def test_factor_raw(self) -> None:
        args = _parser.parse_args(["factor", "--raw", "6"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class ExprCommandTests(unittest.TestCase):
    def test_expr_addition(self) -> None:
        args = _parser.parse_args(["expr", "1", "+", "1"])
        result = args.func(args)
        self.assertEqual(result["value"], 2)

    def test_expr_string_comparison(self) -> None:
        args = _parser.parse_args(["expr", '"abc"', "=", '"abc"'])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_raw(self) -> None:
        args = _parser.parse_args(["expr", "--raw", "1", "+", "1"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class SleepDryRunTests(unittest.TestCase):
    def test_sleep_dry_run(self) -> None:
        args = _parser.parse_args(["sleep", "--dry-run", "10"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_sleep_zero_dry_run(self) -> None:
        args = _parser.parse_args(["sleep", "--dry-run", "0"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class RawModeSystemTests(unittest.TestCase):
    def test_uname_raw(self) -> None:
        args = _parser.parse_args(["uname", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_hostid_raw(self) -> None:
        args = _parser.parse_args(["hostid", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_pathchk_raw(self) -> None:
        args = _parser.parse_args(["pathchk", "--raw", "valid.txt"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_groups_raw(self) -> None:
        args = _parser.parse_args(["groups", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)


class TimeoutNiceStdbufDryRunTests(unittest.TestCase):
    def test_timeout_dry_run(self) -> None:
        args = _parser.parse_args(["timeout", "--dry-run", "1", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_nice_dry_run(self) -> None:
        args = _parser.parse_args(["nice", "--dry-run", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_stdbuf_dry_run(self) -> None:
        args = _parser.parse_args(["stdbuf", "--dry-run", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class SttyNohupChrootTests(unittest.TestCase):
    def test_stty_no_args(self) -> None:
        if sys.platform == "win32":
            self.skipTest("stty unsupported on Windows")
        args = _parser.parse_args(["stty"])
        result = args.func(args)
        self.assertIn("stdin_is_tty", result)

    def test_stty_dry_run(self) -> None:
        if sys.platform == "win32":
            self.skipTest("stty unsupported on Windows")
        args = _parser.parse_args(["stty", "--dry-run", "echo"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])
        self.assertTrue(result["planned"])

    def test_nohup_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            orig = os.getcwd()
            os.chdir(str(root))
            try:
                out = root / "nohup.out"
                args = _parser.parse_args(["nohup", "--dry-run", f"--output={out}", "echo", "test"])
                result = args.func(args)
                self.assertIn("operation", result)
            finally:
                os.chdir(orig)

    def test_kill_dry_run(self) -> None:
        args = _parser.parse_args(["kill", "--dry-run", "1234"])
        result = args.func(args)
        self.assertIn("operations", result)
        self.assertEqual(result["count"], 1)

    def test_chroot_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            args = _parser.parse_args(["chroot", "--dry-run", str(Path(raw)), "echo", "test"])
            result = args.func(args)
            self.assertTrue(result["dry_run"])

    def test_chcon_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["chcon", "--dry-run", "system_u:object_r:etc_t:s0", str(f)])
            result = args.func(args)
            self.assertIn("operations", result)

    def test_runcon_dry_run(self) -> None:
        args = _parser.parse_args(["runcon", "--dry-run", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class YesCommandTests(unittest.TestCase):
    def test_yes_count(self) -> None:
        args = _parser.parse_args(["yes", "--count", "2"])
        result = args.func(args)
        self.assertEqual(result["count"], 2)


if __name__ == "__main__":
    unittest.main()
