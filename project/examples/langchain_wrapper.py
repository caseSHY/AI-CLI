"""LangChain tool wrapper for aicoreutils.

Usage:
    from aicoreutils_langchain import get_aicoreutils_tools
    tools = get_aicoreutils_tools()
    agent = create_openai_functions_agent(llm, tools, prompt)
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

from langchain_core.tools import BaseTool


class AICoreutilsTool(BaseTool):
    """LangChain tool wrapping a single aicoreutils command."""

    name: str = ""
    description: str = ""
    args: tuple[str, ...] = ()

    def _run(self, *args: Any, **kwargs: Any) -> str:
        cmd = [sys.executable, "-m", "aicoreutils", self.name, *self.args]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return result.stderr
        try:
            return json.dumps(json.loads(result.stdout), indent=2)
        except json.JSONDecodeError:
            return result.stdout


def get_aicoreutils_tools() -> list[BaseTool]:
    """Return LangChain tools for common aicoreutils commands."""
    import subprocess as sp
    import sys

    output = sp.run(
        [sys.executable, "-m", "aicoreutils", "tool-list", "--format", "openai"],
        capture_output=True,
        text=True,
        check=True,
    )
    tools_data = json.loads(output.stdout)
    tool_list = tools_data.get("result", {}).get("tools", [])

    langchain_tools: list[BaseTool] = []
    for t in tool_list:
        langchain_tools.append(
            AICoreutilsTool(
                name=t["function"]["name"],
                description=t["function"]["description"],
            )
        )
    return langchain_tools


__all__ = ["AICoreutilsTool", "get_aicoreutils_tools"]
