from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def run_cli(*args: str, cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-m", "agentutils", *args],
        cwd=cwd or ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


class AgentutilsTests(unittest.TestCase):
    def parse_stdout(self, result: subprocess.CompletedProcess[str]) -> dict:
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_catalog_prioritizes_coreutils(self) -> None:
        payload = self.parse_stdout(run_cli("catalog"))
        self.assertTrue(payload["ok"])
        categories = payload["result"]["categories"]
        self.assertEqual(categories[0]["priority"], "P0")
        self.assertIn("ls", categories[0]["tools"])
        self.assertIn("rm", categories[1]["tools"])

    def test_ls_and_stat_emit_json(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "b.txt").write_text("two\n", encoding="utf-8")
            (cwd / "a.txt").write_text("one\n", encoding="utf-8")
            payload = self.parse_stdout(run_cli("ls", ".", cwd=cwd))
            names = [entry["name"] for entry in payload["result"]["entries"]]
            self.assertEqual(names, ["a.txt", "b.txt"])

            stat_payload = self.parse_stdout(run_cli("stat", "a.txt", cwd=cwd))
            self.assertEqual(stat_payload["result"]["entries"][0]["type"], "file")

    def test_readlink_and_test_predicates(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "item.txt"
            target.write_text("content", encoding="utf-8")

            readlink_payload = self.parse_stdout(run_cli("readlink", "--canonicalize", "item.txt", cwd=cwd))
            self.assertEqual(readlink_payload["result"]["entries"][0]["path"], str(target.resolve()))

            test_payload = self.parse_stdout(run_cli("test", "item.txt", "--file", "--non-empty", cwd=cwd))
            self.assertTrue(test_payload["result"]["matches"])

            missing = run_cli("test", "missing.txt", "--exists", "--exit-code", cwd=cwd)
            self.assertEqual(missing.returncode, 1)
            payload = json.loads(missing.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["result"]["matches"])

    def test_path_and_system_context_commands(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "folder").mkdir()
            (cwd / "folder" / "file.txt").write_text("abc", encoding="utf-8")

            base_payload = self.parse_stdout(run_cli("basename", "folder/file.txt", "--suffix", ".txt", cwd=cwd))
            self.assertEqual(base_payload["result"]["entries"][0]["basename"], "file")

            dir_payload = self.parse_stdout(run_cli("dirname", "folder/file.txt", cwd=cwd))
            self.assertEqual(dir_payload["result"]["entries"][0]["dirname"], "folder")

            date_payload = self.parse_stdout(run_cli("date", "--timestamp", "0", "--utc", cwd=cwd))
            self.assertEqual(date_payload["result"]["timestamp"], 0)

            env_payload = self.parse_stdout(run_cli("env", "PYTHONPATH", cwd=cwd))
            self.assertIn("PYTHONPATH", env_payload["result"]["environment"])

            printenv_raw = run_cli("printenv", "PYTHONPATH", "--raw", cwd=cwd)
            self.assertEqual(printenv_raw.returncode, 0, printenv_raw.stderr)
            self.assertIn("src", printenv_raw.stdout)

            for command in ("whoami", "id", "uname", "nproc", "df", "du"):
                payload = self.parse_stdout(run_cli(command, cwd=cwd))
                self.assertTrue(payload["ok"])

    def test_seq_true_false_sleep_and_yes(self) -> None:
        seq_payload = self.parse_stdout(run_cli("seq", "1", "2", "5"))
        self.assertEqual(seq_payload["result"]["lines"], ["1", "3", "5"])

        seq_raw = run_cli("seq", "3", "--raw")
        self.assertEqual(seq_raw.returncode, 0, seq_raw.stderr)
        self.assertEqual(seq_raw.stdout, "1\n2\n3\n")

        self.assertEqual(run_cli("true").returncode, 0)
        false_result = run_cli("false")
        self.assertEqual(false_result.returncode, 1)
        self.assertTrue(json.loads(false_result.stdout)["ok"])

        sleep_payload = self.parse_stdout(run_cli("sleep", "0", "--dry-run"))
        self.assertTrue(sleep_payload["result"]["dry_run"])

        yes_payload = self.parse_stdout(run_cli("yes", "ok", "--count", "3"))
        self.assertEqual(yes_payload["result"]["lines"], ["ok", "ok", "ok"])

    def test_cat_head_tail_wc_hash(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "note.txt"
            target.write_text("alpha beta\nsecond\nthird\n", encoding="utf-8")

            cat_payload = self.parse_stdout(run_cli("cat", "note.txt", "--max-bytes", "5", cwd=cwd))
            self.assertEqual(cat_payload["result"]["content"], "alpha")
            self.assertTrue(cat_payload["result"]["truncated"])

            head_payload = self.parse_stdout(run_cli("head", "note.txt", "--lines", "2", cwd=cwd))
            self.assertEqual(head_payload["result"]["lines"], ["alpha beta", "second"])

            tail_payload = self.parse_stdout(run_cli("tail", "note.txt", "--lines", "1", cwd=cwd))
            self.assertEqual(tail_payload["result"]["lines"], ["third"])

            wc_payload = self.parse_stdout(run_cli("wc", "note.txt", cwd=cwd))
            self.assertEqual(wc_payload["result"]["totals"]["lines"], 3)
            self.assertEqual(wc_payload["result"]["totals"]["words"], 4)

            hash_payload = self.parse_stdout(run_cli("sha256sum", "note.txt", cwd=cwd))
            digest = hash_payload["result"]["entries"][0]["digest"]
            self.assertEqual(len(digest), 64)
            expected_sha256 = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(digest, expected_sha256,
                             "sha256sum must match hashlib.sha256 of the file bytes")

            md5_payload = self.parse_stdout(run_cli("md5sum", "note.txt", cwd=cwd))
            md5_digest = md5_payload["result"]["entries"][0]["digest"]
            self.assertEqual(len(md5_digest), 32)
            expected_md5 = hashlib.md5(target.read_bytes()).hexdigest()
            self.assertEqual(md5_digest, expected_md5,
                             "md5sum must match hashlib.md5 of the file bytes")

            b2_payload = self.parse_stdout(run_cli("b2sum", "note.txt", cwd=cwd))
            b2_digest = b2_payload["result"]["entries"][0]["digest"]
            self.assertEqual(len(b2_digest), 128)
            expected_b2 = hashlib.blake2b(target.read_bytes()).hexdigest()
            self.assertEqual(b2_digest, expected_b2,
                             "b2sum must match hashlib.blake2b of the file bytes")

    def test_sort_uniq_cut_and_tr(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "rows.txt"
            target.write_text("beta\t2\nalpha\t1\nalpha\t1\n10\tz\n2\ty\n", encoding="utf-8")

            sort_payload = self.parse_stdout(run_cli("sort", "rows.txt", cwd=cwd))
            self.assertEqual(sort_payload["result"]["lines"][0], "10\tz")

            numeric_payload = self.parse_stdout(run_cli("sort", "rows.txt", "--numeric", cwd=cwd))
            self.assertEqual(numeric_payload["result"]["lines"][0], "2\ty")

            uniq_payload = self.parse_stdout(run_cli("uniq", "rows.txt", cwd=cwd))
            records = uniq_payload["result"]["records"]
            self.assertEqual(records[1], {"line": "alpha\t1", "count": 2})

            cut_payload = self.parse_stdout(run_cli("cut", "rows.txt", "--fields", "1", cwd=cwd))
            self.assertEqual(cut_payload["result"]["lines"][:3], ["beta", "alpha", "alpha"])

            tr_payload = self.parse_stdout(run_cli("tr", "ab", "AB", "--path", "rows.txt", cwd=cwd))
            self.assertIn("BetA", tr_payload["result"]["content"])

    def test_raw_pipeline_commands(self) -> None:
        sort_result = run_cli("sort", "--raw", input_text="b\na\n")
        self.assertEqual(sort_result.returncode, 0, sort_result.stderr)
        self.assertEqual(sort_result.stdout, "a\nb\n")

        uniq_result = run_cli("uniq", "--raw", input_text="a\na\nb\n")
        self.assertEqual(uniq_result.returncode, 0, uniq_result.stderr)
        self.assertEqual(uniq_result.stdout, "a\nb\n")

        cut_result = run_cli("cut", "--chars", "1", "--raw", input_text="az\nby\n")
        self.assertEqual(cut_result.returncode, 0, cut_result.stderr)
        self.assertEqual(cut_result.stdout, "a\nb\n")

    def test_base64_and_base32(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            target = cwd / "payload.txt"
            target.write_text("hello", encoding="utf-8")

            b64_payload = self.parse_stdout(run_cli("base64", "payload.txt", cwd=cwd))
            self.assertEqual(b64_payload["result"]["content"], "aGVsbG8=")

            decoded = self.parse_stdout(run_cli("base64", "--decode", input_text="aGVsbG8="))
            self.assertEqual(decoded["result"]["content_text"], "hello")

            decoded_with_newline = self.parse_stdout(run_cli("base64", "--decode", input_text="aGVs\nbG8=\n"))
            self.assertEqual(decoded_with_newline["result"]["content_text"], "hello")

            b32_payload = self.parse_stdout(run_cli("base32", "payload.txt", cwd=cwd))
            self.assertEqual(b32_payload["result"]["content"], "NBSWY3DP")

    def test_invalid_cut_range_is_json_error(self) -> None:
        result = run_cli("cut", "--chars", "x", input_text="abc\n")
        self.assertEqual(result.returncode, 5)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_input")

    def test_mutation_dry_run_and_real_operations(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            dry = self.parse_stdout(run_cli("mkdir", "nested", "--dry-run", cwd=cwd))
            self.assertFalse((cwd / "nested").exists())
            self.assertTrue(dry["result"]["operations"][0]["dry_run"])

            self.parse_stdout(run_cli("mkdir", "nested", cwd=cwd))
            self.assertTrue((cwd / "nested").is_dir())

            self.parse_stdout(run_cli("touch", "nested/file.txt", cwd=cwd))
            self.assertTrue((cwd / "nested" / "file.txt").is_file())

            self.parse_stdout(run_cli("cp", "nested/file.txt", "copy.txt", cwd=cwd))
            self.assertTrue((cwd / "copy.txt").is_file())

            self.parse_stdout(run_cli("mv", "copy.txt", "moved.txt", cwd=cwd))
            self.assertTrue((cwd / "moved.txt").is_file())

            self.parse_stdout(run_cli("rm", "moved.txt", cwd=cwd))
            self.assertFalse((cwd / "moved.txt").exists())

    def test_common_directory_destination_semantics(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "src.txt").write_text("data", encoding="utf-8")
            (cwd / "dest").mkdir()

            cp_payload = self.parse_stdout(run_cli("cp", "src.txt", "dest", cwd=cwd))
            self.assertEqual(Path(cp_payload["result"]["operations"][0]["destination"]).name, "src.txt")
            self.assertEqual((cwd / "dest" / "src.txt").read_text(encoding="utf-8"), "data")

            (cwd / "move.txt").write_text("move", encoding="utf-8")
            mv_payload = self.parse_stdout(run_cli("mv", "move.txt", "dest", cwd=cwd))
            self.assertEqual(Path(mv_payload["result"]["operations"][0]["destination"]).name, "move.txt")
            self.assertFalse((cwd / "move.txt").exists())
            self.assertEqual((cwd / "dest" / "move.txt").read_text(encoding="utf-8"), "move")

            (cwd / "linksource.txt").write_text("link", encoding="utf-8")
            self.parse_stdout(run_cli("ln", "linksource.txt", "dest", cwd=cwd))
            self.assertTrue((cwd / "dest" / "linksource.txt").exists())

    def test_mkdir_parents_accepts_existing_directory(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "existing").mkdir()
            payload = self.parse_stdout(run_cli("mkdir", "existing", "--parents", cwd=cwd))
            self.assertFalse(payload["result"]["operations"][0]["created"])

    def test_more_safe_mutation_commands(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            source = cwd / "source.txt"
            source.write_text("abcdef", encoding="utf-8")

            ln_dry = self.parse_stdout(run_cli("ln", "source.txt", "linked.txt", "--dry-run", cwd=cwd))
            self.assertTrue(ln_dry["result"]["operations"][0]["dry_run"])
            self.assertFalse((cwd / "linked.txt").exists())

            self.parse_stdout(run_cli("ln", "source.txt", "linked.txt", cwd=cwd))
            self.assertTrue((cwd / "linked.txt").exists())

            chmod_dry = self.parse_stdout(run_cli("chmod", "600", "source.txt", "--dry-run", cwd=cwd))
            self.assertEqual(chmod_dry["result"]["operations"][0]["new_mode_octal"], "0o600")

            self.parse_stdout(run_cli("truncate", "source.txt", "--size", "3", cwd=cwd))
            self.assertEqual(source.read_text(encoding="utf-8"), "abc")

            mktemp_payload = self.parse_stdout(run_cli("mktemp", "--prefix", "agent.", "--suffix", ".tmp", cwd=cwd))
            temp_path = Path(mktemp_payload["result"]["path"])
            self.assertTrue(temp_path.exists())

            tee_payload = self.parse_stdout(run_cli("tee", "tee.txt", cwd=cwd, input_text="hello"))
            self.assertEqual(tee_payload["result"]["input_bytes"], 5)
            self.assertEqual((cwd / "tee.txt").read_text(encoding="utf-8"), "hello")

            tee_raw = run_cli("tee", "tee-raw.txt", "--raw", cwd=cwd, input_text="echo")
            self.assertEqual(tee_raw.returncode, 0, tee_raw.stderr)
            self.assertEqual(tee_raw.stdout, "echo")
            self.assertEqual((cwd / "tee-raw.txt").read_text(encoding="utf-8"), "echo")

            empty_dir = cwd / "empty"
            empty_dir.mkdir()
            rmdir_dry = self.parse_stdout(run_cli("rmdir", "empty", "--dry-run", cwd=cwd))
            self.assertTrue(rmdir_dry["result"]["operations"][0]["dry_run"])
            self.assertTrue(empty_dir.exists())
            self.parse_stdout(run_cli("rmdir", "empty", cwd=cwd))
            self.assertFalse(empty_dir.exists())

            self.parse_stdout(run_cli("unlink", "linked.txt", cwd=cwd))
            self.assertFalse((cwd / "linked.txt").exists())

    def test_errors_are_json_on_stderr(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            result = run_cli("cat", "missing.txt", cwd=cwd)
            self.assertEqual(result.returncode, 3)
            self.assertEqual(result.stdout, "")
            payload = json.loads(result.stderr)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["error"]["code"], "not_found")

    def test_usage_errors_are_json_on_stderr(self) -> None:
        result = run_cli("ls", "--bad-option")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        payload = json.loads(result.stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "usage")

    def test_rm_refuses_recursive_directory_without_flag(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "folder").mkdir()
            result = run_cli("rm", "folder", cwd=cwd)
            self.assertEqual(result.returncode, 5)
            payload = json.loads(result.stderr)
            self.assertEqual(payload["error"]["code"], "invalid_input")
            self.assertTrue((cwd / "folder").exists())


if __name__ == "__main__":
    unittest.main()
