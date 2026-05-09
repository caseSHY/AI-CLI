from __future__ import annotations

import json
import subprocess
import sys
import unittest

from support import ROOT


def read_text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _aicoreutils_output(*args: str) -> dict:
    """Run aicoreutils and return parsed JSON result dict."""
    env = {**dict(subprocess.os.environ), "PYTHONPATH": str(ROOT / "src")}
    cp = subprocess.run(
        [sys.executable, "-m", "aicoreutils", *args],
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
            "CLAUDE.md",
            "docs/architecture/DOC_GOVERNANCE_RULES.md",
            "docs/architecture/FACT_PROPAGATION_MATRIX.md",
        ]
        for relative in required_files:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).exists(), f"missing {relative}")

        claude_md = read_text("CLAUDE.md")
        for required in [
            "docs/status/CURRENT_STATUS.md",
            "docs/architecture/DOC_GOVERNANCE_RULES.md",
            "docs/architecture/FACT_PROPAGATION_MATRIX.md",
            "uv run pytest tests/ -v --tb=short",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, claude_md)

    def test_agent_governance_guides_are_indexed(self) -> None:
        docs_index = read_text("docs/README.md")
        readme = read_text("README.md")
        for required in [
            "architecture/DOC_GOVERNANCE_RULES.md",
            "architecture/FACT_PROPAGATION_MATRIX.md",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs_index)
                self.assertIn(required, readme)

    def test_current_status_has_no_ci_coreutils_contradiction(self) -> None:
        status = read_text("docs/status/CURRENT_STATUS.md")
        self.assertIn("本地 WSL 已验证 — 54/56 GNU 对照测试通过", status)
        self.assertIn("Locally verified in WSL — 54/56 GNU differential tests passed", status)
        self.assertIn("✅ CI verified", status)
        self.assertIn("CI verified", status)
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

    def test_current_docs_do_not_contain_known_stale_current_facts(self) -> None:
        current_docs = [
            "README.md",
            "docs/README.md",
            "docs/development/TESTING.md",
            "docs/status/CURRENT_STATUS.md",
            "docs/reference/SECURITY_MODEL.md",
            "docs/audits/GNU_COMPATIBILITY_AUDIT.md",
            "docs/guides/USAGE.zh-CN.en.md",
        ]
        forbidden = [
            "现有 99 个测试全部通过",
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
        self.assertRegex(status, r"Windows 推荐入口结果.*\d+ passed, \d+ skipped, 0 failed")
        self.assertRegex(
            status, r"CI 全平台结果.*Ubuntu: \d+ passed.*macOS: \d+ passed.*Windows: \d+ passed.*lint \+ typecheck"
        )
        self.assertRegex(status, r"Windows recommended-entry result.*\d+ passed, \d+ skipped, 0 failed")
        self.assertRegex(
            status,
            r"CI all-platform results.*Ubuntu: \d+ passed.*macOS: \d+ passed.*Windows: \d+ passed.*lint \+ typecheck",
        )
        self.assertRegex(status, r"\(\d+ 测试, 全部通过\)")
        self.assertRegex(status, r"\(\d+ tests, all pass\)")
        from aicoreutils import __version__

        self.assertIn(f"| **项目版本** | {__version__} |", status)
        self.assertIn(f"| **Project version** | {__version__} |", status)
        self.assertNotIn("| **项目版本** | 0.1.0 |", status)
        self.assertNotIn("| **Project version** | 0.1.0 |", status)

    def test_command_count_consistency_across_docs(self) -> None:
        output = _aicoreutils_output("schema")
        actual_count = output["result"]["command_count"]
        self.assertGreaterEqual(actual_count, 114, f"Expected >= 114 commands, got {actual_count}")

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
                if "aicoreutils schema" in stripped and "113" in stripped:
                    with self.subTest(relative=relative, line=i):
                        self.fail(f"{relative}:{i} has stale '113': {stripped}")


if __name__ == "__main__":
    unittest.main()
