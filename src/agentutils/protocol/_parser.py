"""AgentArgumentParser: argparse wrapper that emits JSON errors."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from ..core import EXIT, AgentError, error_envelope, write_json


class AgentArgumentParser(argparse.ArgumentParser):
    """自定义 ArgumentParser：将 argparse 的 usage 错误转为 JSON 格式。

    覆盖 error() 方法：
    - 默认 argparse 将用法错误打印到 stderr 并 exit(2)。
    - agentutils 改为输出 JSON 错误信封到 stderr，然后 SystemExit(2)。
    - 这确保 Agent 收到的所有输出都是 JSON 格式，无一例外。
    """

    def error(self, message: str) -> NoReturn:
        """将 argparse 用法错误转为 JSON 错误信封并退出。"""
        error = AgentError(
            "usage",
            message,
            suggestion="Run 'agentutils schema' or '<command> --help' to discover valid usage.",
        )
        write_json(sys.stderr, error_envelope(None, error))
        raise SystemExit(EXIT["usage"])
