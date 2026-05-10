"""Async command interface for aicoreutils.

异步调用接口：提供 asyncio 包装器，允许 Agent 在事件循环中
并发运行多个 aicoreutils 命令，而非串行等待每个子进程。

使用场景：
    # 并发 ls 多个目录
    results = await run_async_many([
        ("ls", "/dir1"),
        ("ls", "/dir2"),
        ("ls", "/dir3"),
    ])

技术实现：
- run_async 使用 asyncio.create_subprocess_exec 创建子进程。
- run_async_many 使用 asyncio.Semaphore 控制并发数。
- 超时通过 asyncio.wait_for 实现，超时后 kill 子进程。
- 子进程通过 PYTHONPATH 环境变量找到 aicoreutils 包（避免需要 pip install）。
- 并发数和超时默认值来自 core.constants。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from .core.constants import ASYNC_DEFAULT_CONCURRENCY
from .core.encoding import decode_bytes


async def run_async(
    *args: str,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """异步运行单个 aicoreutils 命令并返回 JSON 结果。

    此函数在 asyncio 事件循环中创建子进程，不会阻塞事件循环。

    Args:
        *args: 命令行参数，如 ("ls", ".", "--recursive")。
        cwd: 命令的工作目录，None 则继承当前。
        timeout: 最大等待秒数，None 则无限等待。

    Returns:
        解析后的 JSON 信封字典（{"ok": True, "result": ..., ...}）。

    Raises:
        asyncio.TimeoutError: 命令超时。
        RuntimeError: 命令返回非零退出码。
    """
    cmd = [sys.executable, "-m", "aicoreutils", *args]
    # 计算 src/ 目录的绝对路径，放入 PYTHONPATH 确保子进程能找到包
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1])}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env={**__import__("os").environ, **env},
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc

    import json

    if proc.returncode != 0:
        error_text = decode_bytes(stderr, encoding="utf-8", errors="replace").text
        try:
            error_data = json.loads(error_text)
        except json.JSONDecodeError:
            error_data = {"error": error_text}
        raise RuntimeError(f"Command failed with exit code {proc.returncode}: {error_data}")

    data: object = json.loads(decode_bytes(stdout, encoding="utf-8", errors="replace").text)
    if not isinstance(data, dict):
        raise RuntimeError("Command returned non-object JSON.")
    return {str(key): value for key, value in data.items()}


async def run_async_many(
    commands: list[tuple[str, ...]],
    *,
    concurrency: int = ASYNC_DEFAULT_CONCURRENCY,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """并发运行多个 aicoreutils 命令。

    使用 asyncio.Semaphore 控制并发数，防止同时创建过多子进程。
    asyncio.gather 保证返回顺序与输入命令顺序一致。

    Args:
        commands: 命令参数元组列表，如 [("ls", "."), ("stat", "f.txt")]。
        concurrency: 最大并发数，默认 ASYNC_DEFAULT_CONCURRENCY (10)。
        timeout: 每个命令的超时秒数，None 则无限等待。

    Returns:
        结果字典列表，顺序与输入 commands 一致。

    Raises:
        RuntimeError: 任一命令失败（return_exceptions=False）。
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(cmd_args: tuple[str, ...]) -> dict[str, Any]:
        """包装 run_async，通过信号量限制并发。"""
        async with semaphore:
            return await run_async(*cmd_args, timeout=timeout)

    tasks = [_run_one(cmd) for cmd in commands]
    # return_exceptions=False：任一失败则整体抛出异常
    return await asyncio.gather(*tasks, return_exceptions=False)
