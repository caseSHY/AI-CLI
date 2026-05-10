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

    def test_stty_raw(self) -> None:
        if sys.platform == "win32":
            self.skipTest("stty unsupported on Windows")
        args = _parser.parse_args(["stty", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_stty_dash_dash_separator(self) -> None:
        if sys.platform == "win32":
            self.skipTest("stty unsupported on Windows")
        args = _parser.parse_args(["stty", "--dry-run", "--", "echo"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class FactorEdgeCaseTests(unittest.TestCase):
    def test_factor_non_integer_raises(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["factor", "abc"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_factor_exceeds_max_value_raises(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["factor", "99999999999999999999999"])
        with self.assertRaises(AgentError):
            args.func(args)


class ExprEdgeCaseTests(unittest.TestCase):
    def test_expr_invalid_syntax_raises(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["expr", "1", "+"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")


class ExprOperatorCoverageTests(unittest.TestCase):
    def test_expr_subtraction(self) -> None:
        args = _parser.parse_args(["expr", "5", "-", "3"])
        result = args.func(args)
        self.assertEqual(result["value"], 2)

    def test_expr_multiplication(self) -> None:
        args = _parser.parse_args(["expr", "2", "*", "3"])
        result = args.func(args)
        self.assertEqual(result["value"], 6)

    def test_expr_division(self) -> None:
        args = _parser.parse_args(["expr", "6", "/", "2"])
        result = args.func(args)
        self.assertEqual(result["value"], 3.0)

    def test_expr_modulo(self) -> None:
        args = _parser.parse_args(["expr", "7", "%", "3"])
        result = args.func(args)
        self.assertEqual(result["value"], 1)

    def test_expr_power(self) -> None:
        args = _parser.parse_args(["expr", "2", "**", "3"])
        result = args.func(args)
        self.assertEqual(result["value"], 8)

    def test_expr_not_equal(self) -> None:
        args = _parser.parse_args(["expr", "1", "!=", "2"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_less_than(self) -> None:
        args = _parser.parse_args(["expr", "1", "<", "2"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_less_equal(self) -> None:
        args = _parser.parse_args(["expr", "1", "<=", "2"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_greater_than(self) -> None:
        args = _parser.parse_args(["expr", "2", ">", "1"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_greater_equal(self) -> None:
        args = _parser.parse_args(["expr", "2", ">=", "1"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_bool_and(self) -> None:
        args = _parser.parse_args(["expr", "1", "and", "0"])
        result = args.func(args)
        self.assertFalse(result["value"])

    def test_expr_bool_or(self) -> None:
        args = _parser.parse_args(["expr", "1", "or", "0"])
        result = args.func(args)
        self.assertTrue(result["value"])

    def test_expr_unary_plus(self) -> None:
        args = _parser.parse_args(["expr", "+1"])
        result = args.func(args)
        self.assertEqual(result["value"], 1)

    def test_expr_unary_minus(self) -> None:
        args = _parser.parse_args(["expr", "-1"])
        result = args.func(args)
        self.assertEqual(result["value"], -1)

    def test_expr_comparison_false(self) -> None:
        args = _parser.parse_args(["expr", "2", ">", "3"])
        result = args.func(args)
        self.assertFalse(result["value"])

    def test_expr_type_error(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["expr", "1", "+", '"a"'])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_expr_division_by_zero(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["expr", "1", "/", "0"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_expr_modulo_by_zero(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["expr", "1", "%", "0"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")


class PathchkEdgeCaseTests(unittest.TestCase):
    def test_pathchk_exit_code(self) -> None:
        args = _parser.parse_args(["pathchk", "--exit-code", "valid.txt"])
        result = args.func(args)
        self.assertTrue(result["valid"])

    def test_pathchk_max_path_length(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["pathchk", "--max-path-length=0", "valid.txt"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_pathchk_max_component_length(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["pathchk", "--max-component-length=0", "valid.txt"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")


class RawModeCoverageTests(unittest.TestCase):
    def test_pinky_raw(self) -> None:
        args = _parser.parse_args(["pinky", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_pinky_users_filter(self) -> None:
        args = _parser.parse_args(["pinky", "no_such_user_xyz"])
        result = args.func(args)
        self.assertEqual(result["entries"][0]["active"], False)

    def test_tty_raw(self) -> None:
        args = _parser.parse_args(["tty", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_users_raw(self) -> None:
        args = _parser.parse_args(["users", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_coreutils_raw(self) -> None:
        args = _parser.parse_args(["coreutils", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_printenv_raw_all(self) -> None:
        args = _parser.parse_args(["printenv", "--raw"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_printenv_raw_filtered(self) -> None:
        args = _parser.parse_args(["printenv", "--raw", "PATH"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_date_format(self) -> None:
        args = _parser.parse_args(["date", "--format=%Y"])
        result = args.func(args)
        self.assertIn("formatted", result)

    def test_date_iso8601_date(self) -> None:
        args = _parser.parse_args(["date", "--iso-8601=date"])
        result = args.func(args)
        self.assertIn("formatted", result)


class SleepEdgeCaseTests(unittest.TestCase):
    def test_sleep_exceeds_max_seconds(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["sleep", "--max-seconds=5", "10"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "unsafe_operation")


class KillEdgeCaseTests(unittest.TestCase):
    def test_kill_invalid_pid(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["kill", "--dry-run", "not_a_pid"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")


class FactorStdinTests(unittest.TestCase):
    def test_factor_from_stdin(self) -> None:
        import io

        saved = sys.stdin
        try:
            sys.stdin = io.StringIO("15 8")
            args = _parser.parse_args(["factor"])
            result = args.func(args)
            self.assertEqual(result["count"], 2)
        finally:
            sys.stdin = saved


class ChconChrootNohupEdgeCaseTests(unittest.TestCase):
    def test_chcon_raw(self) -> None:
        args = _parser.parse_args(["chcon", "--raw", "system_u:object_r:etc_t:s0", "/tmp"])
        result = args.func(args)
        self.assertIsInstance(result, bytes)

    def test_chcon_recursive_dry_run(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sub").mkdir()
            (root / "sub" / "f.txt").write_text("x", encoding="utf-8")
            args = _parser.parse_args(["chcon", "--dry-run", "--recursive", "system_u:object_r:etc_t:s0", str(root)])
            result = args.func(args)
            self.assertGreater(result["count"], 1)

    def test_nohup_output_file_conflict(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            out = root / "nohup.out"
            out.write_text("existing", encoding="utf-8")
            orig = os.getcwd()
            os.chdir(str(root))
            try:
                args = _parser.parse_args(["nohup", f"--output={out}", "echo", "test"])
                with self.assertRaises(AgentError) as ctx:
                    args.func(args)
                self.assertEqual(ctx.exception.code, "conflict")
            finally:
                os.chdir(orig)

    def test_chroot_not_a_directory(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "f.txt"
            f.write_text("x", encoding="utf-8")
            args = _parser.parse_args(["chroot", "--dry-run", str(f), "echo", "test"])
            with self.assertRaises(AgentError) as ctx:
                args.func(args)
            self.assertEqual(ctx.exception.code, "invalid_input")

    def test_chroot_dry_run_with_timeout(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--timeout", "5", "echo", "test"])
            result = args.func(args)
            self.assertTrue(result["dry_run"])

    def test_chroot_dry_run_with_max_output_bytes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--max-output-bytes", "1000", "echo", "test"])
            result = args.func(args)
            self.assertTrue(result["dry_run"])

    def test_chroot_timeout_requires_value(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--timeout"])
            with self.assertRaises(AgentError) as ctx:
                args.func(args)
            self.assertEqual(ctx.exception.code, "usage")

    def test_chroot_timeout_invalid_number(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--timeout", "abc", "echo"])
            with self.assertRaises(AgentError) as ctx:
                args.func(args)
            self.assertEqual(ctx.exception.code, "invalid_input")

    def test_chroot_max_output_bytes_requires_value(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--max-output-bytes"])
            with self.assertRaises(AgentError) as ctx:
                args.func(args)
            self.assertEqual(ctx.exception.code, "usage")

    def test_chroot_max_output_bytes_invalid_integer(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--max-output-bytes", "abc", "echo"])
            with self.assertRaises(AgentError) as ctx:
                args.func(args)
            self.assertEqual(ctx.exception.code, "invalid_input")

    def test_chroot_dry_run_flag_in_remainder(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            args = _parser.parse_args(["chroot", "--dry-run", str(root), "--dry-run", "--allow-chroot", "echo", "test"])
            result = args.func(args)
            self.assertTrue(result["dry_run"])


class RunconRemainderParsingTests(unittest.TestCase):
    def test_runcon_dry_run_with_allow_flag_in_remainder(self) -> None:
        args = _parser.parse_args(
            ["runcon", "--dry-run", "system_u:system_r:init_t:s0", "--allow-context", "echo", "test"]
        )
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_runcon_dry_run_with_timeout_in_remainder(self) -> None:
        args = _parser.parse_args(
            ["runcon", "--dry-run", "system_u:system_r:init_t:s0", "--timeout", "10", "echo", "test"]
        )
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class SleepNegativeTest(unittest.TestCase):
    def test_sleep_negative_seconds(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["sleep", "-1"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")


class TimeoutRealExecutionTests(unittest.TestCase):
    def test_timeout_invalid_seconds(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["timeout", "0", "true"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_timeout_with_true(self) -> None:
        args = _parser.parse_args(["timeout", "0.5", "true"])
        result = args.func(args)
        self.assertIn("returncode", result)


class NiceRealExecutionTests(unittest.TestCase):
    def test_nice_with_true(self) -> None:
        args = _parser.parse_args(["nice", "true"])
        result = args.func(args)
        self.assertIn("returncode", result)


class StdbufExtraTests(unittest.TestCase):
    def test_stdbuf_valid_mode_numeric(self) -> None:
        args = _parser.parse_args(["stdbuf", "--dry-run", "--input=1024", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_stdbuf_valid_mode_suffixed(self) -> None:
        args = _parser.parse_args(["stdbuf", "--dry-run", "--output=2K", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_stdbuf_invalid_mode(self) -> None:
        from aicoreutils.core.exceptions import AgentError

        args = _parser.parse_args(["stdbuf", "--dry-run", "--input=invalid", "echo", "test"])
        with self.assertRaises(AgentError) as ctx:
            args.func(args)
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_stdbuf_real_execution(self) -> None:
        args = _parser.parse_args(["stdbuf", "echo", "test"])
        result = args.func(args)
        self.assertIn("returncode", result)

    def test_stdbuf_unbuffered_output(self) -> None:
        args = _parser.parse_args(["stdbuf", "--dry-run", "--output=0", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])

    def test_stdbuf_unbuffered_error(self) -> None:
        args = _parser.parse_args(["stdbuf", "--dry-run", "--error=0", "echo", "test"])
        result = args.func(args)
        self.assertTrue(result["dry_run"])


class PinkyMatchingUserTest(unittest.TestCase):
    def test_pinky_matching_user(self) -> None:
        import getpass

        current_user = getpass.getuser()
        args = _parser.parse_args(["pinky", current_user])
        result = args.func(args)
        self.assertGreaterEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()


class YesCommandTests(unittest.TestCase):
    def test_yes_count(self) -> None:
        args = _parser.parse_args(["yes", "--count", "2"])
        result = args.func(args)
        self.assertEqual(result["count"], 2)


if __name__ == "__main__":
    unittest.main()
