"""Regenerate golden output files from current agentutils output.

Usage:
    python .github/scripts/update_golden.py

This script runs the commands that produce golden samples and overwrites
the corresponding JSON files in project/tests/golden/.  Use it after making
intentional output changes.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import suppress
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN = ROOT / "project" / "tests" / "golden"

sys.path.insert(0, str(ROOT / "src"))
# Import support module from project/tests/ (not a package, use importlib)
spec = importlib.util.spec_from_file_location("support", str(ROOT / "project" / "tests" / "support.py"))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
run_cli = support.run_cli


SAMPLES: list[tuple[str, list[str], dict | None]] = [
    ("seq_1_2_5.json", ["seq", "1", "2", "5"], None),
    ("base64_hello.json", ["base64"], {"input_text": "hello"}),
    ("stat_readme.json", ["stat", "project/docs/README.md"], None),
    ("wc_counts.json", ["wc", "project/tests/golden/base64_hello.json"], None),
    (
        "cp_dryrun.json",
        ["cp", "project/tests/golden/base64_hello.json", "project/tests/golden/_copy_target.json", "--dry-run"],
        None,
    ),
]


def main() -> None:
    for filename, args, kwargs in SAMPLES:
        kw = kwargs or {}
        result = run_cli(*args, **kw)
        if result.returncode != 0:
            print(f"FAILED {filename}: exit {result.returncode}\n{result.stderr}")
            continue
        # Validate JSON before writing
        with suppress(json.JSONDecodeError):
            json.loads(result.stdout)
        (GOLDEN / filename).write_text(result.stdout, encoding="utf-8")
        print(f"Updated {filename}")


if __name__ == "__main__":
    main()
