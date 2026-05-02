"""Path utilities: disk usage, directory size, test predicates, directory iteration.

命令层使用的路径遍历和磁盘操作函数。iter_directory 是 ls/dir/vdir 的核心引擎。
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from ..core import AgentError, path_type, stat_entry


def disk_usage_entry(path: Path) -> dict[str, Any]:
    """获取路径所在磁盘的使用情况（shutil.disk_usage 包装）。

    Returns:
        {path, total_bytes, used_bytes, free_bytes, used_ratio}
    """
    try:
        usage = shutil.disk_usage(path)
    except FileNotFoundError as exc:
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {
        "path": str(path.resolve()),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_ratio": usage.used / usage.total if usage.total else None,
    }


def directory_size(path: Path, *, max_depth: int, follow_symlinks: bool) -> tuple[int, int, bool]:
    """递归计算目录中所有文件的大小之和和文件数。

    Returns:
        (total_bytes, file_count, truncated)
    """
    total = 0
    count = 0
    truncated = False

    def add(target: Path, depth: int) -> None:
        nonlocal total, count, truncated
        if depth > max_depth:
            truncated = True
            return
        try:
            st = target.stat() if follow_symlinks else target.lstat()
        except OSError:
            return
        total += st.st_size
        count += 1
        if target.is_dir() and (follow_symlinks or not target.is_symlink()):
            try:
                children = list(target.iterdir())
            except OSError:
                return
            for child in children:
                add(child, depth + 1)

    add(path, 0)
    return total, count, truncated


def evaluate_test_predicates(path: Path, predicates: list[str]) -> list[dict[str, Any]]:
    """评估 test/[ 命令的文件谓词列表。

    支持的谓词：exists, file, directory, symlink, readable, writable,
    executable, empty, non_empty。
    """
    checks: list[dict[str, Any]] = []
    exists = path.exists() or path.is_symlink()
    for predicate in predicates:
        if predicate == "exists":
            matches = exists
        elif predicate == "file":
            matches = path.is_file()
        elif predicate == "directory":
            matches = path.is_dir()
        elif predicate == "symlink":
            matches = path.is_symlink()
        elif predicate == "readable":
            matches = exists and os.access(path, os.R_OK)
        elif predicate == "writable":
            matches = exists and os.access(path, os.W_OK)
        elif predicate == "executable":
            matches = exists and os.access(path, os.X_OK)
        elif predicate == "empty":
            matches = exists and path.is_file() and path.stat().st_size == 0
        elif predicate == "non_empty":
            matches = exists and path.is_file() and path.stat().st_size > 0
        else:
            raise AgentError("invalid_input", f"Unsupported test predicate: {predicate}")
        checks.append({"predicate": predicate, "matches": bool(matches)})
    return checks


def prime_factors(value: int) -> list[int]:
    """计算整数的质因数分解（trial division 算法）。

    有 agentutils 安全上限 FACTOR_MAX，大数分解不应在此函数中完成。
    """
    factors: list[int] = []
    number = abs(value)
    divisor = 2
    while divisor * divisor <= number:
        while number % divisor == 0:
            factors.append(divisor)
            number //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if number > 1:
        factors.append(number)
    return factors


def path_issues(raw: str, *, max_path_length: int, max_component_length: int, portable: bool) -> list[str]:
    """检查路径字符串的潜在问题（用于 pathchk 命令）。

    Returns:
        问题字符串列表，空列表表示路径有效。
    """
    issues: list[str] = []
    if raw == "":
        issues.append("empty_path")
    if "\0" in raw:
        issues.append("nul_byte")
    if len(raw) > max_path_length:
        issues.append("path_too_long")
    components = [component for component in re.split(r"[\\/]+", raw) if component not in ("", ".")]
    for component in components:
        if len(component) > max_component_length:
            issues.append("component_too_long")
            break
    if portable and re.search(r"[^A-Za-z0-9._/\-\\]", raw):
        issues.append("non_portable_character")
    return issues


def expression_truthy(value: object) -> bool:
    """判断 expr 命令中的值是否为"真"。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


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

    这是 ls/dir/vdir 命令的核心引擎。使用迭代式栈遍历以避免
    递归深度限制，按"目录优先、名称自然排序"输出。

    Returns:
        (entries, truncated)
    """
    entries: list[dict[str, Any]] = []
    truncated = False
    base = root

    def include(path: Path) -> bool:
        return include_hidden or not path.name.startswith(".")

    def sorted_children(path: Path) -> list[Path]:
        try:
            children = [child for child in path.iterdir() if include(child)]
        except PermissionError as exc:
            raise AgentError("permission_denied", "Permission denied while listing directory.", path=str(path)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(path)) from exc
        return sorted(children, key=lambda item: (path_type(item), item.name.lower(), item.name))

    def add(path: Path, depth: int) -> None:
        nonlocal truncated
        if len(entries) >= limit:
            truncated = True
            return
        entries.append(stat_entry(path, base=base, depth=depth))

    if root.is_dir() and not (root.is_symlink() and not follow_symlinks):
        for child in sorted_children(root):
            add(child, 0)
            if truncated:
                return entries, truncated
            # 递归：使用显式栈而非递归函数调用，避免大目录栈溢出
            if recursive and child.is_dir() and (follow_symlinks or not child.is_symlink()) and max_depth > 0:
                stack: list[tuple[Path, int]] = [(child, 1)]
                while stack and not truncated:
                    current, depth = stack.pop()
                    if depth > max_depth:
                        continue
                    for nested in reversed(sorted_children(current)):
                        add(nested, depth)
                        if truncated:
                            break
                        if nested.is_dir() and (follow_symlinks or not nested.is_symlink()) and depth < max_depth:
                            stack.append((nested, depth + 1))
    else:
        add(root, 0)
    return entries, truncated
