"""I/O helpers: stdin, file, byte, and line reading utilities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ..core import AgentError, ensure_exists, resolve_path


def read_stdin_bytes() -> bytes:
    """读取标准输入的全部原始字节。"""
    return sys.stdin.buffer.read()


def read_input_bytes(raw: str) -> tuple[str, bytes]:
    """读取文件或 stdin（"-"）的全部原始字节。

    Returns:
        (来源标签, 字节数据)。标签为文件路径或 "-"。
    """
    if raw == "-":
        return "-", read_stdin_bytes()               # stdin 模式
    path = resolve_path(raw, strict=True)
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    try:
        return str(path), path.read_bytes()
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while reading file.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc


def read_input_texts(paths: list[str], *, encoding: str) -> list[dict[str, str]]:
    """读取多个文件或 stdin 并解码为文本。

    Returns:
        [{"path": 来源, "text": 文本内容}, ...]
    """
    if not paths:
        paths = ["-"]                                 # 无参数时默认读取 stdin
    sources: list[dict[str, str]] = []
    for raw in paths:
        label, data = read_input_bytes(raw)
        sources.append({"path": label, "text": data.decode(encoding, errors="replace")})
    return sources


def combined_lines(paths: list[str], *, encoding: str) -> tuple[list[str], list[str]]:
    """读取多个文件/文本，返回合并后的行列表和来源列表。

    Returns:
        (所有行的列表, 来源路径列表)。行去除了 \\n 分隔符。
    """
    sources = read_input_texts(paths, encoding=encoding)
    lines: list[str] = []
    for source in sources:
        lines.extend(source["text"].splitlines())
    return lines, [source["path"] for source in sources]


def bounded_lines(lines: list[Any], max_lines: int) -> tuple[list[Any], bool]:
    """按行数截断列表，防止输出过大。

    Returns:
        (截断后的列表, 是否被截断)。
    """
    if max_lines < 0:
        raise AgentError("invalid_input", "--max-lines must be >= 0.")
    return lines[:max_lines], len(lines) > max_lines


def lines_to_raw(lines: list[str], *, encoding: str) -> bytes:
    """将行列表编码为带换行符的字节流（--raw 模式输出）。"""
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode(encoding)


def read_text_lines(path: Path, *, encoding: str) -> list[str]:
    """读取文件的所有文本行（去除了 \\n）。

    支持 universal newlines（newline=""），兼容 CRLF/LF/CR。
    """
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        return handle.read().splitlines()


def read_bytes(path: Path, *, max_bytes: int, offset: int = 0) -> tuple[bytes, bool, int]:
    """读取文件的部分字节（支持 offset 和 max_bytes 有界读取）。

    Returns:
        (数据字节, 是否被截断, 文件总大小)。
    """
    if max_bytes < 0:
        raise AgentError("invalid_input", "--max-bytes must be >= 0.")
    if offset < 0:
        raise AgentError("invalid_input", "--offset must be >= 0.")
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(max_bytes)
        truncated = offset + len(data) < size
    return data, truncated, size
