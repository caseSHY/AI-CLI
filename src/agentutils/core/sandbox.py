"""Sandbox utilities: cwd boundary checks, dangerous target protection, overwrite guard.

沙箱安全层：对所有写入、删除、截断、安装类命令强制执行安全校验。

核心规则：
1. cwd 边界：目标路径必须位于当前工作目录内（解析符号链接后的真实路径）。
2. 危险删除保护：拒绝删除文件系统根、用户家目录、当前工作目录。
3. 覆盖保护：默认拒绝覆盖已存在目标文件，需 --allow-overwrite 显式授权。
4. 安全优先：当安全要求与 GNU 行为兼容冲突时，agentutils 选择安全。

所有校验在 dry_run 和真实执行前均运行，确保 dry-run 也能暴露安全风险。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .exceptions import AgentError
from .path_utils import resolve_path


def dangerous_delete_target(path: Path, cwd: Path) -> str | None:
    """检查删除目标是否为危险路径（根、家目录、cwd）。

    在 rm/shred/rmdir/unlink 的 dry-run 和真实执行前调用。
    即使使用 --allow-outside-cwd 也会拒绝这些目标——
    这些保护是不可绕过的。

    Args:
        path: 要检查的路径。
        cwd: 当前工作目录（已 resolve）。

    Returns:
        危险原因字符串，安全时返回 None。
    """
    resolved = resolve_path(path)  # 先解析，防止符号链接绕过
    anchor = Path(resolved.anchor)  # 文件系统根（C:\ 或 /）
    home = Path.home().resolve()
    if resolved == anchor:
        return "Refusing to delete a filesystem root."
    if resolved == home:
        return "Refusing to delete the home directory."
    if resolved == cwd:
        return "Refusing to delete the current working directory."
    return None


def require_inside_cwd(path: Path, cwd: Path, *, allow_outside_cwd: bool) -> None:
    """校验路径在 cwd 内（解析符号链接后），否则拒绝。

    这是所有 mutating 命令的统一安全门。
    先 resolve_path 解析真实路径，再用 relative_to 判断是否在 cwd 内。
    解析步骤确保 ../outside、符号链接指向外部等攻击均被拦截。

    Args:
        path: 要校验的路径。
        cwd: 当前工作目录（已 resolve）。
        allow_outside_cwd: True 时绕过校验（用户显式授权）。

    Raises:
        AgentError(unsafe_operation): 路径在 cwd 外且未授权。
    """
    if allow_outside_cwd:
        return
    resolved = resolve_path(path)  # 关键：先解析真实路径再判断
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
    """检查目标文件是否已存在，存在且未授权则拒绝。

    适用于 cp/mv/install/tee 等会产生新文件或截断已有文件的命令。

    Args:
        destination: 目标路径。
        allow_overwrite: True 时允许覆盖。

    Raises:
        AgentError(conflict): 目标存在且未授权覆盖。
    """
    if destination.exists() and not allow_overwrite:
        raise AgentError(
            "conflict",
            "Destination exists.",
            path=str(destination),
            suggestion="Pass --allow-overwrite if replacing the destination is intentional.",
        )


def destination_inside_directory(source: Path, destination: Path) -> Path:
    """如果 destination 是已存在目录，则将 source 复制到目录内。

    模仿 GNU cp 的行为：cp file.txt existing_dir/ → cp file.txt existing_dir/file.txt
    符号链接指向的目录不被视为目录（避免意外）。

    Returns:
        调整后的目标路径。
    """
    if destination.exists() and destination.is_dir() and not destination.is_symlink():
        return destination / source.name
    return destination


def remove_one(path: Path, *, dry_run: bool = False, recursive: bool = False, force: bool = False) -> str:
    """删除单个文件、符号链接或目录（可选递归）。

    执行顺序：
    1. 危险目标检查（不可绕过）
    2. 存在性检查（force=True 时缺失视为正常）
    3. dry-run → 返回 "would_remove"
    4. 目录 + recursive → shutil.rmtree
    5. 目录 + 非 recursive → rmdir（仅限空目录）
    6. 其他 → unlink

    Args:
        path: 要删除的路径。
        dry_run: True 时仅返回计划操作，不实际执行。
        recursive: True 时递归删除目录（使用 rmtree）。
        force: True 时忽略缺失的文件（返回 "missing_ignored"）。

    Returns:
        状态字符串：would_remove / removed / directory_removed / file_removed / missing_ignored。

    Raises:
        AgentError(unsafe_operation): 危险目标。
        AgentError(not_found): 路径不存在且 force=False。
        AgentError(conflict): 目录非空且 recursive=False。
        AgentError(permission_denied): 权限不足。
        AgentError(io_error): 其他 OS 错误。
    """
    # 步骤 1：危险目标检查（不可绕过）
    reason = dangerous_delete_target(path, Path.cwd().resolve())
    if reason:
        raise AgentError("unsafe_operation", reason, path=str(path))
    # 步骤 2：存在性检查
    if not path.exists() and not path.is_symlink():
        if force:
            return "missing_ignored"  # force 模式：静默忽略
        raise AgentError("not_found", "Path does not exist.", path=str(path))
    # 步骤 3：dry-run 提前返回
    if dry_run:
        return "would_remove"
    # 步骤 4-6：区分目录递归/非递归和文件
    if path.is_dir() and not path.is_symlink():
        if not recursive:
            raise AgentError(
                "invalid_input",
                "Path is a directory; recursive removal requires --recursive.",
                path=str(path),
            )
        else:
            import shutil

            try:
                shutil.rmtree(str(path))
                return "directory_removed"
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while removing tree.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    else:
        try:
            path.unlink()  # unlink 处理文件和符号链接
            return "removed"
        except PermissionError as exc:
            raise AgentError("permission_denied", "Permission denied while removing path.", path=str(path)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(path)) from exc


def remove_recursive(path: Path, *, dry_run: bool, allow_outside_cwd: bool) -> list[dict[str, Any]]:
    """递归删除目录（使用 shutil.rmtree）。

    与 remove_one 相比增加了 cwd 边界校验（因为 rmtree 影响范围大）。

    Args:
        path: 要删除的路径。
        dry_run: True 时仅返回计划操作。
        allow_outside_cwd: True 时允许删除 cwd 外的目录。

    Returns:
        操作记录列表 [{"operation": "rm", "path": ..., "status": "removed"}]。
    """
    cwd = Path.cwd().resolve()
    # 步骤 1：危险目标检查
    reason = dangerous_delete_target(path, cwd)
    if reason:
        raise AgentError("unsafe_operation", reason, path=str(path))
    # 步骤 2：cwd 边界校验
    require_inside_cwd(path, cwd, allow_outside_cwd=allow_outside_cwd)
    operations: list[dict[str, Any]] = []
    if dry_run:
        operations.append({"operation": "rm", "path": str(path), "dry_run": True})
        return operations
    # 步骤 3：非目录或符号链接 → unlink
    if not path.is_dir() or path.is_symlink():
        path.unlink()
        operations.append({"operation": "rm", "path": str(path), "status": "removed"})
        return operations
    # 步骤 4：目录 → rmtree
    try:
        shutil.rmtree(str(path))
        operations.append({"operation": "rm", "path": str(path), "status": "removed"})
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while removing tree.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc
    return operations
