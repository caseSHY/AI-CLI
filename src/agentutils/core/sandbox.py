"""Sandbox utilities: cwd boundary checks, dangerous target protection, overwrite guard."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .exceptions import AgentError
from .path_utils import resolve_path


def dangerous_delete_target(path: Path, cwd: Path) -> str | None:
    resolved = resolve_path(path)
    anchor = Path(resolved.anchor)
    home = Path.home().resolve()
    if resolved == anchor:
        return "Refusing to delete a filesystem root."
    if resolved == home:
        return "Refusing to delete the home directory."
    if resolved == cwd:
        return "Refusing to delete the current working directory."
    return None


def require_inside_cwd(path: Path, cwd: Path, *, allow_outside_cwd: bool) -> None:
    if allow_outside_cwd:
        return
    resolved = resolve_path(path)
    try:
        resolved.relative_to(cwd)
    except ValueError as exc:
        raise AgentError(
            "unsafe_operation",
            "Destructive recursive operation outside the current working directory is blocked.",
            path=str(resolved),
            suggestion="Pass --allow-outside-cwd only when the target is intentional.",
        ) from exc


def refuse_overwrite(destination: Path, allow_overwrite: bool) -> None:
    if destination.exists() and not allow_overwrite:
        raise AgentError(
            "conflict",
            "Destination exists.",
            path=str(destination),
            suggestion="Pass --allow-overwrite if replacing the destination is intentional.",
        )


def destination_inside_directory(source: Path, destination: Path) -> Path:
    if destination.exists() and destination.is_dir() and not destination.is_symlink():
        return destination / source.name
    return destination


def remove_one(path: Path, *, dry_run: bool) -> str:
    """Remove a single file, symlink, or empty directory. Returns status string."""
    reason = dangerous_delete_target(path, Path.cwd().resolve())
    if reason:
        raise AgentError("unsafe_operation", reason, path=str(path))
    if not path.exists() and not path.is_symlink():
        raise AgentError("not_found", "Path does not exist.", path=str(path))
    if dry_run:
        return "would_remove"
    if path.is_dir() and not path.is_symlink():
        try:
            path.rmdir()
            return "removed"
        except OSError as exc:
            raise AgentError(
                "conflict",
                "Directory could not be removed. It may be non-empty or in use.",
                path=str(path),
                details={"message": str(exc)},
            ) from exc
    else:
        try:
            path.unlink()
            return "removed"
        except PermissionError as exc:
            raise AgentError("permission_denied", "Permission denied while removing path.", path=str(path)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(path)) from exc


def remove_recursive(path: Path, *, dry_run: bool, allow_outside_cwd: bool) -> list[dict[str, Any]]:
    """Recursively remove a directory. Returns list of operation records."""
    cwd = Path.cwd().resolve()
    reason = dangerous_delete_target(path, cwd)
    if reason:
        raise AgentError("unsafe_operation", reason, path=str(path))
    require_inside_cwd(path, cwd, allow_outside_cwd=allow_outside_cwd)
    operations: list[dict[str, Any]] = []
    if dry_run:
        operations.append({"operation": "rm", "path": str(path), "dry_run": True})
        return operations
    if not path.is_dir() or path.is_symlink():
        path.unlink()
        operations.append({"operation": "rm", "path": str(path), "status": "removed"})
        return operations
    try:
        shutil.rmtree(str(path))
        operations.append({"operation": "rm", "path": str(path), "status": "removed"})
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while removing tree.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc
    return operations
