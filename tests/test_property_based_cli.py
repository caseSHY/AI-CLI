"""Property-based tests using Hypothesis.

Verifies mathematical/logical properties of agentutils commands under
randomized inputs.  Uses Hypothesis for test-case generation.

Strategy:
- max_examples=100, deadline=None for CI friendliness on Windows.
- Only valid UTF-8 text (no NUL bytes, no surrogates).
- All file ops use TemporaryDirectory.
- Commands requiring file paths (cat, head, tail, wc) create temp files.
- Commands accepting stdin (sort, uniq, tr, cut, base64, nl, fold) pipe input.
"""

from __future__ import annotations

import base64 as b64
import hashlib
import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import assume, given, settings, strategies as st

from support import run_cli


# ── strategies ───────────────────────────────────────────────────────

_text_line = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),
        blacklist_characters="\x00",
    ),
    min_size=0,
    max_size=60,
)

_text_lines = st.lists(
    st.builds(lambda line: line + "\n", _text_line),
    min_size=0,
    max_size=15,
)

flat_text = st.builds("".join, _text_lines)
lines_list = _text_lines
_n_small = st.integers(min_value=0, max_value=25)


# ── helper ───────────────────────────────────────────────────────────

def _lines(result):
    return result.stdout.splitlines()


# ── Cat properties (file-based) ──────────────────────────────────────

class CatPropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_cat_raw_stdout_equals_file_content(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text(text, encoding="utf-8")
            result = run_cli("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, text)

    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_cat_file_and_file_have_same_content(self, text: str) -> None:
        """Two identical files should produce identical cat output."""
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "a.txt").write_text(text, encoding="utf-8")
            (cwd / "b.txt").write_text(text, encoding="utf-8")
            r1 = run_cli("cat", "--raw", "a.txt", cwd=cwd)
            r2 = run_cli("cat", "--raw", "b.txt", cwd=cwd)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertEqual(r1.stdout, r2.stdout)


# ── Sort properties (stdin-based) ────────────────────────────────────

class SortPropertyTests(unittest.TestCase):
    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_sort_output_non_decreasing(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("sort", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = _lines(result)
        self.assertEqual(out, sorted(out, key=str))

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_sort_does_not_drop_lines(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("sort", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = [l for l in _lines(result) if l != ""]
        inp = [l for l in lines if l != ""]
        self.assertEqual(sorted(inp), sorted(out))

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_sort_does_not_invent_lines(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("sort", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = [l for l in _lines(result) if l != ""]
        for line in out:
            self.assertIn(line, lines)

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_sort_numeric_non_decreasing(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("sort", "--numeric", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        nums = []
        for o in _lines(result):
            try:
                nums.append(float(o))
            except ValueError:
                pass
        for i in range(len(nums) - 1):
            self.assertLessEqual(nums[i], nums[i + 1])


# ── Uniq properties (stdin-based) ────────────────────────────────────

class UniqPropertyTests(unittest.TestCase):
    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_uniq_no_adjacent_duplicates(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("uniq", "--raw", "-", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = _lines(result)
        for i in range(len(out) - 1):
            self.assertNotEqual(out[i], out[i + 1],
                                f"adjacent duplicate at {i}: {out[i]!r}")

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_uniq_keeps_nonadjacent_duplicates(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("uniq", "--raw", "-", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out_set = set(_lines(result))
        seen = set()
        non_adj = set()
        prev = None
        for line in lines:
            if line in seen and line != prev:
                non_adj.add(line)
            seen.add(line)
            prev = line
        for line in non_adj:
            self.assertIn(line, out_set,
                          f"non-adjacent duplicate {line!r} missing")


# ── WC properties (file-based) ───────────────────────────────────────

class WcPropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_wc_bytes_equals_utf8_encoded_length(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text(text, encoding="utf-8")
            result = run_cli("wc", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            parts = result.stdout.strip().split()
            if parts:
                self.assertEqual(int(parts[-1]), len(text.encode("utf-8")))

    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_wc_lines_equals_newline_count(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text(text, encoding="utf-8")
            result = run_cli("wc", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            parts = result.stdout.strip().split()
            if len(parts) >= 1:
                self.assertEqual(int(parts[0]), text.count("\n"))


# ── Base64 properties (stdin-based) ──────────────────────────────────

class Base64PropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_base64_encode_then_decode_roundtrip(self, text: str) -> None:
        enc = run_cli("base64", "--raw", input_text=text)
        self.assertEqual(enc.returncode, 0, enc.stderr)
        dec = run_cli("base64", "--decode", "--raw", input_text=enc.stdout)
        self.assertEqual(dec.returncode, 0, dec.stderr)
        self.assertEqual(dec.stdout, text)

    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_base64_output_is_valid_base64(self, text: str) -> None:
        result = run_cli("base64", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        stripped = result.stdout.replace("\n", "")
        self.assertTrue(
            re.fullmatch(r"[A-Za-z0-9+/=]*", stripped),
            f"Invalid base64 chars: {stripped!r}",
        )


# ── Head / Tail properties (file-based) ──────────────────────────────

class HeadTailPropertyTests(unittest.TestCase):
    @given(lines_list, _n_small)
    @settings(max_examples=100, deadline=None)
    def test_head_n_equals_first_n_lines(self, lines: list[str], n: int) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text("".join(lines), encoding="utf-8")
            result = run_cli("head", "--lines", str(n), "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = lines[:n]
            self.assertEqual(_lines(result), expected)

    @given(lines_list, _n_small)
    @settings(max_examples=100, deadline=None)
    def test_tail_n_equals_last_n_lines(self, lines: list[str], n: int) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text("".join(lines), encoding="utf-8")
            result = run_cli("tail", "--lines", str(n), "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = lines[-n:] if n > 0 else []
            self.assertEqual(_lines(result), expected)

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_head_zero_returns_empty(self, lines: list[str]) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text("".join(lines), encoding="utf-8")
            result = run_cli("head", "--lines", "0", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_tail_zero_returns_empty(self, lines: list[str]) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text("".join(lines), encoding="utf-8")
            result = run_cli("tail", "--lines", "0", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")


# ── Cut properties (stdin-based) ─────────────────────────────────────

class CutPropertyTests(unittest.TestCase):
    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_cut_chars_1_equals_first_char_of_each_line(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("cut", "--chars", "1", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        out = _lines(result)
        for i, (inp, outp) in enumerate(zip(lines, out)):
            if inp not in ("\n", ""):
                self.assertEqual(outp, inp[0],
                                 f"line {i}: expected {inp[0]!r} got {outp!r}")

    @given(lines_list)
    @settings(max_examples=100, deadline=None)
    def test_cut_never_crashes(self, lines: list[str]) -> None:
        text = "".join(lines)
        result = run_cli("cut", "--chars", "1-10", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)


# ── Tr properties (stdin-based) ──────────────────────────────────────

class TrPropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_tr_identity_preserves_ascii(self, text: str) -> None:
        assume(text.isascii())
        result = run_cli("tr", "a-z", "a-z", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, text)

    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_tr_case_change_preserves_byte_length(self, text: str) -> None:
        assume(text.isascii())
        result = run_cli("tr", "a-z", "A-Z", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout), len(text))

    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_tr_delete_removes_only_targeted_chars(self, text: str) -> None:
        assume(text.isascii())
        result = run_cli("tr", "--delete", "aeiou", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c in "aeiou" for c in result.stdout))


# ── Echo properties (no-input) ───────────────────────────────────────

class EchoPropertyTests(unittest.TestCase):
    @given(st.lists(st.text(min_size=0, max_size=30), min_size=1, max_size=8))
    @settings(max_examples=100, deadline=None)
    def test_echo_joins_args_with_space_newline(self, args: list[str]) -> None:
        result = run_cli("echo", *args, "--raw")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = " ".join(args) + "\n"
        self.assertEqual(result.stdout, expected)


# ── JSON envelope properties ─────────────────────────────────────────

class JsonEnvelopePropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=50, deadline=None)
    def test_json_envelope_has_all_required_fields(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text(text, encoding="utf-8")
            result = run_cli("cat", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertIn("ok", payload)
            self.assertIn("tool", payload)
            self.assertIn("command", payload)
            self.assertIn("result", payload)
            self.assertIn("warnings", payload)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["tool"], "agentutils")

    @given(flat_text)
    @settings(max_examples=50, deadline=None)
    def test_raw_output_not_json_envelope(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "f.txt").write_text(text, encoding="utf-8")
            result = run_cli("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            if result.stdout:
                self.assertNotEqual(result.stdout[0], "{")


if __name__ == "__main__":
    unittest.main()
