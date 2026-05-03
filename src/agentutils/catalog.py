"""Priority catalog for GNU Coreutils commands in agent workflows.

命令优先级目录：aicoreutils 所有 114 个命令的唯一权威分类来源。

设计原理：
- CATALOG 是数据，不是代码——新增命令只需在列表中追加条目，
  所有优先级推导、分类查询、schema 输出均自动更新。
- P0-P3 四级分类反映 Agent 使用频率和风险级别：
  P0（关键）：Agent 在决策前必须观察文件系统 → ls/stat/cat...
  P1（高）：安全修改文件系统 → cp/mv/rm/mkdir...（带 dry-run）
  P2（中）：文本转换与管道组合 → sort/uniq/cut/tr...
  P3（正常）：系统上下文与有界执行 → date/env/kill...
- 元命令（catalog/schema/coreutils/tool-list/hash）不在 CATALOG 中，
  由 parser.py 单独管理。

注意：plugins.py 中的 register_plugin_command() 会修改 CATALOG。
这是已知的技术债务（可变全局状态），已在 Phase 3 中通过 PluginRegistry 修复。
现在 catalog.py 提供 merge_plugin_commands() 生成合并后的视图，不修改原 CATALOG。
"""

from __future__ import annotations

from typing import TypedDict


class CatalogEntry(TypedDict):
    """目录条目类型：一个优先级组包含多个命令。"""

    priority: str  # "P0" | "P1" | "P2" | "P3"
    urgency: str  # "critical" | "high" | "medium" | "normal"
    category: str  # 分类标识符（如 "read_observe_and_decide"）
    why: str  # 为什么这些命令属于此优先级（人类可读）
    tools: list[str]  # 命令名列表


# 唯一权威的命令优先级数据源
# 修改此列表后，所有 get_* 函数和 priority_catalog() 自动反映变更
CATALOG: list[CatalogEntry] = [
    {
        "priority": "P0",
        "urgency": "critical",
        "category": "read_observe_and_decide",
        "why": "Agents need deterministic filesystem observation before taking action.",
        "tools": [
            "ls",
            "stat",
            "cat",
            "head",
            "tail",
            "wc",
            "pwd",
            "basename",
            "dirname",
            "realpath",
            "readlink",
            "test",
            "sha256sum",
            "md5sum",
        ],
    },
    {
        "priority": "P1",
        "urgency": "high",
        "category": "mutate_files_safely",
        "why": "These commands change state and need dry-run, explicit overwrite, and structured errors.",
        "tools": [
            "cp",
            "mv",
            "rm",
            "mkdir",
            "touch",
            "ln",
            "link",
            "chmod",
            "chown",
            "chgrp",
            "truncate",
            "mktemp",
            "mkfifo",
            "mknod",
            "tee",
            "rmdir",
            "unlink",
            "install",
            "ginstall",
        ],
    },
    {
        "priority": "P2",
        "urgency": "medium",
        "category": "transform_and_compose_text",
        "why": "These commands are useful in pipelines and should preserve stdin/stdout composability.",
        "tools": [
            "sort",
            "uniq",
            "cut",
            "tr",
            "comm",
            "join",
            "paste",
            "split",
            "csplit",
            "fmt",
            "fold",
            "nl",
            "od",
            "seq",
            "numfmt",
            "shuf",
            "tac",
            "pr",
            "ptx",
            "expand",
            "unexpand",
            "tsort",
            "base64",
            "base32",
            "basenc",
            "cksum",
            "sum",
            "b2sum",
            "sha1sum",
            "sha224sum",
            "sha384sum",
            "sha512sum",
            "hash",
        ],
    },
    {
        "priority": "P3",
        "urgency": "normal",
        "category": "system_context_and_execution",
        "why": "Useful, but often environment-specific, long-running, privileged, or less central to file work.",
        "tools": [
            "date",
            "coreutils",
            "df",
            "du",
            "env",
            "id",
            "groups",
            "whoami",
            "uname",
            "arch",
            "nproc",
            "timeout",
            "sleep",
            "tty",
            "true",
            "false",
            "yes",
            "printf",
            "echo",
            "printenv",
            "sync",
            "dd",
            "shred",
            "chroot",
            "nice",
            "nohup",
            "stdbuf",
            "stty",
            "kill",
            "who",
            "users",
            "uptime",
            "hostid",
            "hostname",
            "logname",
            "pinky",
            "dircolors",
            "dir",
            "vdir",
            "[",
            "expr",
            "factor",
            "pathchk",
            "mknod",
            "chcon",
            "runcon",
        ],
    },
]


