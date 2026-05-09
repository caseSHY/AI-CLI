"""File-system commands: ls, stat, cat, head, tail, wc, cp, mv, rm, mkdir, chmod, ...

文件系统命令层：实现 P0（读取观察）和 P1（安全修改）优先级组的所有命令。

每个命令函数遵循统一契约：
    def command_xxx(args: argparse.Namespace) -> dict[str, Any] | bytes:
        # 1. 路径解析和校验（resolve_path + require_inside_cwd）
        # 2. 安全检查（dangerous_delete_target + refuse_overwrite）
        # 3. dry_run 提前返回（if args.dry_run: return {...}）
        # 4. 实际执行并收集结果
        # 5. 返回 JSON 兼容字典或 bytes（--raw 模式）

安全注意：
- 所有写入/删除/截断命令必须通过 sandbox 校验。
- 路径遍历（../）和符号链接逃逸在 resolve_path 层拦截。
- 修改此文件后必须运行全部 37 个沙箱测试。
"""

from __future__ import annotations

import argparse
import base64
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ...core.constants import DD_DEFAULT_BLOCK_SIZE
from ...core.stream import StreamWriter, is_stream_mode
from ...utils import (
    EXIT,
    AgentError,
    dangerous_delete_target,
    destination_inside_directory,
    digest_bytes,
    digest_file,
    directory_size,
    disk_usage_entry,
    ensure_exists,
    ensure_parent,
    iter_directory,
    lines_to_raw,
    parse_octal_mode,
    read_bytes,
    read_input_bytes,
    read_stdin_bytes,
    read_text_lines,
    refuse_overwrite,
    remove_one,
    require_inside_cwd,
    resolve_group_id,
    resolve_path,
    resolve_user_id,
    split_owner_spec,
    stat_entry,
    wc_for_bytes,
)

# ── pwd / realpath / readlink ──────────────────────────────────────────


