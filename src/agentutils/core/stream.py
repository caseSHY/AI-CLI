"""Streaming NDJSON output for large dataset operations.

流式输出层：提供 NDJSON（newline-delimited JSON）格式的逐行输出能力，
用于处理大目录、大文件和大管道场景，避免内存膨胀。

NDJSON 格式说明：
    每行一个 JSON 对象，以 \n 分隔。Agent 可以逐行解析，
    不需要在内存中保存整个响应。

    {"type":"item","path":"..."}
    {"type":"item","path":"..."}
    {"ok":true,"tool":"agentutils",...,"stream":true,"count":1000,"truncated":false,"summary":{...}}

使用场景：
    ls --stream --recursive /large/dir
    find --stream --name "*.py"
"""

from __future__ import annotations

import json
from typing import Any, TextIO

from .envelope import _TOOL_VERSION


class StreamWriter:
    """NDJSON 流式写入器：逐行输出 JSON 条目 + 结尾信封。

    设计原则：
    - 每个条目输出为一行紧凑 JSON（sort_keys=True 保证确定性）。
    - 达到 max_items 上限后自动截断，后续 write_item 返回 False。
    - write_summary 在流末尾写入带 count/truncated 的总结信封。
    - 幂等保护：closed 后 write_item 和 write_summary 均无操作。

    Usage:
        writer = StreamWriter(sys.stdout, command="ls", max_items=10000)
        for item in large_iterator:
            if not writer.write_item(item):
                break  # 截断
        writer.write_summary({"total_bytes": 12345})
    """

    def __init__(
        self,
        stream: TextIO,
        *,
        command: str,
        max_items: int = 0,
    ) -> None:
        self._stream = stream  # 输出流（通常 sys.stdout）
        self._command = command  # 命令名（用于信封）
        self._max_items = max_items  # 最大条目数（0 = 无限制）
        self._count = 0  # 已输出条目计数
        self._truncated = False  # 是否已截断
        self._closed = False  # 是否已关闭

    def write_item(self, item: dict[str, Any]) -> bool:
        """写入一个 NDJSON 条目。

        Returns:
            True 表示已写入（或 dry-run 模式），False 表示已被截断。
            调用方应检查返回值并在 False 时停止迭代。
        """
        if self._closed:
            return False
        if self._max_items and self._count >= self._max_items:
            self._truncated = True
            return False
        self._count += 1
        # 紧凑 JSON 格式：无空格、按键排序、允许非 ASCII
        line = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self._stream.write(line + "\n")
        return True

    def write_summary(self, summary: dict[str, Any]) -> None:
        """写入流末尾的总结信封（带缩进，便于人类调试）。

        只在第一次调用时生效，后续调用为 no-op（幂等保护）。
        """
        if self._closed:
            return
        self._closed = True
        envelope = {
            "ok": True,
            "tool": "agentutils",
            "version": _TOOL_VERSION,
            "command": self._command,
            "stream": True,  # 标记这是流式响应
            "count": self._count,
            "truncated": self._truncated,
            "summary": summary,
        }
        self._stream.write(json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n")

    @property
    def count(self) -> int:
        """已写入的条目数"""
        return self._count

    @property
    def truncated(self) -> bool:
        """是否因 max_items 限制而被截断"""
        return self._truncated


class NullStream:
    """空操作流写入器，用于 dry-run 模式。

    实现与 StreamWriter 相同的接口，但不产生任何输出。
    这允许命令代码统一使用 StreamWriter 接口而无需 if dry_run 分支。
    """

    def write_item(self, item: dict[str, Any]) -> bool:
        return True  # dry-run 总是"成功"

    def write_summary(self, summary: dict[str, Any]) -> None:
        pass  # dry-run 不输出

    @property
    def count(self) -> int:
        return 0

    @property
    def truncated(self) -> bool:
        return False


def is_stream_mode(args: Any) -> bool:
    """检查命令参数是否启用了 --stream 模式。

    使用 getattr 而非 args.stream 直接访问，避免 AttributeError。
    这允许并非所有命令都定义 --stream 参数。
    """
    return getattr(args, "stream", False)