# ═══════════════════════════════════════════════════════════════════════
#  优先级推导（唯一权威来源：上方 CATALOG）
# ═══════════════════════════════════════════════════════════════════════

# 命令名 → 优先级 的快速查找表，在模块加载时从 CATALOG 构建
_COMMAND_PRIORITY_MAP: dict[str, str] = {}
for _entry in CATALOG:
    for _tool in _entry["tools"]:
        _COMMAND_PRIORITY_MAP[_tool] = _entry["priority"]


def get_priority(command_name: str) -> str:
    """查询单个命令的优先级（P0/P1/P2/P3），未找到返回 'unknown'。"""
    return _COMMAND_PRIORITY_MAP.get(command_name, "unknown")


def get_all_commands() -> set[str]:
    """返回所有已知命令名的集合（不含优先级信息）。"""
    return set(_COMMAND_PRIORITY_MAP)


def get_commands_by_priority() -> dict[str, list[str]]:
    """按优先级分组返回命令列表，每组内按字母序排列。

    Returns:
        {"P0": ["basename", "cat", ...], "P1": [...], ...}
    """
    grouped: dict[str, list[str]] = {}
    for cmd, pri in _COMMAND_PRIORITY_MAP.items():
        grouped.setdefault(pri, []).append(cmd)
    for pri in grouped:
        grouped[pri].sort()  # 字母序保证确定性
    return grouped


def implemented_catalog() -> dict[str, list[str]]:
    """与 priority_catalog() 格式兼容的已实现命令字典。

    本质上就是 get_commands_by_priority() 的别名，
    提供与 priority_catalog()['implemented'] 一致的接口。
    """
    return get_commands_by_priority()


def priority_catalog() -> dict[str, object]:
    """生成完整的命令目录 JSON（用于 catalog 和 schema 元命令）。

    Returns:
        包含 source（上游基准）、principles（设计原则）、
        categories（四级分类详情）、implemented（已实现命令）的字典。
        Agent 可通过此输出了解 aicoreutils 的完整能力面。
    """
    return {
        "source": "GNU Coreutils 9.10",
        "principles": [
            "json_by_default",  # 默认输出 JSON
            "no_color_or_progress_noise",  # 无颜色/进度条噪音
            "stderr_for_errors",  # 错误写入 stderr
            "semantic_exit_codes",  # 语义化退出码
            "dry_run_for_mutation",  # 修改命令支持 dry-run
            "stdin_stdout_composable",  # stdin/stdout 可组合
            "bounded_outputs",  # 输出有界
            "self_describing_help_and_schema",  # 自描述帮助和 schema
        ],
        "categories": CATALOG,
        "implemented": implemented_catalog(),
    }


def merge_plugin_commands(plugin_names: set[str], priority: str = "P3") -> dict[str, str]:
    """将插件命令合并到优先级映射表中（不修改 CATALOG）。

    生成新的 _COMMAND_PRIORITY_MAP 风格字典，插件命令映射到指定优先级。
    原 CATALOG 列表不受影响。

    Args:
        plugin_names: 插件命令名集合。
        priority: 插件命令的默认优先级。

    Returns:
        命令名 → 优先级 的字典（包含内置 + 插件命令）。
    """
    merged = dict(_COMMAND_PRIORITY_MAP)
    for name in plugin_names:
        if name not in merged:
            merged[name] = priority
    return merged


def catalog_with_plugins(plugin_names: set[str], priority: str = "P3") -> list[CatalogEntry]:
    """生成包含插件的 CATALOG 视图（不修改原 CATALOG）。

    Returns:
        新的 CatalogEntry 列表，包含原 CATALOG + 插件组。
    """
    if not plugin_names:
        return list(CATALOG)
    result = list(CATALOG)
    result.append(
        {
            "priority": priority,
            "urgency": "normal",
            "category": "plugin",
            "why": "User-installed plugin command.",
            "tools": sorted(plugin_names),
        }
    )
    return result
