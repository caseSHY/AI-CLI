#!/usr/bin/env python3
"""Run release-readiness checks before tagging."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: list[str]) -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONIOENCODING": "utf-8"}
    print(f"==> {name}")
    print(" ".join(command))
    result = subprocess.run(command, cwd=str(ROOT), env=env, text=True)
    if result.returncode != 0:
        print(f"FAILED: {name} ({result.returncode})")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AICoreUtils release-readiness checks.")
    parser.add_argument("--full", action="store_true", help="Also run the full project test suite.")
    args = parser.parse_args(argv)

    checks = [
        ("status consistency", [sys.executable, "scripts/generate_status.py"]),
        ("command risk/test matrix", [sys.executable, "scripts/audit_command_matrix.py"]),
        ("command spec pilot", [sys.executable, "scripts/audit_command_specs.py"]),
        ("supply-chain audit", [sys.executable, "scripts/audit_supply_chain.py"]),
        (
            "version and project consistency tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_version_consistency.py",
                "tests/test_project_consistency.py",
                "-q",
                "--tb=short",
            ],
        ),
        ("ruff check", [sys.executable, "-m", "ruff", "check", "src/", "tests/", "tests/", "scripts/"]),
        ("mypy strict", [sys.executable, "-m", "mypy", "src/aicoreutils/", "--strict"]),
    ]
    if args.full:
        checks.append(
            (
                "full tests",
                [sys.executable, "-m", "pytest", "tests/", "tests/", "-q", "--tb=short"],
            )
        )

    for name, command in checks:
        code = run_step(name, command)
        if code != 0:
            return code

    print("Release gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