def command_pwd(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    return {"path": str(cwd)}


def command_realpath(args: argparse.Namespace) -> dict[str, Any]:
    paths = [
        {
            "input": raw,
            "path": str(resolve_path(raw, strict=args.strict)),
            "exists": Path(raw).expanduser().exists(),
        }
        for raw in args.paths
    ]
    return {"paths": paths}


def command_readlink(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = []
    raw_lines = []
    for raw in args.paths:
        input_path = Path(raw).expanduser()
        if args.canonicalize:
            resolved = str(resolve_path(input_path, strict=args.strict))
            entry = {
                "input": raw,
                "path": resolved,
                "mode": "canonicalize",
                "exists": input_path.exists(),
            }
            target = resolved
        else:
            path = resolve_path(input_path, strict=True)
            if not path.is_symlink():
                raise AgentError(
                    "invalid_input",
                    "Path is not a symbolic link. Use --canonicalize to resolve regular paths.",
                    path=str(path),
                )
            try:
                target = os.readlink(path)
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
            entry = {
                "input": raw,
                "path": str(path),
                "mode": "readlink",
                "target": target,
            }
        entries.append(entry)
        raw_lines.append(target)
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


# ── basename / dirname ─────────────────────────────────────────────────


def command_basename(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = []
    raw_lines = []
    for raw in args.paths:
        name = Path(raw).name
        if args.suffix and name.endswith(args.suffix):
            name = name[: -len(args.suffix)]
        entries.append({"input": raw, "basename": name})
        raw_lines.append(name)
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


def command_dirname(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = []
    raw_lines = []
    for raw in args.paths:
        parent = str(Path(raw).parent)
        if parent == "":
            parent = "."
        entries.append({"input": raw, "dirname": parent})
        raw_lines.append(parent)
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


# ── ls / dir / vdir ────────────────────────────────────────────────────


def command_ls(args: argparse.Namespace) -> dict[str, Any] | bytes:
    root = resolve_path(args.path, strict=True)
    if args.max_depth < 0:
        raise AgentError("invalid_input", "--max-depth must be >= 0.")
    if args.limit < 1:
        raise AgentError("invalid_input", "--limit must be >= 1.")

    # --stream mode: emit NDJSON lines directly to stdout to avoid
    # accumulating all entries in memory (important for large directories).
    if is_stream_mode(args):
        writer = StreamWriter(sys.stdout, command="ls", max_items=args.limit)
        entries, truncated = iter_directory(
            root,
            include_hidden=args.include_hidden,
            recursive=args.recursive,
            max_depth=args.max_depth,
            follow_symlinks=args.follow_symlinks,
            limit=args.limit,
        )
        for entry in entries:
            writer.write_item(entry)
        writer.write_summary({"path": str(root), "count": len(entries), "truncated": truncated})
        return b""  # signal to dispatch: output already written

    entries, truncated = iter_directory(
        root,
        include_hidden=args.include_hidden,
        recursive=args.recursive,
        max_depth=args.max_depth,
        follow_symlinks=args.follow_symlinks,
        limit=args.limit,
    )
    return {
        "path": str(root),
        "recursive": args.recursive,
        "max_depth": args.max_depth,
        "count": len(entries),
        "truncated": truncated,
        "entries": entries,
    }


def command_dir(args: argparse.Namespace) -> dict[str, Any] | bytes:
    result = command_ls(args)
    if isinstance(result, bytes):
        return result  # --stream mode: pass through
    result["alias"] = "dir"
    return result


def command_vdir(args: argparse.Namespace) -> dict[str, Any] | bytes:
    result = command_ls(args)
    if isinstance(result, bytes):
        return result  # --stream mode: pass through
    result["alias"] = "vdir"
    result["verbose"] = True
    return result


# ── stat ───────────────────────────────────────────────────────────────


def command_stat(args: argparse.Namespace) -> dict[str, Any]:
    entries = [stat_entry(resolve_path(raw, strict=True)) for raw in args.paths]
    return {"count": len(entries), "entries": entries}


# ── cat / head / tail ──────────────────────────────────────────────────


def command_cat(args: argparse.Namespace) -> dict[str, Any] | bytes:
    path = resolve_path(args.path, strict=True)
    data, truncated, size = read_bytes(path, max_bytes=args.max_bytes, offset=args.offset)
    if args.raw:
        return data
    text = data.decode(args.encoding, errors="replace")
    return {
        "path": str(path),
        "encoding": args.encoding,
        "offset": args.offset,
        "size_bytes": size,
        "returned_bytes": len(data),
        "truncated": truncated,
        "content": text,
    }


def command_head(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.lines < 0:
        raise AgentError("invalid_input", "--lines must be >= 0.")
    path = resolve_path(args.path, strict=True)
    if args.raw:
        ensure_exists(path)
        if path.is_dir():
            raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
        return b"".join(path.read_bytes().splitlines(keepends=True)[: args.lines])
    lines = read_text_lines(path, encoding=args.encoding)
    selected = lines[: args.lines]
    return {
        "path": str(path),
        "encoding": args.encoding,
        "requested_lines": args.lines,
        "returned_lines": len(selected),
        "total_lines": len(lines),
        "truncated": len(selected) < len(lines),
        "lines": selected,
    }


def command_tail(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.lines < 0:
        raise AgentError("invalid_input", "--lines must be >= 0.")
    path = resolve_path(args.path, strict=True)
    if args.raw:
        ensure_exists(path)
        if path.is_dir():
            raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
        lines_with_endings = path.read_bytes().splitlines(keepends=True)
        return b"".join(lines_with_endings[-args.lines :] if args.lines else [])
    lines = read_text_lines(path, encoding=args.encoding)
    selected = lines[-args.lines :] if args.lines else []
    return {
        "path": str(path),
        "encoding": args.encoding,
        "requested_lines": args.lines,
        "returned_lines": len(selected),
        "total_lines": len(lines),
        "truncated": len(selected) < len(lines),
        "lines": selected,
    }


# ── wc ─────────────────────────────────────────────────────────────────


def command_wc(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = []
    totals = {"bytes": 0, "chars": 0, "lines": 0, "words": 0}
    paths: list[str] = list(args.paths) if args.paths else []
    if args.files0_from:
        with open(args.files0_from, "rb") as fh:
            paths += [p for p in fh.read().decode("utf-8", errors="replace").split("\0") if p]
    if not paths:
        paths = ["-"]  # default to stdin
    for raw in paths:
        if raw == "-":
            data = read_stdin_bytes()
            path_label = "-"
        else:
            path = resolve_path(raw, strict=True)
            ensure_exists(path)
            if path.is_dir():
                raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
            data = path.read_bytes()
            path_label = str(path)
        counts = wc_for_bytes(data, encoding=args.encoding)
        for key in totals:
            totals[key] += counts[key]
        entries.append({"path": path_label, **counts})
    if args.raw:
        lines = [
            f"{entry['lines']} {entry['words']} {entry['bytes']}{'' if entry['path'] == '-' else ' ' + Path(entry['path']).name}"
            for entry in entries
        ]
        if len(entries) > 1:
            lines.append(f"{totals['lines']} {totals['words']} {totals['bytes']} total")
        return lines_to_raw(lines, encoding=args.encoding)
    return {"count": len(entries), "entries": entries, "totals": totals}


# ── hash commands ──────────────────────────────────────────────────────


def command_hash(args: argparse.Namespace) -> dict[str, Any]:
    # --check mode: verify checksums from checksum files
    if getattr(args, "check", False):
        entries = []
        ok_count = 0
        fail_count = 0
        for raw in args.paths or ["-"]:
            if raw == "-":
                content = read_stdin_bytes().decode("utf-8", errors="replace")
                source = "-"
            else:
                path = resolve_path(raw, strict=True)
                content = path.read_text(encoding="utf-8", errors="replace")
                source = str(path)
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                if len(parts) < 2:
                    entries.append({"line": line, "error": "Invalid checksum line format", "status": "FAILED"})
                    fail_count += 1
                    continue
                expected, target_path = parts[0], parts[1]
                target_path = target_path.lstrip("*")  # GNU uses * for binary, ' ' for text
                try:
                    actual = digest_file(Path(target_path), args.algorithm)
                except (FileNotFoundError, OSError) as exc:
                    missing_entry: dict[str, Any] = {
                        "path": target_path,
                        "expected": expected,
                        "actual": None,
                        "error": str(exc),
                        "status": "MISSING",
                    }
                    entries.append(missing_entry)
                    fail_count += 1
                    continue
                ok = actual == expected
                if ok:
                    ok_count += 1
                else:
                    fail_count += 1
                entries.append(
                    {
                        "path": target_path,
                        "expected": expected,
                        "actual": actual,
                        "status": "OK" if ok else "FAILED",
                    }
                )
        check_source: str = source if len(args.paths or []) == 1 else "multiple"
        result: dict[str, Any] = {
            "source": check_source,
            "algorithm": args.algorithm,
            "count": len(entries),
            "ok": ok_count,
            "failed": fail_count,
            "entries": entries,
        }
        if fail_count > 0:
            result["_exit_code"] = 1
        return result

    # Normal hashing mode
    entries = []
    for raw in args.paths if args.paths else ["-"]:
        if raw == "-":
            data = read_stdin_bytes()
            entry_data: dict[str, Any] = {
                "path": "-",
                "algorithm": args.algorithm,
                "digest": digest_bytes(data, args.algorithm),
                "size_bytes": len(data),
            }
            entries.append(entry_data)
            continue
        path = resolve_path(raw, strict=True)
        entry_data = {
            "path": str(path),
            "algorithm": args.algorithm,
            "digest": digest_file(path, args.algorithm),
            "size_bytes": path.stat().st_size,
        }
        entries.append(entry_data)
    return {"count": len(entries), "entries": entries}


def command_cksum(args: argparse.Namespace) -> dict[str, Any] | bytes:
    import zlib

    entries = []
    raw_lines = []
    for raw in args.paths or ["-"]:
        label, data = read_input_bytes(raw)
        checksum = zlib.crc32(data) & 0xFFFFFFFF
        entry = {
            "path": label,
            "algorithm": "crc32",
            "checksum": checksum,
            "size_bytes": len(data),
        }
        entries.append(entry)
        raw_lines.append(f"{checksum} {len(data)} {label}")
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


def command_sum(args: argparse.Namespace) -> dict[str, Any] | bytes:
    from ...utils import simple_sum16

    if args.block_size < 1:
        raise AgentError("invalid_input", "--block-size must be >= 1.")
    entries = []
    raw_lines = []
    for raw in args.paths or ["-"]:
        label, data = read_input_bytes(raw)
        checksum = simple_sum16(data)
        blocks = (len(data) + args.block_size - 1) // args.block_size
        entry = {
            "path": label,
            "algorithm": "byte-sum-16",
            "checksum": checksum,
            "blocks": blocks,
            "block_size": args.block_size,
            "size_bytes": len(data),
        }
        entries.append(entry)
        raw_lines.append(f"{checksum} {blocks} {label}")
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


# ── mkdir / touch ──────────────────────────────────────────────────────


def command_mkdir(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        exists = path.exists()
        if exists and not (args.exist_ok or args.parents):
            raise AgentError(
                "conflict",
                "Directory already exists.",
                path=str(path),
                suggestion="Pass --parents or --exist-ok if an existing directory is acceptable.",
            )
        if exists and not path.is_dir():
            raise AgentError("conflict", "Path exists and is not a directory.", path=str(path))
        if not exists:
            ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        operations.append({"operation": "mkdir", "path": str(path), "created": not exists, "dry_run": args.dry_run})
        if not args.dry_run and not exists:
            path.mkdir(parents=args.parents, exist_ok=args.exist_ok)
    return {"count": len(operations), "operations": operations}


def command_touch(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        existed = path.exists()
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        operations.append({"operation": "touch", "path": str(path), "created": not existed, "dry_run": args.dry_run})
        if not args.dry_run:
            path.touch(exist_ok=True)
    return {"count": len(operations), "operations": operations}


# ── cp / mv ────────────────────────────────────────────────────────────


def command_cp(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    source = resolve_path(args.source, strict=True)
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
    require_inside_cwd(destination, cwd, allow_outside_cwd=False)
    ensure_parent(destination, create=args.parents, dry_run=args.dry_run)
    if source.is_dir():
        if not args.recursive:
            raise AgentError(
                "invalid_input",
                "Source is a directory; recursive copy requires --recursive.",
                path=str(source),
            )
        if destination.exists() and not args.allow_overwrite:
            raise AgentError(
                "conflict",
                "Destination exists.",
                path=str(destination),
                suggestion="Pass --allow-overwrite if merging/replacing is intentional.",
            )
    else:
        refuse_overwrite(destination, args.allow_overwrite)

    operation = {
        "operation": "cp",
        "source": str(source),
        "requested_destination": str(requested_destination),
        "destination": str(destination),
        "recursive": args.recursive,
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=args.allow_overwrite)
        else:
            shutil.copy2(source, destination)
    return {"operations": [operation]}


def command_mv(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    source = resolve_path(args.source, strict=True)
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
    require_inside_cwd(source, cwd, allow_outside_cwd=False)
    require_inside_cwd(destination, cwd, allow_outside_cwd=False)
    ensure_parent(destination, create=args.parents, dry_run=args.dry_run)
    refuse_overwrite(destination, args.allow_overwrite)
    operation = {
        "operation": "mv",
        "source": str(source),
        "requested_destination": str(requested_destination),
        "destination": str(destination),
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        shutil.move(str(source), str(destination))
    return {"operations": [operation]}


# ── ln / link ──────────────────────────────────────────────────────────


def command_ln(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    source = Path(args.source).expanduser()
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
    require_inside_cwd(destination, cwd, allow_outside_cwd=False)
    ensure_parent(destination, create=args.parents, dry_run=args.dry_run)
    if destination.exists() or destination.is_symlink():
        if not args.allow_overwrite:
            raise AgentError(
                "conflict",
                "Destination exists.",
                path=str(destination),
                suggestion="Pass --allow-overwrite if replacing the destination is intentional.",
            )
        if not args.dry_run:
            if destination.is_dir() and not destination.is_symlink():
                raise AgentError("invalid_input", "Destination is a directory.", path=str(destination))
            destination.unlink()
    if not args.symbolic:
        source = resolve_path(source, strict=True)
        if source.is_dir():
            raise AgentError("invalid_input", "Hard-linking directories is not supported.", path=str(source))
    operation = {
        "operation": "ln",
        "source": str(source),
        "requested_destination": str(requested_destination),
        "destination": str(destination),
        "symbolic": args.symbolic,
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        try:
            if args.symbolic:
                os.symlink(str(source), destination)
            else:
                os.link(source, destination)
        except PermissionError as exc:
            raise AgentError(
                "permission_denied", "Permission denied while creating link.", path=str(destination)
            ) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"operations": [operation]}


def command_link(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    source = resolve_path(args.source, strict=True)
    if source.is_dir():
        raise AgentError("invalid_input", "Hard-linking directories is not supported.", path=str(source))
    destination = resolve_path(args.destination)
    require_inside_cwd(destination, cwd, allow_outside_cwd=False)
    ensure_parent(destination, create=args.parents, dry_run=args.dry_run)
    if destination.exists() or destination.is_symlink():
        if not args.allow_overwrite:
            raise AgentError(
                "conflict",
                "Destination exists.",
                path=str(destination),
                suggestion="Pass --allow-overwrite if replacing the destination is intentional.",
            )
        if destination.is_dir() and not destination.is_symlink():
            raise AgentError("invalid_input", "Destination is a directory.", path=str(destination))
        if not args.dry_run:
            destination.unlink()
    operation = {
        "operation": "link",
        "source": str(source),
        "destination": str(destination),
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        try:
            os.link(source, destination)
        except PermissionError as exc:
            raise AgentError(
                "permission_denied", "Permission denied while creating hard link.", path=str(destination)
            ) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"operations": [operation]}


# ── chmod / chown / chgrp ──────────────────────────────────────────────


def command_chmod(args: argparse.Namespace) -> dict[str, Any]:
    import stat as statmod

    if args.reference:
        ref_path = resolve_path(args.reference, strict=True)
        ref_mode = statmod.S_IMODE(ref_path.lstat().st_mode)
        new_mode = ref_mode
    elif args.mode:
        new_mode = parse_octal_mode(args.mode)
    else:
        raise AgentError("invalid_input", "chmod requires either a mode argument or --reference.")
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        old_mode = statmod.S_IMODE(path.lstat().st_mode)
        operations.append(
            {
                "operation": "chmod",
                "path": str(path),
                "old_mode_octal": oct(old_mode),
                "new_mode_octal": oct(new_mode),
                "dry_run": args.dry_run,
            }
        )
        if not args.dry_run:
            try:
                os.chmod(path, new_mode, follow_symlinks=not args.no_follow)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while changing mode.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_chown(args: argparse.Namespace) -> dict[str, Any]:
    if args.reference:
        ref_path = resolve_path(args.reference, strict=True)
        ref_st = ref_path.lstat()
        owner_raw: str = str(getattr(ref_st, "st_uid", ""))
        group_raw: str = str(getattr(ref_st, "st_gid", ""))
    elif args.owner:
        owner_raw, group_raw = split_owner_spec(args.owner)  # type: ignore[assignment]
    else:
        raise AgentError("invalid_input", "chown requires either an owner spec or --reference.")
    uid = resolve_user_id(owner_raw)
    gid = resolve_group_id(group_raw)
    if uid is None and gid is None:
        raise AgentError("invalid_input", "chown requires an owner, group, or both.")
    cwd = Path.cwd().resolve()
    operations = []
    chown = getattr(os, "chown", None)
    supported = callable(chown)
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        st = path.lstat()
        operation = {
            "operation": "chown",
            "path": str(path),
            "owner": owner_raw,
            "group": group_raw,
            "uid": uid,
            "gid": gid,
            "old_uid": getattr(st, "st_uid", None),
            "old_gid": getattr(st, "st_gid", None),
            "supported": supported,
            "dry_run": args.dry_run,
        }
        operations.append(operation)
        if not args.dry_run:
            if not supported:
                raise AgentError("invalid_input", "chown is not supported on this platform.", path=str(path))
            assert callable(chown)
            try:
                chown(path, -1 if uid is None else uid, -1 if gid is None else gid, follow_symlinks=not args.no_follow)
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while changing owner.", path=str(path)
                ) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_chgrp(args: argparse.Namespace) -> dict[str, Any]:
    if args.reference:
        ref_path = resolve_path(args.reference, strict=True)
        ref_st = ref_path.lstat()
        gid = getattr(ref_st, "st_gid", None)
    elif args.group:
        gid = resolve_group_id(args.group)
    else:
        raise AgentError("invalid_input", "chgrp requires either a group argument or --reference.")
    if gid is None:
        raise AgentError("invalid_input", "A group is required.")
    cwd = Path.cwd().resolve()
    operations = []
    chown = getattr(os, "chown", None)
    supported = callable(chown)
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        st = path.lstat()
        operation = {
            "operation": "chgrp",
            "path": str(path),
            "group": args.group,
            "gid": gid,
            "old_gid": getattr(st, "st_gid", None),
            "supported": supported,
            "dry_run": args.dry_run,
        }
        operations.append(operation)
        if not args.dry_run:
            if not supported:
                raise AgentError("invalid_input", "chgrp is not supported on this platform.", path=str(path))
            assert callable(chown)
            try:
                chown(path, -1, gid, follow_symlinks=not args.no_follow)
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while changing group.", path=str(path)
                ) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


# ── truncate / mktemp / mkfifo / mknod ─────────────────────────────────


def command_truncate(args: argparse.Namespace) -> dict[str, Any]:
    if args.size < 0:
        raise AgentError("invalid_input", "--size must be >= 0.")
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        existed = path.exists()
        if not existed and args.no_create:
            raise AgentError("not_found", "Path does not exist and --no-create was passed.", path=str(path))
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        old_size = path.stat().st_size if existed else None
        operations.append(
            {
                "operation": "truncate",
                "path": str(path),
                "old_size_bytes": old_size,
                "new_size_bytes": args.size,
                "created": not existed,
                "dry_run": args.dry_run,
            }
        )
        if not args.dry_run:
            try:
                with path.open("ab") as handle:
                    handle.truncate(args.size)
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while truncating file.", path=str(path)
                ) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_mktemp(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    tmpdir = resolve_path(args.tmpdir or ".", strict=True)
    require_inside_cwd(tmpdir, cwd, allow_outside_cwd=False)
    if not tmpdir.is_dir():
        raise AgentError("invalid_input", "--tmpdir must be a directory.", path=str(tmpdir))
    if args.dry_run:
        candidate = tmpdir / f"{args.prefix}{uuid.uuid4().hex}{args.suffix}"
        return {
            "operation": "mktemp",
            "path": str(candidate),
            "directory": args.directory,
            "created": False,
            "dry_run": True,
        }
    try:
        if args.directory:
            path = tempfile.mkdtemp(prefix=args.prefix, suffix=args.suffix, dir=tmpdir)
        else:
            fd, path = tempfile.mkstemp(prefix=args.prefix, suffix=args.suffix, dir=tmpdir)
            os.close(fd)
    except PermissionError as exc:
        raise AgentError(
            "permission_denied", "Permission denied while creating temporary path.", path=str(tmpdir)
        ) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(tmpdir)) from exc
    return {
        "operation": "mktemp",
        "path": str(Path(path).resolve()),
        "directory": args.directory,
        "created": True,
        "dry_run": False,
    }


def command_mkfifo(args: argparse.Namespace) -> dict[str, Any]:
    mode = parse_octal_mode(args.mode)
    cwd = Path.cwd().resolve()
    operations = []
    mkfifo = getattr(os, "mkfifo", None)
    supported = callable(mkfifo)
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        if path.exists() or path.is_symlink():
            raise AgentError("conflict", "Destination exists.", path=str(path))
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        operation = {
            "operation": "mkfifo",
            "path": str(path),
            "mode_octal": oct(mode),
            "supported": supported,
            "dry_run": args.dry_run,
        }
        operations.append(operation)
        if not args.dry_run:
            if not supported:
                raise AgentError(
                    "invalid_input",
                    "mkfifo is not supported on this platform.",
                    path=str(path),
                    suggestion="Use --dry-run for planning or run on a platform with os.mkfifo support.",
                )
            assert callable(mkfifo)
            try:
                mkfifo(path, mode)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while creating FIFO.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_mknod(args: argparse.Namespace) -> dict[str, Any]:
    mode = parse_octal_mode(args.mode)
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        if path.exists() or path.is_symlink():
            raise AgentError("conflict", "Destination exists.", path=str(path))
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        mkfifo = getattr(os, "mkfifo", None)
        supported = args.node_type == "regular" or callable(mkfifo)
        operation = {
            "operation": "mknod",
            "path": str(path),
            "type": args.node_type,
            "mode_octal": oct(mode),
            "supported": supported,
            "dry_run": args.dry_run,
        }
        operations.append(operation)
        if not args.dry_run:
            try:
                if args.node_type == "regular":
                    with path.open("xb"):
                        pass
                    os.chmod(path, mode)
                elif args.node_type == "fifo" and callable(mkfifo):
                    mkfifo(path, mode)
                else:
                    raise AgentError(
                        "invalid_input", "Requested node type is not supported on this platform.", path=str(path)
                    )
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while creating node.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


# ── install ────────────────────────────────────────────────────────────


def command_install(args: argparse.Namespace) -> dict[str, Any]:
    mode = parse_octal_mode(args.mode)
    operations = []
    if args.directory:
        if not args.paths:
            raise AgentError("invalid_input", "install --directory requires at least one directory path.")
        for raw in args.paths:
            path = resolve_path(raw)
            existed = path.exists()
            if existed and not path.is_dir():
                raise AgentError("conflict", "Path exists and is not a directory.", path=str(path))
            ensure_parent(path, create=True, dry_run=args.dry_run)
            operation = {
                "operation": args.command,
                "directory": True,
                "path": str(path),
                "mode_octal": oct(mode),
                "created": not existed,
                "dry_run": args.dry_run,
            }
            operations.append(operation)
            if not args.dry_run:
                path.mkdir(parents=True, exist_ok=True)
                os.chmod(path, mode)
        return {"count": len(operations), "operations": operations}

    if len(args.paths) != 2:
        raise AgentError("invalid_input", "install requires SOURCE and DESTINATION unless --directory is used.")
    source = resolve_path(args.paths[0], strict=True)
    if source.is_dir():
        raise AgentError("invalid_input", "install source must be a file.", path=str(source))
    cwd = Path.cwd().resolve()
    requested_destination = resolve_path(args.paths[1])
    destination = destination_inside_directory(source, requested_destination)
    require_inside_cwd(destination, cwd, allow_outside_cwd=False)
    ensure_parent(destination, create=args.parents, dry_run=args.dry_run)
    if destination.exists() and not args.allow_overwrite:
        raise AgentError(
            "conflict",
            "Destination exists.",
            path=str(destination),
            suggestion="Pass --allow-overwrite if replacing the destination is intentional.",
        )
    operation = {
        "operation": args.command,
        "directory": False,
        "source": str(source),
        "requested_destination": str(requested_destination),
        "destination": str(destination),
        "mode_octal": oct(mode),
        "dry_run": args.dry_run,
    }
    operations.append(operation)
    if not args.dry_run:
        try:
            shutil.copy2(source, destination)
            os.chmod(destination, mode)
        except PermissionError as exc:
            raise AgentError(
                "permission_denied", "Permission denied while installing file.", path=str(destination)
            ) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"count": len(operations), "operations": operations}


# ── tee / rmdir / unlink ───────────────────────────────────────────────


def command_tee(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.max_preview_bytes < 0:
        raise AgentError("invalid_input", "--max-preview-bytes must be >= 0.")
    cwd = Path.cwd().resolve()
    data = read_stdin_bytes()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        operations.append(
            {
                "operation": "tee",
                "path": str(path),
                "append": args.append,
                "bytes": len(data),
                "dry_run": args.dry_run,
            }
        )
        if not args.dry_run:
            try:
                with path.open("ab" if args.append else "wb") as handle:
                    handle.write(data)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while writing file.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    if args.raw:
        return data
    preview = data[: args.max_preview_bytes]
    return {
        "input_bytes": len(data),
        "returned_preview_bytes": len(preview),
        "truncated": len(data) > len(preview),
        "content_base64": base64.b64encode(preview).decode("ascii"),
        "operations": operations,
    }


def command_rmdir(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        if not path.is_dir() or path.is_symlink():
            raise AgentError("invalid_input", "Path is not a directory.", path=str(path))
        operations.append({"operation": "rmdir", "path": str(path), "dry_run": args.dry_run})
        if not args.dry_run:
            try:
                path.rmdir()
            except OSError as exc:
                raise AgentError(
                    "conflict",
                    "Directory could not be removed. It may be non-empty or in use.",
                    path=str(path),
                    details={"message": str(exc)},
                ) from exc
    return {"count": len(operations), "operations": operations}


def command_unlink(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        if not path.exists() and not path.is_symlink():
            if args.force:
                operations.append(
                    {"operation": "unlink", "path": str(path), "status": "missing_ignored", "dry_run": args.dry_run}
                )
                continue
            raise AgentError("not_found", "Path does not exist.", path=str(path))
        if path.is_dir() and not path.is_symlink():
            raise AgentError("invalid_input", "unlink refuses to remove directories.", path=str(path))
        status = "would_unlink" if args.dry_run else "unlinked"
        operations.append({"operation": "unlink", "path": str(path), "status": status, "dry_run": args.dry_run})
        if not args.dry_run:
            try:
                path.unlink()
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while unlinking path.", path=str(path)
                ) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


# ── rm / shred ─────────────────────────────────────────────────────────


def command_rm(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        if not path.exists() and not path.is_symlink():
            if args.force:
                operations.append(
                    {"operation": "rm", "path": str(path), "status": "missing_ignored", "dry_run": args.dry_run}
                )
                continue
            raise AgentError("not_found", "Path does not exist.", path=str(path))
        reason = dangerous_delete_target(path, cwd)
        if reason:
            raise AgentError("unsafe_operation", reason, path=str(path))
        require_inside_cwd(path, cwd, allow_outside_cwd=args.allow_outside_cwd)
        if args.dry_run:
            status = "would_remove_directory" if path.is_dir() and not path.is_symlink() else "would_remove_file"
        else:
            status = remove_one(path, recursive=args.recursive, force=args.force)
        operations.append({"operation": "rm", "path": str(path), "status": status, "dry_run": args.dry_run})
    return {"count": len(operations), "operations": operations}


def command_shred(args: argparse.Namespace) -> dict[str, Any]:
    if args.passes < 1:
        raise AgentError("invalid_input", "--passes must be >= 1.")
    cwd = Path.cwd().resolve()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
        require_inside_cwd(path, cwd, allow_outside_cwd=False)
        if path.is_dir():
            raise AgentError("invalid_input", "shred refuses directories.", path=str(path))
        size = path.stat().st_size
        operation = {
            "operation": "shred",
            "path": str(path),
            "size_bytes": size,
            "passes": args.passes,
            "remove": args.remove,
            "pattern": "zero",
            "dry_run": args.dry_run,
        }
        operations.append(operation)
        if not args.dry_run:
            if not args.allow_destructive:
                raise AgentError(
                    "unsafe_operation",
                    "shred is destructive and requires --allow-destructive for real execution.",
                    path=str(path),
                    suggestion="Run with --dry-run first, then pass --allow-destructive if intentional.",
                )
            try:
                chunk = b"\0" * min(size, DD_DEFAULT_BLOCK_SIZE)
                with path.open("r+b") as handle:
                    for _ in range(args.passes):
                        handle.seek(0)
                        remaining = size
                        while remaining > 0:
                            to_write = chunk[: min(len(chunk), remaining)]
                            handle.write(to_write)
                            remaining -= len(to_write)
                        handle.flush()
                        os.fsync(handle.fileno())
                if args.remove:
                    path.unlink()
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while shredding file.", path=str(path)
                ) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


# ── test / [ ────────────────────────────────────────────────────────────


def command_test(args: argparse.Namespace) -> dict[str, Any]:
    from ...utils import evaluate_test_predicates

    path = Path(args.path).expanduser()
    predicates = []
    if args.exists:
        predicates.append("exists")
    if args.file:
        predicates.append("file")
    if args.directory:
        predicates.append("directory")
    if args.symlink:
        predicates.append("symlink")
    if args.readable:
        predicates.append("readable")
    if args.writable:
        predicates.append("writable")
    if args.executable:
        predicates.append("executable")
    if args.empty:
        predicates.append("empty")
    if args.non_empty:
        predicates.append("non_empty")
    if not predicates:
        predicates.append("exists")
    checks = evaluate_test_predicates(path, predicates)
    matches = all(check["matches"] for check in checks)
    result: dict[str, Any] = {
        "path": str(path),
        "matches": matches,
        "checks": checks,
    }
    if args.exit_code and not matches:
        result["_exit_code"] = EXIT["predicate_false"]
    return result


def command_bracket(args: argparse.Namespace) -> dict[str, Any]:
    tokens = list(args.tokens)
    for flag_name, flag in (
        ("bracket_exists", "-e"),
        ("bracket_file", "-f"),
        ("bracket_directory", "-d"),
        ("bracket_symlink", "-L"),
        ("bracket_readable", "-r"),
        ("bracket_writable", "-w"),
        ("bracket_executable", "-x"),
        ("bracket_non_empty", "-s"),
    ):
        if getattr(args, flag_name, False):
            tokens.insert(0, flag)
            break
    if tokens and tokens[-1] == "]":
        tokens = tokens[:-1]
    if len(tokens) == 1:
        synthetic = argparse.Namespace(
            path=tokens[0],
            exists=True,
            file=False,
            directory=False,
            symlink=False,
            readable=False,
            writable=False,
            executable=False,
            empty=False,
            non_empty=False,
            exit_code=args.exit_code,
        )
        return command_test(synthetic)
    if len(tokens) == 2 and tokens[0] in ("-e", "-f", "-d", "-L", "-r", "-w", "-x", "-s"):
        flags = {
            "exists": tokens[0] == "-e",
            "file": tokens[0] == "-f",
            "directory": tokens[0] == "-d",
            "symlink": tokens[0] == "-L",
            "readable": tokens[0] == "-r",
            "writable": tokens[0] == "-w",
            "executable": tokens[0] == "-x",
            "non_empty": tokens[0] == "-s",
        }
        synthetic = argparse.Namespace(
            path=tokens[1],
            exists=flags.get("exists", False),
            file=flags.get("file", False),
            directory=flags.get("directory", False),
            symlink=flags.get("symlink", False),
            readable=flags.get("readable", False),
            writable=flags.get("writable", False),
            executable=flags.get("executable", False),
            empty=False,
            non_empty=flags.get("non_empty", False),
            exit_code=args.exit_code,
        )
        return command_test(synthetic)
    if len(tokens) == 3 and tokens[1] in ("=", "==", "!="):
        matches = tokens[0] == tokens[2] if tokens[1] in ("=", "==") else tokens[0] != tokens[2]
        result: dict[str, Any] = {"expression": tokens, "matches": matches}
        if args.exit_code and not matches:
            result["_exit_code"] = EXIT["predicate_false"]
        return result
    raise AgentError(
        "invalid_input",
        "Only simple [ PATH ], [ -f PATH ], and string equality forms are supported.",
        details={"tokens": args.tokens},
    )


# ── df / du / dd / sync ────────────────────────────────────────────────


def command_df(args: argparse.Namespace) -> dict[str, Any]:
    paths = args.paths or ["."]
    entries = [disk_usage_entry(resolve_path(raw, strict=True)) for raw in paths]
    return {"count": len(entries), "entries": entries}


def command_du(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_depth < 0:
        raise AgentError("invalid_input", "--max-depth must be >= 0.")
    entries = []
    total = 0
    for raw in args.paths or ["."]:
        path = resolve_path(raw, strict=True)
        size, count, truncated = directory_size(path, max_depth=args.max_depth, follow_symlinks=args.follow_symlinks)
        total += size
        entries.append(
            {
                "path": str(path),
                "size_bytes": size,
                "entries_counted": count,
                "max_depth": args.max_depth,
                "truncated_by_depth": truncated,
            }
        )
    return {"count": len(entries), "total_bytes": total, "entries": entries}


def command_dd(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.bs < 1:
        raise AgentError("invalid_input", "--bs must be >= 1.")
    if args.count is not None and args.count < 0:
        raise AgentError("invalid_input", "--count must be >= 0.")
    if args.skip < 0 or args.seek < 0:
        raise AgentError("invalid_input", "--skip and --seek must be >= 0.")
    label, data = read_input_bytes(args.input)
    start = args.skip * args.bs
    selected = data[start:]
    if args.count is not None:
        selected = selected[: args.count * args.bs]

    conv_options = set(args.conv.split(",")) if args.conv else set()
    # conv=sync: pad each input block to bs with NULs
    if "sync" in conv_options and args.count is not None:
        expected = args.count * args.bs
        if len(selected) < expected:
            selected += b"\x00" * (expected - len(selected))

    output_path = None if args.output == "-" else resolve_path(args.output)
    if output_path is not None:
        cwd = Path.cwd().resolve()
        require_inside_cwd(output_path, cwd, allow_outside_cwd=False)
        ensure_parent(output_path, create=args.parents, dry_run=args.dry_run)
        # conv=notrunc: do not truncate existing output file on seek>0
        notrunc = "notrunc" in conv_options
        if output_path.exists() and not args.allow_overwrite and args.seek == 0 and not notrunc:
            raise AgentError(
                "conflict",
                "Output file exists.",
                path=str(output_path),
                suggestion="Pass --allow-overwrite if replacing or updating the output is intentional.",
            )
        if not args.dry_run:
            try:
                mode = "r+b" if output_path.exists() and (args.seek > 0 or notrunc) else "wb"
                with output_path.open(mode) as handle:
                    handle.seek(args.seek * args.bs)
                    handle.write(selected)
                    if "fsync" in conv_options:
                        handle.flush()
                        os.fsync(handle.fileno())
            except PermissionError as exc:
                raise AgentError(
                    "permission_denied", "Permission denied while writing output.", path=str(output_path)
                ) from exc
            except OSError as exc:
                if "noerror" in conv_options:
                    pass  # conv=noerror: skip write errors
                else:
                    raise AgentError("io_error", str(exc), path=str(output_path)) from exc

    if args.raw:
        return selected
    preview = selected[: args.max_preview_bytes]
    return {
        "input_path": label,
        "output_path": "-" if output_path is None else str(output_path),
        "input_bytes": len(data),
        "copied_bytes": len(selected),
        "bs": args.bs,
        "count": args.count,
        "skip_blocks": args.skip,
        "seek_blocks": args.seek,
        "conv": sorted(conv_options) if conv_options else None,
        "dry_run": args.dry_run,
        "content_base64": base64.b64encode(preview).decode("ascii"),
        "returned_preview_bytes": len(preview),
        "truncated": len(preview) < len(selected),
    }


def command_sync(args: argparse.Namespace) -> dict[str, Any]:
    sync = getattr(os, "sync", None)
    supported = callable(sync)
    if not args.dry_run and supported:
        assert callable(sync)
        try:
            sync()
        except OSError as exc:
            raise AgentError("io_error", str(exc)) from exc
    return {
        "operation": "sync",
        "supported": supported,
        "synced": bool(supported and not args.dry_run),
        "dry_run": args.dry_run,
    }
