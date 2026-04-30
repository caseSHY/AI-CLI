from __future__ import annotations

import unittest

from support import ROOT


class CiConfigTests(unittest.TestCase):
    def test_github_actions_workflow_exists_and_runs_unittest(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow.exists(), "missing .github/workflows/ci.yml")
        text = workflow.read_text(encoding="utf-8")
        self.assertTrue(
            "python -m unittest discover -s tests" in text
            or "python -m pytest tests/" in text
        )
        self.assertIn("PYTHONPATH", text)

    def test_pyproject_uses_src_layout(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('where = ["src"]', text)
        self.assertIn('agentutils = "agentutils.cli:main"', text)
        self.assertIn("pytest>=8.0", text)


if __name__ == "__main__":
    unittest.main()
