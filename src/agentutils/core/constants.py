"""Centralized configuration constants for agentutils.

所有魔术数字、默认值、限制值的唯一权威来源。
修改这些值后，所有命令自动同步，无需逐文件搜索替换。

使用方式：
    from agentutils.core.constants import DEFAULT_MAX_LINES
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
#  输出限制 / Output bounds
# ═══════════════════════════════════════════════════════════════════════

# 默认最大输出行数（JSON 条目）。适用于 ls、sort、wc、cat 等所有
# 产生列表输出的命令。Agent 可通过 --max-lines 覆盖。
DEFAULT_MAX_LINES: int = 10_000

# 默认最大输出字节数（--raw 模式捕获）。适用于 timeout/nice/nohup/
# stdbuf/chroot 等子进程 stdout/stderr 捕获。
DEFAULT_MAX_OUTPUT_BYTES: int = 65_536  # 64 KiB

# 默认最大文件读取字节数。适用于 cat/head/tail/dd 等命令。
DEFAULT_MAX_BYTES: int = 1_048_576  # 1 MiB (1024 * 1024)

# 默认最大路径长度（字符数）。适用于 pathchk 等命令。
DEFAULT_MAX_PATH_LENGTH: int = 4_096

# 默认最大文件预览字节数。适用于 hexdump 风格输出。
DEFAULT_MAX_PREVIEW_BYTES: int = 4_096

# 默认最大条目生成数。适用于 seq/yes 等无限生成命令的安全上限。
DEFAULT_MAX_ITEMS: int = 10_000

# ═══════════════════════════════════════════════════════════════════════
#  文本处理 / Text processing
# ═══════════════════════════════════════════════════════════════════════

# 默认制表符宽度。适用于 expand/unexpand 命令。
DEFAULT_TAB_SIZE: int = 8

# 默认文本宽度。适用于 fold/fmt 等格式化命令。
DEFAULT_WIDTH: int = 80

# 默认最大递归深度。适用于 du/ls 等递归遍历命令。
DEFAULT_MAX_DEPTH: int = 8

# ═══════════════════════════════════════════════════════════════════════
#  计算限制 / Computation limits
# ═══════════════════════════════════════════════════════════════════════

# factor 命令的安全上限（绝对值）。防止大数分解导致 CPU 耗尽。
FACTOR_MAX: int = 10**12

# ═══════════════════════════════════════════════════════════════════════
#  哈希/摘要 / Hashing
# ═══════════════════════════════════════════════════════════════════════

# 文件哈希的分块读取大小。平衡内存使用与 I/O 效率。
HASH_CHUNK_SIZE: int = 1_048_576  # 1 MiB

# ═══════════════════════════════════════════════════════════════════════
#  并发 / Concurrency
# ═══════════════════════════════════════════════════════════════════════

# 默认并发数。适用于 run_async_many 的 Semaphore。
ASYNC_DEFAULT_CONCURRENCY: int = 10

# 默认异步超时（秒）。适用于 run_async 的 asyncio.wait_for。
ASYNC_DEFAULT_TIMEOUT: float = 30.0

# ═══════════════════════════════════════════════════════════════════════
#  其他 / Miscellaneous
# ═══════════════════════════════════════════════════════════════════════

# dd 命令的默认块大小。
DD_DEFAULT_BLOCK_SIZE: int = 1_048_576  # 1 MiB
