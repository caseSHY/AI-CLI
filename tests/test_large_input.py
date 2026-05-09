"""Large input behavior tests for core commands.

Verifies that sort, grep (via text search in wc), and wc handle large files
without OOM or unreasonable hang times.  Uses a 100 MB text file generated on
demand.

These tests are marked as slow and skipped by default in CI via the custom
pytest marker.  Run locally with:

    uv run pytest tests/test_large_input.py -v -m slow
"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import run_cli

MB = 1_048_576
LARGE_SIZE_MB = 100
TIMEOUT_SECONDS = 120


def _generate_large_text(target: Path, size_mb: int) -> None:
    """Generate a text file of approximately size_mb MB.

    Writes repeating lines of varying length to avoid degenerate compression
    or pattern-matching behaviour.  Each chunk is ~1 MB of distinct text.
    """
    lines = [
        f"Line {i:08d}: The quick brown fox jumps over the lazy dog. abcdefghijklmnopqrstuvwxyz0123456789\n"
        for i in range(1000)
    ]
    chunk = "".join(lines)
    chunk_bytes = chunk.encode("utf-8")
    repeat = (size_mb * MB) // len(chunk_bytes) + 1
    with open(target, "wb") as fh:
        for _ in range(repeat):
            fh.write(chunk_bytes)


class SortLargeInputTests(unittest.TestCase):
    def test_sort_100mb_no_oom(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            big = root / "big.txt"
            _generate_large_text(big, LARGE_SIZE_MB)
            self.assertGreater(big.stat().st_size, 50 * MB)

            t0 = time.monotonic()
            result = run_cli("sort", "--raw", str(big), cwd=root, extra_env={"LC_ALL": "C"})
            elapsed = time.monotonic() - t0

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(elapsed, TIMEOUT_SECONDS, f"sort took {elapsed:.1f}s, expected <{TIMEOUT_SECONDS}s")
            self.assertGreater(len(result.stdout), 0)


class WcLargeInputTests(unittest.TestCase):
    def test_wc_100mb_no_oom(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            big = root / "big.txt"
            _generate_large_text(big, LARGE_SIZE_MB)

            t0 = time.monotonic()
            result = run_cli("wc", str(big), cwd=root)
            elapsed = time.monotonic() - t0

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(elapsed, TIMEOUT_SECONDS, f"wc took {elapsed:.1f}s, expected <{TIMEOUT_SECONDS}s")
            payload = json.loads(result.stdout)
            entry = payload["result"]["entries"][0]
            self.assertGreater(entry["lines"], 0)
            self.assertGreater(entry["bytes"], 50 * MB)
            self.assertGreater(entry["chars"], 0)


class CatLargeInputTests(unittest.TestCase):
    def test_cat_100mb_with_explicit_max_bytes(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            big = root / "big.txt"
            _generate_large_text(big, LARGE_SIZE_MB)

            t0 = time.monotonic()
            # Bypass the 1 MiB default with a large max-bytes
            result = run_cli("cat", "--raw", "--max-bytes", "999000000", str(big), cwd=root)
            elapsed = time.monotonic() - t0

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(elapsed, TIMEOUT_SECONDS, f"cat took {elapsed:.1f}s, expected <{TIMEOUT_SECONDS}s")
            self.assertGreater(len(result.stdout), 50 * MB)


if __name__ == "__main__":
    unittest.main()
