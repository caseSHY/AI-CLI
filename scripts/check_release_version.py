#!/usr/bin/env python3
"""Verify that the git tag and pyproject.toml version match before publishing.

Usage:
    python scripts/check_release_version.py          # read GITHUB_REF_NAME
    python scripts/check_release_version.py v1.2.3   # explicit tag
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_pyproject_version() -> str:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', content)
    return m.group(1) if m else "unknown"


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_REF_NAME", "")
    if tag.startswith("refs/tags/"):
        tag = tag.replace("refs/tags/", "", 1)
    tag_version = tag.removeprefix("v")
    pkg_version = get_pyproject_version()

    if tag_version != pkg_version:
        print(f"ERROR: Tag v{tag_version} != pyproject.toml version {pkg_version}")
        return 1
    print(f"Version check: v{tag_version} == pyproject.toml {pkg_version} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
