"""Unit tests for protocol layer: hashing, printf, numfmt, ranges, text utilities."""

from __future__ import annotations

import unittest
from pathlib import Path

from aicoreutils.core.exceptions import AgentError
from aicoreutils.protocol._hashing import HASH_ALGORITHMS, digest_bytes, simple_sum16
from aicoreutils.protocol._numfmt import IEC_UNITS, SI_UNITS, format_numfmt_value, parse_numfmt_value
from aicoreutils.protocol._printf import coerce_printf_value, format_printf, printf_conversions
from aicoreutils.protocol._ranges import alpha_suffix, numeric_suffix, parse_ranges, selected_indexes
from aicoreutils.protocol._system import (
    active_user_entries,
    normalize_command_args,
    parse_signal,
    resolve_group_id,
    resolve_user_id,
    run_subprocess_capture,
    selected_environment,
    split_owner_spec,
    stdin_tty_name,
    subprocess_result,
    system_uptime_seconds,
)
from aicoreutils.protocol._text import (
    count_words,
    decode_standard_escapes,
    expand_tr_set,
    parse_octal_mode,
    split_fields,
    squeeze_repeats,
    unexpand_line,
    wc_for_bytes,
)

# ── _hashing ──


class HashingTests(unittest.TestCase):
    def test_known_algorithms(self) -> None:
        for name in ("md5", "sha1", "sha256", "sha512", "blake2b"):
            self.assertIn(name, HASH_ALGORITHMS)

    def test_digest_bytes_md5(self) -> None:
        result = digest_bytes(b"hello", "md5")
        self.assertEqual(result, "5d41402abc4b2a76b9719d911017c592")

    def test_digest_bytes_sha256(self) -> None:
        result = digest_bytes(b"hello", "sha256")
        self.assertEqual(len(result), 64)

    def test_digest_bytes_unsupported_algorithm(self) -> None:
        with self.assertRaises(AgentError) as ctx:
            digest_bytes(b"data", "nonexistent")
        self.assertEqual(ctx.exception.code, "invalid_input")

    def test_simple_sum16(self) -> None:
        self.assertEqual(simple_sum16(b"abc"), (97 + 98 + 99) & 0xFFFF)

    def test_simple_sum16_empty(self) -> None:
        self.assertEqual(simple_sum16(b""), 0)

    def test_simple_sum16_large(self) -> None:
        self.assertEqual(simple_sum16(b"\xff" * 1000), (255 * 1000) & 0xFFFF)


# ── _printf ──


class PrintfTests(unittest.TestCase):
    def test_conversions_basic(self) -> None:
        self.assertEqual(printf_conversions("%s %d"), ["s", "d"])

    def test_conversions_escaped_percent(self) -> None:
        self.assertEqual(printf_conversions("%% %s"), ["s"])

    def test_conversions_empty(self) -> None:
        self.assertEqual(printf_conversions("hello"), [])

    def test_conversions_incomplete_raises(self) -> None:
        with self.assertRaises(AgentError):
            printf_conversions("hello %")

    def test_conversions_star_raises(self) -> None:
        with self.assertRaises(AgentError):
            printf_conversions("%*d")

    def test_coerce_int(self) -> None:
        self.assertIsInstance(coerce_printf_value("42", "d"), int)

    def test_coerce_float(self) -> None:
        self.assertIsInstance(coerce_printf_value("3.14", "f"), float)

    def test_coerce_string(self) -> None:
        self.assertEqual(coerce_printf_value("hello", "s"), "hello")

    def test_format_string_basic(self) -> None:
        result = format_printf("hello %s", ["world"])
        self.assertEqual(result, "hello world")

    def test_format_integer(self) -> None:
        result = format_printf("%d", ["42"])
        self.assertEqual(result, "42")

    def test_format_values_not_multiple_of_conversions(self) -> None:
        with self.assertRaises(AgentError):
            format_printf("%d %d", ["1"])

    def test_format_no_conversions_with_values(self) -> None:
        with self.assertRaises(AgentError):
            format_printf("hello", ["extra"])

    def test_format_no_conversions_no_values(self) -> None:
        result = format_printf("hello", [])
        self.assertEqual(result, "hello")


# ── _numfmt ──


