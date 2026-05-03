"""JSON envelope helpers for aicoreutils.

JSON 信封格式是 aicoreutils 与 LLM Agent 之间的核心协议。
每个命令的 stdout 输出（成功）和 stderr 输出（失败）都遵循此格式。

协议契约：
    成功 → stdout: {"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}
    失败 → stderr: {"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}

--raw 模式会绕过信封，直接输出原始字节流到 stdout。
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING, Any, TextIO

if TYPE_CHECKING:
    from .exceptions import AgentError

# 项目版本号。作为信封的 version 字段，允许 Agent 做版本兼容性判断。
# 每次发版前需同步 pyproject.toml 中的 version。
_TOOL_VERSION = "0.3.3"


def utc_iso(timestamp: float) -> str:
    """将 Unix 时间戳转换为 ISO 8601 UTC 字符串（末尾 Z 标记）。

    用于 stat_entry 中的 modified_at/created_at 字段，
    保证跨平台时间格式一致。
    """
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).isoformat().replace("+00:00", "Z")


def write_json(stream: TextIO, payload: dict[str, Any], *, pretty: bool = False) -> None:
    """将字典序列化为一行 JSON 写入流。

    Args:
        stream: 输出流（通常为 sys.stdout 或 sys.stderr）。
        payload: 要序列化的字典。
        pretty: True 时启用缩进格式化（--pretty 标志）。

    默认使用紧凑格式（无空格），确保 Agent 解析效率最高。
    sort_keys=True 保证输出确定性，方便 Agent 做哈希比对。
    ensure_ascii=False 允许非 ASCII 字符直接输出（UTF-8）。
    """
    kwargs: dict[str, Any] = {"ensure_ascii": False, "sort_keys": True}
    if pretty:
        kwargs["indent"] = 2  # 人类可读模式：2 空格缩进
    else:
        kwargs["separators"] = (",", ":")  # 紧凑模式：最小空白
    stream.write(json.dumps(payload, **kwargs))
    stream.write("\n")


def envelope(command: str, result: Any, *, warnings: list[str] | None = None) -> dict[str, Any]:
    """构建成功响应信封。

    Args:
        command: 执行的命令名（如 "ls"）。
        result: 命令的返回结果（dict 或 bytes，--raw 模式下为 bytes）。
        warnings: 非致命警告列表（如 "部分目录因权限不足被跳过"）。

    Returns:
        JSON 兼容的字典，写入 stdout 通知 Agent 操作成功。
    """
    return {
        "ok": True,
        "tool": "aicoreutils",
        "version": _TOOL_VERSION,
        "command": command,
        "result": result,
        "warnings": warnings or [],
    }


def error_envelope(command: str | None, error: AgentError) -> dict[str, Any]:
    """构建失败响应信封。

    Args:
        command: 执行的命令名。解析阶段失败时为 None。
        error: AgentError 实例，包含语义码和人类可读消息。

    Returns:
        JSON 兼容的字典，写入 stderr 通知 Agent 操作失败。
    """
    return {
        "ok": False,
        "tool": "aicoreutils",
        "version": _TOOL_VERSION,
        "command": command,
        "error": error.to_dict(),
    }
