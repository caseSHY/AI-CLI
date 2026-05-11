#!/usr/bin/env python3
"""Sync project metadata from pyproject.toml to all dependent files.

Reads authoritative values from pyproject.toml and updates:
  - README.md: LTS badge, pip install pin (inside <!-- metadata-sync:start/end -->)
  - server.json: version fields
  - glama.json: version field (if present)
  - CLAUDE.md: version in Project overview

Usage:
    python scripts/sync_metadata.py          # sync all files
    python scripts/sync_metadata.py --check  # dry-run: report what would change
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_pyproject() -> dict[str, str]:
    """Read authoritative metadata from pyproject.toml."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for key, pattern in [
        ("version", r'version\s*=\s*"([^"]+)"'),
        ("name", r'^\s*name\s*=\s*"([^"]+)"'),
        ("description", r'^\s*description\s*=\s*"([^"]+)"'),
        ("repo_url", r'Homepage\s*=\s*"([^"]+)"'),
    ]:
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            meta[key] = m.group(1)
    return meta


# ── sync functions per file ──


def sync_server_json(version: str) -> bool:
    """Update version fields in server.json."""
    fp = ROOT / "server.json"
    data = json.loads(fp.read_text(encoding="utf-8"))
    changed = False
    if data.get("version") != version:
        data["version"] = version
        changed = True
    for pkg in data.get("packages", []):
        if pkg.get("version") != version:
            pkg["version"] = version
            changed = True
    if changed:
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def sync_glama_json(version: str) -> bool:
    """Update version in glama.json if present."""
    fp = ROOT / "glama.json"
    if not fp.exists():
        return False
    data = json.loads(fp.read_text(encoding="utf-8"))
    changed = False
    if data.get("version") != version:
        data["version"] = version
        changed = True
    if changed:
        fp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def _replace_marked_section(text: str, marker_name: str, replacement: str) -> tuple[str, bool]:
    """Replace content between `<!-- metadata-sync:start NAME -->` and `<!-- metadata-sync:end NAME -->`."""
    start_tag = f"<!-- metadata-sync:start {marker_name} -->"
    end_tag = f"<!-- metadata-sync:end {marker_name} -->"
    pattern = re.compile(rf"({re.escape(start_tag)}\n)(.*?)(\n{re.escape(end_tag)})", re.DOTALL)
    m = pattern.search(text)
    if not m:
        return text, False
    new_block = f"{m.group(1)}{replacement}{m.group(3)}"
    return text[: m.start()] + new_block + text[m.end() :], True


def sync_readme(version: str) -> bool:
    """Update version references in README.md."""
    fp = ROOT / "README.md"
    text = fp.read_text(encoding="utf-8")
    changed = False

    # LTS badge version in URL
    new_badge = f"[![LTS](https://img.shields.io/badge/LTS-{version}-blue)]"
    badge_pattern = r"\[!\[LTS\]\(https://img\.shields\.io/badge/LTS-[\d.]+-blue\)\]"
    new_text = re.sub(badge_pattern, new_badge, text)
    if new_text != text:
        text = new_text
        changed = True

    # pip pin version in stability note
    pin_pattern = re.compile(r"(pip install aicoreutils==)[\d.]+")
    new_text, pin_changed = re.subn(pin_pattern, rf"\g<1>{version}", text)
    if pin_changed and new_text != text:
        text = new_text
        changed = True

    # LTS version text
    lts_pattern = re.compile(r"(\*\*v)[\d.]+( LTS\*\*)")
    new_text, lts_changed = re.subn(lts_pattern, rf"\g<1>{version}\2", text)
    if lts_changed and new_text != text:
        text = new_text
        changed = True

    if changed:
        fp.write_text(text, encoding="utf-8")
    return changed


def sync_claude_md(version: str) -> bool:
    """Update version in CLAUDE.md Project overview."""
    fp = ROOT / "CLAUDE.md"
    text = fp.read_text(encoding="utf-8")
    pattern = re.compile(r"(Package: `aicoreutils` \(v)[\d.]+(\))")
    new_text, n = re.subn(pattern, rf"\g<1>{version}\2", text)
    if n and new_text != text:
        fp.write_text(new_text, encoding="utf-8")
        return True
    return False


def sync_quickstart_md(version: str) -> bool:
    """Update JSON envelope version examples in QUICKSTART.md."""
    fp = ROOT / "docs" / "QUICKSTART.md"
    if not fp.exists():
        return False
    text = fp.read_text(encoding="utf-8")
    # Update "version": "X.Y.Z" in JSON envelope examples
    pattern = re.compile(r'("version":\s*")\d+\.\d+\.\d+(")')
    new_text, n = re.subn(pattern, rf"\g<1>{version}\2", text)
    if n and new_text != text:
        fp.write_text(new_text, encoding="utf-8")
        return True
    return False


# ── main ──


def main() -> int:
    dry_run = "--check" in sys.argv
    meta = read_pyproject()
    version = meta.get("version", "unknown")
    if version == "unknown":
        print("ERROR: could not read version from pyproject.toml")
        return 1

    # file → sync function
    syncs = [
        ("server.json", sync_server_json),
        ("glama.json", sync_glama_json),
        ("README.md", sync_readme),
        ("CLAUDE.md", sync_claude_md),
        ("docs/QUICKSTART.md", sync_quickstart_md),
    ]

    any_changed = False
    for rel_path, sync_fn in syncs:
        changed = sync_fn(version)
        action = "would update" if dry_run else ("updated" if changed else "up to date")
        print(f"  {action}: {rel_path}")
        any_changed = any_changed or changed

    if dry_run:
        print("--check mode: no files modified" if not any_changed else "--check mode: files would be modified")
        return 1 if any_changed else 0
    print("Metadata sync complete." if any_changed else "All files up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
