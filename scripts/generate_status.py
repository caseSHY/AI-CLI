#!/usr/bin/env python3
"""Generate or verify dynamic fields in CURRENT_STATUS.md.

Usage:
    python scripts/generate_status.py          # check (dry-run) — exit non-zero if stale
    python scripts/generate_status.py --write  # auto-update dynamic fields
    python scripts/generate_status.py --changelog-latest  # print latest CHANGELOG entry
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
README_FILE = ROOT / "README.md"
SERVER_JSON_FILE = ROOT / "server.json"
INIT_FILE = ROOT / "src" / "aicoreutils" / "__init__.py"
CI_WORKFLOW_FILE = ROOT / ".github" / "workflows" / "ci.yml"


def get_package_version() -> str:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "unknown"


def get_init_version() -> str:
    content = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    return match.group(1) if match else "unknown"


def get_server_versions() -> list[str]:
    data = json.loads(SERVER_JSON_FILE.read_text(encoding="utf-8"))
    versions = [str(data.get("version", ""))]
    versions.extend(str(package.get("version", "")) for package in data.get("packages", []))
    return versions


def get_readme_pins() -> list[str]:
    text = README_FILE.read_text(encoding="utf-8")
    return re.findall(r"aicoreutils==(\d+\.\d+\.\d+)", text)


def get_command_count() -> int:
    env = {**subprocess.os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "aicoreutils", "schema"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        timeout=30,
    )
    if result.returncode != 0:
        return 0
    with contextlib.suppress(json.JSONDecodeError, KeyError, TypeError):
        return int(json.loads(result.stdout)["result"]["command_count"])
    return 0


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
    content = CI_WORKFLOW_FILE.read_text(encoding="utf-8")
    return len(re.findall(r"^\s{2}\w[\w-]*:\s*$", content, re.MULTILINE))


def get_ci_coverage_thresholds() -> set[int]:
    content = CI_WORKFLOW_FILE.read_text(encoding="utf-8")
    return {int(match) for match in re.findall(r"--cov-fail-under=(\d+)", content)}


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


def status_has_managed_markers() -> bool:
    text = STATUS_FILE.read_text(encoding="utf-8")
    required_markers = [
        "<!-- status-managed:start cn-baseline -->",
        "<!-- status-managed:end cn-baseline -->",
        "<!-- status-managed:start en-baseline -->",
        "<!-- status-managed:end en-baseline -->",
    ]
    return all(marker in text for marker in required_markers)


def status_mentions_command_count(command_count: int) -> bool:
    text = STATUS_FILE.read_text(encoding="utf-8")
    return f"全部 {command_count} 命令" in text and f"All {command_count} commands" in text


def status_mentions_coverage_threshold(threshold: int) -> bool:
    text = STATUS_FILE.read_text(encoding="utf-8")
    return f"阈值 {threshold}%" in text and f"threshold {threshold}%" in text


def write_status() -> None:
    """Update AUTO-GENERATED fields in CURRENT_STATUS.md."""
    pkg_ver = get_package_version()
    commit = get_git_commit()
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

    # Git commit in verified-target fields only. Historical CI references must not be rewritten.
    text = re.sub(
        r"(\|\s*\*\*验证对象\*\*\s*\|[^\n]*?`)[0-9a-f]{7}(`)",
        rf"\g<1>{commit}\2",
        text,
    )
    text = re.sub(
        r"(\|\s*\*\*Verified target\*\*\s*\|[^\n]*?`)[0-9a-f]{7}(`)",
        rf"\g<1>{commit}\2",
        text,
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
    print(f"Updated: v{pkg_ver}, commit={commit}, {ci_jobs}/{ci_jobs} CI, {sandbox} sandbox tests")


def check() -> int:
    issues = 0
    pkg_ver = get_package_version()
    init_ver = get_init_version()
    command_count = get_command_count()
    coverage_thresholds = get_ci_coverage_thresholds()
    fields = parse_current_status()

    if not status_has_managed_markers():
        print("STALE: CURRENT_STATUS.md is missing status-managed baseline markers")
        issues += 1

    if init_ver != pkg_ver:
        print(f"STALE: __version__={init_ver}, package={pkg_ver}")
        issues += 1
    for server_ver in get_server_versions():
        if server_ver != pkg_ver:
            print(f"STALE: server.json version={server_ver}, package={pkg_ver}")
            issues += 1
    for pin in get_readme_pins():
        if pin != pkg_ver:
            print(f"STALE: README pin={pin}, package={pkg_ver}")
            issues += 1

    if fields.get("version_cn") != pkg_ver:
        print(f"STALE: version_cn={fields.get('version_cn')}, package={pkg_ver}")
        issues += 1
    if fields.get("version_en") != pkg_ver:
        print(f"STALE: version_en={fields.get('version_en')}, package={pkg_ver}")
        issues += 1

    if command_count <= 0:
        print("STALE: command_count could not be read from aicoreutils schema")
        issues += 1
    elif not status_mentions_command_count(command_count):
        print(f"STALE: CURRENT_STATUS.md does not mention command_count={command_count} in both languages")
        issues += 1

    if len(coverage_thresholds) != 1:
        print(f"STALE: inconsistent CI coverage thresholds: {sorted(coverage_thresholds)}")
        issues += 1
    else:
        threshold = next(iter(coverage_thresholds))
        if not status_mentions_coverage_threshold(threshold):
            print(f"STALE: CURRENT_STATUS.md does not mention coverage threshold {threshold}% in both languages")
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