class NumfmtTests(unittest.TestCase):
    def test_parse_si_kilo(self) -> None:
        self.assertAlmostEqual(parse_numfmt_value("1.5K", "si"), 1500.0)

    def test_parse_si_mega(self) -> None:
        self.assertAlmostEqual(parse_numfmt_value("2M", "si"), 2_000_000.0)

    def test_parse_iec_kilo(self) -> None:
        self.assertAlmostEqual(parse_numfmt_value("1K", "iec"), 1024.0)

    def test_parse_none(self) -> None:
        self.assertAlmostEqual(parse_numfmt_value("123", "none"), 123.0)

    def test_parse_none_with_suffix_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_numfmt_value("1K", "none")

    def test_parse_invalid_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_numfmt_value("notanumber", "si")

    def test_format_si(self) -> None:
        result = format_numfmt_value(1500.0, "si", 1)
        self.assertEqual(result, "1.5K")

    def test_format_iec(self) -> None:
        result = format_numfmt_value(2048.0, "iec", 0)
        self.assertEqual(result, "2Ki")

    def test_format_none(self) -> None:
        result = format_numfmt_value(3.14159, "none", 2)
        self.assertEqual(result, "3.14")

    def test_format_negative_precision_raises(self) -> None:
        with self.assertRaises(AgentError):
            format_numfmt_value(1.0, "si", -1)

    def test_si_units_table(self) -> None:
        self.assertIn("K", SI_UNITS)
        self.assertEqual(SI_UNITS["M"], 1_000_000.0)

    def test_iec_units_table(self) -> None:
        self.assertIn("K", IEC_UNITS)
        self.assertEqual(IEC_UNITS["M"], 1024.0**2)


# ── _ranges ──


class RangesTests(unittest.TestCase):
    def test_alpha_suffix_single(self) -> None:
        self.assertEqual(alpha_suffix(0, 1), "a")
        self.assertEqual(alpha_suffix(25, 1), "z")

    def test_alpha_suffix_double(self) -> None:
        self.assertEqual(alpha_suffix(0, 2), "aa")
        self.assertEqual(alpha_suffix(26, 2), "ba")

    def test_alpha_suffix_exceeds_limit(self) -> None:
        with self.assertRaises(AgentError):
            alpha_suffix(26, 1)  # 26 = 'aa' which needs width 2

    def test_alpha_suffix_invalid_width(self) -> None:
        with self.assertRaises(AgentError):
            alpha_suffix(0, 0)

    def test_numeric_suffix(self) -> None:
        self.assertEqual(numeric_suffix(5, 3), "005")

    def test_numeric_suffix_exceeds_width(self) -> None:
        with self.assertRaises(AgentError):
            numeric_suffix(1000, 3)

    def test_numeric_suffix_invalid_width(self) -> None:
        with self.assertRaises(AgentError):
            numeric_suffix(0, 0)

    def test_parse_ranges_single(self) -> None:
        self.assertEqual(parse_ranges("3"), [(3, 3)])

    def test_parse_ranges_range(self) -> None:
        self.assertEqual(parse_ranges("1-3"), [(1, 3)])

    def test_parse_ranges_multiple(self) -> None:
        self.assertEqual(parse_ranges("1-3,7"), [(1, 3), (7, 7)])

    def test_parse_ranges_start_negative_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_ranges("0")  # 1-based, 0 is invalid

    def test_parse_ranges_reversed_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_ranges("5-2")

    def test_parse_ranges_empty_item_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_ranges("1,,3")

    def test_selected_indexes_basic(self) -> None:
        result = selected_indexes(10, [(1, 3)])
        self.assertEqual(result, [0, 1, 2])

    def test_selected_indexes_open_start(self) -> None:
        ranges = [(None, 3)]
        result = selected_indexes(5, ranges)
        self.assertEqual(result, [0, 1, 2])

    def test_selected_indexes_open_end(self) -> None:
        ranges = [(3, None)]
        result = selected_indexes(5, ranges)
        self.assertEqual(result, [2, 3, 4])

    def test_selected_indexes_no_duplicates(self) -> None:
        result = selected_indexes(10, [(1, 5), (3, 7)])
        self.assertEqual(result, [0, 1, 2, 3, 4, 5, 6])


# ── _text ──


