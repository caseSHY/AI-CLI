from __future__ import annotations

import unittest

from support import ROOT


class CiConfigTests(unittest.TestCase):
    def test_github_actions_workflow_exists_and_runs_unittest(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow.exists(), "missing .github/workflows/ci.yml")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("uv run pytest tests/", text)
        self.assertIn("uv sync", text)

    def test_wsl_local_ci_scripts_mirror_ubuntu_job(self) -> None:
        powershell_wrapper = ROOT / ".github" / "scripts" / "run-ci-wsl.ps1"
        wsl_script = ROOT / ".github" / "scripts" / "wsl-ci.sh"
        testing_doc = ROOT / "docs" / "development" / "TESTING.md"
        wsl_doc = ROOT / "docs" / "development" / "WSL_CI.md"

        for path in [powershell_wrapper, wsl_script, testing_doc, wsl_doc]:
            with self.subTest(path=path):
                self.assertTrue(path.exists(), f"missing {path}")

        script_text = wsl_script.read_text(encoding="utf-8")
        for required in [
            "apt-get install -y coreutils",
            "uv sync --extra dev",
            "ruff check src/ tests/",
            "ruff format --check src/ tests/",
            "mypy src/aicoreutils/ --strict",
            "uv run pytest tests/ -v --tb=short --cov=src/aicoreutils --cov-report=term-missing",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, script_text)

        docs_text = testing_doc.read_text(encoding="utf-8") + wsl_doc.read_text(encoding="utf-8")
        self.assertIn(r".\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps", docs_text)
        self.assertIn(".venv-wsl", docs_text)

    def test_pyproject_uses_src_layout(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('where = ["src"]', text)
        self.assertIn('aicoreutils = "aicoreutils.parser:main"', text)
        self.assertIn('agentutils = "aicoreutils.parser:main"', text)  # backward compat
        self.assertIn("pytest>=8.0", text)


if __name__ == "__main__":
    unittest.main()
