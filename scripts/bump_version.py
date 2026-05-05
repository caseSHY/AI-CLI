#!/usr/bin/env python3
"""Semi-automated version bump for AICoreUtils.

Updates all 5 files that carry the version number:
    pyproject.toml, __init__.py, server.json, CURRENT_STATUS.md
and appends a new CHANGELOG section template.

Usage:
    python scripts/bump_version.py 1.2.0          # bump to 1.2.0
    python scripts/bump_version.py 1.2.0 --dry-run  # preview only
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES_TO_UPDATE = [
    (ROOT / "pyproject.toml", r'(version\s*=\s*)"(\d+\.\d+\.\d+)"', r'\g<1>"{new}"'),
    (ROOT / "src" / "aicoreutils" / "__init__.py", r'(__version__\s*=\s*)"(\d+\.\d+\.\d+)"', r'\g<1>"{new}"'),
    (ROOT / "server.json", r'("version":\s*)"\d+\.\d+\.\d+"', r'\g<1>"{new}"'),
    (
        ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md",
        r"(\|\s*\*\*项目版本\*\*\s*\|\s*)\d+\.\d+\.\d+",
        r"\g<1>{new}",
    ),
    (
        ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md",
        r"(\|\s*\*\*Project version\*\*\s*\|\s*)\d+\.\d+\.\d+",
        r"\g<1>{new}",
    ),
]

CHANGELOG_TEMPLATE = """\
## [{new}] - {today}

### Added
-

### Changed
-

### Fixed
-

### Security
-
"""


def get_current_version() -> str:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', content)
    return m.group(1) if m else "unknown"


def bump(new_version: str, dry_run: bool = False) -> None:
    current = get_current_version()
    if current == new_version:
        print(f"Already at version {new_version}")
        return

    print(f"Bumping {current} → {new_version}{' (dry-run)' if dry_run else ''}")

    for filepath, pattern_str, replacement_template in FILES_TO_UPDATE:
        text = filepath.read_text(encoding="utf-8")
        pattern = re.compile(pattern_str)
        new_text = pattern.sub(replacement_template.format(new=new_version), text)

        # server.json needs special handling (two version fields)
        if filepath.name == "server.json":
            new_text = re.sub(
                r'("version":\s*)"\d+\.\d+\.\d+"',
                rf'\g<1>"{new_version}"',
                new_text,
            )

        if new_text != text:
            if dry_run:
                print(f"  Would update: {filepath}")
            else:
                filepath.write_text(new_text, encoding="utf-8")
                print(f"  Updated: {filepath}")

    # Prepend CHANGELOG entry
    changelog = ROOT / "CHANGELOG.md"
    cl_text = changelog.read_text(encoding="utf-8")
    marker = "\n## ["
    first = cl_text.index(marker)
    new_entry = CHANGELOG_TEMPLATE.format(new=new_version, today=date.today().isoformat())
    if dry_run:
        print(f"  Would prepend CHANGELOG entry for {new_version}")
    else:
        changelog.write_text(cl_text[:first] + new_entry + "\n" + cl_text[first:], encoding="utf-8")
        print(f"  Prepended CHANGELOG entry for {new_version}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(f"Usage: python {__file__} <new_version> [--dry-run]")
        sys.exit(1)

    new_ver = sys.argv[1]
    dry = "--dry-run" in sys.argv
    bump(new_ver, dry_run=dry)
