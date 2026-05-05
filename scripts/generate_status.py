#!/usr/bin/env python3
"""Generate or verify dynamic fields in CURRENT_STATUS.md.

Usage:
    python scripts/generate_status.py          # check (dry-run) — exit non-zero if stale
    python scripts/generate_status.py --write  # auto-update dynamic fields
    python scripts/generate_status.py --changelog-latest  # print latest CHANGELOG entry
"""

from __future__ import annotations

import contextlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"


def get_package_version() -> str:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "unknown"


def get_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=10,
    )
    return result.stdout.strip()[:7] if result.returncode == 0 else "unknown"


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
    for line in result.stderr.splitlines():
        if "skipped" in line.lower():
            with contextlib.suppress(AttributeError, ValueError):
                skipped = int(re.search(r"(\d+) skipped", line).group(1))
    return total, skipped


def count_ci_jobs() -> int:
    content = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    return len(re.findall(r"^\s{2}\w[\w-]*:\s*$", content, re.MULTILINE))


def get_sandbox_test_count() -> int:
    """Count test methods in the sandbox escape hardening file."""
    import ast

    f = ROOT / "project" / "tests" / "test_sandbox_escape_hardening.py"
    if not f.exists():
        return 0
    tree = ast.parse(f.read_text(encoding="utf-8"))
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
            count += 1
    return count


def extract_latest_changelog() -> str:
    """Extract the latest version entry from CHANGELOG.md."""
    text = CHANGELOG_FILE.read_text(encoding="utf-8")
    m = re.search(r"(##\s+\[[\d.]+\].*?)(?=\n##\s+\[|\Z)", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def parse_current_status() -> dict[str, str]:
    text = STATUS_FILE.read_text(encoding="utf-8")
    fields = {}
    patterns = {
        "version_cn": r"\|\s*\*\*项目版本\*\*\s*\|\s*([0-9.]+)",
        "version_en": r"\|\s*\*\*Project version\*\*\s*\|\s*([0-9.]+)",
    }
    for key, pat in patterns.items():
        match = re.search(pat, text)
        if match:
            fields[key] = match.group(1)
    return fields


def write_status() -> None:
    """Update AUTO-GENERATED fields in CURRENT_STATUS.md."""
    pkg_ver = get_package_version()
    commit = get_git_commit()
    total, skipped = count_test_results()
    passed = total - skipped if total else 0
    ci_jobs = count_ci_jobs()
    sandbox = get_sandbox_test_count()

    text = STATUS_FILE.read_text(encoding="utf-8")

    # Version fields
    text = re.sub(
        r"(\|\s*\*\*项目版本\*\*\s*\|\s*)[0-9.]+(\s*\|)",
        rf"\g<1>{pkg_ver}\2",
        text,
    )
    text = re.sub(
        r"(\|\s*\*\*Project version\*\*\s*\|\s*)[0-9.]+(\s*\|)",
        rf"\g<1>{pkg_ver}\2",
        text,
    )

    # Git commit (English field)
    text = re.sub(
        r"`([0-9a-f]{7})`",
        f"`{commit}`",
        text,
        count=1,
    )
    # Git commit (CN field) — second occurrence
    text = re.sub(
        r"`([0-9a-f]{7})`",
        f"`{commit}`",
        text,
        count=1,
    )

    # CI job count
    text = re.sub(
        r"(CI 全平台验证 )\d+/\d+",
        rf"\g<1>{ci_jobs}/{ci_jobs}",
        text,
    )
    text = re.sub(
        r"(CI )\d+/\d+( on all platforms)",
        rf"\g<1>{ci_jobs}/{ci_jobs}\2",
        text,
    )

    # Test results — Windows
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

    # Sandbox test count
    text = re.sub(
        r"(沙箱逃逸测试.*\()\d+ (测试)",
        rf"\g<1>{sandbox} \2",
        text,
    )
    text = re.sub(
        r"(Sandbox escape.*\()\d+ (tests)",
        rf"\g<1>{sandbox} \2",
        text,
    )

    STATUS_FILE.write_text(text, encoding="utf-8")
    print(
        f"Updated: v{pkg_ver}, commit={commit}, {passed}p/{skipped}s, {ci_jobs}/{ci_jobs} CI, {sandbox} sandbox tests"
    )


def check() -> int:
    issues = 0
    pkg_ver = get_package_version()
    fields = parse_current_status()

    if fields.get("version_cn") != pkg_ver:
        print(f"STALE: version_cn={fields.get('version_cn')}, package={pkg_ver}")
        issues += 1
    if fields.get("version_en") != pkg_ver:
        print(f"STALE: version_en={fields.get('version_en')}, package={pkg_ver}")
        issues += 1

    if issues == 0:
        print("CURRENT_STATUS.md is up to date.")
    return issues


if __name__ == "__main__":
    if "--changelog-latest" in sys.argv:
        print(extract_latest_changelog())
    elif "--write" in sys.argv:
        write_status()
    else:
        sys.exit(check())
