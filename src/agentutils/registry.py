"""Unified command registry with auto-discovery from the parser.

命令注册表：提供从 catalog.py（唯一权威来源）导出的命令查询函数。

这个模块存在的意义：
- 为 parser.py 提供单一 import 入口点（而非直接从 catalog 导入）。
- 未来如果注册表需要扩展（如包含插件命令、运行时注册等），
  只需修改此文件而不影响 parser.py 的导入路径。
- 当前本质上是一个 re-export 层，后续重构时可合并入 catalog.py。
"""

from __future__ import annotations

# 从唯一权威来源 catalog.py 重导出所有优先级查询函数
from .catalog import (
    _COMMAND_PRIORITY_MAP,
    get_all_commands,
    get_commands_by_priority,
    get_priority,
    implemented_catalog,
)

__all__ = [
    "_COMMAND_PRIORITY_MAP",
    "get_all_commands",
    "get_commands_by_priority",
    "get_priority",
    "implemented_catalog",
]
