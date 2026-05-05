"""Verify version consistency across all source locations.

Checks:
- pyproject.toml, __init__.py, server.json, envelope, mcp_server — version match
- CURRENT_STATUS.md — version matches __version__
- README.md — production pin version matches current version
- CURRENT_STATUS.md — version consistency test is recorded as in CI pipeline
"""

import importlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _get_version():
    spec = importlib.util.spec_from_file_location("aicoreutils", ROOT / "src" / "aicoreutils" / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.__version__


def test_pyproject_version():
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', content)
    assert m, "version not found in pyproject.toml"
    assert m.group(1) == _get_version()


def test_envelope_version():
    from aicoreutils.core.envelope import _TOOL_VERSION  # noqa: E402

    assert __version__ == _TOOL_VERSION, f"envelope: {_TOOL_VERSION} != __version__: {__version__}"


def test_mcp_server_version():
    content = (ROOT / "src" / "aicoreutils" / "mcp_server.py").read_text(encoding="utf-8")
    assert "__version__" in content, "mcp_server.py should use __version__"


def test_server_json_version():
    data = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert data["version"] == _get_version()
    assert data["packages"][0]["version"] == _get_version()


def test_current_status_version():
    """CURRENT_STATUS.md version must match __version__."""
    status = (ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    m_cn = re.search(r"\|\s*\*\*项目版本\*\*\s*\|\s*([0-9.]+)", status)
    m_en = re.search(r"\|\s*\*\*Project version\*\*\s*\|\s*([0-9.]+)", status)
    assert m_cn, "Chinese version field not found in CURRENT_STATUS.md"
    assert m_en, "English version field not found in CURRENT_STATUS.md"
    assert m_cn.group(1) == _get_version(), (
        f"CURRENT_STATUS.md Chinese version {m_cn.group(1)} != __version__ {_get_version()}"
    )
    assert m_en.group(1) == _get_version(), (
        f"CURRENT_STATUS.md English version {m_en.group(1)} != __version__ {_get_version()}"
    )


def test_readme_pin_version():
    """README production pin version must match current __version__."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pins = re.findall(r"aicoreutils==(\d+\.\d+\.\d+)", readme)
    for pin in pins:
        assert pin == _get_version(), (
            f"README pin version {pin} does not match __version__ {_get_version()}. "
            f"Update the pip install command in README."
        )


def test_current_status_ci_includes_version_consistency():
    """CURRENT_STATUS.md must report that version consistency is in CI pipeline."""
    status = (ROOT / "project" / "docs" / "status" / "CURRENT_STATUS.md").read_text(encoding="utf-8")
    assert "CI 未纳入" not in status, (
        "CURRENT_STATUS.md still says version consistency 'CI 未纳入' but it is in CI pipeline"
    )
    assert "not yet in CI" not in status, (
        "CURRENT_STATUS.md still says version consistency 'not yet in CI' but it is in CI pipeline"
    )
    assert "已在 CI pipeline 中" in status or "in CI pipeline" in status, (
        "CURRENT_STATUS.md should confirm version consistency test is in CI pipeline"
    )


__version__ = _get_version()  # noqa: E402
