"""Verify version consistency across all source locations."""
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
    from aicoreutils.core.envelope import _TOOL_VERSION
    assert __version__ == _TOOL_VERSION, f"envelope: {_TOOL_VERSION} != __version__: {__version__}"


def test_mcp_server_version():
    content = (ROOT / "src" / "aicoreutils" / "mcp_server.py").read_text(encoding="utf-8")
    assert "__version__" in content, "mcp_server.py should use __version__"


def test_server_json_version():
    data = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    assert data["version"] == _get_version()
    assert data["packages"][0]["version"] == _get_version()


__version__ = _get_version()  # noqa: E402
