"""Path resolution and filesystem metadata utilities.

路径工具层：提供跨平台的安全路径解析、文件类型检测、元数据收集、
目录遍历和磁盘用量计算。所有路径操作均将 OS 异常转换为 AgentError。

安全注意：
- resolve_path 始终解析符号链接（expanduser + resolve），防止 symlink 逃逸。
- iter_directory/disk_usage_entry/directory_size 中的 PermissionError 被
  静默跳过（SECURITY: 见函数内注释）。
"""

from __future__ import annotations

import os
import stat as statmod
from contextlib import suppress
from pathlib import Path
from typing import Any

from .envelope import utc_iso
from .exceptions import AgentError


def resolve_path(raw: str | Path, *, strict: bool = False) -> Path:
    """安全解析路径：展开 ~、规范化、跟随符号链接。

    这是所有命令的统一路径入口。先 expanduser 后 resolve，
    确保即使传入 ~/../outside 也会被解析为真实绝对路径，
    从而在上层 sandbox 校验中正确拦截越界访问。

    Args:
        raw: 原始路径字符串或 Path 对象。
        strict: True 时路径必须已存在，否则抛出 not_found。
                默认 False，允许解析不存在的路径（如 touch 新文件）。

    Returns:
        解析后的绝对 Path 对象。

    Raises:
        AgentError(not_found): strict=True 且路径不存在。
        AgentError(permission_denied): 无权限访问路径。
        AgentError(io_error): 其他 OS 错误。
    """
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
    """检测路径的文件系统类型（不跟随符号链接）。

    使用 lstat 而非 stat 以避免跟随符号链接。
    覆盖 POSIX 全部 7 种文件类型 + "unknown" 兜底。

    Returns:
        类型字符串：symlink / directory / file / fifo / socket /
        character_device / block_device / unknown。
    """
    try:
        mode = path.lstat().st_mode  # lstat 不跟随符号链接
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    # 按优先级检测：symlink 最先，目录优先于普通文件
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
    """收集单个路径的完整元数据，返回 JSON 兼容字典。

    Args:
        path: 要收集元数据的路径。
        base: 可选基准路径，用于计算相对路径（通常为 ls 的 cwd）。
        depth: 可选深度值，递归遍历时记录。

    Returns:
        包含 path/name/type/size_bytes/mode_octal/modified_at/created_at/
        is_symlink 等字段的字典。符号链接额外包含 link_target。
    """
    try:
        st = path.lstat()  # lstat：不跟随符号链接
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while reading metadata.", path=str(path)) from exc

    entry: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "type": path_type(path),
        "size_bytes": st.st_size,
        "mode_octal": oct(statmod.S_IMODE(st.st_mode)),  # 如 0o644
        "modified_at": utc_iso(st.st_mtime),
        "created_at": utc_iso(st.st_ctime),
        "is_symlink": path.is_symlink(),
    }
    if base is not None:
        try:
            entry["relative_path"] = str(path.relative_to(base))
        except ValueError:
            # 路径不在 base 之下（如传入绝对路径），回退为完整路径
            entry["relative_path"] = str(path)
    if depth is not None:
        entry["depth"] = depth
    if path.is_symlink():
        try:
            entry["link_target"] = os.readlink(path)
        except OSError:
            # 符号链接损坏或平台不支持（Windows 无权限时）
            entry["link_target"] = None
    return entry


def ensure_exists(path: Path) -> None:
    """断言路径存在（含损坏的符号链接），否则抛出 not_found。

    注意：path.exists() 对损坏的符号链接返回 False，
    但 path.is_symlink() 仍返回 True，需要同时检查两者。
    """
    if not path.exists() and not path.is_symlink():
        raise AgentError("not_found", "Path does not exist.", path=str(path))


def ensure_parent(path: Path, *, create: bool, dry_run: bool = False) -> None:
    """确保目标路径的父目录存在。

    Args:
        path: 目标路径（需要检查的是其 parent）。
        create: True 时自动创建缺失的父目录（如 mkdir -p）。
        dry_run: True 时只检查不创建。

    Raises:
        AgentError(not_found): create=False 且父目录不存在。
    """
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
    """遍历目录树，返回 stat_entry 列表和截断标志。

    排序规则：目录优先，同类型按名称字母序（不区分大小写）。
    这模仿了 GNU ls 的默认排序行为：directory-first。

    Args:
        root: 遍历根路径。若为文件则返回单元素列表。
        include_hidden: 是否包含 . 开头的隐藏文件。
        recursive: 是否递归进入子目录。
        max_depth: 最大递归深度（相对于 root）。
        follow_symlinks: 是否跟随符号链接进入目录。
        limit: 最大条目数，超过则截断并将 truncated 设为 True。

    Returns:
        (entries, truncated): 条目列表和是否被截断的布尔值。

    安全注意：
        PermissionError 被静默跳过。这是有意为之：遍历目录树时
        遇到无权限的子目录应返回部分结果而非整体失败（如 /proc, /sys）。
    """
    entries: list[dict[str, Any]] = []
    truncated = False
    root_depth = len(root.parts)  # 用于计算相对深度

    def _collect(current: Path, _depth: int) -> None:
        """递归收集目录条目。闭包捕获 entries/truncated。"""
        nonlocal truncated
        if truncated:
            return
        try:
            # 目录优先排序：目录排前面，同类型按名称字母序不区分大小写
            children = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            # SECURITY: 静默跳过无权限目录是设计决定。
            # 这允许 Agent 在受限环境中仍能获得部分目录列表，
            # 而不是因为单个 /proc 目录而整体失败。
            # TODO: 应在返回的 warnings 中添加提示。
            return
        for child in children:
            if truncated:
                return
            name = child.name
            if not include_hidden and name.startswith("."):
                continue
            entry = stat_entry(child, base=root, depth=_depth - root_depth)
            if not follow_symlinks and entry["is_symlink"]:
                pass  # 仅记录元数据，不解析
            entries.append(entry)
            if len(entries) >= limit:
                truncated = True
                return
            # 递归条件：recursive 模式 + 是目录 + 深度未达上限
            if recursive and entry["type"] == "directory" and _depth < max_depth:
                resolved = child.resolve() if follow_symlinks else child
                if follow_symlinks:
                    _collect(resolved, _depth + 1)
                else:
                    _collect(child, _depth + 1)

    if root.is_dir():
        _collect(root, root_depth)
    else:
        # 单个文件：返回一个元素，base 为父目录，depth=0
        entries.append(stat_entry(root, base=root.parent, depth=0))
    return entries, truncated


def disk_usage_entry(path: Path) -> dict[str, Any]:
    """计算目录的磁盘占用量（所有文件大小之和）。

    不跟随符号链接，通过 suppress(OSError) 处理单个文件 stat 失败。
    PermissionError 在顶层被静默捕获：返回值仅反映可 stat 的文件。

    Returns:
        {"path": str, "size_bytes": int}
    """
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():  # 跳过符号链接避免重复计数
                with suppress(OSError):
                    total += item.stat().st_size
    except PermissionError:
        # SECURITY: 静默跳过无权限目录是设计决定。
        # 返回值仅反映可 stat 的文件，不因受限目录而整体失败。
        pass
    return {"path": str(path), "size_bytes": total}


def directory_size(path: Path) -> int:
    """计算目录的总字节数（disk_usage_entry 的简化版）。

    与 disk_usage_entry 共享相同的静默跳过逻辑。

    Returns:
        总字节数（int），非字典。
    """
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                with suppress(OSError):
                    total += item.stat().st_size
    except PermissionError:
        # SECURITY: 同上，静默跳过无权限目录。
        pass
    return total
