"""Core modules for aicoreutils: exceptions, envelope, path utilities, sandbox, streaming.

aicoreutils.core 是项目的核心基础层，提供所有命令实现公用的基础能力。

模块层次（从底层到高层）：
    exit_codes.py   — 语义退出码 → POSIX 进程退出码映射（无外部依赖）。
    exceptions.py   — AgentError 异常类（依赖 exit_codes）。
    envelope.py     — JSON 信封序列化（依赖 exceptions 类型标注）。
    path_utils.py   — 安全路径解析、元数据收集、目录遍历。
    sandbox.py      — cwd 边界校验、删除保护、覆盖保护（依赖 path_utils）。
    stream.py       — NDJSON 流式输出（依赖 envelope 的版本号）。
    constants.py    — 集中化配置常量（Magic Number 唯一权威来源）。
    plugin_registry.py — 不可变插件注册表（线程安全）。

所有模块通过本 __init__.py 聚合导出，供 protocol.py 和命令模块使用。
"""

from __future__ import annotations

from .command import BaseCommand, CommandResult, FileInfoCommand, MutatingCommand, TextFilterCommand
from .config import DEFAULT_CONFIG, AgentConfig
from .constants import (
    ASYNC_DEFAULT_CONCURRENCY,
    ASYNC_DEFAULT_TIMEOUT,
    DD_DEFAULT_BLOCK_SIZE,
    DEFAULT_ENCODING,
    DEFAULT_ENCODING_ERRORS,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ITEMS,
    DEFAULT_MAX_LINES,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_PATH_LENGTH,
    DEFAULT_MAX_PREVIEW_BYTES,
    DEFAULT_TAB_SIZE,
    DEFAULT_WIDTH,
    ENCODING_CHOICES,
    ENCODING_ERRORS_CHOICES,
    ENCODING_PROFILE_CHOICES,
    FACTOR_MAX,
    HASH_CHUNK_SIZE,
)
from .encoding import EncodingResult, decode_bytes, detect_bom, detect_encoding, encoding_metadata, normalize_encoding
from .envelope import deprecation_warning, envelope, error_envelope, utc_iso, write_json
from .exceptions import AgentError
from .exit_codes import EXIT
from .path_utils import (
    directory_size,
    disk_usage_entry,
    ensure_exists,
    ensure_parent,
    iter_directory,
    path_type,
    resolve_path,
    stat_entry,
)
from .plugin_registry import CommandFunc, PluginRegistry
from .sandbox import (
    dangerous_delete_target,
    destination_inside_directory,
    refuse_overwrite,
    remove_one,
    require_inside_cwd,
)
from .stream import NullStream, StreamWriter, is_stream_mode

__all__ = [
    "AgentConfig",
    "ASYNC_DEFAULT_CONCURRENCY",
    "BaseCommand",
    "ASYNC_DEFAULT_TIMEOUT",
    "AgentError",
    "CommandFunc",
    "CommandResult",
    "DD_DEFAULT_BLOCK_SIZE",
    "DEFAULT_CONFIG",
    "DEFAULT_ENCODING",
    "DEFAULT_ENCODING_ERRORS",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_DEPTH",
    "DEFAULT_MAX_ITEMS",
    "DEFAULT_MAX_LINES",
    "DEFAULT_MAX_OUTPUT_BYTES",
    "DEFAULT_MAX_PATH_LENGTH",
    "DEFAULT_MAX_PREVIEW_BYTES",
    "DEFAULT_TAB_SIZE",
    "DEFAULT_WIDTH",
    "ENCODING_CHOICES",
    "ENCODING_ERRORS_CHOICES",
    "ENCODING_PROFILE_CHOICES",
    "EXIT",
    "EncodingResult",
    "FACTOR_MAX",
    "FileInfoCommand",
    "HASH_CHUNK_SIZE",
    "MutatingCommand",
    "NullStream",
    "normalize_encoding",
    "PluginRegistry",
    "StreamWriter",
    "TextFilterCommand",
    "dangerous_delete_target",
    "decode_bytes",
    "deprecation_warning",
    "destination_inside_directory",
    "detect_bom",
    "detect_encoding",
    "directory_size",
    "disk_usage_entry",
    "encoding_metadata",
    "envelope",
    "ensure_exists",
    "ensure_parent",
    "error_envelope",
    "is_stream_mode",
    "iter_directory",
    "path_type",
    "refuse_overwrite",
    "remove_one",
    "require_inside_cwd",
    "resolve_path",
    "stat_entry",
    "utc_iso",
    "write_json",
]