class TextUtilsTests(unittest.TestCase):
    def test_decode_standard_escapes_newline(self) -> None:
        self.assertEqual(decode_standard_escapes("a\\nb"), "a\nb")

    def test_decode_standard_escapes_tab(self) -> None:
        self.assertEqual(decode_standard_escapes("a\\tb"), "a\tb")

    def test_decode_standard_escapes_hex(self) -> None:
        self.assertEqual(decode_standard_escapes("\\x41"), "A")

    def test_decode_standard_escapes_no_escape(self) -> None:
        self.assertEqual(decode_standard_escapes("hello"), "hello")

    def test_parse_octal_mode_valid(self) -> None:
        self.assertEqual(parse_octal_mode("644"), 0o644)
        self.assertEqual(parse_octal_mode("0o755"), 0o755)

    def test_parse_octal_mode_invalid(self) -> None:
        with self.assertRaises(AgentError):
            parse_octal_mode("999")
        with self.assertRaises(AgentError):
            parse_octal_mode("u+x")

    def test_count_words(self) -> None:
        self.assertEqual(count_words("hello world"), 2)
        self.assertEqual(count_words("a b c"), 3)

    def test_wc_for_bytes(self) -> None:
        data = b"hello\nworld\n"
        result = wc_for_bytes(data, encoding="utf-8")
        self.assertEqual(result["bytes"], 12)
        self.assertEqual(result["lines"], 2)
        self.assertEqual(result["words"], 2)

    # ── _system ──

    def test_split_fields_tab(self) -> None:
        self.assertEqual(split_fields("a\tb\tc", "\t"), ["a", "b", "c"])

    def test_split_fields_whitespace(self) -> None:
        self.assertEqual(split_fields("a  b  c", None), ["a", "b", "c"])

    def test_squeeze_repeats(self) -> None:
        result = squeeze_repeats("aaabbbccc", set("ab"))
        self.assertEqual(result, "abccc")

    def test_squeeze_repeats_empty(self) -> None:
        self.assertEqual(squeeze_repeats("", set("a")), "")

    def test_expand_tr_set_range(self) -> None:
        self.assertEqual(expand_tr_set("a-z"), "abcdefghijklmnopqrstuvwxyz")

    def test_expand_tr_set_literal(self) -> None:
        self.assertEqual(expand_tr_set("abc"), "abc")

    def test_expand_tr_set_reversed_range_ignored(self) -> None:
        result = expand_tr_set("z-a")
        self.assertEqual(result, "z-a")

    def test_unexpand_line_leading_spaces(self) -> None:
        result = unexpand_line("        hello", tab_size=8, all_blanks=False)
        self.assertEqual(result, "\thello")

    def test_unexpand_line_no_leading_spaces(self) -> None:
        result = unexpand_line("hello", tab_size=4, all_blanks=False)
        self.assertEqual(result, "hello")

    def test_unexpand_line_all_blanks(self) -> None:
        result = unexpand_line("hello        world", tab_size=8, all_blanks=True)
        self.assertIn("\t", result)

    def test_decode_escapes_double_backslash(self) -> None:
        self.assertEqual(decode_standard_escapes("\\\\"), "\\")

    def test_decode_escapes_non_special_follow(self) -> None:
        self.assertEqual(decode_standard_escapes("\\q"), "q")

    def test_parse_octal_mode_empty(self) -> None:
        with self.assertRaises(AgentError):
            parse_octal_mode("")

    def test_parse_numfmt_unsupported_unit(self) -> None:
        with self.assertRaises(AgentError):
            parse_numfmt_value("1Z", "si")

    def test_parse_numfmt_unsupported_iec_unit(self) -> None:
        with self.assertRaises(AgentError):
            parse_numfmt_value("1Z", "iec")

    def test_format_numfmt_large_ieee(self) -> None:
        result = format_numfmt_value(2_000_000_000_000.0, "si", 1)
        self.assertIn("T", result)

    def test_coerce_printf_char_from_char(self) -> None:
        result = coerce_printf_value("A", "c")
        self.assertEqual(result, "A")

    def test_coerce_printf_invalid_float(self) -> None:
        with self.assertRaises(AgentError):
            coerce_printf_value("not_a_number", "f")

    def test_selected_indexes_end_negative_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_ranges("1-0")


