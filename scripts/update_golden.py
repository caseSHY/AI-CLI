"""Regenerate golden output files from current agentutils output.

Usage:
    python scripts/update_golden.py

This script runs the commands that produce golden samples and overwrites
the corresponding JSON files in tests/golden/.  Use it after making
intentional output changes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"

sys.path.insert(0, str(ROOT / "src"))
from tests.support import run_cli


SAMPLES: list[tuple[str, list[str], dict | None]] = [
    ("seq_1_2_5.json", ["seq", "1", "2", "5"], None),
    ("base64_hello.json", ["base64"], {"input_text": "hello"}),
    ("stat_readme.json", ["stat", "docs/README.md"], None),
    ("wc_counts.json", ["wc", "tests/golden/base64_hello.json"], None),
    ("cp_dryrun.json", ["cp", "tests/golden/base64_hello.json", "tests/golden/_copy_target.json", "--dry-run"], None),
]


def main() -> None:
    for filename, args, kwargs in SAMPLES:
        kw = kwargs or {}
        result = run_cli(*args, **kw)
        if result.returncode != 0:
            print(f"FAILED {filename}: exit {result.returncode}\n{result.stderr}")
            continue
        # Validate JSON before writing
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError:
            # --raw output is not JSON — write as-is
            pass
        (GOLDEN / filename).write_text(result.stdout, encoding="utf-8")
        print(f"Updated {filename}")


if __name__ == "__main__":
    main()
