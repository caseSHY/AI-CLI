"""Text escaping, field splitting, character transformation, and word-count utilities.

C 风格转义序列解析（\\n, \\t, \\xNN 等），tr 命令的字符集转换，
expand/unexpand 的制表符逻辑，以及 wc 命令的字数统计。
"""

from __future__ import annotations

import re
from typing import Any

from ..core import AgentError


def decode_standard_escapes(value: str) -> str:
    """解码 C 风格转义序列：\\n → 换行, \\t → 制表, \\xNN → 十六进制字节。"""
    escapes = {
        "\\": "\\",
        "0": "\0",
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
    }
    output: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            output.append(char)
            index += 1
            continue
        marker = value[index + 1]
        if marker == "x":
            hex_digits = value[index + 2 : index + 4]
            if hex_digits and all(item in "0123456789abcdefABCDEF" for item in hex_digits):
                output.append(chr(int(hex_digits, 16)))
                index += 2 + len(hex_digits)
                continue
        output.append(escapes.get(marker, marker))
        index += 2
    return "".join(output)


def parse_octal_mode(raw: str) -> int:
    """解析八进制权限模式（如 644, 755, 0o644），仅支持八进制。

    注意：不支持 GNU 符号模式（u+x, g-w 等），这是 agentutils 的有意限制。
    """
    value = raw.strip()
    if value.startswith("0o"):
        value = value[2:]
    if not value or len(value) > 4 or any(char not in "01234567" for char in value):
        raise AgentError(
            "invalid_input",
            "Only octal chmod modes are supported by this agent-friendly implementation.",
            details={"mode": raw},
            suggestion="Use modes like 644, 755, or 0644.",
        )
    return int(value, 8)


def count_words(text: str) -> int:
    """按空白字符分词并计数。"""
    return len(text.split())


def wc_for_bytes(data: bytes, *, encoding: str) -> dict[str, Any]:
    """统计字节数据的 bytes/chars/lines/words 四项指标。"""
    text = data.decode(encoding, errors="replace")
    return {
        "bytes": len(data),
        "chars": len(text),
        "lines": data.count(b"\n"),
        "words": count_words(text),
    }


def unexpand_line(line: str, *, tab_size: int, all_blanks: bool) -> str:
    """将前导空格（或全部空格）转换为制表符。

    Args:
        line: 输入行。
        tab_size: 制表符宽度。
        all_blanks: True 时转换所有空格运行，False 时仅转换行首。
    """
    def compress_spaces(match: re.Match[str]) -> str:
        width = len(match.group(0))
        return "\t" * (width // tab_size) + " " * (width % tab_size)

    if all_blanks:
        return re.sub(r" +", compress_spaces, line)
    leading = re.match(r" +", line)
    if not leading:
        return line
    return compress_spaces(leading) + line[leading.end():]


def split_fields(line: str, delimiter: str | None) -> list[str]:
    """按分隔符或空白字符拆分字段。"""
    return line.split(delimiter) if delimiter is not None else line.split()


def squeeze_repeats(text: str, squeeze_set: set[str]) -> str:
    """压缩连续重复字符：将 squeeze_set 中的连续重复压缩为单个。"""
    if not text:
        return text
    output = [text[0]]
    for char in text[1:]:
        if char == output[-1] and char in squeeze_set:
            continue
        output.append(char)
    return "".join(output)


def expand_tr_set(spec: str) -> str:
    """展开字符集规范，支持 a-z 范围语法。

    例如 "a-z" → "abcdefghijklmnopqrstuvwxyz"。
    """
    output: list[str] = []
    index = 0
    while index < len(spec):
        if index + 2 < len(spec) and spec[index + 1] == "-":
            start = ord(spec[index])
            end = ord(spec[index + 2])
            if start <= end:
                output.extend(chr(value) for value in range(start, end + 1))
                index += 3
                continue
        output.append(spec[index])
        index += 1
    return "".join(output)


def transform_text(args: Any, text: str) -> str:
    """tr 命令的字符转换/删除/压缩引擎。

    组合 --delete、SET1→SET2 转换、--squeeze-repeats 三种操作。
    """
    set1 = expand_tr_set(args.set1)
    set2 = expand_tr_set(args.set2) if args.set2 is not None else None
    if args.delete:
        output = text.translate({ord(char): None for char in set1})
        squeeze_source = set1
    else:
        if set2 is None and args.squeeze_repeats:
            output = text
            squeeze_source = set1
        elif set2 is None:
            raise AgentError("invalid_input", "Translation requires SET2 unless --delete is used.")
        elif not set2:
            raise AgentError("invalid_input", "SET2 cannot be empty for translation.")
        else:
            translation = {}
            for index, char in enumerate(set1):
                replacement = set2[index] if index < len(set2) else set2[-1]
                translation[ord(char)] = replacement
            output = text.translate(translation)
            squeeze_source = set2
    if args.squeeze_repeats:
        output = squeeze_repeats(output, set(squeeze_source))
    return output
