from __future__ import annotations

import unittest

from support import ROOT


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class DocsGovernanceTests(unittest.TestCase):
    def test_copilot_and_agent_instruction_entry_points_exist(self) -> None:
        required_files = [
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".github/instructions/docs-governance.instructions.md",
            ".github/instructions/python-tests.instructions.md",
            "docs/agent-guides/DOC_GOVERNANCE_RULES.md",
            "docs/agent-guides/FACT_PROPAGATION_MATRIX.md",
        ]
        for relative in required_files:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).exists(), f"missing {relative}")

        copilot = read_text(".github/copilot-instructions.md")
        for required in [
            "docs/status/CURRENT_STATUS.md",
            "docs/agent-guides/DOC_GOVERNANCE_RULES.md",
            "docs/agent-guides/FACT_PROPAGATION_MATRIX.md",
            "python -m pytest tests/ -v --tb=short",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, copilot)

    def test_agent_governance_guides_are_indexed(self) -> None:
        docs_index = read_text("docs/README.md")
        readme = read_text("README.md")
        for required in [
            "agent-guides/DOC_GOVERNANCE_RULES.md",
            "agent-guides/FACT_PROPAGATION_MATRIX.md",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs_index)
                self.assertIn(required, readme)

    def test_current_status_has_no_ci_coreutils_contradiction(self) -> None:
        status = read_text("docs/status/CURRENT_STATUS.md")
        self.assertIn("待验证 — coreutils 已安装，需 CI 触发", status)
        self.assertIn("Pending — coreutils installed, needs CI trigger", status)
        self.assertIn("Windows runner", status)
        self.assertIn("Ubuntu runner", status)

        forbidden = [
            "CI 未安装 coreutils 包",
            "CI 未安装 GNU coreutils",
            "Not verified — CI missing coreutils",
            "GNU coreutils not installed",
            "无 Windows CI runner",
            "No Windows runner",
        ]
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, status)

    def test_testing_doc_ci_topology_matches_workflow(self) -> None:
        workflow = read_text(".github/workflows/ci.yml")
        testing = read_text("docs/development/TESTING.md")

        for required in [
            "test-ubuntu",
            "ubuntu-latest",
            "test-windows",
            "windows-latest",
            "apt-get install -y coreutils",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, workflow)

        for required in [
            "ubuntu-latest（test-ubuntu）+ windows-latest（test-windows）",
            "已安装 GNU coreutils",
            "Platform**: ubuntu-latest (test-ubuntu) + windows-latest (test-windows)",
            "GNU coreutils installed",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, testing)

        for forbidden in [
            "CI 未安装 GNU coreutils",
            "GNU coreutils not installed, GNU differential tests are skipped",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, testing)

    def test_governance_report_keeps_untriggered_ci_as_pending(self) -> None:
        report = read_text(
            "docs/reports/project-governance/"
            "2026-04-30-project-structure-and-docs-governance-report.md"
        )
        self.assertIn(
            "| K-004 | CI 中 GNU differential tests 未实际运行过 | "
            "⏳ 待验证 — coreutils 已安装但 CI 尚未触发 |",
            report,
        )
        self.assertNotIn(
            "| K-004 | CI 中 GNU differential tests 未实际运行过 | ✅",
            report,
        )

    def test_current_docs_do_not_contain_known_stale_current_facts(self) -> None:
        current_docs = [
            "README.md",
            "AGENTS.md",
            "docs/README.md",
            "docs/development/TESTING.md",
            "docs/status/CURRENT_STATUS.md",
            "docs/reference/SECURITY_MODEL.md",
            "docs/audits/GNU_COMPATIBILITY_AUDIT.md",
            "docs/guides/USAGE.zh-CN.en.md",
        ]
        forbidden = [
            "现有 99 个测试全部通过",
            "99 passed",
            "120 passed",
            "CI 未安装 GNU coreutils",
            "GNU coreutils not installed",
            "无 Windows CI runner",
            "No Windows runner",
        ]
        for relative in current_docs:
            text = read_text(relative)
            for phrase in forbidden:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
