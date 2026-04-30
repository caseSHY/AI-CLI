"""System-information and process commands: date, env, id, uname, timeout, etc."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import operator
import os
import platform
import subprocess
import sys
import time as timemod
from pathlib import Path
from typing import Any

from .protocol import (
    AgentError,
    EXIT,
    active_user_entries,
    ensure_parent,
    evaluate_test_predicates,
    expression_truthy,
    lines_to_raw,
    normalize_command_args,
    parse_signal,
    path_issues,
    prime_factors,
    resolve_path,
    run_subprocess_capture,
    selected_environment,
    stdin_tty_name,
    subprocess_result,
    system_uptime_seconds,
    utc_iso,
)


# ── date ───────────────────────────────────────────────────────────────

def command_date(args: argparse.Namespace) -> dict[str, Any] | bytes:
    timestamp = args.timestamp if args.timestamp is not None else timemod.time()
    tz = dt.UTC if args.utc else None
    value = dt.datetime.fromtimestamp(timestamp, tz=tz).astimezone(dt.UTC if args.utc else None)
    if args.format:
        formatted = value.strftime(args.format)
    elif args.iso_8601 == "date":
        formatted = value.date().isoformat()
    else:
        formatted = value.isoformat()
    result = {
        "timestamp": timestamp,
        "iso": value.isoformat(),
        "utc": args.utc,
        "timezone": value.tzname(),
        "formatted": formatted,
    }
    if args.raw:
        return (formatted + "\n").encode("utf-8")
    return result


# ── env / printenv ─────────────────────────────────────────────────────

def command_env(args: argparse.Namespace) -> dict[str, Any] | bytes:
    env = selected_environment(args.names)
    if args.raw:
        lines = [f"{key}={value}" for key, value in env.items()]
        return lines_to_raw(lines, encoding="utf-8")
    missing = [name for name in (args.names or []) if name not in os.environ]
    return {"count": len(env), "environment": env, "missing": missing}


def command_printenv(args: argparse.Namespace) -> dict[str, Any] | bytes:
    env = selected_environment(args.names)
    if args.raw:
        if args.names:
            lines = [env[name] for name in args.names if name in env]
        else:
            lines = [f"{key}={value}" for key, value in env.items()]
        return lines_to_raw(lines, encoding="utf-8")
    missing = [name for name in (args.names or []) if name not in os.environ]
    return {"count": len(env), "values": env, "missing": missing}


# ── whoami / groups / id ───────────────────────────────────────────────

def command_whoami(args: argparse.Namespace) -> dict[str, Any]:
    import getpass
    return {"user": getpass.getuser()}


def command_groups(args: argparse.Namespace) -> dict[str, Any] | bytes:
    import getpass
    user = args.user or getpass.getuser()
    getgroups = getattr(os, "getgroups", None)
    group_ids = getgroups() if callable(getgroups) else []
    group_names = []
    try:
        import grp  # type: ignore[import-not-found]
        for gid in group_ids:
            try:
                group_names.append(grp.getgrgid(gid).gr_name)
            except KeyError:
                group_names.append(str(gid))
    except ImportError:
        group_names = [str(gid) for gid in group_ids]
    if args.raw:
        return (" ".join(group_names) + "\n").encode("utf-8")
    return {"user": user, "groups": [{"id": gid, "name": name} for gid, name in zip(group_ids, group_names)]}


def command_id(args: argparse.Namespace) -> dict[str, Any]:
    import getpass
    username = getpass.getuser()
    uid_val = None
    gid_val = None
    group_ids = []
    group_names = []
    try:
        uid_val = os.getuid()
    except Exception:
        pass
    try:
        gid_val = os.getgid()
    except Exception:
        pass
    try:
        group_ids = os.getgroups()
    except Exception:
        pass
    try:
        import grp  # type: ignore[import-not-found]
        for gid in group_ids:
            try:
                group_names.append(grp.getgrgid(gid).gr_name)
            except KeyError:
                group_names.append(str(gid))
    except ImportError:
        group_names = [str(gid) for gid in group_ids]
    return {
        "user": username,
        "uid": uid_val,
        "gid": gid_val,
        "groups": group_names,
        "gids": group_ids,
    }


# ── uname / arch / hostname / hostid / logname ─────────────────────────

def command_uname(args: argparse.Namespace) -> dict[str, Any] | bytes:
    info = platform.uname()
    result = {
        "system": info.system,
        "node": info.node,
        "release": info.release,
        "version": info.version,
        "machine": info.machine,
        "processor": info.processor,
    }
    if args.raw:
        return (" ".join(str(result[key]) for key in ("system", "node", "release", "version", "machine")) + "\n").encode(
            "utf-8"
        )
    return result


def command_arch(args: argparse.Namespace) -> dict[str, Any]:
    return {"architecture": platform.machine()}


def command_hostname(args: argparse.Namespace) -> dict[str, Any]:
    return {"hostname": platform.node()}


def command_hostid(args: argparse.Namespace) -> dict[str, Any] | bytes:
    host_id = hex(abs(hash(platform.node())) & 0xFFFFFFFF)[2:].zfill(8)
    if args.raw:
        return (host_id + "\n").encode("utf-8")
    return {"hostid": host_id, "hostname": platform.node()}


def command_logname(args: argparse.Namespace) -> dict[str, Any]:
    import getpass
    return {"login": os.environ.get("LOGNAME") or getpass.getuser()}


# ── uptime / tty / users / who ─────────────────────────────────────────

def command_uptime(args: argparse.Namespace) -> dict[str, Any]:
    return {"uptime_seconds": system_uptime_seconds()}


def command_tty(args: argparse.Namespace) -> dict[str, Any] | bytes:
    is_tty = sys.stdin.isatty()
    name = stdin_tty_name()
    if args.raw:
        return ((name or "not a tty") + "\n").encode("utf-8")
    result: dict[str, Any] = {"stdin_is_tty": is_tty, "tty": name}
    if args.exit_code and not is_tty:
        result["_exit_code"] = EXIT["predicate_false"]
    return result


def command_users(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = active_user_entries()
    users = sorted({entry["user"] for entry in entries})
    if args.raw:
        return (" ".join(users) + "\n").encode("utf-8")
    return {"count": len(users), "users": users, "entries": entries}


def command_who(args: argparse.Namespace) -> dict[str, Any]:
    user_list = active_user_entries()
    entries = [
        {
            "user": entry["user"],
            "terminal": entry["terminal"],
            "time": entry.get("time", ""),
        }
        for entry in user_list
    ]
    return {"count": len(entries), "entries": entries}


# ── nproc ──────────────────────────────────────────────────────────────

def command_nproc(args: argparse.Namespace) -> dict[str, Any]:
    try:
        count = len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError):
        count = os.cpu_count() or 1
    return {"count": count}


# ── timeout ────────────────────────────────────────────────────────────

def command_timeout(args: argparse.Namespace) -> dict[str, Any]:
    if args.seconds <= 0:
        raise AgentError("invalid_input", "timeout seconds must be > 0.")
    command = normalize_command_args(args.command_args)
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


# ── nohup ──────────────────────────────────────────────────────────────

def command_nohup(args: argparse.Namespace) -> dict[str, Any]:
    command = normalize_command_args(args.command_args)
    output_path = resolve_path(args.output)
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


# ── kill ───────────────────────────────────────────────────────────────

def command_kill(args: argparse.Namespace) -> dict[str, Any]:
    signum = parse_signal(args.signal)
    operations = []
    for raw in args.pids:
        try:
            pid = int(raw)
        except ValueError as exc:
            raise AgentError("invalid_input", "PIDs must be integers.", details={"pid": raw}) from exc
        operation = {"operation": "kill", "pid": pid, "signal": signum, "dry_run": args.dry_run}
        operations.append(operation)
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
                raise AgentError("permission_denied", "Permission denied while signaling process.", details={"pid": pid}) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), details={"pid": pid}) from exc
    return {"count": len(operations), "operations": operations}


# ── sleep ──────────────────────────────────────────────────────────────

def command_sleep(args: argparse.Namespace) -> dict[str, Any]:
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
    return {"seconds": args.seconds, "slept": not args.dry_run, "dry_run": args.dry_run}


# ── true / false ───────────────────────────────────────────────────────

def command_true(args: argparse.Namespace) -> dict[str, Any]:
    return {"value": True}


def command_false(args: argparse.Namespace) -> dict[str, Any]:
    return {"value": False, "_exit_code": EXIT["predicate_false"]}


# ── pathchk ────────────────────────────────────────────────────────────

def command_pathchk(args: argparse.Namespace) -> dict[str, Any] | bytes:
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
        return lines_to_raw(raw_lines, encoding="utf-8")
    result: dict[str, Any] = {"count": len(entries), "valid": all_valid, "entries": entries}
    if args.exit_code and not all_valid:
        result["_exit_code"] = EXIT["predicate_false"]
    return result


# ── factor ─────────────────────────────────────────────────────────────

def command_factor(args: argparse.Namespace) -> dict[str, Any] | bytes:
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
        suffix = " " + " ".join(str(factor) for factor in factors) if factors else ""
        raw_lines.append(f"{value}:{suffix}")
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


# ── expr ───────────────────────────────────────────────────────────────

def command_expr(args: argparse.Namespace) -> dict[str, Any] | bytes:
    expression = " ".join("==" if token == "=" else token for token in args.tokens)
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise AgentError("invalid_input", "Expression syntax is invalid.", details={"expression": expression}) from exc
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
        if isinstance(value, bool):
            rendered = "1" if value else "0"
        else:
            rendered = str(value)
        return (rendered + "\n").encode("utf-8")
    result = {"expression": expression, "value": value, "truthy": truthy, "type": type(value).__name__}
    if args.exit_code and not truthy:
        result["_exit_code"] = EXIT["predicate_false"]
    return result


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
            except ZeroDivisionError:
                raise AgentError("invalid_input", "Division by zero.")
        if isinstance(tree.op, ast.Mod):
            try:
                return operator.mod(left, right)
            except ZeroDivisionError:
                raise AgentError("invalid_input", "Modulo by zero.")
        if isinstance(tree.op, ast.Pow):
            return operator.pow(left, right)
    if isinstance(tree, ast.Compare):
        left = safe_eval_expr_node(tree.left)
        for op, comp in zip(tree.ops, tree.comparators):
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
