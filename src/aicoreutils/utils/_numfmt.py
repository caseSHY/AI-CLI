"""Number formatting: SI/IEC unit parsing and human-readable conversion.

Supports numfmt's --from-unit / --to-unit with SI (1000-based) and
IEC (1024-based) unit systems.
"""

from __future__ import annotations

import re

from ..core import AgentError

SI_UNITS: dict[str, float] = {
    "": 1.0,
    "K": 1000.0,
    "M": 1000.0**2,
    "G": 1000.0**3,
    "T": 1000.0**4,
    "P": 1000.0**5,
    "E": 1000.0**6,
}
IEC_UNITS: dict[str, float] = {
    "": 1.0,
    "K": 1024.0,
    "M": 1024.0**2,
    "G": 1024.0**3,
    "T": 1024.0**4,
    "P": 1024.0**5,
    "E": 1024.0**6,
}


def parse_numfmt_value(raw: str, unit_system: str) -> float:
    """解析带可选单位后缀的数值字符串为标准浮点数。

    Args:
        raw: 输入字符串，如 "1.5K"、"2M"。
        unit_system: "si" | "iec" | "none"。

    Returns:
        规范化的浮点数值（无单位）。
    """
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))([A-Za-z]*)", raw.strip())
    if not match:
        raise AgentError(
            "invalid_input", "numfmt input must be a number with an optional unit suffix.", details={"value": raw}
        )
    value = float(match.group(1))
    suffix = match.group(2)
    if unit_system == "none":
        if suffix:
            raise AgentError(
                "invalid_input", "Unit suffix was provided but --from-unit is none.", details={"value": raw}
            )
        return value
    normalized = suffix.upper().removesuffix("B")
    if unit_system == "iec":
        normalized = normalized.removesuffix("I")
    units = SI_UNITS if unit_system == "si" else IEC_UNITS
    if normalized not in units:
        raise AgentError(
            "invalid_input",
            "Unsupported numfmt unit suffix.",
            details={"value": raw, "suffix": suffix, "unit_system": unit_system},
        )
    return value * units[normalized]


def format_numfmt_value(value: float, unit_system: str, precision: int) -> str:
    """将裸数值格式化为人类可读的单位后缀字符串。

    Args:
        value: 裸数值。
        unit_system: "si" | "iec" | "none"。
        precision: 小数位数，截尾零会被去除。

    Returns:
        格式化后的字符串，如 "1.5K"、"2Mi"。
    """
    if precision < 0:
        raise AgentError("invalid_input", "--precision must be >= 0.")
    if unit_system == "none":
        formatted = f"{value:.{precision}f}"
        return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted
    units = SI_UNITS if unit_system == "si" else IEC_UNITS
    suffixes = ["", "K", "M", "G", "T", "P", "E"]
    suffix = ""
    scaled = value
    for candidate in suffixes:
        factor = units[candidate]
        if abs(value) >= factor:
            suffix = candidate
            scaled = value / factor
    formatted = f"{scaled:.{precision}f}".rstrip("0").rstrip(".")
    if unit_system == "iec" and suffix:
        suffix = f"{suffix}i"
    return f"{formatted}{suffix}"
