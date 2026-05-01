from __future__ import annotations

import json
import subprocess
import sys
import unittest

from support import ROOT


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _agentutils_output(*args: str) -> dict:
    """Run agentutils and return parsed JSON result dict."""
    env = {**dict(subprocess.os.environ), "PYTHONPATH": str(ROOT / "src")}
    cp = subprocess.run(
        [sys.executable, "-m", "agentutils", *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        env=env,
        timeout=30,
    )
    return json.loads(cp.stdout)


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
        self.assertIn("本地 WSL 已验证 — 55/56 GNU 对照测试通过", status)
        self.assertIn("Locally verified in WSL — 55/56 GNU differential tests passed", status)
        self.assertIn("远程待验证 — 本地 WSL 已通过，但 GitHub Actions 仍需重新触发", status)
        self.assertIn("Remote pending — local WSL passed, but GitHub Actions still needs a new run", status)
        self.assertIn("Windows runner", status)
        self.assertIn("Ubuntu runner", status)

        forbidden = [
            "CI 未安装 coreutils 包",
            "CI 未安装 GNU coreutils",
            "Not verified — CI missing coreutils",
            "GNU coreutils not installed",
            "无 Windows CI runner",
            "No Windows runner",
            "WSL 尚未安装",
            "WSL 未安装",
            "WSL is not installed",
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
        report = read_text("docs/reports/project-governance/2026-04-30-project-structure-and-docs-governance-report.md")
        self.assertIn(
            "| K-004 | CI 中 GNU differential tests 未实际运行过 | ⏳ 待验证 — coreutils 已安装但 CI 尚未触发 |",
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
            "54 个测试通过",
            "54 tests passing",
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

    def test_current_status_records_correct_test_count(self) -> None:
        status = read_text("docs/status/CURRENT_STATUS.md")
        self.assertIn("| **Windows 推荐入口结果** | 137 passed, 54 skipped, 0 failed, 118 subtests passed |", status)
        self.assertIn("| **WSL 本地 CI 结果** | 190 passed, 1 skipped, 0 failed, 118 subtests passed |", status)
        self.assertIn(
            "| **Windows recommended-entry result** | 137 passed, 54 skipped, 0 failed, 118 subtests passed |",
            status,
        )
        self.assertIn("| **WSL local CI result** | 190 passed, 1 skipped, 0 failed, 118 subtests passed |", status)
        self.assertIn("(9 测试, 全部通过)", status)
        self.assertIn("(9 tests, all pass)", status)
        self.assertIn("| **项目版本** | 0.2.0 |", status)
        self.assertIn("| **Project version** | 0.2.0 |", status)
        self.assertNotIn("132 passed", status)
        self.assertNotIn("| **Passed** | 132 |", status)
        self.assertNotIn("| **Passed** | 137 |", status)
        self.assertNotIn("| **项目版本** | 0.1.0 |", status)
        self.assertNotIn("| **Project version** | 0.1.0 |", status)

    def test_command_count_consistency_across_docs(self) -> None:
        output = _agentutils_output("schema")
        actual_count = output["result"]["command_count"]
        self.assertEqual(actual_count, 114)

        docs_to_check = [
            "README.md",
            "docs/status/CURRENT_STATUS.md",
            "docs/development/TESTING.md",
            "docs/audits/GNU_COMPATIBILITY_AUDIT.md",
        ]
        for relative in docs_to_check:
            text = read_text(relative)
            with self.subTest(relative=relative):
                self.assertIn("114", text)

    def test_active_docs_do_not_contain_stale_command_count(self) -> None:
        active_docs = [
            "README.md",
            "docs/status/CURRENT_STATUS.md",
            "docs/development/TESTING.md",
            "docs/audits/GNU_COMPATIBILITY_AUDIT.md",
        ]
        for relative in active_docs:
            text = read_text(relative)
            lines = text.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if "schema" in stripped.lower() and "113" in stripped and "command" in stripped.lower():
                    with self.subTest(relative=relative, line=i):
                        self.fail(f"{relative}:{i} has stale '113 commands' near 'schema': {stripped}")
                if "agentutils schema" in stripped and "113" in stripped:
                    with self.subTest(relative=relative, line=i):
                        self.fail(f"{relative}:{i} has stale '113': {stripped}")


if __name__ == "__main__":
    unittest.main()
