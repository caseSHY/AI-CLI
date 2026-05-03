"""Immutable configuration object for aicoreutils.

Provides AgentConfig, a frozen dataclass that centralizes all
tunable defaults.  Command functions receive it via argparse namespace
(``args._config``) or import the module-level default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    """不可变配置对象：集中管理所有可调默认值。

    命令函数通过 argparse namespace（args._config）或模块级默认值
    DEFAULT_CONFIG 访问配置。
    """

    # ── 输出限制 ──
    max_lines: int = 10_000
    max_bytes: int = 1_048_576  # 1 MiB
    max_output_bytes: int = 65_536  # 64 KiB
    max_path_length: int = 4_096
    max_preview_bytes: int = 4_096
    max_depth: int = 8

    # ── 文本处理 ──
    tab_size: int = 8
    default_width: int = 80

    # ── 计算限制 ──
    factor_max: int = 10**12

    # ── 并发 ──
    async_concurrency: int = 10
    async_timeout: float = 30.0

    # ── 路径 ──
    cwd: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_env(cls) -> AgentConfig:
        """从 AGENTUTILS_* 环境变量读取覆盖值。"""
        import os
        from typing import Any

        kwargs: dict[str, Any] = {}
        for fld in cls.__dataclass_fields__:
            env_key = f"AGENTUTILS_{fld.upper()}"
            if env_key in os.environ:
                raw = os.environ[env_key]
                target_type = cls.__dataclass_fields__[fld].type
                if target_type is int:
                    kwargs[fld] = int(raw)
                elif target_type is float:
                    kwargs[fld] = float(raw)
                elif target_type is Path:
                    kwargs[fld] = Path(raw)
                else:
                    kwargs[fld] = raw
        return cls(**kwargs) if kwargs else cls()


# 模块级默认配置实例。命令模块可通过 from .core.config import DEFAULT_CONFIG 引用
DEFAULT_CONFIG = AgentConfig()
