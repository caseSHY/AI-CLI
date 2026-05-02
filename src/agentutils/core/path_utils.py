"""Path resolution and filesystem metadata utilities."""

from __future__ import annotations

import os
import stat as statmod
from contextlib import suppress
from pathlib import Path
from typing import Any

from .envelope import utc_iso
from .exceptions import AgentError


def resolve_path(raw: str | Path, *, strict: bool = False) -> Path:
    try:
        return Path(raw).expanduser().resolve(strict=strict)
    except FileNotFoundError as exc:
        raise AgentError(
            "not_found",
            "Path does not exist.",
            path=str(raw),
            suggestion="Check the path or call realpath without --strict to inspect the normalized path.",
        ) from exc
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while resolving path.", path=str(raw)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(raw)) from exc


def path_type(path: Path) -> str:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    if statmod.S_ISLNK(mode):
        return "symlink"
    if statmod.S_ISDIR(mode):
        return "directory"
    if statmod.S_ISREG(mode):
        return "file"
    if statmod.S_ISFIFO(mode):
        return "fifo"
    if statmod.S_ISSOCK(mode):
        return "socket"
    if statmod.S_ISCHR(mode):
        return "character_device"
    if statmod.S_ISBLK(mode):
        return "block_device"
    return "unknown"


def stat_entry(path: Path, *, base: Path | None = None, depth: int | None = None) -> dict[str, Any]:
    try:
        st = path.lstat()
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while reading metadata.", path=str(path)) from exc

    entry: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "type": path_type(path),
        "size_bytes": st.st_size,
        "mode_octal": oct(statmod.S_IMODE(st.st_mode)),
        "modified_at": utc_iso(st.st_mtime),
        "created_at": utc_iso(st.st_ctime),
        "is_symlink": path.is_symlink(),
    }
    if base is not None:
        try:
            entry["relative_path"] = str(path.relative_to(base))
        except ValueError:
            entry["relative_path"] = str(path)
    if depth is not None:
        entry["depth"] = depth
    if path.is_symlink():
        try:
            entry["link_target"] = os.readlink(path)
        except OSError:
            entry["link_target"] = None
    return entry


def ensure_exists(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        raise AgentError("not_found", "Path does not exist.", path=str(path))


def ensure_parent(path: Path, *, create: bool, dry_run: bool = False) -> None:
    parent = path.parent
    if parent.exists():
        return
    if not create:
        raise AgentError(
            "not_found",
            "Parent directory does not exist.",
            path=str(parent),
            suggestion="Pass --parents to create missing parent directories.",
        )
    if not dry_run:
        parent.mkdir(parents=True, exist_ok=True)


def iter_directory(
    root: Path,
    *,
    include_hidden: bool,
    recursive: bool,
    max_depth: int,
    follow_symlinks: bool,
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    entries: list[dict[str, Any]] = []
    truncated = False
    root_depth = len(root.parts)

    def _collect(current: Path, _depth: int) -> None:
        nonlocal truncated
        if truncated:
            return
        try:
            children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            # Silently skip directories we cannot read. This is intentional:
            # iterating a tree should return partial results rather than failing
            # entirely on OS-level permission boundaries (e.g. /proc, /sys).
            return
        for child in children:
            if truncated:
                return
            name = child.name
            if not include_hidden and name.startswith("."):
                continue
            entry = stat_entry(child, base=root, depth=_depth - root_depth)
            if not follow_symlinks and entry["is_symlink"]:
                pass
            entries.append(entry)
            if len(entries) >= limit:
                truncated = True
                return
            if recursive and entry["type"] == "directory" and _depth < max_depth:
                resolved = child.resolve() if follow_symlinks else child
                if follow_symlinks:
                    _collect(resolved, _depth + 1)
                else:
                    _collect(child, _depth + 1)

    if root.is_dir():
        _collect(root, root_depth)
    else:
        entries.append(stat_entry(root, base=root.parent, depth=0))
    return entries, truncated


def disk_usage_entry(path: Path) -> dict[str, Any]:
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                with suppress(OSError):
                    total += item.stat().st_size
    except PermissionError:
        # Permission errors while walking the tree are silently swallowed.
        # The returned total reflects only files that could be stat'd.
        pass
    return {"path": str(path), "size_bytes": total}


def directory_size(path: Path) -> int:
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                with suppress(OSError):
                    total += item.stat().st_size
    except PermissionError:
        # Permission errors while walking the tree are silently swallowed.
        # The returned total reflects only files that could be stat'd.
        pass
    return total
