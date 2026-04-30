from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    if extra:
        env.update(extra)
    return env


def run_cli(
    *args: str,
    cwd: Path | None = None,
    input_text: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agentutils", *args],
        cwd=cwd or ROOT,
        env=test_env(extra_env),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_stdout(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def parse_stderr(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stderr)
