"""System commands: date, env, whoami, uname, timeout, kill, sleep, ...

系统命令层：实现 P3（系统上下文与有界执行）优先级组的所有命令。

命令类型：
- 系统信息：date/uname/arch/hostname/uptime/nproc/df/du
- 用户/组：whoami/groups/id/logname/users/who/pinky
- 环境：env/printenv
- 终端：tty/stty
- 执行控制：timeout/nice/nohup/stdbuf/chroot（默认 dry-run + --allow-*）
- 信号：kill（默认 dry-run + --allow-signal）
- 安全上下文：chcon/runcon（默认 dry-run + --allow-context）
- 逻辑/数学：sleep/true/false/expr/factor/pathchk

安全注意：
- 危险命令（kill/nice/nohup/chroot/chcon/runcon/stty）默认拒绝真实执行。
- 所有子进程执行命令需 --allow-* 显式授权。
- 修改此文件后必须运行相关安全测试。
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import importlib
import operator
import os
import platform
import re
import shutil
import subprocess
import sys
import time as timemod
from pathlib import Path
from typing import Any, cast

from ...core.command import BaseCommand, CommandResult
from ...utils import (
    EXIT,
    AgentError,
    active_user_entries,
    ensure_parent,
    expression_truthy,
    lines_to_raw,
    normalize_command_args,
    parse_signal,
    path_issues,
    prime_factors,
    require_inside_cwd,
    resolve_path,
    run_subprocess_capture,
    selected_environment,
    stdin_tty_name,
    subprocess_result,
    system_uptime_seconds,
)


class CoreutilsCommand(BaseCommand):
    """Return the list of implemented commands and implementation metadata."""

    name = "coreutils"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        commands = list(getattr(args, "implemented_commands", []) or [])
        if args.raw or args.list:
            return CommandResult(raw_bytes=lines_to_raw(commands, encoding=getattr(args, "encoding", "utf-8")))
        return CommandResult(
            data={
                "implementation": "aicoreutils",
                "compatible_with": "GNU Coreutils inspired subset",
                "gnu_option_compatible": False,
                "json_default": True,
                "commands": commands,
                "count": len(commands),
            }
        )


def command_coreutils(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return CoreutilsCommand()(args)


# ── date ───────────────────────────────────────────────────────────────


class DateCommand(BaseCommand):
    """Return the current or specified date/time."""

    name = "date"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        timestamp = args.timestamp if args.timestamp is not None else timemod.time()
        tz = dt.UTC if args.utc else None
        value = dt.datetime.fromtimestamp(timestamp, tz=tz).astimezone(dt.UTC if args.utc else None)
        if args.format:
            formatted = value.strftime(args.format)
        elif args.iso_8601 == "date":
            formatted = value.date().isoformat()
        else:
            formatted = value.isoformat()
        tzname = value.tzname()
        if tzname is not None:
            try:
                tzname.encode("ascii")
            except UnicodeEncodeError:
                tzname = str(value.utcoffset()) if value.utcoffset() is not None else "unknown"
        if args.raw:
            return CommandResult(raw_bytes=(formatted + "\n").encode(getattr(args, "encoding", "utf-8")))
        return CommandResult(
            data={
                "timestamp": timestamp,
                "iso": value.isoformat(),
                "utc": args.utc,
                "timezone": tzname,
                "formatted": formatted,
            }
        )


def command_date(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return DateCommand()(args)


# ── env / printenv ─────────────────────────────────────────────────────


class EnvCommand(BaseCommand):
    """Query or list environment variables."""

    name = "env"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        env = selected_environment(args.names)
        if args.raw:
            lines = [f"{key}={value}" for key, value in env.items()]
            return CommandResult(raw_bytes=lines_to_raw(lines, encoding=getattr(args, "encoding", "utf-8")))
        missing = [name for name in (args.names or []) if name not in os.environ]
        return CommandResult(data={"count": len(env), "environment": env, "missing": missing})


def command_env(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return EnvCommand()(args)


class PrintenvCommand(BaseCommand):
    """Print environment variable values."""

    name = "printenv"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        env = selected_environment(args.names)
        if args.raw:
            if args.names:
                lines = [env[name] for name in args.names if name in env]
            else:
                lines = [f"{key}={value}" for key, value in env.items()]
            return CommandResult(raw_bytes=lines_to_raw(lines, encoding=getattr(args, "encoding", "utf-8")))
        missing = [name for name in (args.names or []) if name not in os.environ]
        return CommandResult(data={"count": len(env), "values": env, "missing": missing})


def command_printenv(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return PrintenvCommand()(args)


# ── whoami / groups / id ───────────────────────────────────────────────


class WhoamiCommand(BaseCommand):
    """Return the current user."""

    name = "whoami"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        import getpass

        return CommandResult(data={"user": getpass.getuser()})


def command_whoami(args: argparse.Namespace) -> dict[str, Any]:
    return WhoamiCommand()(args)  # type: ignore[return-value]


class GroupsCommand(BaseCommand):
    """Return group memberships for a user."""

    name = "groups"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        import getpass

        user = args.user or getpass.getuser()
        getgroups = getattr(os, "getgroups", None)
        group_ids = [int(gid) for gid in getgroups()] if callable(getgroups) else []
        group_names: list[str] = []
        try:
            grp_module = importlib.import_module("grp")
            getgrgid = getattr(grp_module, "getgrgid", None)
            if not callable(getgrgid):
                raise ImportError("grp.getgrgid is unavailable")
            for gid in group_ids:
                try:
                    group_names.append(str(cast(Any, getgrgid(gid)).gr_name))
                except KeyError:
                    group_names.append(str(gid))
        except ImportError:
            group_names = [str(gid) for gid in group_ids]
        if args.raw:
            return CommandResult(raw_bytes=(" ".join(group_names) + "\n").encode(getattr(args, "encoding", "utf-8")))
        return CommandResult(
            data={
                "user": user,
                "groups": [{"id": gid, "name": name} for gid, name in zip(group_ids, group_names, strict=True)],
            }
        )


def command_groups(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return GroupsCommand()(args)


class IdCommand(BaseCommand):
    """Return user and group identity."""

    name = "id"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        import getpass

        username = getpass.getuser()
        uid_val: int | None = None
        gid_val: int | None = None
        group_ids: list[int] = []
        group_names: list[str] = []
        getuid = getattr(os, "getuid", None)
        getgid = getattr(os, "getgid", None)
        getgroups = getattr(os, "getgroups", None)
        if callable(getuid):
            uid_val = int(getuid())
        if callable(getgid):
            gid_val = int(getgid())
        if callable(getgroups):
            group_ids = [int(gid) for gid in getgroups()]
        try:
            grp_module = importlib.import_module("grp")
            getgrgid = getattr(grp_module, "getgrgid", None)
            if not callable(getgrgid):
                raise ImportError("grp.getgrgid is unavailable")
            for gid in group_ids:
                try:
                    group_names.append(str(cast(Any, getgrgid(gid)).gr_name))
                except KeyError:
                    group_names.append(str(gid))
        except ImportError:
            group_names = [str(gid) for gid in group_ids]
        return CommandResult(
            data={
                "user": username,
                "uid": uid_val,
                "gid": gid_val,
                "groups": group_names,
                "gids": group_ids,
            }
        )


def command_id(args: argparse.Namespace) -> dict[str, Any]:
    return IdCommand()(args)  # type: ignore[return-value]


# ── uname / arch / hostname / hostid / logname ─────────────────────────


class UnameCommand(BaseCommand):
    """Return system information."""

    name = "uname"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        info = platform.uname()
        data = {
            "system": info.system,
            "node": info.node,
            "release": info.release,
            "version": info.version,
            "machine": info.machine,
            "processor": info.processor,
        }
        if args.raw:
            raw = " ".join(str(data[k]) for k in ("system", "node", "release", "version", "machine")) + "\n"
            return CommandResult(raw_bytes=raw.encode(getattr(args, "encoding", "utf-8")))
        return CommandResult(data=data)


def command_uname(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return UnameCommand()(args)


class ArchCommand(BaseCommand):
    """Return machine architecture."""

    name = "arch"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        return CommandResult(data={"architecture": platform.machine()})


def command_arch(args: argparse.Namespace) -> dict[str, Any]:
    return ArchCommand()(args)  # type: ignore[return-value]


class HostnameCommand(BaseCommand):
    """Return the host name."""

    name = "hostname"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        return CommandResult(data={"hostname": platform.node()})


def command_hostname(args: argparse.Namespace) -> dict[str, Any]:
    return HostnameCommand()(args)  # type: ignore[return-value]


class HostidCommand(BaseCommand):
    """Return a deterministic host identifier derived from hostname."""

    name = "hostid"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        host_id = hex(abs(hash(platform.node())) & 0xFFFFFFFF)[2:].zfill(8)
        if args.raw:
            return CommandResult(raw_bytes=(host_id + "\n").encode(getattr(args, "encoding", "utf-8")))
        return CommandResult(data={"hostid": host_id, "hostname": platform.node()})


def command_hostid(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return HostidCommand()(args)


class LognameCommand(BaseCommand):
    """Return the login name of the current user."""

    name = "logname"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        import getpass

        return CommandResult(data={"login": os.environ.get("LOGNAME") or getpass.getuser()})


def command_logname(args: argparse.Namespace) -> dict[str, Any]:
    return LognameCommand()(args)  # type: ignore[return-value]


class PinkyCommand(BaseCommand):
    """Lightweight user lookup — filter and normalize active user entries."""

    name = "pinky"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        active_entries = active_user_entries()
        if args.users:
            entries: list[dict[str, Any]] = []
            for user in args.users:
                matches = [entry for entry in active_entries if entry["user"] == user]
                if matches:
                    entries.extend(matches)
                else:
                    entries.append({"user": user, "terminal": None, "time": "", "source": "requested", "active": False})
        else:
            entries = active_entries

        normalized = [
            {
                "user": entry["user"],
                "terminal": entry.get("terminal"),
                "time": entry.get("time", ""),
                "source": entry.get("source", "unknown"),
                "active": entry.get("active", True),
            }
            for entry in entries
        ]
        if args.raw:
            lines = [
                "\t".join(
                    [
                        str(entry["user"]),
                        str(entry["terminal"] or ""),
                        str(entry["time"] or ""),
                    ]
                ).rstrip()
                for entry in normalized
            ]
            return CommandResult(raw_bytes=lines_to_raw(lines, encoding=getattr(args, "encoding", "utf-8")))
        return CommandResult(data={"count": len(normalized), "long": args.long, "entries": normalized})


def command_pinky(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return PinkyCommand()(args)


# ── uptime / tty / users / who ─────────────────────────────────────────


class UptimeCommand(BaseCommand):
    """Return system uptime in seconds."""

    name = "uptime"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        return CommandResult(data={"uptime_seconds": system_uptime_seconds()})


def command_uptime(args: argparse.Namespace) -> dict[str, Any]:
    return UptimeCommand()(args)  # type: ignore[return-value]


class TtyCommand(BaseCommand):
    """Return the terminal name connected to stdin."""

    name = "tty"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        is_tty = sys.stdin.isatty()
        name = stdin_tty_name()
        if args.raw:
            return CommandResult(raw_bytes=((name or "not a tty") + "\n").encode(getattr(args, "encoding", "utf-8")))
        exit_code = EXIT["predicate_false"] if args.exit_code and not is_tty else 0
        return CommandResult(data={"stdin_is_tty": is_tty, "tty": name}, exit_code=exit_code)


def command_tty(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return TtyCommand()(args)


class UsersCommand(BaseCommand):
    """List currently logged-in users."""

    name = "users"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        entries = active_user_entries()
        users = sorted({entry["user"] for entry in entries})
        if args.raw:
            return CommandResult(raw_bytes=(" ".join(users) + "\n").encode(getattr(args, "encoding", "utf-8")))
        return CommandResult(data={"count": len(users), "users": users, "entries": entries})


def command_users(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return UsersCommand()(args)


class WhoCommand(BaseCommand):
    """Show who is logged on."""

    name = "who"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        user_list = active_user_entries()
        entries = [{"user": e["user"], "terminal": e["terminal"], "time": e.get("time", "")} for e in user_list]
        return CommandResult(data={"count": len(entries), "entries": entries})


def command_who(args: argparse.Namespace) -> dict[str, Any]:
    return WhoCommand()(args)  # type: ignore[return-value]


# ── nproc ──────────────────────────────────────────────────────────────


class NprocCommand(BaseCommand):
    """Return the number of available processors."""

    name = "nproc"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        try:
            sched_getaffinity = getattr(os, "sched_getaffinity", None)
            if not callable(sched_getaffinity):
                raise AttributeError("os.sched_getaffinity is unavailable")
            count = len(sched_getaffinity(0))
        except (AttributeError, NotImplementedError):
            count = os.cpu_count() or 1
        return CommandResult(data={"count": count})


def command_nproc(args: argparse.Namespace) -> dict[str, Any]:
    return NprocCommand()(args)  # type: ignore[return-value]


# ── timeout ────────────────────────────────────────────────────────────
# Stays function-based: subprocess wrapper with timeout and output capture.
# The subprocess lifecycle (launch, wait, timeout, capture) is inherently procedural.


def command_timeout(args: argparse.Namespace) -> dict[str, Any]:
    if args.seconds <= 0:
        raise AgentError("invalid_input", "timeout seconds must be > 0.")
    # Re-extract --dry-run and --max-output-bytes that may appear
    # after the command name in the REMAINDER (e.g. timeout 1 true --dry-run).
    # argparse.REMAINDER captures everything after the last recognized flag;
    # this gives a second chance to extract execution-control flags.
    remainder: list[str] = list(args.command_args)
    clean_remainder: list[str] = []
    i = 0
    while i < len(remainder):
        token = remainder[i]
        if token == "--dry-run":
            args.dry_run = True
            i += 1
        elif token == "--max-output-bytes" and i + 1 < len(remainder):
            try:
                args.max_output_bytes = int(remainder[i + 1])
            except ValueError as exc:
                raise AgentError("invalid_input", "--max-output-bytes must be an integer.") from exc
            i += 2
        elif token == "--":
            clean_remainder.extend(remainder[i + 1 :])
            break
        else:
            clean_remainder.append(token)
            i += 1
    command = normalize_command_args(clean_remainder)
    if args.dry_run:
        return {"command": command, "timeout_seconds": args.seconds, "dry_run": True}
    completed, timed_out = run_subprocess_capture(
        command,
        timeout=args.seconds,
        max_output_bytes=args.max_output_bytes,
    )
    assert completed is not None
    result = subprocess_result(command, completed, timed_out=timed_out, max_output_bytes=args.max_output_bytes)
    result["timeout_seconds"] = args.seconds
    result["_exit_code"] = EXIT["unsafe_operation"] if timed_out else completed.returncode
    return result


# ── nice ───────────────────────────────────────────────────────────────
# Stays function-based: subprocess wrapper with niceness adjustment.
# The preexec_fn + capture_output pattern is inherently procedural.


def command_nice(args: argparse.Namespace) -> dict[str, Any]:
    command = normalize_command_args(args.command_args)
    if args.dry_run:
        return {"command": command, "adjustment": args.adjustment, "dry_run": True}
    env = os.environ.copy()

    def preexec() -> None:
        if hasattr(os, "nice"):
            os.nice(args.adjustment)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=args.timeout,
            check=False,
            env=env,
            preexec_fn=preexec if hasattr(os, "nice") and os.name != "nt" else None,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(command, EXIT["unsafe_operation"], exc.stdout or b"", exc.stderr or b"")
        timed_out = True
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Command executable was not found.", path=command[0]) from exc
    result = subprocess_result(command, completed, timed_out=timed_out, max_output_bytes=args.max_output_bytes)
    result["adjustment"] = args.adjustment
    result["nice_supported"] = hasattr(os, "nice") and os.name != "nt"
    result["_exit_code"] = EXIT["unsafe_operation"] if timed_out else completed.returncode
    return result


def _validate_stdbuf_mode(raw: str | None, *, name: str) -> str | None:
    if raw is None:
        return None
    if raw in {"0", "L"} or re.fullmatch(r"\d+(?:[KkMmGg])?", raw):
        return raw
    raise AgentError(
        "invalid_input",
        f"Invalid stdbuf {name} buffering mode.",
        details={"value": raw},
        suggestion="Use 0, L, or a byte size optionally followed by K, M, or G.",
    )


# Stays function-based: subprocess wrapper that sets environment-level buffering
# hints. The env manipulation + subprocess pattern is inherently procedural.
def command_stdbuf(args: argparse.Namespace) -> dict[str, Any]:
    buffering = {
        "stdin": _validate_stdbuf_mode(args.input, name="stdin"),
        "stdout": _validate_stdbuf_mode(args.output, name="stdout"),
        "stderr": _validate_stdbuf_mode(args.error, name="stderr"),
    }
    command = normalize_command_args(args.command_args)
    if args.dry_run:
        return {
            "command": command,
            "buffering": buffering,
            "timeout_seconds": args.timeout,
            "dry_run": True,
            "emulation": "environment-hints",
        }

    env = os.environ.copy()
    for stream, mode in buffering.items():
        if mode is not None:
            env[f"AICOREUTILS_STDBUF_{stream.upper()}"] = mode
    if buffering["stdout"] == "0" or buffering["stderr"] == "0":
        env["PYTHONUNBUFFERED"] = "1"

    completed, timed_out = run_subprocess_capture(
        command,
        timeout=args.timeout,
        max_output_bytes=args.max_output_bytes,
        env=env,
    )
    assert completed is not None
    result = subprocess_result(command, completed, timed_out=timed_out, max_output_bytes=args.max_output_bytes)
    result["buffering"] = buffering
    result["timeout_seconds"] = args.timeout
    result["emulation"] = "environment-hints"
    result["_exit_code"] = EXIT["unsafe_operation"] if timed_out else completed.returncode
    return result


# Stays function-based: termios manipulation with platform-specific fd handling
# and --allow-change safety gate. The file-descriptor lifecycle is inherently procedural.
def command_stty(args: argparse.Namespace) -> dict[str, Any] | bytes:
    settings = list(args.settings)
    if settings and settings[0] == "--":
        settings = settings[1:]
    target = args.device or "stdin"
    is_tty = bool(args.device) or sys.stdin.isatty()
    supported = os.name != "nt"

    result: dict[str, Any] = {
        "target": target,
        "stdin_is_tty": sys.stdin.isatty(),
        "supported": supported,
        "settings": settings,
        "dry_run": args.dry_run,
        "changed": False,
    }

    if args.raw:
        status = " ".join(settings) if settings else ("tty" if is_tty else "not a tty")
        return (status + "\n").encode(getattr(args, "encoding", "utf-8"))

    if not settings:
        return result
    if args.dry_run:
        result["planned"] = True
        return result
    if not args.allow_change:
        raise AgentError(
            "unsafe_operation",
            "Changing terminal settings requires --allow-change.",
            suggestion="Run with --dry-run first, then pass --allow-change if intentional.",
        )
    if not supported:
        raise AgentError("invalid_input", "stty changes are not supported on this platform.")

    try:
        termios = importlib.import_module("termios")
        tty = importlib.import_module("tty")
        tcgetattr = getattr(termios, "tcgetattr", None)
        tcsetattr = getattr(termios, "tcsetattr", None)
        tcsadrain = getattr(termios, "TCSADRAIN", None)
        echo = getattr(termios, "ECHO", None)
        icanon = getattr(termios, "ICANON", None)
        isig = getattr(termios, "ISIG", None)
        setraw = getattr(tty, "setraw", None)
        if not callable(tcgetattr) or not callable(tcsetattr) or not callable(setraw):
            raise ImportError("termios control functions are unavailable")
        if not all(isinstance(value, int) for value in (tcsadrain, echo, icanon, isig)):
            raise ImportError("termios constants are unavailable")
        tcsadrain_value = cast(int, tcsadrain)
        echo_value = cast(int, echo)
        icanon_value = cast(int, icanon)
        isig_value = cast(int, isig)
    except ImportError as exc:
        raise AgentError("invalid_input", "termios is not available on this platform.") from exc

    opened_fd: int | None = None
    try:
        if args.device:
            device_path = resolve_path(args.device, strict=True)
            opened_fd = os.open(device_path, os.O_RDWR)
            fd = opened_fd
        else:
            if not sys.stdin.isatty():
                raise AgentError("invalid_input", "stdin is not a TTY; use --file to target a terminal device.")
            fd = sys.stdin.fileno()

        attrs = tcgetattr(fd)
        for setting in settings:
            if setting == "raw":
                setraw(fd, when=tcsadrain_value)
                attrs = tcgetattr(fd)
            elif setting == "sane":
                attrs[3] |= echo_value | icanon_value | isig_value
            elif setting == "echo":
                attrs[3] |= echo_value
            elif setting == "-echo":
                attrs[3] &= ~echo_value
            else:
                raise AgentError(
                    "invalid_input",
                    "Unsupported stty setting.",
                    details={"setting": setting},
                    suggestion="Supported settings are: raw, sane, echo, -echo.",
                )
        tcsetattr(fd, tcsadrain_value, attrs)
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=args.device) from exc
    finally:
        if opened_fd is not None:
            os.close(opened_fd)

    result["changed"] = True
    return result


# ── nohup ──────────────────────────────────────────────────────────────
# Stays function-based: starts a background subprocess with redirected output.
# Requires --allow-background gate; the Popen lifecycle is inherently procedural.


def command_nohup(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    command = normalize_command_args(args.command_args)
    output_path = resolve_path(args.output)
    require_inside_cwd(output_path, cwd, allow_outside_cwd=False)
    ensure_parent(output_path, create=args.parents, dry_run=args.dry_run)
    if output_path.exists() and not args.append and not args.allow_overwrite:
        raise AgentError(
            "conflict",
            "nohup output file exists.",
            path=str(output_path),
            suggestion="Pass --append or --allow-overwrite if writing to this file is intentional.",
        )
    operation = {
        "operation": "nohup",
        "command": command,
        "output": str(output_path),
        "append": args.append,
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        return {"operation": operation}
    if not args.allow_background:
        raise AgentError(
            "unsafe_operation",
            "Starting a background process requires --allow-background.",
            suggestion="Run with --dry-run first, then pass --allow-background if intentional.",
        )
    try:
        mode = "ab" if args.append else "wb"
        handle = output_path.open(mode)
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        handle.close()
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Command executable was not found.", path=command[0]) from exc
    operation["pid"] = process.pid
    operation["started"] = True
    return {"operation": operation}


def _consume_remainder_execution_options(args: argparse.Namespace, *, allow_flag: str) -> list[str]:
    """Extract execution control flags from the command remainder.

    chroot and runcon accept a REMAINDER argument that mixes execution
    options (--timeout, --max-output-bytes, --dry-run, --allow-*) with
    the actual command to execute.  argparse.REMAINDER captures them
    all together, so this function re-parses the known flags out of the
    remainder, mutating ``args`` in place and returning the remaining
    tokens (the subprocess command + its args).

    Stops at the first unrecognized token (assumed to be the command name)
    or at ``--`` (explicit end-of-options marker).
    """
    command_args = list(args.command_args)
    index = 0
    while index < len(command_args):
        token = command_args[index]
        if token == "--":
            break
        if token == "--dry-run":
            args.dry_run = True
            index += 1
            continue
        if token == allow_flag:
            if allow_flag == "--allow-chroot":
                args.allow_chroot = True
            else:
                args.allow_context = True
            index += 1
            continue
        if token == "--timeout":
            if index + 1 >= len(command_args):
                raise AgentError("usage", "--timeout requires a value.")
            try:
                args.timeout = float(command_args[index + 1])
            except ValueError as exc:
                raise AgentError("invalid_input", "--timeout must be a number.") from exc
            index += 2
            continue
        if token == "--max-output-bytes":
            if index + 1 >= len(command_args):
                raise AgentError("usage", "--max-output-bytes requires a value.")
            try:
                args.max_output_bytes = int(command_args[index + 1])
            except ValueError as exc:
                raise AgentError("invalid_input", "--max-output-bytes must be an integer.") from exc
            index += 2
            continue
        break
    return command_args[index:]


# Stays function-based: chroot jail with --allow-chroot gate. The chroot() +
# preexec_fn pattern is platform-specific and inherently procedural.
def command_chroot(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_path(args.root, strict=True)
    if not root.is_dir():
        raise AgentError("invalid_input", "chroot root must be a directory.", path=str(root))
    command = normalize_command_args(_consume_remainder_execution_options(args, allow_flag="--allow-chroot"))
    if args.dry_run:
        return {"root": str(root), "command": command, "timeout_seconds": args.timeout, "dry_run": True}
    if not args.allow_chroot:
        raise AgentError(
            "unsafe_operation",
            "chroot changes process root and requires --allow-chroot.",
            path=str(root),
            suggestion="Run with --dry-run first, then pass --allow-chroot if intentional.",
        )
    chroot = getattr(os, "chroot", None)
    if os.name == "nt" or not callable(chroot):
        raise AgentError("invalid_input", "chroot is not supported on this platform.", path=str(root))

    def enter_chroot() -> None:
        chroot(root)
        os.chdir("/")

    if args.max_output_bytes < 0:
        raise AgentError("invalid_input", "--max-output-bytes must be >= 0.")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=args.timeout,
            check=False,
            preexec_fn=enter_chroot,
        )
        timed_out = False
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Command executable was not found inside the chroot.", path=command[0]) from exc
    except PermissionError as exc:
        raise AgentError(
            "permission_denied", "Permission denied while executing chroot command.", path=command[0]
        ) from exc
    except subprocess.TimeoutExpired as exc:
        completed = subprocess.CompletedProcess(command, EXIT["unsafe_operation"], exc.stdout or b"", exc.stderr or b"")
        timed_out = True

    result = subprocess_result(command, completed, timed_out=timed_out, max_output_bytes=args.max_output_bytes)
    result["root"] = str(root)
    result["timeout_seconds"] = args.timeout
    result["_exit_code"] = EXIT["unsafe_operation"] if timed_out else completed.returncode
    return result


def _context_targets(paths: list[str], *, recursive: bool) -> list[Path]:
    targets: list[Path] = []
    for raw in paths:
        path = resolve_path(raw, strict=True)
        targets.append(path)
        if recursive and path.is_dir() and not path.is_symlink():
            targets.extend(sorted(path.rglob("*")))
    return targets


# Stays function-based: SELinux security context via xattr. Platform-specific
# (requires os.setxattr + "security.selinux"); --allow-context gate.
def command_chcon(args: argparse.Namespace) -> dict[str, Any] | bytes:
    targets = _context_targets(args.paths, recursive=args.recursive)
    operations = [
        {
            "operation": "chcon",
            "path": str(path),
            "context": args.context,
            "recursive": args.recursive,
            "no_follow": args.no_follow,
            "dry_run": args.dry_run,
        }
        for path in targets
    ]
    if args.raw:
        return lines_to_raw(
            [f"{args.context}\t{operation['path']}" for operation in operations],
            encoding=getattr(args, "encoding", "utf-8"),
        )
    if args.dry_run:
        return {"count": len(operations), "operations": operations}
    if not args.allow_context:
        raise AgentError(
            "unsafe_operation",
            "Changing security context requires --allow-context.",
            suggestion="Run with --dry-run first, then pass --allow-context if intentional.",
        )
    if not hasattr(os, "setxattr"):
        raise AgentError("invalid_input", "SELinux context changes are not supported on this platform.")

    encoded = args.context.encode(getattr(args, "encoding", "utf-8"))
    for path in targets:
        try:
            try:
                os.setxattr(path, "security.selinux", encoded, follow_symlinks=not args.no_follow)
            except TypeError:
                os.setxattr(path, "security.selinux", encoded)
        except PermissionError as exc:
            raise AgentError(
                "permission_denied", "Permission denied while changing security context.", path=str(path)
            ) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


# Stays function-based: SELinux runcon subprocess wrapper. Platform-specific
# (requires runcon executable); --allow-context gate.
def command_runcon(args: argparse.Namespace) -> dict[str, Any]:
    command = normalize_command_args(_consume_remainder_execution_options(args, allow_flag="--allow-context"))
    if args.dry_run:
        return {"context": args.context, "command": command, "timeout_seconds": args.timeout, "dry_run": True}
    if not args.allow_context:
        raise AgentError(
            "unsafe_operation",
            "Running a command under another security context requires --allow-context.",
            suggestion="Run with --dry-run first, then pass --allow-context if intentional.",
        )
    runner = shutil.which("runcon")
    if runner is None:
        raise AgentError("invalid_input", "SELinux runcon executable is not available on this platform.")
    wrapped = [runner, args.context, *command]
    completed, timed_out = run_subprocess_capture(
        wrapped,
        timeout=args.timeout,
        max_output_bytes=args.max_output_bytes,
    )
    assert completed is not None
    result = subprocess_result(wrapped, completed, timed_out=timed_out, max_output_bytes=args.max_output_bytes)
    result["context"] = args.context
    result["timeout_seconds"] = args.timeout
    result["_exit_code"] = EXIT["unsafe_operation"] if timed_out else completed.returncode
    return result


# ── kill ───────────────────────────────────────────────────────────────


class KillCommand(BaseCommand):
    """Send a signal to processes by PID — gated behind --allow-signal."""

    name = "kill"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        signum = parse_signal(args.signal)
        operations: list[dict[str, Any]] = []
        for raw in args.pids:
            try:
                pid = int(raw)
            except ValueError as exc:
                raise AgentError("invalid_input", "PIDs must be integers.", details={"pid": raw}) from exc
            operations.append({"operation": "kill", "pid": pid, "signal": signum, "dry_run": args.dry_run})
            if not args.dry_run:
                if not args.allow_signal:
                    raise AgentError(
                        "unsafe_operation",
                        "Sending a signal requires --allow-signal.",
                        details={"pid": pid, "signal": signum},
                    )
                try:
                    os.kill(pid, signum)
                except ProcessLookupError as exc:
                    raise AgentError("not_found", "Process does not exist.", details={"pid": pid}) from exc
                except PermissionError as exc:
                    raise AgentError(
                        "permission_denied", "Permission denied while signaling process.", details={"pid": pid}
                    ) from exc
                except OSError as exc:
                    raise AgentError("io_error", str(exc), details={"pid": pid}) from exc
        return CommandResult(data={"count": len(operations), "operations": operations})


def command_kill(args: argparse.Namespace) -> dict[str, Any]:
    return KillCommand()(args)  # type: ignore[return-value]


# ── sleep ──────────────────────────────────────────────────────────────


class SleepCommand(BaseCommand):
    """Sleep for a bounded duration with dry-run support."""

    name = "sleep"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        if args.seconds < 0:
            raise AgentError("invalid_input", "seconds must be >= 0.")
        if args.seconds > args.max_seconds:
            raise AgentError(
                "unsafe_operation",
                "Sleep duration exceeds --max-seconds.",
                details={"seconds": args.seconds, "max_seconds": args.max_seconds},
            )
        if not args.dry_run:
            timemod.sleep(args.seconds)
        return CommandResult(data={"seconds": args.seconds, "slept": not args.dry_run, "dry_run": args.dry_run})


def command_sleep(args: argparse.Namespace) -> dict[str, Any]:
    return SleepCommand()(args)  # type: ignore[return-value]


# ── true / false ───────────────────────────────────────────────────────


class TrueCommand(BaseCommand):
    """Return true (always succeeds)."""

    name = "true"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        return CommandResult(data={"value": True})


def command_true(args: argparse.Namespace) -> dict[str, Any]:
    return TrueCommand()(args)  # type: ignore[return-value]


class FalseCommand(BaseCommand):
    """Return false (always fails with predicate_false exit code)."""

    name = "false"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        return CommandResult(data={"value": False}, exit_code=EXIT["predicate_false"])


def command_false(args: argparse.Namespace) -> dict[str, Any]:
    return FalseCommand()(args)  # type: ignore[return-value]


# ── pathchk ────────────────────────────────────────────────────────────


class PathchkCommand(BaseCommand):
    """Validate path components against portability constraints."""

    name = "pathchk"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        if args.max_path_length < 1:
            raise AgentError("invalid_input", "--max-path-length must be >= 1.")
        if args.max_component_length < 1:
            raise AgentError("invalid_input", "--max-component-length must be >= 1.")
        entries = []
        raw_lines = []
        all_valid = True
        for raw in args.paths:
            issues = path_issues(
                raw,
                max_path_length=args.max_path_length,
                max_component_length=args.max_component_length,
                portable=args.portable,
            )
            valid = not issues
            all_valid = all_valid and valid
            entries.append({"path": raw, "valid": valid, "issues": issues})
            raw_lines.append(f"{'valid' if valid else 'invalid'}\t{','.join(issues)}\t{raw}")
        if args.raw:
            return CommandResult(raw_bytes=lines_to_raw(raw_lines, encoding=getattr(args, "encoding", "utf-8")))
        exit_code = EXIT["predicate_false"] if args.exit_code and not all_valid else 0
        return CommandResult(data={"count": len(entries), "valid": all_valid, "entries": entries}, exit_code=exit_code)


def command_pathchk(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return PathchkCommand()(args)


# ── factor ─────────────────────────────────────────────────────────────


class FactorCommand(BaseCommand):
    """Compute prime factors of integers."""

    name = "factor"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        raw_values = args.numbers or sys.stdin.read().split()
        entries = []
        raw_lines = []
        for raw in raw_values:
            try:
                value = int(raw, 0)
            except ValueError as exc:
                raise AgentError("invalid_input", "factor inputs must be integers.", details={"value": raw}) from exc
            if abs(value) > args.max_value:
                raise AgentError(
                    "unsafe_operation",
                    "factor input exceeds --max-value.",
                    details={"value": value, "max_value": args.max_value},
                )
            factors = prime_factors(value) if abs(value) > 1 else []
            entries.append({"input": raw, "value": value, "factors": factors})
            suffix = " " + " ".join(str(f) for f in factors) if factors else ""
            raw_lines.append(f"{value}:{suffix}")
        if args.raw:
            return CommandResult(raw_bytes=lines_to_raw(raw_lines, encoding=getattr(args, "encoding", "utf-8")))
        return CommandResult(data={"count": len(entries), "entries": entries})


def command_factor(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return FactorCommand()(args)


# ── expr ───────────────────────────────────────────────────────────────


class ExprCommand(BaseCommand):
    """Evaluate arithmetic and string expressions."""

    name = "expr"

    def execute(self, args: argparse.Namespace) -> CommandResult:
        expression = " ".join("==" if token == "=" else token for token in args.tokens)
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise AgentError(
                "invalid_input", "Expression syntax is invalid.", details={"expression": expression}
            ) from exc
        try:
            value = safe_eval_expr_node(tree)
        except TypeError as exc:
            raise AgentError(
                "invalid_input",
                "Expression operands are incompatible for the requested operation.",
                details={"expression": expression},
            ) from exc
        truthy = expression_truthy(value)
        if args.raw:
            rendered = ("1" if value else "0") if isinstance(value, bool) else str(value)
            return CommandResult(raw_bytes=(rendered + "\n").encode(getattr(args, "encoding", "utf-8")))
        exit_code = EXIT["predicate_false"] if args.exit_code and not truthy else 0
        return CommandResult(
            data={"expression": expression, "value": value, "truthy": truthy, "type": type(value).__name__},
            exit_code=exit_code,
        )


def command_expr(args: argparse.Namespace) -> dict[str, Any] | bytes:
    return ExprCommand()(args)


def safe_eval_expr_node(tree: ast.AST) -> Any:
    if isinstance(tree, ast.Expression):
        return safe_eval_expr_node(tree.body)
    if isinstance(tree, ast.Constant):
        return tree.value
    if isinstance(tree, ast.BinOp):
        left = safe_eval_expr_node(tree.left)
        right = safe_eval_expr_node(tree.right)
        if isinstance(tree.op, ast.Add):
            return operator.add(left, right)
        if isinstance(tree.op, ast.Sub):
            return operator.sub(left, right)
        if isinstance(tree.op, ast.Mult):
            return operator.mul(left, right)
        if isinstance(tree.op, ast.Div):
            try:
                return operator.truediv(left, right)
            except ZeroDivisionError as exc:
                raise AgentError("invalid_input", "Division by zero.") from exc
        if isinstance(tree.op, ast.Mod):
            try:
                return operator.mod(left, right)
            except ZeroDivisionError as exc:
                raise AgentError("invalid_input", "Modulo by zero.") from exc
        if isinstance(tree.op, ast.Pow):
            return operator.pow(left, right)
    if isinstance(tree, ast.Compare):
        left = safe_eval_expr_node(tree.left)
        for op, comp in zip(tree.ops, tree.comparators, strict=True):
            right = safe_eval_expr_node(comp)
            if isinstance(op, ast.Eq):
                result = left == right
            elif isinstance(op, ast.NotEq):
                result = left != right
            elif isinstance(op, ast.Lt):
                result = left < right
            elif isinstance(op, ast.LtE):
                result = left <= right
            elif isinstance(op, ast.Gt):
                result = left > right
            elif isinstance(op, ast.GtE):
                result = left >= right
            else:
                raise AgentError("invalid_input", "Expression uses an unsupported comparison operator.")
            if not result:
                return False
            left = right
        return True
    if isinstance(tree, ast.BoolOp):
        if isinstance(tree.op, ast.And):
            return all(safe_eval_expr_node(v) for v in tree.values)
        if isinstance(tree.op, ast.Or):
            return any(safe_eval_expr_node(v) for v in tree.values)
    if isinstance(tree, ast.UnaryOp):
        operand = safe_eval_expr_node(tree.operand)
        if isinstance(tree.op, ast.UAdd):
            return +operand
        if isinstance(tree.op, ast.USub):
            return -operand
    raise AgentError("invalid_input", "Expression uses an unsupported operation.")
