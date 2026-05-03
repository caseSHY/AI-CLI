"""Immutable plugin command registry.

Provides PluginRegistry, a frozen container that holds plugin-discovered
command functions.  Each mutation returns a *new* instance, making the
registry safe to share across threads and eliminating the global mutable
state that plagued the old plugins.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# 命令函数类型别名：接收 argparse.Namespace，返回 dict | bytes
CommandFunc = Callable[..., Any]


class PluginRegistry:
    """不可变插件命令注册表。

    每个注册操作返回新实例，原始实例不受影响。
    线程安全：无内部可变状态，无需锁。

    Usage:
        registry = PluginRegistry()
        registry = registry.register("mycmd", my_func)
        registry = registry.discover()       # 扫描 aicoreutils_* 包
    """

    __slots__ = ("_commands",)

    def __init__(self, commands: dict[str, CommandFunc] | None = None) -> None:
        self._commands: dict[str, CommandFunc] = dict(commands or {})

    # ── 查询 ──
    def __contains__(self, name: str) -> bool:
        return name in self._commands

    def __getitem__(self, name: str) -> CommandFunc:
        return self._commands[name]

    def get(self, name: str, default: CommandFunc | None = None) -> CommandFunc | None:
        return self._commands.get(name, default)

    def items(self) -> list[tuple[str, CommandFunc]]:
        return list(self._commands.items())

    @property
    def names(self) -> set[str]:
        return set(self._commands)

    @property
    def count(self) -> int:
        return len(self._commands)

    # ── 注册（返回新实例）──
    def register(self, name: str, func: CommandFunc) -> PluginRegistry:
        """注册单个命令，返回新 PluginRegistry。

        如果同名命令已存在，新函数覆盖旧函数。
        """
        new_cmds = dict(self._commands)
        new_cmds[name] = func
        return PluginRegistry(new_cmds)

    def merge(self, other: PluginRegistry) -> PluginRegistry:
        """合并另一个注册表，返回新实例。后注册的命令优先。"""
        new_cmds = dict(self._commands)
        new_cmds.update(other._commands)
        return PluginRegistry(new_cmds)

    # ── 发现 ──
    @classmethod
    def discover(cls) -> PluginRegistry:
        """扫描 sys.path 发现所有 aicoreutils_* 插件包。

        Returns:
            包含所有发现命令的新 PluginRegistry。
        """
        import importlib
        import pkgutil

        discovered: dict[str, CommandFunc] = {}
        for _finder, name, ispkg in pkgutil.iter_modules():
            if not name.startswith("aicoreutils_") or not ispkg:
                continue
            try:
                module = importlib.import_module(name)
                commands = getattr(module, "COMMANDS", None)
                if isinstance(commands, dict):
                    for cmd_name, cmd_func in commands.items():
                        if callable(cmd_func):
                            discovered[cmd_name] = cmd_func
            except ImportError:
                continue  # 单个插件加载失败不阻塞其他
        return cls(discovered)

    def __repr__(self) -> str:
        return f"PluginRegistry(commands={sorted(self._commands)})"
