"""GNU differential tests — compare agentutils raw output against GNU coreutils.

Each test compares agentutils --raw stdout and exit code against the
equivalent GNU coreutils command.  If a GNU command is not found via
shutil.which() the test is skipped.

File-based commands (cat, head, tail, wc, paste, join, comm) use TemporaryDirectory.
Stdin-based commands (sort, uniq, cut, tr, base64, nl, fold) pipe input directly.
No-input commands (seq, printf) call directly.

Strategy for stderr:
- On success (returncode 0) both GNU and agentutils stderr should be empty.
- On error we only compare exit codes, never exact stderr text.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import run_cli as _run_agent

# ── helpers ──────────────────────────────────────────────────────────


def find_gnu(name: str) -> str | None:
    return shutil.which(name)


def run_gnu(
    args: list[str],
    *,
    input_text: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    exe = find_gnu(args[0])
    assert exe is not None, f"GNU {args[0]} not found"
    return subprocess.run(
        [exe, *args[1:]], cwd=cwd, input=input_text,
        text=True, capture_output=True, check=False,
    )


def run_agent_raw(*args: str, input_text: str | None = None, cwd: Path | None = None):
    return _run_agent(*args, input_text=input_text, cwd=cwd)


def skip_if_no_gnu(cmd: str) -> None:
    if find_gnu(cmd) is None:
        raise unittest.SkipTest(f"GNU {cmd!r} not available")


def _nl(s: str | None) -> str:
    if s is None:
        return ""
    return s.replace("\r\n", "\n")


def _write(cwd: Path, name: str, text: str) -> Path:
    p = cwd / name
    p.write_text(text, encoding="utf-8")
    return p


# ── Cat (file-based) ─────────────────────────────────────────────────


class GnuCatDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("cat")

    def test_cat_plain_text_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "hello world\nsecond line\n")
            g = run_gnu(["cat", "f.txt"], cwd=cwd)
            a = run_agent_raw("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))
            self.assertEqual(g.stderr, a.stderr)

    def test_cat_no_trailing_newline_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "no newline at end")
            g = run_gnu(["cat", "f.txt"], cwd=cwd)
            a = run_agent_raw("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cat_utf8_chinese_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "你好世界\n中文测试\n")
            g = run_gnu(["cat", "f.txt"], cwd=cwd)
            a = run_agent_raw("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cat_multiple_empty_lines_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "\n\n\n\n")
            g = run_gnu(["cat", "f.txt"], cwd=cwd)
            a = run_agent_raw("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cat_empty_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "")
            g = run_gnu(["cat", "f.txt"], cwd=cwd)
            a = run_agent_raw("cat", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Sort (stdin-based) ───────────────────────────────────────────────


class GnuSortDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("sort")

    def test_sort_plain(self) -> None:
        text = "b\na\nc\n"
        g = run_gnu(["sort"], input_text=text)
        a = run_agent_raw("sort", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_sort_duplicates(self) -> None:
        text = "b\na\nb\na\nc\n"
        g = run_gnu(["sort"], input_text=text)
        a = run_agent_raw("sort", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_sort_dictionary_default(self) -> None:
        text = "10\n2\n1\n20\n"
        g = run_gnu(["sort"], input_text=text)
        a = run_agent_raw("sort", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_sort_numeric(self) -> None:
        text = "10\n2\n1\n20\n"
        g = run_gnu(["sort", "-n"], input_text=text)
        # Windows sort.exe does not support -n; skip on non-zero exit
        if g.returncode != 0:
            raise unittest.SkipTest("GNU sort -n not available (likely Windows sort.exe)")
        a = run_agent_raw("sort", "--numeric", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_sort_empty_input(self) -> None:
        g = run_gnu(["sort"], input_text="")
        a = run_agent_raw("sort", "--raw", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_sort_single_line(self) -> None:
        g = run_gnu(["sort"], input_text="only\n")
        a = run_agent_raw("sort", "--raw", input_text="only\n")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    @unittest.skip("Chinese UTF-8 sort comparison unreliable on Windows due to GBK codec issues")
    def test_sort_chinese_utf8(self) -> None:
        text = "你好\n世界\n安康\n"
        g = run_gnu(["sort"], input_text=text)
        a = run_agent_raw("sort", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Uniq (stdin-based) ───────────────────────────────────────────────


class GnuUniqDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("uniq")

    def test_uniq_adjacent_dedup(self) -> None:
        text = "a\na\nb\nb\nc\n"
        g = run_gnu(["uniq"], input_text=text)
        a = run_agent_raw("uniq", "--raw", "-", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_uniq_nonadjacent_kept(self) -> None:
        text = "a\nb\na\n"
        g = run_gnu(["uniq"], input_text=text)
        a = run_agent_raw("uniq", "--raw", "-", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_uniq_empty_input(self) -> None:
        g = run_gnu(["uniq"], input_text="")
        a = run_agent_raw("uniq", "--raw", "-", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_uniq_all_same(self) -> None:
        text = "x\nx\nx\nx\n"
        g = run_gnu(["uniq"], input_text=text)
        a = run_agent_raw("uniq", "--raw", "-", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── WC (file-based) ──────────────────────────────────────────────────


class GnuWcDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("wc")

    def _assert_wc(self, text: str) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", text)
            g = run_gnu(["wc", "f.txt"], cwd=cwd)
            a = run_agent_raw("wc", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode, f"exit code mismatch: gnu={g.returncode} agent={a.returncode}")
            pg = _nl(g.stdout).strip().split()
            pa = _nl(a.stdout).strip().split()
            self.assertEqual(len(pg), len(pa), f"wc output format mismatch: gnu={pg!r} agent={pa!r}")
            if len(pg) >= 3:
                self.assertEqual(int(pg[0]), int(pa[0]), f"lines mismatch for {text!r}")
                self.assertEqual(int(pg[1]), int(pa[1]), f"words mismatch for {text!r}")
                self.assertEqual(int(pg[2]), int(pa[2]), f"bytes mismatch for {text!r}")

    def test_wc_plain_text(self) -> None:
        self._assert_wc("hello world\nsecond line\n")

    def test_wc_empty_file(self) -> None:
        self._assert_wc("")

    def test_wc_chinese_text(self) -> None:
        self._assert_wc("你好世界\n测试\n")

    def test_wc_only_newlines(self) -> None:
        self._assert_wc("\n\n\n")


# ── Head / Tail (file-based) ─────────────────────────────────────────


class GnuHeadTailDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        if find_gnu("head") is None or find_gnu("tail") is None:
            raise unittest.SkipTest("GNU head/tail not available")

    def test_head_first_n(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\nc\nd\ne\n")
            g = run_gnu(["head", "-n", "3", "f.txt"], cwd=cwd)
            a = run_agent_raw("head", "--lines", "3", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_head_n_larger_than_input(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\n")
            g = run_gnu(["head", "-n", "10", "f.txt"], cwd=cwd)
            a = run_agent_raw("head", "--lines", "10", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_head_zero_lines(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\n")
            g = run_gnu(["head", "-n", "0", "f.txt"], cwd=cwd)
            a = run_agent_raw("head", "--lines", "0", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_head_empty_file(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "")
            g = run_gnu(["head", "-n", "3", "f.txt"], cwd=cwd)
            a = run_agent_raw("head", "--lines", "3", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tail_last_n(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\nc\nd\ne\n")
            g = run_gnu(["tail", "-n", "3", "f.txt"], cwd=cwd)
            a = run_agent_raw("tail", "--lines", "3", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tail_n_larger_than_input(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\n")
            g = run_gnu(["tail", "-n", "10", "f.txt"], cwd=cwd)
            a = run_agent_raw("tail", "--lines", "10", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tail_zero_lines(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "f.txt", "a\nb\n")
            g = run_gnu(["tail", "-n", "0", "f.txt"], cwd=cwd)
            a = run_agent_raw("tail", "--lines", "0", "--raw", "f.txt", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Cut (stdin-based) ────────────────────────────────────────────────


class GnuCutDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("cut")

    def test_cut_chars_range(self) -> None:
        text = "abcdef\n123456\n"
        g = run_gnu(["cut", "-c", "1-3"], input_text=text)
        a = run_agent_raw("cut", "--chars", "1-3", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cut_chars_list(self) -> None:
        text = "abcdef\n123456\n"
        g = run_gnu(["cut", "-c", "1,3,5"], input_text=text)
        a = run_agent_raw("cut", "--chars", "1,3,5", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cut_fields_tab(self) -> None:
        text = "a\tb\tc\n1\t2\t3\n"
        g = run_gnu(["cut", "-f", "2"], input_text=text)
        a = run_agent_raw("cut", "--fields", "2", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cut_short_line(self) -> None:
        text = "a\nabcdef\nxy\n"
        g = run_gnu(["cut", "-c", "3-5"], input_text=text)
        a = run_agent_raw("cut", "--chars", "3-5", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_cut_empty_line(self) -> None:
        text = "abc\n\n123\n"
        g = run_gnu(["cut", "-c", "1"], input_text=text)
        a = run_agent_raw("cut", "--chars", "1", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Tr (stdin-based) ─────────────────────────────────────────────────


class GnuTrDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("tr")

    def test_tr_char_replace(self) -> None:
        g = run_gnu(["tr", "a-z", "A-Z"], input_text="hello world\n")
        a = run_agent_raw("tr", "a-z", "A-Z", "--raw", input_text="hello world\n")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tr_delete_chars(self) -> None:
        g = run_gnu(["tr", "-d", "a-z"], input_text="hello 123\n")
        a = run_agent_raw("tr", "--delete", "a-z", "--raw", input_text="hello 123\n")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tr_squeeze_repeats(self) -> None:
        g = run_gnu(["tr", "-s", " "], input_text="hello   world\n")
        a = run_agent_raw("tr", "--squeeze", " ", "--raw", input_text="hello   world\n")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_tr_empty_input(self) -> None:
        g = run_gnu(["tr", "a-z", "A-Z"], input_text="")
        a = run_agent_raw("tr", "a-z", "A-Z", "--raw", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Seq (no-input) ───────────────────────────────────────────────────


class GnuSeqDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("seq")

    def test_seq_single_arg(self) -> None:
        g = run_gnu(["seq", "3"])
        a = run_agent_raw("seq", "3", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_seq_first_last(self) -> None:
        g = run_gnu(["seq", "1", "5"])
        a = run_agent_raw("seq", "1", "5", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_seq_with_increment(self) -> None:
        g = run_gnu(["seq", "1", "2", "5"])
        a = run_agent_raw("seq", "1", "2", "5", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_seq_decrement(self) -> None:
        g = run_gnu(["seq", "5", "-1", "1"])
        a = run_agent_raw("seq", "5", "-1", "1", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Base64 (stdin-based) ─────────────────────────────────────────────


class GnuBase64DifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("base64")

    def test_base64_encode_hello(self) -> None:
        g = run_gnu(["base64"], input_text="hello")
        a = run_agent_raw("base64", "--raw", input_text="hello")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_base64_encode_empty(self) -> None:
        g = run_gnu(["base64"], input_text="")
        a = run_agent_raw("base64", "--raw", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_base64_encode_multiline(self) -> None:
        text = "line one\nline two\nthird line\n"
        g = run_gnu(["base64"], input_text=text)
        a = run_agent_raw("base64", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_base64_decode(self) -> None:
        encoded = "aGVsbG8gd29ybGQ=\n"
        g = run_gnu(["base64", "-d"], input_text=encoded)
        a = run_agent_raw("base64", "--decode", "--raw", input_text=encoded)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Printf (no-input) ────────────────────────────────────────────────


class GnuPrintfDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("printf")

    def test_printf_string(self) -> None:
        g = run_gnu(["printf", "hello %s\\n", "world"])
        a = run_agent_raw("printf", "hello %s\\n", "world", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_printf_integer(self) -> None:
        g = run_gnu(["printf", "%d %d\\n", "42", "-7"])
        a = run_agent_raw("printf", "%d %d\\n", "42", "-7", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_printf_escaped_newline(self) -> None:
        g = run_gnu(["printf", "a\\nb\\n"])
        a = run_agent_raw("printf", "a\\nb\\n", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_printf_zeropad(self) -> None:
        g = run_gnu(["printf", "%03d\\n", "7"])
        a = run_agent_raw("printf", "%03d\\n", "7", "--raw")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Fold (stdin-based) ───────────────────────────────────────────────


class GnuFoldDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("fold")

    def test_fold_custom_width(self) -> None:
        g = run_gnu(["fold", "-w", "5"], input_text="abcdefghij\n")
        a = run_agent_raw("fold", "--width", "5", "--break-words", "--raw", "-", input_text="abcdefghij\n")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_fold_empty_input(self) -> None:
        g = run_gnu(["fold"], input_text="")
        a = run_agent_raw("fold", "--raw", "-", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Nl (stdin-based) ─────────────────────────────────────────────────


class GnuNlDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("nl")

    def test_nl_plain(self) -> None:
        text = "alpha\nbeta\ngamma\n"
        g = run_gnu(["nl"], input_text=text)
        a = run_agent_raw("nl", "--raw", "-", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_nl_empty_input(self) -> None:
        g = run_gnu(["nl"], input_text="")
        a = run_agent_raw("nl", "--raw", "-", input_text="")
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Paste (file-based) ───────────────────────────────────────────────


class GnuPasteDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("paste")

    def test_paste_two_files(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "a.txt", "1\n2\n3\n")
            _write(cwd, "b.txt", "x\ny\nz\n")
            g = run_gnu(["paste", "a.txt", "b.txt"], cwd=cwd)
            a = run_agent_raw("paste", "a.txt", "b.txt", "--raw", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))

    def test_paste_with_delimiter(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "a.txt", "1\n2\n")
            _write(cwd, "b.txt", "x\ny\n")
            g = run_gnu(["paste", "-d", "|", "a.txt", "b.txt"], cwd=cwd)
            a = run_agent_raw("paste", "--delimiter", "|", "a.txt", "b.txt", "--raw", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Join (file-based) ────────────────────────────────────────────────


class GnuJoinDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("join")

    def test_join_matching_key(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "left.txt", "1 Alice\n2 Bob\n")
            _write(cwd, "right.txt", "1 Dev\n2 Ops\n")
            g = run_gnu(["join", "left.txt", "right.txt"], cwd=cwd)
            a = run_agent_raw("join", "left.txt", "right.txt", "--raw", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))


# ── Comm (file-based) ────────────────────────────────────────────────


class GnuCommDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("comm")

    def test_comm_plain(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            _write(cwd, "left.txt", "a\nb\nc\n")
            _write(cwd, "right.txt", "b\nd\n")
            g = run_gnu(["comm", "left.txt", "right.txt"], cwd=cwd)
            a = run_agent_raw("comm", "left.txt", "right.txt", "--raw", cwd=cwd)
            self.assertEqual(g.returncode, a.returncode)
            self.assertEqual(_nl(g.stdout), _nl(a.stdout))


if __name__ == "__main__":
    unittest.main()
