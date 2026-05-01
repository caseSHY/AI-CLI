"""Async command interface for agentutils.

Phase 2.2: Provides async wrappers for running agentutils commands
from asyncio event loops, enabling concurrent Agent operations.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any


async def run_async(
    *args: str,
    cwd: Path | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run an agentutils command asynchronously and return the JSON result.

    Args:
        *args: Command-line arguments (e.g., "ls", ".", "--recursive").
        cwd: Working directory for the command.
        timeout: Maximum seconds to wait.

    Returns:
        Parsed JSON envelope from the command.

    Raises:
        asyncio.TimeoutError: If the command times out.
        RuntimeError: If the command returns a non-zero exit code.
    """
    cmd = [sys.executable, "-m", "agentutils", *args]
    env = {"PYTHONPATH": str(Path(__file__).resolve().parents[2])}

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
        error_text = stderr.decode("utf-8", errors="replace")
        try:
            error_data = json.loads(error_text)
        except json.JSONDecodeError:
            error_data = {"error": error_text}
        raise RuntimeError(f"Command failed with exit code {proc.returncode}: {error_data}")

    data: object = json.loads(stdout.decode("utf-8", errors="replace"))
    if not isinstance(data, dict):
        raise RuntimeError("Command returned non-object JSON.")
    return {str(key): value for key, value in data.items()}


async def run_async_many(
    commands: list[tuple[str, ...]],
    *,
    concurrency: int = 10,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Run multiple agentutils commands concurrently.

    Args:
        commands: List of command argument tuples.
        concurrency: Maximum number of concurrent commands.
        timeout: Per-command timeout in seconds.

    Returns:
        List of result dicts in the same order as commands.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(cmd_args: tuple[str, ...]) -> dict[str, Any]:
        async with semaphore:
            return await run_async(*cmd_args, timeout=timeout)

    tasks = [_run_one(cmd) for cmd in commands]
    return await asyncio.gather(*tasks, return_exceptions=False)
