"""Core exception classes for agentutils.

AgentError 是 agentutils 唯一的异常类型。所有命令实现只抛出此异常，
不抛出裸 OSError、ValueError 等。这使得上层调用方（parser.main）
可以统一捕获并转换为 JSON 错误响应。

设计原则：
- 每个 AgentError 携带一个语义码（code），对应 exit_codes.EXIT 的键。
- 可选的 path 字段标识出错的路径，方便 Agent 定位问题。
- 可选的 suggestion 字段提供人类可读的修复建议。
- 可选的 details 字典携带机器可读的额外上下文。
"""

from __future__ import annotations

from typing import Any

from .exit_codes import EXIT


class AgentError(Exception):
    """语义化错误：机器可读的错误码 + 可选路径 + 修复建议。

    所有 agentutils 命令在遇到可恢复/需报告的错误时抛出此异常。
    上层 parser.main() 统一捕获并序列化为 JSON 错误信封输出到 stderr。

    Attributes:
        code: 语义错误码，必须是 EXIT 字典的有效键（如 "not_found"）。
        message: 人类可读的错误描述。
        path: 可选，出错的路径。
        suggestion: 可选，修复建议（如 "Pass --allow-overwrite"）。
        details: 可选，附加的结构化信息（如原始 OS 错误消息）。
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        path: str | None = None,
        suggestion: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code  # 语义错误码
        self.message = message  # 人类可读消息
        self.path = path  # 可选：出错路径
        self.suggestion = suggestion  # 可选：修复建议
        self.details = details or {}  # 可选：附加上下文

    @property
    def exit_code(self) -> int:
        """从语义码查表得到 POSIX 进程退出码。"""
        return EXIT.get(self.code, EXIT["general_error"])

    def to_dict(self) -> dict[str, Any]:
        """序列化为 JSON 兼容的字典，剔除 None 字段减少噪音。"""
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.path is not None:
            error["path"] = self.path
        if self.suggestion is not None:
            error["suggestion"] = self.suggestion
        if self.details:
            error["details"] = self.details
        return error
