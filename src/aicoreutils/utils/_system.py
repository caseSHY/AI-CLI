"""System / subprocess helpers: user/group resolution, signal lookup, subprocess execution.

平台相关的系统工具函数。Windows 上 user/group 名称解析不可用时抛出 AgentError。
"""

from __future__ import annotations

import base64
import importlib
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from ..core import EXIT, AgentError


def resolve_user_id(raw: str | None) -> int | None:
    """将用户名或数字 uid 解析为数字 uid。

    Windows 上不支持 pwd 模块，非数字输入会抛出 AgentError。
    """
    if raw is None or raw == "":
        return None
    if raw.isdigit():
        return int(raw)
    try:
        pwd_module = importlib.import_module("pwd")
        getpwnam = getattr(pwd_module, "getpwnam", None)
        if not callable(getpwnam):
            raise ImportError("pwd.getpwnam is unavailable")
        return int(cast(Any, getpwnam(raw)).pw_uid)
    except ImportError as exc:
        raise AgentError(
            "invalid_input",
            "User name lookup is not supported on this platform; use a numeric uid.",
            details={"owner": raw},
        ) from exc
    except KeyError as exc:
        raise AgentError("invalid_input", "User name was not found.", details={"owner": raw}) from exc


def resolve_group_id(raw: str | None) -> int | None:
    """将组名或数字 gid 解析为数字 gid。

    Windows 上不支持 grp 模块。
    """
    if raw is None or raw == "":
        return None
    if raw.isdigit():
        return int(raw)
    try:
        grp_module = importlib.import_module("grp")
        getgrnam = getattr(grp_module, "getgrnam", None)
        if not callable(getgrnam):
            raise ImportError("grp.getgrnam is unavailable")
        return int(cast(Any, getgrnam(raw)).gr_gid)
    except ImportError as exc:
        raise AgentError(
            "invalid_input",
            "Group name lookup is not supported on this platform; use a numeric gid.",
            details={"group": raw},
        ) from exc
    except KeyError as exc:
        raise AgentError("invalid_input", "Group name was not found.", details={"group": raw}) from exc


def split_owner_spec(spec: str) -> tuple[str | None, str | None]:
    """解析 chown 的所有者规范字符串。

    支持 'owner:group' 和 'owner.group' 两种分隔符（GNU 兼容）。
    """
    if ":" in spec:
        owner, group = spec.split(":", 1)
    elif "." in spec:
        owner, group = spec.split(".", 1)
    else:
        owner, group = spec, None
    if owner == "" and group == "":
        raise AgentError("invalid_input", "Owner specification cannot be empty.")
    return owner or None, group or None


def parse_signal(raw: str) -> int:
    """将信号名或数字解析为信号编号。

    支持 'SIGTERM'、'TERM'、'15' 等形式。
    """
    value = raw.upper()
    if value.isdigit():
        return int(value)
    if not value.startswith("SIG"):
        value = f"SIG{value}"
    import signal

    signum = getattr(signal, value, None)
    if signum is None:
        raise AgentError("invalid_input", "Unknown signal.", details={"signal": raw})
    return int(signum)


def normalize_command_args(raw: list[str]) -> list[str]:
    """规范化子进程命令参数：移除前导 '--' 并确保非空。"""
    command = list(raw)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise AgentError("invalid_input", "A command is required.")
    return command


def run_subprocess_capture(
    command: list[str],
    *,
    timeout: float | None,
    max_output_bytes: int,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[bytes] | None, bool]:
    """在子进程中执行命令并捕获 stdout/stderr。

    Returns:
        (CompletedProcess, timed_out)。
    """
    if not command:
        raise AgentError("invalid_input", "A command is required.")
    if max_output_bytes < 0:
        raise AgentError("invalid_input", "--max-output-bytes must be >= 0.")
    try:
        completed = subprocess.run(command, capture_output=True, timeout=timeout, check=False, env=env)
        return completed, False
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Command executable was not found.", path=command[0]) from exc
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while executing command.", path=command[0]) from exc
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        completed = subprocess.CompletedProcess(command, EXIT["unsafe_operation"], stdout, stderr)
        return completed, True


def subprocess_result(
    command: list[str],
    completed: subprocess.CompletedProcess[bytes],
    *,
    timed_out: bool,
    max_output_bytes: int,
) -> dict[str, Any]:
    """Convert a subprocess result to an agent-safe JSON dict.

    stdout/stderr are base64-encoded so the JSON envelope stays valid
    regardless of whether the subprocess produced binary output, invalid
    UTF-8, or terminal escape sequences.  Callers that expect text output
    should base64-decode and then decode with the appropriate encoding.
    """
    stdout = completed.stdout or b""
    stderr = completed.stderr or b""
    return {
        "command": command,
        "returncode": completed.returncode,
        "timed_out": timed_out,
        "stdout_base64": base64.b64encode(stdout[:max_output_bytes]).decode("ascii"),
        "stderr_base64": base64.b64encode(stderr[:max_output_bytes]).decode("ascii"),
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "stdout_truncated": len(stdout) > max_output_bytes,
        "stderr_truncated": len(stderr) > max_output_bytes,
    }


def system_uptime_seconds() -> float | None:
    """获取系统运行时间（秒）。

    优先读取 /proc/uptime（Linux），回退 macOS sysctl，
    最后尝试 Windows GetTickCount64 API。
    """
    proc_uptime = Path("/proc/uptime")
    if proc_uptime.exists():
        try:
            return float(proc_uptime.read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            pass
    if sys.platform == "darwin":
        try:
            import time

            output = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True)
            # Format: { sec = 1234567890, usec = 123456 } Tue Apr 30 10:00:00 2026
            sec_match = re.search(r"sec\s*=\s*(\d+)", output)
            if sec_match:
                boot_time = int(sec_match.group(1))
                now = time.time()
                return now - boot_time
        except Exception:
            pass
    try:
        import ctypes

        get_tick_count = cast(Any, ctypes).windll.kernel32.GetTickCount64
        get_tick_count.restype = ctypes.c_ulonglong
        return float(get_tick_count()) / 1000.0
    except Exception:
        return None


def stdin_tty_name() -> str | None:
    """获取 stdin 的终端名称，非 TTY 时返回 None。"""
    if not sys.stdin.isatty():
        return None
    ttyname = getattr(os, "ttyname", None)
    if not callable(ttyname):
        return None
    try:
        return str(ttyname(sys.stdin.fileno()))
    except OSError:
        return None


def active_user_entries() -> list[dict[str, Any]]:
    """获取当前活跃用户条目列表（当前进程用户 + 终端信息）。"""
    import getpass

    user = getpass.getuser()
    terminal = stdin_tty_name()
    return [{"user": user, "terminal": terminal, "source": "current_process"}]


def selected_environment(names: list[str] | None) -> dict[str, str]:
    """返回选中的环境变量子集，names=None 时返回全部。"""
    if not names:
        return dict(sorted(os.environ.items()))
    return {name: os.environ[name] for name in names if name in os.environ}
