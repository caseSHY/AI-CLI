from __future__ import annotations

import unittest

from support import ROOT


class DocsBilingualTests(unittest.TestCase):
    def test_human_markdown_files_are_chinese_first_bilingual(self) -> None:
        markdown_files = [
            path
            for path in ROOT.rglob("*.md")
            if ".git" not in path.parts
            and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
            and "__pycache__" not in path.parts
            and "coreutils-9.10" not in path.parts
            and "reports" not in path.relative_to(ROOT).parts
            and "analysis" not in path.relative_to(ROOT).parts
            and path.name
            not in {
                "CLAUDE.md",
                "CLAUDE.local.md",
                "CHANGELOG.md",
                "AGENT_TASKS.md",
            }
            and not path.name.startswith("GPTCodex-vs-DeepSeekCopilot-")
        ]
        self.assertTrue(markdown_files)
        for path in markdown_files:
            text = path.read_text(encoding="utf-8")
            chinese_index = text.find("中文")
            english_index = text.find("English")
            self.assertNotEqual(chinese_index, -1, f"{path} is missing a Chinese section marker")
            self.assertNotEqual(english_index, -1, f"{path} is missing an English section marker")
            self.assertLess(chinese_index, english_index, f"{path} must show Chinese before English")


if __name__ == "__main__":
    unittest.main()
