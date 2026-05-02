"""printf-style format string parsing and value coercion."""

from __future__ import annotations

from ..core import AgentError
from ._text import decode_standard_escapes


def printf_conversions(format_string: str) -> list[str]:
    """提取 printf 格式字符串中的所有转换标识符（diouxXeEfFgGcrsa）。

    不支持 '*' 宽度和精度语法。
    """
    conversions: list[str] = []
    index = 0
    valid = "diouxXeEfFgGcrsa"
    while index < len(format_string):
        if format_string[index] != "%":
            index += 1
            continue
        if index + 1 < len(format_string) and format_string[index + 1] == "%":
            index += 2  # 跳过转义的 %%
            continue
        end = index + 1
        while end < len(format_string) and format_string[end] not in valid:
            if format_string[end] == "*":
                raise AgentError("invalid_input", "printf '*' width and precision are not supported.")
            end += 1
        if end >= len(format_string):
            raise AgentError("invalid_input", "printf format contains an incomplete conversion.")
        conversions.append(format_string[end])
        index = end + 1
    return conversions


def coerce_printf_value(value: str, conversion: str) -> object:
    """将字符串值转换为 printf 转换符所需类型（int/float/str）。"""
    try:
        if conversion in "diouxX":
            return int(value, 0)
        if conversion in "eEfFgG":
            return float(value)
        if conversion == "c":
            return value if len(value) == 1 else int(value, 0)
    except ValueError as exc:
        raise AgentError(
            "invalid_input",
            "printf value cannot be coerced for the requested conversion.",
            details={"value": value, "conversion": conversion},
        ) from exc
    return value


def format_printf(format_string: str, values: list[str]) -> str:
    """执行 printf 格式化，支持格式字符串循环和值循环。

    规则：values 数量必须是 conversions 数量的整数倍。
    """
    fmt = decode_standard_escapes(format_string)
    conversions = printf_conversions(fmt)
    if not conversions:
        if values:
            raise AgentError("invalid_input", "printf received values but the format has no conversions.")
        return fmt
    if len(values) % len(conversions) != 0:
        raise AgentError(
            "invalid_input",
            "printf values must fill the format exactly; repeat the format by passing a multiple of its conversions.",
            details={"values": len(values), "conversions_per_format": len(conversions)},
        )
    output: list[str] = []
    for start in range(0, len(values), len(conversions)):
        chunk = values[start : start + len(conversions)]
        converted = tuple(
            coerce_printf_value(value, conversion) for value, conversion in zip(chunk, conversions, strict=True)
        )
        try:
            output.append(fmt % converted)
        except (TypeError, ValueError) as exc:
            raise AgentError("invalid_input", "printf format could not be applied to the supplied values.") from exc
    return "".join(output)
