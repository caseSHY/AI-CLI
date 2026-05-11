#!/usr/bin/env python3
"""Check metadata consistency across all project files.

Reads authoritative values from pyproject.toml and verifies they match
every documented location.  Exit 0 if consistent, exit 1 with a report if not.

Usage:
    python scripts/check_metadata_consistency.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── authoritative source ──


def read_pyproject() -> dict[str, str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for key, pattern in [
        ("version", r'version\s*=\s*"([^"]+)"'),
        ("name", r'name\s*=\s*"([^"]+)"'),
        ("repo_url", r'Homepage\s*=\s*"([^"]+)"'),
    ]:
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            meta[key] = m.group(1)
    return meta


# ── check functions ──


def _check(meta: dict[str, str], filepath: str, field: str, actual: str, expected: str) -> list[str]:
    fp = str(ROOT / filepath)
    if actual != expected:
        return [f"{fp}: {field} = {actual!r}, expected {expected!r}"]
    return []


def check_pyproject_self(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    ver = meta.get("version", "")
    if not ver:
        issues.append("pyproject.toml: version not found")
    if not re.match(r"^\d+\.\d+\.\d+$", ver):
        issues.append(f"pyproject.toml: version {ver!r} not in MAJOR.MINOR.PATCH format")
    if meta.get("name") != "aicoreutils":
        issues.append(f"pyproject.toml: name = {meta.get('name')!r}, expected 'aicoreutils'")
    if "github.com/caseSHY/AI-CLI" not in meta.get("repo_url", ""):
        issues.append(f"pyproject.toml: unexpected repo_url = {meta.get('repo_url')!r}")
    return issues


def check_server_json(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    fp = ROOT / "server.json"
    if not fp.exists():
        return []
    data = json.loads(fp.read_text(encoding="utf-8"))
    expected_ver = meta.get("version", "")
    issues += _check(meta, "server.json", "version", data.get("version", ""), expected_ver)
    for i, pkg in enumerate(data.get("packages", [])):
        issues += _check(meta, "server.json", f"packages[{i}].version", pkg.get("version", ""), expected_ver)
    issues += _check(meta, "server.json", "name", data.get("name", ""), "io.github.caseSHY/aicoreutils")
    issues += _check(meta, "server.json", "packages[0].identifier", data["packages"][0]["identifier"], "aicoreutils")
    return issues


def check_readme(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    ver = meta.get("version", "")

    # LTS badge
    badge_m = re.search(r"LTS-([\d.]+)-blue", text)
    if badge_m:
        issues += _check(meta, "README.md", "LTS badge", badge_m.group(1), ver)

    # pip pin
    pin_m = re.search(r"pip install aicoreutils==([\d.]+)", text)
    if pin_m:
        issues += _check(meta, "README.md", "pip install pin", pin_m.group(1), ver)

    return issues


def check_changelog(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    ver = meta.get("version", "")
    # First ## [X.Y.Z] entry
    m = re.search(r"##\s*\[([\d.]+)\]", text)
    if m:
        issues += _check(meta, "CHANGELOG.md", "latest entry", m.group(1), ver)
    return issues


def check_claude_md(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    ver = meta.get("version", "")
    m = re.search(r"Package: `aicoreutils` \(v([\d.]+)\)", text)
    if m:
        issues += _check(meta, "CLAUDE.md", "version", m.group(1), ver)
    return issues


def check_current_status(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    text = (ROOT / "docs" / "status" / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    ver = meta.get("version", "")
    # Chinese version
    m = re.search(r"\|\s*\*\*项目版本\*\*\s*\|\s*([\d.]+)\s*\|", text)
    if m:
        issues += _check(meta, "CURRENT_STATUS.md", "项目版本 (cn)", m.group(1), ver)
    # English version
    m = re.search(r"\|\s*\*\*Project version\*\*\s*\|\s*([\d.]+)\s*\|", text)
    if m:
        issues += _check(meta, "CURRENT_STATUS.md", "Project version (en)", m.group(1), ver)
    return issues


def check_quickstart(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    fp = ROOT / "docs" / "QUICKSTART.md"
    if not fp.exists():
        return issues
    text = fp.read_text(encoding="utf-8")
    ver = meta.get("version", "")
    for m in re.finditer(r'"version":\s*"(\d+\.\d+\.\d+)"', text):
        issues += _check(
            meta,
            "docs/QUICKSTART.md",
            f"JSON envelope version (line ~{text[: m.start()].count(chr(10)) + 1})",
            m.group(1),
            ver,
        )
    return issues


def check_glama_json(meta: dict[str, str]) -> list[str]:
    issues: list[str] = []
    fp = ROOT / "glama.json"
    if not fp.exists():
        return issues
    data = json.loads(fp.read_text(encoding="utf-8"))
    if "version" in data:
        issues += _check(meta, "glama.json", "version", data["version"], meta.get("version", ""))
    return issues


# ── main ──


def main() -> int:
    meta = read_pyproject()
    ver = meta.get("version", "unknown")
    name = meta.get("name", "unknown")
    print(f"Authoritative source: pyproject.toml  version={ver}  name={name}")

    checkers = [
        ("pyproject.toml", check_pyproject_self),
        ("server.json", check_server_json),
        ("README.md", check_readme),
        ("CHANGELOG.md", check_changelog),
        ("CLAUDE.md", check_claude_md),
        ("CURRENT_STATUS.md", check_current_status),
        ("QUICKSTART.md", check_quickstart),
        ("glama.json", check_glama_json),
    ]

    all_issues: list[str] = []
    for _, fn in checkers:
        issues = fn(meta)
        if issues:
            all_issues.extend(issues)

    if all_issues:
        print(f"\n{len(all_issues)} inconsistencies found:\n")
        for issue in all_issues:
            print(f"  ✗ {issue}")
        print("\nRun 'python scripts/sync_metadata.py' to auto-fix version references.")
        return 1

    print("All metadata consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