class SystemProtocolTests(unittest.TestCase):
    def test_resolve_user_id_numeric(self) -> None:
        self.assertEqual(resolve_user_id("1000"), 1000)
        self.assertIsNone(resolve_user_id(None))
        self.assertIsNone(resolve_user_id(""))

    def test_resolve_group_id_numeric(self) -> None:
        self.assertEqual(resolve_group_id("1000"), 1000)
        self.assertIsNone(resolve_group_id(None))
        self.assertIsNone(resolve_group_id(""))

    def test_split_owner_spec(self) -> None:
        self.assertEqual(split_owner_spec("1000:1001"), ("1000", "1001"))
        self.assertEqual(split_owner_spec("1000.1001"), ("1000", "1001"))
        self.assertEqual(split_owner_spec("1000"), ("1000", None))
        self.assertEqual(split_owner_spec(":1001"), (None, "1001"))

    def test_split_owner_spec_empty_raises(self) -> None:
        with self.assertRaises(AgentError):
            split_owner_spec(":")

    def test_parse_signal_numeric_and_named(self) -> None:
        self.assertEqual(parse_signal("15"), 15)
        self.assertEqual(parse_signal("TERM"), parse_signal("SIGTERM"))

    def test_parse_signal_unknown_raises(self) -> None:
        with self.assertRaises(AgentError):
            parse_signal("not_a_signal")

    def test_normalize_command_args(self) -> None:
        self.assertEqual(normalize_command_args(["--", "python", "--version"]), ["python", "--version"])
        self.assertEqual(normalize_command_args(["python"]), ["python"])

    def test_normalize_command_args_empty_raises(self) -> None:
        with self.assertRaises(AgentError):
            normalize_command_args([])
        with self.assertRaises(AgentError):
            normalize_command_args(["--"])

    def test_run_subprocess_capture_success(self) -> None:
        import sys

        completed, timed_out = run_subprocess_capture(
            [sys.executable, "-c", "print('ok')"],
            timeout=5,
            max_output_bytes=100,
        )
        self.assertFalse(timed_out)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.returncode, 0)
        self.assertIn(b"ok", completed.stdout)

    def test_run_subprocess_capture_empty_command_raises(self) -> None:
        with self.assertRaises(AgentError):
            run_subprocess_capture([], timeout=1, max_output_bytes=100)

    def test_run_subprocess_capture_negative_output_limit_raises(self) -> None:
        import sys

        with self.assertRaises(AgentError):
            run_subprocess_capture([sys.executable, "--version"], timeout=1, max_output_bytes=-1)

    def test_subprocess_result_truncates_and_base64_encodes(self) -> None:
        import subprocess

        completed = subprocess.CompletedProcess(["cmd"], 0, b"abcdef", b"uvwxyz")
        result = subprocess_result(["cmd"], completed, timed_out=False, max_output_bytes=3)
        self.assertEqual(result["stdout_bytes"], 6)
        self.assertEqual(result["stderr_bytes"], 6)
        self.assertTrue(result["stdout_truncated"])
        self.assertTrue(result["stderr_truncated"])
        self.assertEqual(result["stdout_base64"], "YWJj")
        self.assertEqual(result["stderr_base64"], "dXZ3")

    def test_selected_environment(self) -> None:
        import os

        os.environ["AICOREUTILS_TEST_ENV"] = "value"
        try:
            self.assertEqual(selected_environment(["AICOREUTILS_TEST_ENV"]), {"AICOREUTILS_TEST_ENV": "value"})
            self.assertIn("AICOREUTILS_TEST_ENV", selected_environment(None))
        finally:
            del os.environ["AICOREUTILS_TEST_ENV"]

    def test_active_user_entries_shape(self) -> None:
        entries = active_user_entries()
        self.assertGreaterEqual(len(entries), 1)
        self.assertIn("user", entries[0])
        self.assertIn("terminal", entries[0])
        self.assertEqual(entries[0]["source"], "current_process")

    def test_resolve_user_id_name_success(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        pwd_module = SimpleNamespace(getpwnam=lambda _: SimpleNamespace(pw_uid=501))
        with mock.patch("aicoreutils.protocol._system.importlib.import_module", return_value=pwd_module):
            self.assertEqual(resolve_user_id("alice"), 501)

    def test_resolve_user_id_name_unavailable_raises(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        with (
            mock.patch(
                "aicoreutils.protocol._system.importlib.import_module",
                return_value=SimpleNamespace(getpwnam=None),
            ),
            self.assertRaises(AgentError),
        ):
            resolve_user_id("alice")

    def test_resolve_user_id_name_missing_raises(self) -> None:
        from unittest import mock

        pwd_module = mock.Mock()
        pwd_module.getpwnam.side_effect = KeyError("alice")
        with (
            mock.patch("aicoreutils.protocol._system.importlib.import_module", return_value=pwd_module),
            self.assertRaises(AgentError),
        ):
            resolve_user_id("alice")

    def test_resolve_group_id_name_success(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        grp_module = SimpleNamespace(getgrnam=lambda _: SimpleNamespace(gr_gid=20))
        with mock.patch("aicoreutils.protocol._system.importlib.import_module", return_value=grp_module):
            self.assertEqual(resolve_group_id("staff"), 20)

    def test_resolve_group_id_name_unavailable_raises(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        with (
            mock.patch(
                "aicoreutils.protocol._system.importlib.import_module",
                return_value=SimpleNamespace(getgrnam=None),
            ),
            self.assertRaises(AgentError),
        ):
            resolve_group_id("staff")

    def test_resolve_group_id_name_missing_raises(self) -> None:
        from unittest import mock

        grp_module = mock.Mock()
        grp_module.getgrnam.side_effect = KeyError("staff")
        with (
            mock.patch("aicoreutils.protocol._system.importlib.import_module", return_value=grp_module),
            self.assertRaises(AgentError),
        ):
            resolve_group_id("staff")

    def test_run_subprocess_capture_not_found_raises(self) -> None:
        from unittest import mock

        with (
            mock.patch("aicoreutils.protocol._system.subprocess.run", side_effect=FileNotFoundError()),
            self.assertRaises(AgentError) as ctx,
        ):
            run_subprocess_capture(["missing-command"], timeout=1, max_output_bytes=100)
        self.assertEqual(ctx.exception.code, "not_found")

    def test_run_subprocess_capture_permission_denied_raises(self) -> None:
        from unittest import mock

        with (
            mock.patch("aicoreutils.protocol._system.subprocess.run", side_effect=PermissionError()),
            self.assertRaises(AgentError) as ctx,
        ):
            run_subprocess_capture(["denied-command"], timeout=1, max_output_bytes=100)
        self.assertEqual(ctx.exception.code, "permission_denied")

    def test_run_subprocess_capture_timeout(self) -> None:
        import subprocess
        from unittest import mock

        timeout = subprocess.TimeoutExpired(["slow"], timeout=1, output=b"partial-out", stderr=b"partial-err")
        with mock.patch("aicoreutils.protocol._system.subprocess.run", side_effect=timeout):
            completed, timed_out = run_subprocess_capture(["slow"], timeout=1, max_output_bytes=100)
        self.assertTrue(timed_out)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.stdout, b"partial-out")
        self.assertEqual(completed.stderr, b"partial-err")

    def test_system_uptime_seconds_reads_proc(self) -> None:
        from unittest import mock

        proc_uptime = mock.Mock()
        proc_uptime.exists.return_value = True
        proc_uptime.read_text.return_value = "123.5 456.0"
        with mock.patch("aicoreutils.protocol._system.Path", return_value=proc_uptime):
            self.assertEqual(system_uptime_seconds(), 123.5)

    def test_system_uptime_seconds_returns_none_when_fallbacks_fail(self) -> None:
        from unittest import mock

        proc_uptime = mock.Mock()
        proc_uptime.exists.return_value = False
        with (
            mock.patch("aicoreutils.protocol._system.Path", return_value=proc_uptime),
            mock.patch("aicoreutils.protocol._system.sys.platform", "linux"),
            mock.patch("aicoreutils.protocol._system.cast", side_effect=AttributeError()),
        ):
            self.assertIsNone(system_uptime_seconds())

    def test_stdin_tty_name_non_tty(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        stdin = SimpleNamespace(isatty=lambda: False)
        with mock.patch("aicoreutils.protocol._system.sys.stdin", stdin):
            self.assertIsNone(stdin_tty_name())

    def test_stdin_tty_name_success_and_oserror(self) -> None:
        from types import SimpleNamespace
        from unittest import mock

        stdin = SimpleNamespace(isatty=lambda: True, fileno=lambda: 9)
        with (
            mock.patch("aicoreutils.protocol._system.sys.stdin", stdin),
            mock.patch("aicoreutils.protocol._system.os.ttyname", return_value="/dev/pts/1", create=True),
        ):
            self.assertEqual(stdin_tty_name(), "/dev/pts/1")
        with (
            mock.patch("aicoreutils.protocol._system.sys.stdin", stdin),
            mock.patch("aicoreutils.protocol._system.os.ttyname", side_effect=OSError(), create=True),
        ):
            self.assertIsNone(stdin_tty_name())


class DigestFileTests(unittest.TestCase):
    def test_digest_file_temporary(self) -> None:
        from tempfile import NamedTemporaryFile

        from aicoreutils.protocol._hashing import digest_file

        with NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"hello world")
            f.flush()
            path = Path(f.name)
        try:
            result = digest_file(path, "sha256")
            self.assertEqual(len(result), 64)
            self.assertNotEqual(result, "")
        finally:
            path.unlink()

    def test_digest_file_directory_raises(self) -> None:
        from aicoreutils.protocol._hashing import digest_file

        with self.assertRaises(AgentError) as ctx:
            digest_file(Path("."), "md5")
        self.assertEqual(ctx.exception.code, "invalid_input")


if __name__ == "__main__":
    unittest.main()
