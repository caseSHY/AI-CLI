"""Agent-friendly CLI layer inspired by GNU Coreutils.

aicoreutils 是一个面向 LLM Agent 的 JSON 优先命令行工具包。

核心设计原则：
- JSON 优先输出（--raw 显式绕过）
- 错误以 JSON 写入 stderr
- 语义化退出码（0-10，8 为安全拒绝）
- 修改命令支持 --dry-run
- 危险操作需要显式 --allow-* 授权
- 输出确定性、有界、无颜色/进度条噪音

版本号在 pyproject.toml 和本文件的 __version__ 中同时维护。
"""

from __future__ import annotations

__version__ = "0.4.3"

# 异步接口（0.2.0 新增）：支持在 asyncio 事件循环中并发调用
from .async_interface import run_async, run_async_many

# 核心模块（0.2.0 新增）：流式输出
from .core import StreamWriter, is_stream_mode

# Parser：CLI 入口、参数解析、命令分发
from .parser import build_parser, command_catalog, command_schema, command_tool_list, dispatch, main

# 插件系统（0.2.0 新增）：自动发现 aicoreutils_* 命名空间包
from .plugins import discover_plugins, get_plugin_commands, register_plugin_command

# Protocol：核心协议类型和工具函数（向后兼容导出）
from .protocol import (
    EXIT,
    HASH_ALGORITHMS,
    AgentArgumentParser,
    AgentError,
    envelope,
    error_envelope,
    resolve_path,
    stat_entry,
    utc_iso,
    write_json,
)

__all__ = [
    "AgentArgumentParser",
    "AgentError",
    "EXIT",
    "HASH_ALGORITHMS",
    "StreamWriter",
    "__version__",
    "build_parser",
    "command_catalog",
    "command_schema",
    "command_tool_list",
    "discover_plugins",
    "dispatch",
    "envelope",
    "error_envelope",
    "get_plugin_commands",
    "is_stream_mode",
    "main",
    "register_plugin_command",
    "resolve_path",
    "run_async",
    "run_async_many",
    "stat_entry",
    "utc_iso",
    "write_json",
]
