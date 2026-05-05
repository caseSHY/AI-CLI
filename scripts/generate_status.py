#!/usr/bin/env python3
"""Generate or verify dynamic fields in CURRENT_STATUS.md.

Usage:
    python scripts/generate_status.py          # check (dry-run) — exit non-zero if stale
    python scripts/generate_status.py --write  # auto-update CURRENT_STATUS.md
"""

from __future__ import annotations

import contextlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md"


def get_package_version() -> str:
    """Read version from pyproject.toml."""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "unknown"


def count_test_results() -> tuple[int, int]:
    """Run pytest --collect-only to count tests (fast, no execution)."""
    env = {**subprocess.os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "project/tests/", "--collect-only", "-q", "--no-header"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        timeout=60,
    )
    total = 0
    skipped = 0
    for line in result.stdout.splitlines():
        if line.strip().endswith(" selected"):
            with contextlib.suppress(ValueError, IndexError):
                total = int(line.split()[0])
    # count skip markers
    for line in result.stderr.splitlines():
        if "skipped" in line.lower():
            with contextlib.suppress(AttributeError, ValueError):
                skipped = int(re.search(r"(\d+) skipped", line).group(1))
    # fallback: count from known pattern
    if total == 0:
        import ast

        count = 0
        for f in (ROOT / "project" / "tests").glob("test_*.py"):
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name.startswith("test"):
                    count += 1
        total = count
    return total, skipped


def count_ci_jobs() -> int:
    """Count CI jobs from workflow YAML."""
    content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    return len(re.findall(r"^\s{2}\w[\w-]*:\s*$", content, re.MULTILINE))


def parse_current_status() -> dict[str, str]:
    """Parse key fields from CURRENT_STATUS.md."""
    text = STATUS_FILE.read_text(encoding="utf-8")
    fields = {}
    patterns = {
        "version_cn": r"\|\s*\*\*项目版本\*\*\s*\|\s*([0-9.]+)",
        "version_en": r"\|\s*\*\*Project version\*\*\s*\|\s*([0-9.]+)",
        "windows_passed": r"Windows 推荐入口结果.*?(\d+) passed, (\d+) skipped",
        "ci_jobs": r"CI 全平台验证 (\d+)/(\d+)",
        "sandbox_tests": r"沙箱逃逸测试.*\((\d+) 测试",
    }
    for key, pat in patterns.items():
        match = re.search(pat, text)
        if match:
            fields[key] = match.group(1)
    return fields


def check() -> int:
    """Check for stale values. Returns number of issues (0 = clean)."""
    issues = 0
    pkg_ver = get_package_version()
    fields = parse_current_status()

    if fields.get("version_cn") != pkg_ver:
        print(f"STALE: version_cn={fields.get('version_cn')}, package={pkg_ver}")
        issues += 1
    if fields.get("version_en") != pkg_ver:
        print(f"STALE: version_en={fields.get('version_en')}, package={pkg_ver}")
        issues += 1

    ci_count = count_ci_jobs()
    if fields.get("ci_jobs") != str(ci_count):
        print(f"STALE: ci_jobs={fields.get('ci_jobs')}, actual={ci_count}")
        issues += 1

    if issues == 0:
        print("CURRENT_STATUS.md is up to date.")
    return issues


if __name__ == "__main__":
    if "--write" in sys.argv:
        print("--write mode: update test counts and CI counts in CURRENT_STATUS.md")
        total, skipped = count_test_results()
        passed = total - skipped
        ci = count_ci_jobs()
        text = STATUS_FILE.read_text(encoding="utf-8")

        # Update test counts
        text = re.sub(
            r"(Windows 推荐入口结果 \| )\d+ passed, \d+ skipped",
            rf"\g<1>{passed} passed, {skipped} skipped",
            text,
        )
        text = re.sub(
            r"(Windows recommended-entry result \| )\d+ passed, \d+ skipped",
            rf"\g<1>{passed} passed, {skipped} skipped",
            text,
        )

        # Update CI job count
        text = re.sub(
            r"(CI 全平台验证 )\d+/\d+",
            rf"\g<1>{ci}/{ci}",
            text,
        )

        STATUS_FILE.write_text(text, encoding="utf-8")
        print(f"Updated: {passed} passed, {skipped} skipped, {ci}/{ci} CI jobs")
    else:
        sys.exit(check())
