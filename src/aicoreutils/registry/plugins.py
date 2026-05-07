"""Plugin discovery and registration system for aicoreutils.

插件系统：允许第三方通过 aicoreutils_* 命名空间包或编程式注册扩展命令。

Phase 3 架构：
- PluginRegistry（来自 core.plugin_registry）是不可变容器。
  每个 register/discover 返回新实例，线程安全。
- catalog.py 提供 merge_plugin_commands() 创建合并后的优先级视图，
  不修改全局 CATALOG。
- 向后兼容：旧的 discover_plugins / register_plugin_command /
  get_plugin_commands 保持原有签名，委托给模块级 PluginRegistry。

使用示例（在 aicoreutils_extra 插件包中）：

    # aicoreutils_extra/__init__.py
    COMMANDS = {
        "mycommand": my_command_function,
    }

然后 aicoreutils 会自动发现并注册 "mycommand"。
"""

from __future__ import annotations

from ..core.plugin_registry import CommandFunc, PluginRegistry

# 模块级注册表单例。初始为空，可通过 discover() 或 register() 修改。
# 返回新实例的模式确保了旧引用不受影响。
_registry: PluginRegistry = PluginRegistry()


def discover_plugins() -> dict[str, CommandFunc]:
    """扫描 aicoreutils_* 包并更新全局注册表。

    Returns:
        发现的命令名 → 命令函数字典。
    """
    global _registry
    discovered = PluginRegistry.discover()
    _registry = _registry.merge(discovered)
    return {name: _registry[name] for name in discovered.names}


def get_plugin_commands() -> dict[str, CommandFunc]:
    """返回当前已注册插件命令的快照。"""
    return {name: _registry[name] for name in _registry.names}


def register_plugin_command(name: str, func: CommandFunc, priority: str = "P3") -> None:
    """编程式注册单个插件命令，无需创建独立包。

    Args:
        name: 命令名（将在 CLI 中作为子命令使用）。
        func: 命令函数，签名为 (argparse.Namespace) -> dict[str, Any] | bytes。
        priority: 优先级（P0/P1/P2/P3），默认 P3。供 catalog 合并使用。
    """
    global _registry
    _registry = _registry.register(name, func)


def get_registry() -> PluginRegistry:
    """返回当前全局 PluginRegistry 实例。

    优先于 get_plugin_commands() 使用，当需要 PluginRegistry 对象时
    （如传递给 build_parser 或 catalog 合并）。
    """
    return _registry


def reset_plugins() -> None:
    """将全局注册表重置为空。供测试隔离使用。"""
    global _registry
    _registry = PluginRegistry()


def has_plugins() -> bool:
    """如果有任何插件已注册则返回 True。"""
    return _registry.count > 0
