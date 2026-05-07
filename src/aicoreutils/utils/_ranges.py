"""Range parsing and suffix generation for cut/csplit/split commands."""

from __future__ import annotations

from ..core import AgentError


def alpha_suffix(index: int, width: int) -> str:
    """生成字母后缀（aa, ab, ..., zz, aaa, ...）用于 split 输出文件名。"""
    if width < 1:
        raise AgentError("invalid_input", "--suffix-length must be >= 1.")
    limit = 26**width
    if index >= limit:
        raise AgentError(
            "invalid_input",
            "Too many split chunks for the requested alphabetic suffix length.",
            details={"index": index, "suffix_length": width},
        )
    chars = ["a"] * width
    value = index
    for position in range(width - 1, -1, -1):
        chars[position] = chr(ord("a") + (value % 26))
        value //= 26
    return "".join(chars)


def numeric_suffix(index: int, width: int) -> str:
    """生成数字后缀（001, 002, ...）用于 split 输出文件名。"""
    if width < 1:
        raise AgentError("invalid_input", "--suffix-length must be >= 1.")
    suffix = str(index).zfill(width)
    if len(suffix) > width:
        raise AgentError(
            "invalid_input",
            "Too many split chunks for the requested numeric suffix length.",
            details={"index": index, "suffix_length": width},
        )
    return suffix


def parse_ranges(spec: str) -> list[tuple[int | None, int | None]]:
    """解析逗号分隔的 1-based 范围字符串。

    例如 "1-3,7" → [(1, 3), (7, 7)]。
    None 表示开放范围（如 -5 或 3-）。
    """
    ranges: list[tuple[int | None, int | None]] = []
    for part in spec.split(","):
        item = part.strip()
        if not item:
            raise AgentError("invalid_input", "Range specification contains an empty item.")
        try:
            if "-" in item:
                start_raw, end_raw = item.split("-", 1)
                start = int(start_raw) if start_raw else None
                end = int(end_raw) if end_raw else None
            else:
                start = int(item)
                end = start
        except ValueError as exc:
            raise AgentError(
                "invalid_input",
                "Range specification must contain positive integers, commas, and hyphens.",
                details={"range": spec},
            ) from exc
        if start is not None and start < 1:
            raise AgentError("invalid_input", "Ranges are 1-based and must be positive.")
        if end is not None and end < 1:
            raise AgentError("invalid_input", "Ranges are 1-based and must be positive.")
        if start is not None and end is not None and start > end:
            raise AgentError("invalid_input", "Range start cannot be greater than range end.")
        ranges.append((start, end))
    return ranges


def selected_indexes(length: int, ranges: list[tuple[int | None, int | None]]) -> list[int]:
    """将 1-based 范围转换为去重、排序的 0-based 索引列表。

    用于 cut 命令的字段选择。
    """
    indexes: list[int] = []
    seen: set[int] = set()
    for start, end in ranges:
        first = 1 if start is None else start
        last = length if end is None else end
        for one_based in range(first, min(last, length) + 1):
            zero_based = one_based - 1
            if zero_based not in seen:
                seen.add(zero_based)
                indexes.append(zero_based)
    return indexes
