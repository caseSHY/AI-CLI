"""A small, deterministic CLI protocol for agent workflows."""

from __future__ import annotations

import argparse
import ast
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import getpass
import platform
import random
import re
import shutil
import stat as statmod
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
import zlib
from pathlib import Path
from typing import Any, BinaryIO, Iterable, TextIO

from . import __version__
from .catalog import priority_catalog


EXIT = {
    "ok": 0,
    "predicate_false": 1,
    "general_error": 1,
    "usage": 2,
    "not_found": 3,
    "permission_denied": 4,
    "invalid_input": 5,
    "conflict": 6,
    "partial_failure": 7,
    "unsafe_operation": 8,
    "io_error": 10,
}

HASH_ALGORITHMS = {
    "md5": "md5",
    "sha1": "sha1",
    "sha224": "sha224",
    "sha256": "sha256",
    "sha384": "sha384",
    "sha512": "sha512",
    "b2sum": "blake2b",
    "blake2b": "blake2b",
}


class AgentError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        path: str | None = None,
        suggestion: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path
        self.suggestion = suggestion
        self.details = details or {}

    @property
    def exit_code(self) -> int:
        return EXIT.get(self.code, EXIT["general_error"])

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.path is not None:
            error["path"] = self.path
        if self.suggestion is not None:
            error["suggestion"] = self.suggestion
        if self.details:
            error["details"] = self.details
        return error


class AgentArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        error = AgentError(
            "usage",
            message,
            suggestion="Run 'agentutils schema' or '<command> --help' to discover valid usage.",
        )
        write_json(sys.stderr, error_envelope(None, error))
        raise SystemExit(EXIT["usage"])


def utc_iso(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).isoformat().replace("+00:00", "Z")


def write_json(stream: TextIO, payload: dict[str, Any], *, pretty: bool = False) -> None:
    kwargs: dict[str, Any] = {"ensure_ascii": False, "sort_keys": True}
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    stream.write(json.dumps(payload, **kwargs))
    stream.write("\n")


def envelope(command: str, result: Any, *, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "tool": "agentutils",
        "version": __version__,
        "command": command,
        "result": result,
        "warnings": warnings or [],
    }


def error_envelope(command: str | None, error: AgentError) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": "agentutils",
        "version": __version__,
        "command": command,
        "error": error.to_dict(),
    }


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
        raise AgentError(
            "permission_denied",
            "Permission denied while resolving path.",
            path=str(raw),
        ) from exc
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


def command_catalog(args: argparse.Namespace) -> dict[str, Any]:
    return priority_catalog()


def command_schema(args: argparse.Namespace) -> dict[str, Any]:
    implemented_commands = [
        "catalog",
        "schema",
        "pwd",
        "basename",
        "dirname",
        "realpath",
        "ls",
        "dir",
        "vdir",
        "stat",
        "cat",
        "head",
        "tail",
        "wc",
        "readlink",
        "test",
        "[",
        "md5sum",
        "sha1sum",
        "sha224sum",
        "sha256sum",
        "sha384sum",
        "sha512sum",
        "b2sum",
        "hash",
        "sort",
        "comm",
        "join",
        "paste",
        "shuf",
        "tac",
        "nl",
        "fold",
        "fmt",
        "csplit",
        "split",
        "od",
        "pr",
        "ptx",
        "numfmt",
        "uniq",
        "cut",
        "tr",
        "expand",
        "unexpand",
        "base64",
        "base32",
        "basenc",
        "cksum",
        "sum",
        "tsort",
        "date",
        "env",
        "printenv",
        "whoami",
        "groups",
        "id",
        "uname",
        "arch",
        "hostname",
        "hostid",
        "logname",
        "uptime",
        "tty",
        "users",
        "who",
        "nproc",
        "df",
        "du",
        "dd",
        "sync",
        "dircolors",
        "seq",
        "printf",
        "echo",
        "pathchk",
        "factor",
        "expr",
        "true",
        "false",
        "sleep",
        "yes",
        "timeout",
        "nice",
        "nohup",
        "kill",
        "mkdir",
        "touch",
        "cp",
        "mv",
        "rm",
        "ln",
        "link",
        "chmod",
        "chown",
        "chgrp",
        "truncate",
        "mktemp",
        "mkfifo",
        "mknod",
        "install",
        "ginstall",
        "tee",
        "rmdir",
        "unlink",
        "shred",
    ]
    return {
        "protocol": {
            "stdout_success": {
                "ok": True,
                "tool": "agentutils",
                "version": __version__,
                "command": "<subcommand>",
                "result": {},
                "warnings": [],
            },
            "stderr_error": {
                "ok": False,
                "tool": "agentutils",
                "version": __version__,
                "command": "<subcommand>",
                "error": {
                    "code": "<semantic_code>",
                    "message": "<clear human and machine readable message>",
                    "path": "<optional path>",
                    "suggestion": "<optional fix>",
                },
            },
        },
        "exit_codes": EXIT,
        "implemented_commands": implemented_commands,
        "safety": {
            "json_default": True,
            "colors": False,
            "progress_bars": False,
            "mutation_commands_support_dry_run": True,
            "overwrite_requires_explicit_flag": True,
            "recursive_rm_outside_cwd_requires_explicit_flag": True,
            "raw_pipeline_output_requires_explicit_flag": True,
        },
    }


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
                        if (
                            nested.is_dir()
                            and (follow_symlinks or not nested.is_symlink())
                            and depth < max_depth
                        ):
                            stack.append((nested, depth + 1))
    else:
        add(root, 0)
    return entries, truncated


def command_ls(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_path(args.path, strict=True)
    if args.max_depth < 0:
        raise AgentError("invalid_input", "--max-depth must be >= 0.")
    if args.limit < 1:
        raise AgentError("invalid_input", "--limit must be >= 1.")
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


def command_dir(args: argparse.Namespace) -> dict[str, Any]:
    result = command_ls(args)
    result["alias"] = "dir"
    return result


def command_vdir(args: argparse.Namespace) -> dict[str, Any]:
    result = command_ls(args)
    result["alias"] = "vdir"
    result["verbose"] = True
    return result


def command_stat(args: argparse.Namespace) -> dict[str, Any]:
    entries = [stat_entry(resolve_path(raw, strict=True)) for raw in args.paths]
    return {"count": len(entries), "entries": entries}


def read_bytes(path: Path, *, max_bytes: int, offset: int = 0) -> tuple[bytes, bool, int]:
    if max_bytes < 0:
        raise AgentError("invalid_input", "--max-bytes must be >= 0.")
    if offset < 0:
        raise AgentError("invalid_input", "--offset must be >= 0.")
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    size = path.stat().st_size
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(max_bytes)
        truncated = offset + len(data) < size
    return data, truncated, size


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


def read_text_lines(path: Path, *, encoding: str) -> list[str]:
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        return handle.read().splitlines()


def command_head(args: argparse.Namespace) -> dict[str, Any]:
    if args.lines < 0:
        raise AgentError("invalid_input", "--lines must be >= 0.")
    path = resolve_path(args.path, strict=True)
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


def command_tail(args: argparse.Namespace) -> dict[str, Any]:
    if args.lines < 0:
        raise AgentError("invalid_input", "--lines must be >= 0.")
    path = resolve_path(args.path, strict=True)
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


def count_words(text: str) -> int:
    return len(text.split())


def wc_for_bytes(data: bytes, *, encoding: str) -> dict[str, Any]:
    text = data.decode(encoding, errors="replace")
    return {
        "bytes": len(data),
        "chars": len(text),
        "lines": data.count(b"\n"),
        "words": count_words(text),
    }


def command_wc(args: argparse.Namespace) -> dict[str, Any]:
    entries = []
    totals = {"bytes": 0, "chars": 0, "lines": 0, "words": 0}
    for raw in args.paths:
        if raw == "-":
            data = sys.stdin.buffer.read()
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
    return {"count": len(entries), "entries": entries, "totals": totals}


def read_stdin_bytes() -> bytes:
    return sys.stdin.buffer.read()


def read_input_bytes(raw: str) -> tuple[str, bytes]:
    if raw == "-":
        return "-", read_stdin_bytes()
    path = resolve_path(raw, strict=True)
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    try:
        return str(path), path.read_bytes()
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while reading file.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc


def read_input_texts(paths: list[str], *, encoding: str) -> list[dict[str, str]]:
    if not paths:
        paths = ["-"]
    sources = []
    for raw in paths:
        label, data = read_input_bytes(raw)
        sources.append({"path": label, "text": data.decode(encoding, errors="replace")})
    return sources


def combined_lines(paths: list[str], *, encoding: str) -> tuple[list[str], list[str]]:
    sources = read_input_texts(paths, encoding=encoding)
    lines: list[str] = []
    for source in sources:
        lines.extend(source["text"].splitlines())
    return lines, [source["path"] for source in sources]


def bounded_lines(lines: list[Any], max_lines: int) -> tuple[list[Any], bool]:
    if max_lines < 0:
        raise AgentError("invalid_input", "--max-lines must be >= 0.")
    return lines[:max_lines], len(lines) > max_lines


def lines_to_raw(lines: list[str], *, encoding: str) -> bytes:
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode(encoding)


def decode_standard_escapes(value: str) -> str:
    escapes = {
        "\\": "\\",
        "0": "\0",
        "a": "\a",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
    }
    output: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 >= len(value):
            output.append(char)
            index += 1
            continue
        marker = value[index + 1]
        if marker == "x":
            hex_digits = value[index + 2 : index + 4]
            if hex_digits and all(item in "0123456789abcdefABCDEF" for item in hex_digits):
                output.append(chr(int(hex_digits, 16)))
                index += 2 + len(hex_digits)
                continue
        output.append(escapes.get(marker, marker))
        index += 2
    return "".join(output)


def printf_conversions(format_string: str) -> list[str]:
    conversions = []
    index = 0
    valid = "diouxXeEfFgGcrsa"
    while index < len(format_string):
        if format_string[index] != "%":
            index += 1
            continue
        if index + 1 < len(format_string) and format_string[index + 1] == "%":
            index += 2
            continue
        end = index + 1
        while end < len(format_string) and format_string[end] not in valid:
            if format_string[end] == "*":
                raise AgentError("invalid_input", "printf '*' width and precision are not supported.")
            end += 1
        if end >= len(format_string):
            raise AgentError("invalid_input", "printf format contains an incomplete conversion.")
        conversions.append(format_string[end])
        index = end + 1
    return conversions


def coerce_printf_value(value: str, conversion: str) -> object:
    try:
        if conversion in "diouxX":
            return int(value, 0)
        if conversion in "eEfFgG":
            return float(value)
        if conversion == "c":
            return value if len(value) == 1 else int(value, 0)
    except ValueError as exc:
        raise AgentError(
            "invalid_input",
            "printf value cannot be coerced for the requested conversion.",
            details={"value": value, "conversion": conversion},
        ) from exc
    return value


def format_printf(format_string: str, values: list[str]) -> str:
    fmt = decode_standard_escapes(format_string)
    conversions = printf_conversions(fmt)
    if not conversions:
        if values:
            raise AgentError("invalid_input", "printf received values but the format has no conversions.")
        return fmt
    if len(values) % len(conversions) != 0:
        raise AgentError(
            "invalid_input",
            "printf values must fill the format exactly; repeat the format by passing a multiple of its conversions.",
            details={"values": len(values), "conversions_per_format": len(conversions)},
        )
    output = []
    for start in range(0, len(values), len(conversions)):
        chunk = values[start : start + len(conversions)]
        converted = tuple(coerce_printf_value(value, conversion) for value, conversion in zip(chunk, conversions))
        try:
            output.append(fmt % converted)
        except (TypeError, ValueError) as exc:
            raise AgentError("invalid_input", "printf format could not be applied to the supplied values.") from exc
    return "".join(output)


def simple_sum16(data: bytes) -> int:
    return sum(data) & 0xFFFF


def alpha_suffix(index: int, width: int) -> str:
    if width < 1:
        raise AgentError("invalid_input", "--suffix-length must be >= 1.")
    limit = 26**width
    if index >= limit:
        raise AgentError(
            "invalid_input",
            "Too many split chunks for the requested alphabetic suffix length.",
            details={"index": index, "suffix_length": width},
        )
    chars = ["a"] * width
    value = index
    for position in range(width - 1, -1, -1):
        chars[position] = chr(ord("a") + (value % 26))
        value //= 26
    return "".join(chars)


def numeric_suffix(index: int, width: int) -> str:
    if width < 1:
        raise AgentError("invalid_input", "--suffix-length must be >= 1.")
    suffix = str(index).zfill(width)
    if len(suffix) > width:
        raise AgentError(
            "invalid_input",
            "Too many split chunks for the requested numeric suffix length.",
            details={"index": index, "suffix_length": width},
        )
    return suffix


def unexpand_line(line: str, *, tab_size: int, all_blanks: bool) -> str:
    def compress_spaces(match: re.Match[str]) -> str:
        width = len(match.group(0))
        return "\t" * (width // tab_size) + " " * (width % tab_size)

    if all_blanks:
        return re.sub(r" +", compress_spaces, line)
    leading = re.match(r" +", line)
    if not leading:
        return line
    return compress_spaces(leading) + line[leading.end() :]


def digest_file(path: Path, algorithm: str, *, chunk_size: int = 1024 * 1024) -> str:
    if algorithm not in HASH_ALGORITHMS:
        raise AgentError(
            "invalid_input",
            f"Unsupported hash algorithm: {algorithm}",
            suggestion=f"Use one of: {', '.join(sorted(HASH_ALGORITHMS))}.",
        )
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    digest = hashlib.new(HASH_ALGORITHMS[algorithm])
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def digest_bytes(data: bytes, algorithm: str) -> str:
    if algorithm not in HASH_ALGORITHMS:
        raise AgentError(
            "invalid_input",
            f"Unsupported hash algorithm: {algorithm}",
            suggestion=f"Use one of: {', '.join(sorted(HASH_ALGORITHMS))}.",
        )
    digest = hashlib.new(HASH_ALGORITHMS[algorithm])
    digest.update(data)
    return digest.hexdigest()


def command_hash(args: argparse.Namespace) -> dict[str, Any]:
    entries = []
    for raw in args.paths:
        if raw == "-":
            data = read_stdin_bytes()
            entries.append(
                {
                    "path": "-",
                    "algorithm": args.algorithm,
                    "digest": digest_bytes(data, args.algorithm),
                    "size_bytes": len(data),
                }
            )
            continue
        path = resolve_path(raw, strict=True)
        entries.append(
            {
                "path": str(path),
                "algorithm": args.algorithm,
                "digest": digest_file(path, args.algorithm),
                "size_bytes": path.stat().st_size,
            }
        )
    return {"count": len(entries), "entries": entries}


def command_cksum(args: argparse.Namespace) -> dict[str, Any] | bytes:
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


def command_sort(args: argparse.Namespace) -> dict[str, Any] | bytes:
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)

    def key(line: str) -> Any:
        comparable = line.lower() if args.ignore_case else line
        if not args.numeric:
            return comparable
        first = comparable.split(maxsplit=1)[0] if comparable.split(maxsplit=1) else ""
        try:
            return (0, float(first), comparable)
        except ValueError:
            return (1, comparable)

    sorted_lines = sorted(lines, key=key, reverse=args.reverse)
    if args.unique:
        unique_lines = []
        seen = set()
        for line in sorted_lines:
            identity = line.lower() if args.ignore_case else line
            if identity in seen:
                continue
            seen.add(identity)
            unique_lines.append(line)
        sorted_lines = unique_lines
    if args.raw:
        return lines_to_raw(sorted_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(sorted_lines, args.max_lines)
    return {
        "source_paths": source_paths,
        "input_lines": len(lines),
        "returned_lines": len(emitted),
        "total_output_lines": len(sorted_lines),
        "truncated": truncated,
        "reverse": args.reverse,
        "unique": args.unique,
        "numeric": args.numeric,
        "lines": emitted,
    }


def command_comm(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if len(args.paths) != 2:
        raise AgentError("invalid_input", "comm requires exactly two input files.")
    left_lines, left_sources = combined_lines([args.paths[0]], encoding=args.encoding)
    right_lines, right_sources = combined_lines([args.paths[1]], encoding=args.encoding)
    left_set = set(left_lines)
    right_set = set(right_lines)
    only_left = [line for line in left_lines if line not in right_set]
    only_right = [line for line in right_lines if line not in left_set]
    common = [line for line in left_lines if line in right_set]
    records = []
    if not args.suppress_1:
        records.extend({"column": 1, "line": line} for line in only_left)
    if not args.suppress_2:
        records.extend({"column": 2, "line": line} for line in only_right)
    if not args.suppress_3:
        records.extend({"column": 3, "line": line} for line in common)
    if args.raw:
        raw_lines = [f"{record['column']}\t{record['line']}" for record in records]
        return lines_to_raw(raw_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": left_sources + right_sources,
        "counts": {"only_first": len(only_left), "only_second": len(only_right), "common": len(common)},
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


def split_fields(line: str, delimiter: str | None) -> list[str]:
    return line.split(delimiter) if delimiter is not None else line.split()


def command_join(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if len(args.paths) != 2:
        raise AgentError("invalid_input", "join requires exactly two input files.")
    if args.field1 < 1 or args.field2 < 1:
        raise AgentError("invalid_input", "--field1 and --field2 are 1-based and must be positive.")
    left_lines, left_sources = combined_lines([args.paths[0]], encoding=args.encoding)
    right_lines, right_sources = combined_lines([args.paths[1]], encoding=args.encoding)
    right_index: dict[str, list[list[str]]] = {}
    for line in right_lines:
        fields = split_fields(line, args.delimiter)
        if len(fields) >= args.field2:
            right_index.setdefault(fields[args.field2 - 1], []).append(fields)
    records = []
    output_lines = []
    for line in left_lines:
        left_fields = split_fields(line, args.delimiter)
        if len(left_fields) < args.field1:
            continue
        key = left_fields[args.field1 - 1]
        for right_fields in right_index.get(key, []):
            combined = [key] + [field for i, field in enumerate(left_fields) if i != args.field1 - 1]
            combined += [field for i, field in enumerate(right_fields) if i != args.field2 - 1]
            output = args.output_delimiter.join(combined)
            records.append({"key": key, "fields": combined, "line": output})
            output_lines.append(output)
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": left_sources + right_sources,
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


def command_paste(args: argparse.Namespace) -> dict[str, Any] | bytes:
    sources = read_input_texts(args.paths, encoding=args.encoding)
    line_groups = [source["text"].splitlines() for source in sources]
    max_len = max((len(lines) for lines in line_groups), default=0)
    output_lines = []
    for index in range(max_len):
        row = [lines[index] if index < len(lines) else "" for lines in line_groups]
        output_lines.append(args.delimiter.join(row))
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def command_shuf(args: argparse.Namespace) -> dict[str, Any] | bytes:
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    rng = random.Random(args.seed)
    shuffled = list(lines)
    rng.shuffle(shuffled)
    if args.count is not None:
        if args.count < 0:
            raise AgentError("invalid_input", "--count must be >= 0.")
        shuffled = shuffled[: args.count]
    if args.raw:
        return lines_to_raw(shuffled, encoding=args.encoding)
    emitted, truncated = bounded_lines(shuffled, args.max_lines)
    return {
        "source_paths": source_paths,
        "input_lines": len(lines),
        "returned_lines": len(emitted),
        "total_output_lines": len(shuffled),
        "truncated": truncated,
        "seed": args.seed,
        "lines": emitted,
    }


def command_tac(args: argparse.Namespace) -> dict[str, Any] | bytes:
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    output_lines = list(reversed(lines))
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    return {
        "source_paths": source_paths,
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def command_nl(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.start < 0:
        raise AgentError("invalid_input", "--start must be >= 0.")
    if args.increment < 1:
        raise AgentError("invalid_input", "--increment must be >= 1.")
    if args.width < 1:
        raise AgentError("invalid_input", "--width must be >= 1.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    records = []
    output_lines = []
    number = args.start
    for line in lines:
        should_number = args.number_blank or bool(line)
        if should_number:
            formatted_number = str(number).rjust(args.width)
            output = f"{formatted_number}{args.separator}{line}"
            record_number: int | None = number
            number += args.increment
        else:
            output = line
            record_number = None
        records.append({"number": record_number, "line": line, "output": output})
        output_lines.append(output)
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": source_paths,
        "input_lines": len(lines),
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


def command_fold(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.width < 1:
        raise AgentError("invalid_input", "--width must be >= 1.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    output_lines = []
    for line in lines:
        if not line:
            output_lines.append("")
            continue
        wrapped = textwrap.wrap(
            line,
            width=args.width,
            break_long_words=args.break_words,
            break_on_hyphens=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        output_lines.extend(wrapped or [""])
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    return {
        "source_paths": source_paths,
        "width": args.width,
        "break_words": args.break_words,
        "input_lines": len(lines),
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def command_fmt(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.width < 1:
        raise AgentError("invalid_input", "--width must be >= 1.")
    sources = read_input_texts(args.paths, encoding=args.encoding)
    output_lines: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        joined = " ".join(line.strip() for line in paragraph)
        wrapped = textwrap.wrap(joined, width=args.width, break_long_words=False, break_on_hyphens=False)
        output_lines.extend(wrapped or [""])
        paragraph.clear()

    for source in sources:
        for line in source["text"].splitlines():
            if line.strip():
                paragraph.append(line)
            else:
                flush_paragraph()
                output_lines.append("")
    flush_paragraph()

    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "width": args.width,
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def command_csplit(args: argparse.Namespace) -> dict[str, Any]:
    if args.pattern == "":
        raise AgentError("invalid_input", "--pattern cannot be empty.")
    label, data = read_input_bytes(args.path)
    text = data.decode(args.encoding, errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    try:
        regex = re.compile(args.pattern, re.MULTILINE)
    except re.error as exc:
        raise AgentError("invalid_input", "Invalid csplit regular expression.", details={"pattern": args.pattern}) from exc
    matches = list(regex.finditer(text))
    if args.max_splits < 0:
        raise AgentError("invalid_input", "--max-splits must be >= 0.")
    if args.max_splits:
        matches = matches[: args.max_splits]
    boundaries = [0] + [match.start() for match in matches] + [len(text)]
    chunks = [text[boundaries[index] : boundaries[index + 1]] for index in range(len(boundaries) - 1)]
    output_dir = resolve_path(args.output_dir, strict=True)
    if not output_dir.is_dir():
        raise AgentError("invalid_input", "--output-dir must be a directory.", path=str(output_dir))
    operations = []
    for index, chunk in enumerate(chunks):
        suffix = numeric_suffix(index, args.suffix_length)
        destination = output_dir / f"{args.prefix}{suffix}"
        if destination.exists() and not args.allow_overwrite:
            raise AgentError(
                "conflict",
                "csplit destination exists.",
                path=str(destination),
                suggestion="Pass --allow-overwrite if replacing split outputs is intentional.",
            )
        encoded = chunk.encode(args.encoding)
        operations.append(
            {
                "operation": "csplit",
                "source_path": label,
                "destination": str(destination),
                "index": index,
                "suffix": suffix,
                "bytes": len(encoded),
                "dry_run": args.dry_run,
            }
        )
        if not args.dry_run:
            try:
                destination.write_bytes(encoded)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while writing csplit output.", path=str(destination)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {
        "source_path": label,
        "pattern": args.pattern,
        "matches": len(matches),
        "chunks": len(chunks),
        "dry_run": args.dry_run,
        "operations": operations,
    }


def split_chunks_by_lines(data: bytes, lines_per_file: int) -> list[tuple[bytes, int]]:
    if lines_per_file < 1:
        raise AgentError("invalid_input", "--lines must be >= 1.")
    lines = data.splitlines(keepends=True)
    return [(b"".join(lines[index : index + lines_per_file]), len(lines[index : index + lines_per_file])) for index in range(0, len(lines), lines_per_file)]


def split_chunks_by_bytes(data: bytes, bytes_per_file: int) -> list[tuple[bytes, int]]:
    if bytes_per_file < 1:
        raise AgentError("invalid_input", "--bytes must be >= 1.")
    return [(data[index : index + bytes_per_file], 0) for index in range(0, len(data), bytes_per_file)]


def command_split(args: argparse.Namespace) -> dict[str, Any]:
    if args.lines is None and args.bytes is None:
        args.lines = 1000
    label, data = read_input_bytes(args.path)
    output_dir = resolve_path(args.output_dir, strict=True)
    if not output_dir.is_dir():
        raise AgentError("invalid_input", "--output-dir must be a directory.", path=str(output_dir))
    if args.lines is not None:
        chunks = split_chunks_by_lines(data, args.lines)
        mode = "lines"
    else:
        chunks = split_chunks_by_bytes(data, args.bytes)
        mode = "bytes"
    operations = []
    for index, (chunk, line_count) in enumerate(chunks):
        suffix = numeric_suffix(index, args.suffix_length) if args.numeric_suffixes else alpha_suffix(index, args.suffix_length)
        destination = output_dir / f"{args.prefix}{suffix}"
        if destination.exists() and not args.allow_overwrite:
            raise AgentError(
                "conflict",
                "Split destination exists.",
                path=str(destination),
                suggestion="Pass --allow-overwrite if replacing split outputs is intentional.",
            )
        operations.append(
            {
                "operation": "split",
                "source_path": label,
                "destination": str(destination),
                "index": index,
                "suffix": suffix,
                "bytes": len(chunk),
                "lines": line_count if mode == "lines" else None,
                "dry_run": args.dry_run,
            }
        )
        if not args.dry_run:
            try:
                destination.write_bytes(chunk)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while writing split file.", path=str(destination)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {
        "source_path": label,
        "input_bytes": len(data),
        "mode": mode,
        "chunks": len(operations),
        "dry_run": args.dry_run,
        "operations": operations,
    }


def command_od(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.offset < 0:
        raise AgentError("invalid_input", "--offset must be >= 0.")
    if args.max_bytes < 0:
        raise AgentError("invalid_input", "--max-bytes must be >= 0.")
    if args.bytes_per_line < 1:
        raise AgentError("invalid_input", "--bytes-per-line must be >= 1.")
    inputs = args.paths or ["-"]
    chunks = []
    source_paths = []
    for raw in inputs:
        label, data = read_input_bytes(raw)
        source_paths.append(label)
        chunks.append(data)
    data = b"".join(chunks)
    selected = data[args.offset : args.offset + args.max_bytes]
    truncated = args.offset + len(selected) < len(data)

    def render_byte(value: int) -> str:
        if args.format == "hex":
            return f"{value:02x}"
        if args.format == "octal":
            return f"{value:03o}"
        if args.format == "decimal":
            return f"{value:03d}"
        return chr(value) if 32 <= value <= 126 else "."

    rows = []
    raw_lines = []
    for relative in range(0, len(selected), args.bytes_per_line):
        row_bytes = selected[relative : relative + args.bytes_per_line]
        offset = args.offset + relative
        values = [render_byte(value) for value in row_bytes]
        rows.append({"offset": offset, "offset_hex": f"{offset:06x}", "values": values})
        raw_lines.append(f"{offset:06x} {' '.join(values)}".rstrip())
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    return {
        "source_paths": source_paths,
        "format": args.format,
        "input_bytes": len(data),
        "offset": args.offset,
        "returned_bytes": len(selected),
        "truncated": truncated,
        "rows": rows,
    }


def command_tsort(args: argparse.Namespace) -> dict[str, Any] | bytes:
    sources = read_input_texts(args.paths, encoding=args.encoding)
    tokens: list[str] = []
    for source in sources:
        tokens.extend(source["text"].split())
    if len(tokens) % 2 != 0:
        raise AgentError("invalid_input", "tsort input must contain whitespace-separated node pairs.")

    nodes = set(tokens)
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    indegree = {node: 0 for node in nodes}
    edges = []
    for left, right in zip(tokens[0::2], tokens[1::2]):
        edges.append({"before": left, "after": right})
        if right not in adjacency[left]:
            adjacency[left].add(right)
            indegree[right] += 1

    ready = sorted(node for node, count in indegree.items() if count == 0)
    ordered = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for neighbor in sorted(adjacency[node]):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                ready.append(neighbor)
                ready.sort()

    if len(ordered) != len(nodes):
        cycle_nodes = sorted(node for node, count in indegree.items() if count > 0)
        raise AgentError(
            "conflict",
            "tsort input contains a cycle.",
            details={"cycle_nodes": cycle_nodes},
            suggestion="Remove or break cyclic dependency pairs before sorting.",
        )
    if args.raw:
        return lines_to_raw(ordered, encoding=args.encoding)
    emitted, truncated = bounded_lines(ordered, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "nodes": len(nodes),
        "edges": edges,
        "returned_lines": len(emitted),
        "total_output_lines": len(ordered),
        "truncated": truncated,
        "lines": emitted,
    }


def command_pr(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.width < 1:
        raise AgentError("invalid_input", "--width must be >= 1.")
    if args.page_length < 1:
        raise AgentError("invalid_input", "--page-length must be >= 1.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    output_lines = []
    page = 1
    for start in range(0, len(lines), args.page_length):
        page_lines = lines[start : start + args.page_length]
        if args.header:
            output_lines.append(f"{args.header}  Page {page}")
            output_lines.append("")
        for line in page_lines:
            output_lines.append(line[: args.width])
        page += 1
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    return {
        "source_paths": source_paths,
        "width": args.width,
        "page_length": args.page_length,
        "pages": page - 1 if lines else 0,
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def command_ptx(args: argparse.Namespace) -> dict[str, Any] | bytes:
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    ignore = {item.lower() if args.ignore_case else item for item in args.ignore}
    only = {item.lower() if args.ignore_case else item for item in args.only}
    records = []
    raw_lines = []
    for line_number, line in enumerate(lines, start=1):
        words = re.findall(r"[\w'-]+", line)
        for index, word in enumerate(words):
            key = word.lower() if args.ignore_case else word
            if only and key not in only:
                continue
            if ignore and key in ignore:
                continue
            left = " ".join(words[max(0, index - args.context) : index])
            right = " ".join(words[index + 1 : index + 1 + args.context])
            record = {"keyword": word, "line_number": line_number, "left": left, "right": right, "line": line}
            records.append(record)
            raw_lines.append(f"{left}\t{word}\t{right}".strip())
    records.sort(key=lambda record: (record["keyword"].lower(), record["line_number"]))
    raw_lines = [f"{record['left']}\t{record['keyword']}\t{record['right']}".strip() for record in records]
    if args.raw:
        return lines_to_raw(raw_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": source_paths,
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


def command_uniq(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.repeated and args.unique_only:
        raise AgentError("invalid_input", "--repeated and --unique-only cannot be used together.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    records = []
    current: str | None = None
    current_key: str | None = None
    count = 0
    for line in lines:
        key = line.lower() if args.ignore_case else line
        if current is None:
            current = line
            current_key = key
            count = 1
            continue
        if key == current_key:
            count += 1
            continue
        records.append({"line": current, "count": count})
        current = line
        current_key = key
        count = 1
    if current is not None:
        records.append({"line": current, "count": count})

    if args.repeated:
        records = [record for record in records if record["count"] > 1]
    if args.unique_only:
        records = [record for record in records if record["count"] == 1]

    if args.raw:
        if args.count:
            output_lines = [f"{record['count']}\t{record['line']}" for record in records]
        else:
            output_lines = [record["line"] for record in records]
        return lines_to_raw(output_lines, encoding=args.encoding)

    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": source_paths,
        "input_lines": len(lines),
        "groups": len(records),
        "returned_groups": len(emitted),
        "truncated": truncated,
        "counted": args.count,
        "records": emitted,
    }


def parse_ranges(spec: str) -> list[tuple[int | None, int | None]]:
    ranges = []
    for part in spec.split(","):
        item = part.strip()
        if not item:
            raise AgentError("invalid_input", "Range specification contains an empty item.")
        try:
            if "-" in item:
                start_raw, end_raw = item.split("-", 1)
                start = int(start_raw) if start_raw else None
                end = int(end_raw) if end_raw else None
            else:
                start = int(item)
                end = start
        except ValueError as exc:
            raise AgentError(
                "invalid_input",
                "Range specification must contain positive integers, commas, and hyphens.",
                details={"range": spec},
            ) from exc
        if start is not None and start < 1:
            raise AgentError("invalid_input", "Ranges are 1-based and must be positive.")
        if end is not None and end < 1:
            raise AgentError("invalid_input", "Ranges are 1-based and must be positive.")
        if start is not None and end is not None and start > end:
            raise AgentError("invalid_input", "Range start cannot be greater than range end.")
        ranges.append((start, end))
    return ranges


def selected_indexes(length: int, ranges: list[tuple[int | None, int | None]]) -> list[int]:
    indexes: list[int] = []
    seen = set()
    for start, end in ranges:
        first = 1 if start is None else start
        last = length if end is None else end
        for one_based in range(first, min(last, length) + 1):
            zero_based = one_based - 1
            if zero_based not in seen:
                seen.add(zero_based)
                indexes.append(zero_based)
    return indexes


def cut_line(args: argparse.Namespace, line: str, ranges: list[tuple[int | None, int | None]]) -> str:
    if args.fields:
        fields = line.split(args.delimiter)
        selected = [fields[index] for index in selected_indexes(len(fields), ranges)]
        return args.output_delimiter.join(selected)
    if args.chars:
        chars = list(line)
        selected = [chars[index] for index in selected_indexes(len(chars), ranges)]
        return "".join(selected)
    data = line.encode(args.encoding)
    selected = bytes(data[index] for index in selected_indexes(len(data), ranges))
    return selected.decode(args.encoding, errors="replace")


def command_cut(args: argparse.Namespace) -> dict[str, Any] | bytes:
    ranges = parse_ranges(args.fields or args.chars or args.bytes)
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    output_lines = [cut_line(args, line, ranges) for line in lines]
    if args.raw:
        return lines_to_raw(output_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(output_lines, args.max_lines)
    mode = "fields" if args.fields else "chars" if args.chars else "bytes"
    return {
        "source_paths": source_paths,
        "mode": mode,
        "input_lines": len(lines),
        "returned_lines": len(emitted),
        "total_output_lines": len(output_lines),
        "truncated": truncated,
        "lines": emitted,
    }


def squeeze_repeats(text: str, squeeze_set: set[str]) -> str:
    if not text:
        return text
    output = [text[0]]
    for char in text[1:]:
        if char == output[-1] and char in squeeze_set:
            continue
        output.append(char)
    return "".join(output)


def transform_text(args: argparse.Namespace, text: str) -> str:
    if args.delete:
        output = text.translate({ord(char): None for char in args.set1})
        squeeze_source = args.set1
    else:
        if args.set2 is None:
            raise AgentError("invalid_input", "Translation requires SET2 unless --delete is used.")
        if not args.set2:
            raise AgentError("invalid_input", "SET2 cannot be empty for translation.")
        translation = {}
        for index, char in enumerate(args.set1):
            replacement = args.set2[index] if index < len(args.set2) else args.set2[-1]
            translation[ord(char)] = replacement
        output = text.translate(translation)
        squeeze_source = args.set2
    if args.squeeze_repeats:
        output = squeeze_repeats(output, set(squeeze_source))
    return output


def command_tr(args: argparse.Namespace) -> dict[str, Any] | bytes:
    sources = read_input_texts(args.paths, encoding=args.encoding)
    output = "".join(transform_text(args, source["text"]) for source in sources)
    if args.raw:
        return output.encode(args.encoding)
    lines = output.splitlines()
    emitted, truncated = bounded_lines(lines, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "mode": "delete" if args.delete else "translate",
        "squeeze_repeats": args.squeeze_repeats,
        "returned_lines": len(emitted),
        "total_output_lines": len(lines),
        "truncated": truncated,
        "content": output if not truncated else "\n".join(emitted),
        "lines": emitted,
    }


def command_expand(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.tabs < 1:
        raise AgentError("invalid_input", "--tabs must be >= 1.")
    sources = read_input_texts(args.paths, encoding=args.encoding)
    output = "".join(source["text"].expandtabs(args.tabs) for source in sources)
    if args.raw:
        return output.encode(args.encoding)
    lines = output.splitlines()
    emitted, truncated = bounded_lines(lines, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "tabs": args.tabs,
        "returned_lines": len(emitted),
        "total_output_lines": len(lines),
        "truncated": truncated,
        "content": output if not truncated else "\n".join(emitted),
        "lines": emitted,
    }


def command_unexpand(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.tabs < 1:
        raise AgentError("invalid_input", "--tabs must be >= 1.")
    sources = read_input_texts(args.paths, encoding=args.encoding)
    output_parts = []
    for source in sources:
        lines = source["text"].splitlines(keepends=True)
        output_parts.extend(unexpand_line(line, tab_size=args.tabs, all_blanks=args.all) for line in lines)
    output = "".join(output_parts)
    if args.raw:
        return output.encode(args.encoding)
    lines = output.splitlines()
    emitted, truncated = bounded_lines(lines, args.max_lines)
    return {
        "source_paths": [source["path"] for source in sources],
        "tabs": args.tabs,
        "all": args.all,
        "returned_lines": len(emitted),
        "total_output_lines": len(lines),
        "truncated": truncated,
        "content": output if not truncated else "\n".join(emitted),
        "lines": emitted,
    }


def command_codec(args: argparse.Namespace) -> dict[str, Any] | bytes:
    inputs = args.paths or ["-"]
    chunks = []
    source_paths = []
    for raw in inputs:
        label, data = read_input_bytes(raw)
        source_paths.append(label)
        chunks.append(data)
    data = b"".join(chunks)
    try:
        if args.codec == "base64":
            output = base64.b64decode(b"".join(data.split()), validate=True) if args.decode else base64.b64encode(data)
        elif args.codec == "base32":
            output = base64.b32decode(b"".join(data.split()), casefold=True) if args.decode else base64.b32encode(data)
        else:
            raise AgentError("invalid_input", f"Unsupported codec: {args.codec}")
    except (ValueError, binascii.Error) as exc:
        raise AgentError("invalid_input", f"Invalid {args.codec} input for decoding.") from exc

    if args.raw:
        return output

    if args.max_output_bytes < 0:
        raise AgentError("invalid_input", "--max-output-bytes must be >= 0.")
    truncated = len(output) > args.max_output_bytes
    emitted = output[: args.max_output_bytes]
    result: dict[str, Any] = {
        "source_paths": source_paths,
        "codec": args.codec,
        "operation": "decode" if args.decode else "encode",
        "input_bytes": len(data),
        "output_bytes": len(output),
        "returned_bytes": len(emitted),
        "truncated": truncated,
    }
    if args.decode:
        result["content_base64"] = base64.b64encode(emitted).decode("ascii")
        try:
            result["content_text"] = emitted.decode(args.encoding)
        except UnicodeDecodeError:
            result["content_text"] = None
    else:
        result["content"] = emitted.decode("ascii")
    return result


def command_basenc(args: argparse.Namespace) -> dict[str, Any] | bytes:
    inputs = args.paths or ["-"]
    chunks = []
    source_paths = []
    for raw in inputs:
        label, data = read_input_bytes(raw)
        source_paths.append(label)
        chunks.append(data)
    data = b"".join(chunks)
    compact = b"".join(data.split())
    try:
        if args.base == "base16":
            output = base64.b16decode(compact, casefold=True) if args.decode else base64.b16encode(data)
        elif args.base == "base32":
            output = base64.b32decode(compact, casefold=True) if args.decode else base64.b32encode(data)
        elif args.base == "base64":
            output = base64.b64decode(compact, validate=True) if args.decode else base64.b64encode(data)
        elif args.base == "base64url":
            if args.decode:
                compact += b"=" * ((4 - len(compact) % 4) % 4)
                output = base64.urlsafe_b64decode(compact)
            else:
                output = base64.urlsafe_b64encode(data).rstrip(b"=")
        else:
            raise AgentError("invalid_input", f"Unsupported basenc base: {args.base}")
    except (ValueError, binascii.Error) as exc:
        raise AgentError("invalid_input", f"Invalid {args.base} input for decoding.") from exc

    if args.raw:
        return output
    if args.max_output_bytes < 0:
        raise AgentError("invalid_input", "--max-output-bytes must be >= 0.")
    truncated = len(output) > args.max_output_bytes
    emitted = output[: args.max_output_bytes]
    result: dict[str, Any] = {
        "source_paths": source_paths,
        "base": args.base,
        "operation": "decode" if args.decode else "encode",
        "input_bytes": len(data),
        "output_bytes": len(output),
        "returned_bytes": len(emitted),
        "truncated": truncated,
    }
    if args.decode:
        result["content_base64"] = base64.b64encode(emitted).decode("ascii")
        try:
            result["content_text"] = emitted.decode(args.encoding)
        except UnicodeDecodeError:
            result["content_text"] = None
    else:
        result["content"] = emitted.decode("ascii")
    return result


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


def evaluate_test_predicates(path: Path, predicates: list[str]) -> list[dict[str, Any]]:
    checks = []
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


def command_test(args: argparse.Namespace) -> dict[str, Any]:
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


def command_ln(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.source).expanduser()
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
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
            raise AgentError("permission_denied", "Permission denied while creating link.", path=str(destination)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"operations": [operation]}


def command_link(args: argparse.Namespace) -> dict[str, Any]:
    source = resolve_path(args.source, strict=True)
    if source.is_dir():
        raise AgentError("invalid_input", "Hard-linking directories is not supported.", path=str(source))
    destination = resolve_path(args.destination)
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
            raise AgentError("permission_denied", "Permission denied while creating hard link.", path=str(destination)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"operations": [operation]}


def command_mkfifo(args: argparse.Namespace) -> dict[str, Any]:
    mode = parse_octal_mode(args.mode)
    operations = []
    supported = hasattr(os, "mkfifo")
    for raw in args.paths:
        path = resolve_path(raw)
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
            try:
                os.mkfifo(path, mode)  # type: ignore[attr-defined]
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while creating FIFO.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def resolve_user_id(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    if raw.isdigit():
        return int(raw)
    try:
        import pwd  # type: ignore[import-not-found]

        return pwd.getpwnam(raw).pw_uid
    except ImportError as exc:
        raise AgentError(
            "invalid_input",
            "User name lookup is not supported on this platform; use a numeric uid.",
            details={"owner": raw},
        ) from exc
    except KeyError as exc:
        raise AgentError("invalid_input", "User name was not found.", details={"owner": raw}) from exc


def resolve_group_id(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    if raw.isdigit():
        return int(raw)
    try:
        import grp  # type: ignore[import-not-found]

        return grp.getgrnam(raw).gr_gid
    except ImportError as exc:
        raise AgentError(
            "invalid_input",
            "Group name lookup is not supported on this platform; use a numeric gid.",
            details={"group": raw},
        ) from exc
    except KeyError as exc:
        raise AgentError("invalid_input", "Group name was not found.", details={"group": raw}) from exc


def split_owner_spec(spec: str) -> tuple[str | None, str | None]:
    if ":" in spec:
        owner, group = spec.split(":", 1)
    elif "." in spec:
        owner, group = spec.split(".", 1)
    else:
        owner, group = spec, None
    if owner == "" and group == "":
        raise AgentError("invalid_input", "Owner specification cannot be empty.")
    return owner or None, group or None


def command_chown(args: argparse.Namespace) -> dict[str, Any]:
    owner_raw, group_raw = split_owner_spec(args.owner)
    uid = resolve_user_id(owner_raw)
    gid = resolve_group_id(group_raw)
    if uid is None and gid is None:
        raise AgentError("invalid_input", "chown requires an owner, group, or both.")
    operations = []
    supported = hasattr(os, "chown")
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
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
            try:
                os.chown(path, -1 if uid is None else uid, -1 if gid is None else gid, follow_symlinks=not args.no_follow)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while changing owner.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_chgrp(args: argparse.Namespace) -> dict[str, Any]:
    gid = resolve_group_id(args.group)
    operations = []
    supported = hasattr(os, "chown")
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
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
            try:
                os.chown(path, -1, gid, follow_symlinks=not args.no_follow)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while changing group.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_mknod(args: argparse.Namespace) -> dict[str, Any]:
    mode = parse_octal_mode(args.mode)
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        if path.exists() or path.is_symlink():
            raise AgentError("conflict", "Destination exists.", path=str(path))
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        supported = args.node_type == "regular" or hasattr(os, "mkfifo")
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
                elif args.node_type == "fifo" and hasattr(os, "mkfifo"):
                    os.mkfifo(path, mode)  # type: ignore[attr-defined]
                else:
                    raise AgentError("invalid_input", "Requested node type is not supported on this platform.", path=str(path))
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while creating node.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def parse_octal_mode(raw: str) -> int:
    value = raw.strip()
    if value.startswith("0o"):
        value = value[2:]
    if not value or len(value) > 4 or any(char not in "01234567" for char in value):
        raise AgentError(
            "invalid_input",
            "Only octal chmod modes are supported by this agent-friendly implementation.",
            details={"mode": raw},
            suggestion="Use modes like 644, 755, or 0644.",
        )
    return int(value, 8)


def command_chmod(args: argparse.Namespace) -> dict[str, Any]:
    new_mode = parse_octal_mode(args.mode)
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
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


def command_truncate(args: argparse.Namespace) -> dict[str, Any]:
    if args.size < 0:
        raise AgentError("invalid_input", "--size must be >= 0.")
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
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
                raise AgentError("permission_denied", "Permission denied while truncating file.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def command_mktemp(args: argparse.Namespace) -> dict[str, Any]:
    tmpdir = resolve_path(args.tmpdir or ".", strict=True)
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
        raise AgentError("permission_denied", "Permission denied while creating temporary path.", path=str(tmpdir)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(tmpdir)) from exc
    return {
        "operation": "mktemp",
        "path": str(Path(path).resolve()),
        "directory": args.directory,
        "created": True,
        "dry_run": False,
    }


def command_tee(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.max_preview_bytes < 0:
        raise AgentError("invalid_input", "--max-preview-bytes must be >= 0.")
    data = read_stdin_bytes()
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
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
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
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
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
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
                raise AgentError("permission_denied", "Permission denied while unlinking path.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


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


def command_date(args: argparse.Namespace) -> dict[str, Any] | bytes:
    timestamp = args.timestamp if args.timestamp is not None else time.time()
    timezone = dt.UTC if args.utc else None
    value = dt.datetime.fromtimestamp(timestamp, tz=timezone).astimezone(dt.UTC if args.utc else None)
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


def selected_environment(names: list[str] | None) -> dict[str, str]:
    if not names:
        return dict(sorted(os.environ.items()))
    return {name: os.environ[name] for name in names if name in os.environ}


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


def command_whoami(args: argparse.Namespace) -> dict[str, Any] | bytes:
    user = getpass.getuser()
    if args.raw:
        return (user + "\n").encode("utf-8")
    return {"user": user}


def command_groups(args: argparse.Namespace) -> dict[str, Any] | bytes:
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


def command_id(args: argparse.Namespace) -> dict[str, Any] | bytes:
    user = getpass.getuser()
    result: dict[str, Any] = {"user": user}
    for attr, key in (("getuid", "uid"), ("geteuid", "effective_uid"), ("getgid", "gid"), ("getegid", "effective_gid")):
        func = getattr(os, attr, None)
        result[key] = func() if callable(func) else None
    getgroups = getattr(os, "getgroups", None)
    result["groups"] = getgroups() if callable(getgroups) else []
    if args.raw:
        parts = [f"user={user}"]
        for key in ("uid", "gid", "effective_uid", "effective_gid"):
            if result[key] is not None:
                parts.append(f"{key}={result[key]}")
        return (" ".join(parts) + "\n").encode("utf-8")
    return result


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


def command_arch(args: argparse.Namespace) -> dict[str, Any] | bytes:
    machine = platform.machine() or platform.uname().machine
    if args.raw:
        return (machine + "\n").encode("utf-8")
    return {"machine": machine}


def command_hostname(args: argparse.Namespace) -> dict[str, Any] | bytes:
    name = platform.node()
    if args.raw:
        return (name + "\n").encode("utf-8")
    return {"hostname": name}


def command_hostid(args: argparse.Namespace) -> dict[str, Any] | bytes:
    name = platform.node()
    value = zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF
    value_hex = f"{value:08x}"
    if args.raw:
        return (value_hex + "\n").encode("utf-8")
    return {"hostid": value, "hostid_hex": value_hex, "source": "crc32(hostname)", "hostname": name}


def command_logname(args: argparse.Namespace) -> dict[str, Any] | bytes:
    user = os.environ.get("LOGNAME") or os.environ.get("USER") or os.environ.get("USERNAME") or getpass.getuser()
    if args.raw:
        return (user + "\n").encode("utf-8")
    return {"logname": user}


def system_uptime_seconds() -> float | None:
    proc_uptime = Path("/proc/uptime")
    if proc_uptime.exists():
        try:
            return float(proc_uptime.read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            pass
    try:
        import ctypes

        get_tick_count = ctypes.windll.kernel32.GetTickCount64  # type: ignore[attr-defined]
        get_tick_count.restype = ctypes.c_ulonglong
        return float(get_tick_count()) / 1000.0
    except Exception:
        return None


def command_uptime(args: argparse.Namespace) -> dict[str, Any] | bytes:
    uptime = system_uptime_seconds()
    if uptime is None:
        raise AgentError("invalid_input", "System uptime is not available on this platform.")
    boot_timestamp = time.time() - uptime
    if args.raw:
        return (f"{uptime:.3f}\n").encode("utf-8")
    return {
        "uptime_seconds": uptime,
        "boot_time": utc_iso(boot_timestamp),
        "days": int(uptime // 86400),
    }


def stdin_tty_name() -> str | None:
    if not sys.stdin.isatty():
        return None
    ttyname = getattr(os, "ttyname", None)
    if not callable(ttyname):
        return None
    try:
        return ttyname(sys.stdin.fileno())
    except OSError:
        return None


def command_tty(args: argparse.Namespace) -> dict[str, Any] | bytes:
    is_tty = sys.stdin.isatty()
    name = stdin_tty_name()
    if args.raw:
        return ((name or "not a tty") + "\n").encode("utf-8")
    result: dict[str, Any] = {"stdin_is_tty": is_tty, "tty": name}
    if args.exit_code and not is_tty:
        result["_exit_code"] = EXIT["predicate_false"]
    return result


def active_user_entries() -> list[dict[str, Any]]:
    user = getpass.getuser()
    terminal = stdin_tty_name()
    return [{"user": user, "terminal": terminal, "source": "current_process"}]


def command_users(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = active_user_entries()
    users = sorted({entry["user"] for entry in entries})
    if args.raw:
        return (" ".join(users) + "\n").encode("utf-8")
    return {"count": len(users), "users": users, "entries": entries}


def command_who(args: argparse.Namespace) -> dict[str, Any] | bytes:
    entries = active_user_entries()
    if args.raw:
        lines = [f"{entry['user']} {entry['terminal'] or '-'}" for entry in entries]
        return lines_to_raw(lines, encoding="utf-8")
    return {"count": len(entries), "entries": entries}


def command_nproc(args: argparse.Namespace) -> dict[str, Any] | bytes:
    count = os.cpu_count() or 1
    if args.raw:
        return (str(count) + "\n").encode("utf-8")
    return {"processors": count}


def disk_usage_entry(path: Path) -> dict[str, Any]:
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


def command_df(args: argparse.Namespace) -> dict[str, Any]:
    paths = args.paths or ["."]
    entries = [disk_usage_entry(resolve_path(raw, strict=True)) for raw in paths]
    return {"count": len(entries), "entries": entries}


def directory_size(path: Path, *, max_depth: int, follow_symlinks: bool) -> tuple[int, int, bool]:
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

    output_path = None if args.output == "-" else resolve_path(args.output)
    if output_path is not None:
        ensure_parent(output_path, create=args.parents, dry_run=args.dry_run)
        if output_path.exists() and not args.allow_overwrite and args.seek == 0:
            raise AgentError(
                "conflict",
                "Output file exists.",
                path=str(output_path),
                suggestion="Pass --allow-overwrite if replacing or updating the output is intentional.",
            )
        if not args.dry_run:
            try:
                mode = "r+b" if output_path.exists() and args.seek > 0 else "wb"
                with output_path.open(mode) as handle:
                    handle.seek(args.seek * args.bs)
                    handle.write(selected)
            except PermissionError as exc:
                raise AgentError("permission_denied", "Permission denied while writing output.", path=str(output_path)) from exc
            except OSError as exc:
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
        "dry_run": args.dry_run,
        "content_base64": base64.b64encode(preview).decode("ascii"),
        "returned_preview_bytes": len(preview),
        "truncated": len(preview) < len(selected),
    }


def command_sync(args: argparse.Namespace) -> dict[str, Any]:
    supported = hasattr(os, "sync")
    if not args.dry_run and supported:
        try:
            os.sync()  # type: ignore[attr-defined]
        except OSError as exc:
            raise AgentError("io_error", str(exc)) from exc
    return {"operation": "sync", "supported": supported, "synced": bool(supported and not args.dry_run), "dry_run": args.dry_run}


def command_dircolors(args: argparse.Namespace) -> dict[str, Any] | bytes:
    result = {
        "colors_enabled": False,
        "ls_colors": "",
        "reason": "agentutils disables color by default to keep output machine-readable.",
    }
    if args.raw:
        shell = args.shell
        if shell in ("bash", "zsh", "sh"):
            return b"LS_COLORS=''; export LS_COLORS\n"
        if shell == "fish":
            return b"set -gx LS_COLORS ''\n"
        return b"LS_COLORS=\n"
    return result


def command_seq(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if len(args.numbers) == 1:
        first = 1.0
        increment = args.increment
        last = args.numbers[0]
    elif len(args.numbers) == 2:
        first = args.numbers[0]
        increment = args.increment
        last = args.numbers[1]
    elif len(args.numbers) == 3:
        first, increment, last = args.numbers
    else:
        raise AgentError("invalid_input", "seq accepts [FIRST [INCREMENT]] LAST.")
    if increment == 0:
        raise AgentError("invalid_input", "--increment cannot be 0.")
    if args.max_items < 0:
        raise AgentError("invalid_input", "--max-items must be >= 0.")
    values = []
    current = first
    forward = increment > 0
    while (current <= last if forward else current >= last) and len(values) < args.max_items:
        values.append(current)
        current += increment
    would_continue = current <= last if forward else current >= last

    def format_value(value: float) -> str:
        if args.format:
            try:
                return args.format % value
            except (TypeError, ValueError) as exc:
                raise AgentError("invalid_input", "Invalid printf-style --format for seq.") from exc
        return str(int(value)) if value == int(value) else str(value)

    lines = [format_value(value) for value in values]
    if args.raw:
        return (args.separator.join(lines) + ("\n" if lines else "")).encode("utf-8")
    return {
        "first": first,
        "increment": increment,
        "last": last,
        "count": len(values),
        "truncated": would_continue,
        "values": values,
        "lines": lines,
    }


def command_printf(args: argparse.Namespace) -> dict[str, Any] | bytes:
    output = format_printf(args.format_string, args.values)
    data = output.encode(args.encoding)
    if args.raw:
        return data
    return {
        "format": args.format_string,
        "values": args.values,
        "encoding": args.encoding,
        "bytes": len(data),
        "content": output,
    }


def command_echo(args: argparse.Namespace) -> dict[str, Any] | bytes:
    text = " ".join(args.words)
    if args.escapes:
        text = decode_standard_escapes(text)
    ending = "" if args.no_newline else "\n"
    data = (text + ending).encode(args.encoding)
    if args.raw:
        return data
    return {
        "words": args.words,
        "text": text,
        "newline": not args.no_newline,
        "escapes": args.escapes,
        "encoding": args.encoding,
        "bytes": len(data),
    }


SI_UNITS = {"": 1.0, "K": 1000.0, "M": 1000.0**2, "G": 1000.0**3, "T": 1000.0**4, "P": 1000.0**5, "E": 1000.0**6}
IEC_UNITS = {"": 1.0, "K": 1024.0, "M": 1024.0**2, "G": 1024.0**3, "T": 1024.0**4, "P": 1024.0**5, "E": 1024.0**6}


def parse_numfmt_value(raw: str, unit_system: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))([A-Za-z]*)", raw.strip())
    if not match:
        raise AgentError("invalid_input", "numfmt input must be a number with an optional unit suffix.", details={"value": raw})
    value = float(match.group(1))
    suffix = match.group(2)
    if unit_system == "none":
        if suffix:
            raise AgentError("invalid_input", "Unit suffix was provided but --from-unit is none.", details={"value": raw})
        return value
    normalized = suffix.upper().removesuffix("B")
    if unit_system == "iec":
        normalized = normalized.removesuffix("I")
    units = SI_UNITS if unit_system == "si" else IEC_UNITS
    if normalized not in units:
        raise AgentError(
            "invalid_input",
            "Unsupported numfmt unit suffix.",
            details={"value": raw, "suffix": suffix, "unit_system": unit_system},
        )
    return value * units[normalized]


def format_numfmt_value(value: float, unit_system: str, precision: int) -> str:
    if precision < 0:
        raise AgentError("invalid_input", "--precision must be >= 0.")
    if unit_system == "none":
        formatted = f"{value:.{precision}f}"
        return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted
    units = SI_UNITS if unit_system == "si" else IEC_UNITS
    suffixes = ["", "K", "M", "G", "T", "P", "E"]
    suffix = ""
    scaled = value
    for candidate in suffixes:
        factor = units[candidate]
        if abs(value) >= factor:
            suffix = candidate
            scaled = value / factor
    formatted = f"{scaled:.{precision}f}".rstrip("0").rstrip(".")
    if unit_system == "iec" and suffix:
        suffix = f"{suffix}i"
    return f"{formatted}{suffix}"


def command_numfmt(args: argparse.Namespace) -> dict[str, Any] | bytes:
    raw_values = args.numbers or sys.stdin.read().split()
    records = []
    raw_lines = []
    for raw in raw_values:
        value = parse_numfmt_value(raw, args.from_unit)
        formatted = format_numfmt_value(value, args.to_unit, args.precision)
        records.append({"input": raw, "value": value, "output": formatted})
        raw_lines.append(formatted)
    if args.raw:
        return lines_to_raw(raw_lines, encoding="utf-8")
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "from_unit": args.from_unit,
        "to_unit": args.to_unit,
        "precision": args.precision,
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


def prime_factors(value: int) -> list[int]:
    factors = []
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


def safe_eval_expr_node(node: ast.AST) -> object:
    if isinstance(node, ast.Expression):
        return safe_eval_expr_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str, bool)):
            return node.value
        raise AgentError("invalid_input", "Unsupported expression literal.")
    if isinstance(node, ast.UnaryOp):
        operand = safe_eval_expr_node(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand  # type: ignore[operator]
        if isinstance(node.op, ast.UAdd):
            return +operand  # type: ignore[operator]
        if isinstance(node.op, ast.Not):
            return not bool(operand)
    if isinstance(node, ast.BinOp):
        left = safe_eval_expr_node(node.left)
        right = safe_eval_expr_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right  # type: ignore[operator]
        if isinstance(node.op, ast.Sub):
            return left - right  # type: ignore[operator]
        if isinstance(node.op, ast.Mult):
            return left * right  # type: ignore[operator]
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise AgentError("invalid_input", "Division by zero.")
            return left / right  # type: ignore[operator]
        if isinstance(node.op, ast.FloorDiv):
            if right == 0:
                raise AgentError("invalid_input", "Division by zero.")
            return left // right  # type: ignore[operator]
        if isinstance(node.op, ast.Mod):
            if right == 0:
                raise AgentError("invalid_input", "Modulo by zero.")
            return left % right  # type: ignore[operator]
    if isinstance(node, ast.Compare):
        left = safe_eval_expr_node(node.left)
        for operator_node, comparator in zip(node.ops, node.comparators):
            right = safe_eval_expr_node(comparator)
            if isinstance(operator_node, ast.Eq):
                ok = left == right
            elif isinstance(operator_node, ast.NotEq):
                ok = left != right
            elif isinstance(operator_node, ast.Lt):
                ok = left < right  # type: ignore[operator]
            elif isinstance(operator_node, ast.LtE):
                ok = left <= right  # type: ignore[operator]
            elif isinstance(operator_node, ast.Gt):
                ok = left > right  # type: ignore[operator]
            elif isinstance(operator_node, ast.GtE):
                ok = left >= right  # type: ignore[operator]
            else:
                raise AgentError("invalid_input", "Unsupported expression comparison.")
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [bool(safe_eval_expr_node(value)) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    raise AgentError("invalid_input", "Unsupported expression syntax.")


def expression_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


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


def path_issues(raw: str, *, max_path_length: int, max_component_length: int, portable: bool) -> list[str]:
    issues = []
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


def command_true(args: argparse.Namespace) -> dict[str, Any]:
    return {"value": True}


def command_false(args: argparse.Namespace) -> dict[str, Any]:
    return {"value": False, "_exit_code": EXIT["predicate_false"]}


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
        time.sleep(args.seconds)
    return {"seconds": args.seconds, "slept": not args.dry_run, "dry_run": args.dry_run}


def normalize_command_args(raw: list[str]) -> list[str]:
    command = list(raw)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise AgentError("invalid_input", "A command is required.")
    return command


def run_subprocess_capture(command: list[str], *, timeout: float | None, max_output_bytes: int, env: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess[bytes] | None, bool]:
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


def subprocess_result(command: list[str], completed: subprocess.CompletedProcess[bytes], *, timed_out: bool, max_output_bytes: int) -> dict[str, Any]:
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


def parse_signal(raw: str) -> int:
    value = raw.upper()
    if value.isdigit():
        return int(value)
    if not value.startswith("SIG"):
        value = f"SIG{value}"
    signum = getattr(signal, value, None)
    if signum is None:
        raise AgentError("invalid_input", "Unknown signal.", details={"signal": raw})
    return int(signum)


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


def command_yes(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.count < 0:
        raise AgentError("invalid_input", "--count must be >= 0.")
    line = " ".join(args.words) if args.words else "y"
    lines = [line] * args.count
    if args.raw:
        return lines_to_raw(lines, encoding="utf-8")
    return {"line": line, "count": args.count, "lines": lines}


def command_mkdir(args: argparse.Namespace) -> dict[str, Any]:
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
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
    operations = []
    for raw in args.paths:
        path = resolve_path(raw)
        existed = path.exists()
        ensure_parent(path, create=args.parents, dry_run=args.dry_run)
        operations.append({"operation": "touch", "path": str(path), "created": not existed, "dry_run": args.dry_run})
        if not args.dry_run:
            path.touch(exist_ok=True)
    return {"count": len(operations), "operations": operations}


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
    requested_destination = resolve_path(args.paths[1])
    destination = destination_inside_directory(source, requested_destination)
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
            raise AgentError("permission_denied", "Permission denied while installing file.", path=str(destination)) from exc
        except OSError as exc:
            raise AgentError("io_error", str(exc), path=str(destination)) from exc
    return {"count": len(operations), "operations": operations}


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


def command_cp(args: argparse.Namespace) -> dict[str, Any]:
    source = resolve_path(args.source, strict=True)
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
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
    source = resolve_path(args.source, strict=True)
    requested_destination = resolve_path(args.destination)
    destination = destination_inside_directory(source, requested_destination)
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


def remove_one(path: Path, *, recursive: bool, force: bool) -> str:
    try:
        if path.is_dir() and not path.is_symlink():
            if not recursive:
                raise AgentError(
                    "invalid_input",
                    "Path is a directory; recursive removal requires --recursive.",
                    path=str(path),
                )
            shutil.rmtree(path)
            return "directory_removed"
        path.unlink()
        return "file_removed"
    except FileNotFoundError as exc:
        if force:
            return "missing_ignored"
        raise AgentError("not_found", "Path does not exist.", path=str(path)) from exc
    except PermissionError as exc:
        raise AgentError("permission_denied", "Permission denied while removing path.", path=str(path)) from exc
    except OSError as exc:
        raise AgentError("io_error", str(exc), path=str(path)) from exc


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
        if path.is_dir() and not path.is_symlink():
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
    operations = []
    for raw in args.paths:
        path = resolve_path(raw, strict=True)
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
                chunk = b"\0" * min(size, 1024 * 1024)
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
                raise AgentError("permission_denied", "Permission denied while shredding file.", path=str(path)) from exc
            except OSError as exc:
                raise AgentError("io_error", str(exc), path=str(path)) from exc
    return {"count": len(operations), "operations": operations}


def build_parser() -> argparse.ArgumentParser:
    parser = AgentArgumentParser(
        prog="agentutils",
        description="Agent-friendly CLI layer inspired by GNU Coreutils. Outputs JSON by default.",
        epilog=(
            "Examples:\n"
            "  python -m agentutils catalog --pretty\n"
            "  python -m agentutils ls . --recursive --max-depth 1\n"
            "  python -m agentutils cat README.md --max-bytes 4096\n"
            "  python -m agentutils rm build --recursive --dry-run\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"agentutils {__version__}")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=AgentArgumentParser)

    p = sub.add_parser("catalog", help="List prioritized GNU Coreutils categories for agents.")
    p.set_defaults(func=command_catalog)

    p = sub.add_parser("schema", help="Print the agentutils JSON protocol and exit codes.")
    p.set_defaults(func=command_schema)

    p = sub.add_parser("pwd", help="Print the current working directory as JSON.")
    p.set_defaults(func=command_pwd)

    p = sub.add_parser("basename", help="Return final path components.")
    p.add_argument("paths", nargs="+", help="Paths to transform.")
    p.add_argument("--suffix", help="Remove suffix from each basename when present.")
    p.add_argument("--raw", action="store_true", help="Write one basename per line without a JSON envelope.")
    p.set_defaults(func=command_basename)

    p = sub.add_parser("dirname", help="Return parent path components.")
    p.add_argument("paths", nargs="+", help="Paths to transform.")
    p.add_argument("--raw", action="store_true", help="Write one dirname per line without a JSON envelope.")
    p.set_defaults(func=command_dirname)

    p = sub.add_parser("realpath", help="Resolve paths deterministically.")
    p.add_argument("paths", nargs="+", help="Paths to resolve.")
    p.add_argument("--strict", action="store_true", help="Fail if any path does not exist.")
    p.set_defaults(func=command_realpath)

    p = sub.add_parser("readlink", help="Read symbolic link targets or canonicalize paths.")
    p.add_argument("paths", nargs="+", help="Symlinks to inspect, or paths to canonicalize.")
    p.add_argument("--canonicalize", "-f", action="store_true", help="Return canonical resolved paths.")
    p.add_argument("--strict", action="store_true", help="With --canonicalize, fail if a path does not exist.")
    p.add_argument("--raw", action="store_true", help="Write one target/path per line without a JSON envelope.")
    p.set_defaults(func=command_readlink)

    p = sub.add_parser("test", help="Evaluate path predicates as structured JSON.")
    p.add_argument("path", help="Path to test.")
    p.add_argument("--exists", "-e", action="store_true", help="Path exists. This is the default predicate.")
    p.add_argument("--file", "-f", action="store_true", help="Path is a regular file.")
    p.add_argument("--directory", "-d", action="store_true", help="Path is a directory.")
    p.add_argument("--symlink", "-L", action="store_true", help="Path is a symbolic link.")
    p.add_argument("--readable", "-r", action="store_true", help="Path is readable.")
    p.add_argument("--writable", "-w", action="store_true", help="Path is writable.")
    p.add_argument("--executable", "-x", action="store_true", help="Path is executable.")
    p.add_argument("--empty", action="store_true", help="Path is an empty regular file.")
    p.add_argument("--non-empty", "-s", action="store_true", help="Path is a non-empty regular file.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when predicates do not match.")
    p.set_defaults(func=command_test)

    p = sub.add_parser("[", help="Evaluate a small test/[ expression subset.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when the expression is false.")
    p.add_argument("-e", dest="bracket_exists", action="store_true", help="Path exists.")
    p.add_argument("-f", dest="bracket_file", action="store_true", help="Path is a file.")
    p.add_argument("-d", dest="bracket_directory", action="store_true", help="Path is a directory.")
    p.add_argument("-L", dest="bracket_symlink", action="store_true", help="Path is a symlink.")
    p.add_argument("-r", dest="bracket_readable", action="store_true", help="Path is readable.")
    p.add_argument("-w", dest="bracket_writable", action="store_true", help="Path is writable.")
    p.add_argument("-x", dest="bracket_executable", action="store_true", help="Path is executable.")
    p.add_argument("-s", dest="bracket_non_empty", action="store_true", help="Path is non-empty.")
    p.add_argument("tokens", nargs=argparse.REMAINDER, help="Expression tokens, optionally ending with ']'.")
    p.set_defaults(func=command_bracket)

    p = sub.add_parser("ls", help="List files as structured JSON.")
    p.add_argument("path", nargs="?", default=".", help="File or directory to list.")
    p.add_argument("--recursive", action="store_true", help="Recurse into directories.")
    p.add_argument("--max-depth", type=int, default=2, help="Maximum recursive depth.")
    p.add_argument("--include-hidden", action="store_true", help="Include names starting with '.'.")
    p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
    p.add_argument("--limit", type=int, default=1000, help="Maximum entries to emit.")
    p.set_defaults(func=command_ls)

    for command_name, func in (("dir", command_dir), ("vdir", command_vdir)):
        p = sub.add_parser(command_name, help=f"{command_name} alias for structured directory listing.")
        p.add_argument("path", nargs="?", default=".", help="File or directory to list.")
        p.add_argument("--recursive", action="store_true", help="Recurse into directories.")
        p.add_argument("--max-depth", type=int, default=2, help="Maximum recursive depth.")
        p.add_argument("--include-hidden", action="store_true", help="Include names starting with '.'.")
        p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
        p.add_argument("--limit", type=int, default=1000, help="Maximum entries to emit.")
        p.set_defaults(func=func)

    p = sub.add_parser("stat", help="Return metadata for paths as JSON.")
    p.add_argument("paths", nargs="+", help="Paths to inspect.")
    p.set_defaults(func=command_stat)

    p = sub.add_parser("cat", help="Read a file with bounded JSON output by default.")
    p.add_argument("path", help="File to read.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for JSON content.")
    p.add_argument("--max-bytes", type=int, default=1024 * 1024, help="Maximum bytes to return.")
    p.add_argument("--offset", type=int, default=0, help="Byte offset to start reading from.")
    p.add_argument("--raw", action="store_true", help="Write raw bytes to stdout without a JSON envelope.")
    p.set_defaults(func=command_cat)

    for name, func in (("head", command_head), ("tail", command_tail)):
        p = sub.add_parser(name, help=f"Return {name} lines as JSON.")
        p.add_argument("path", help="File to read.")
        p.add_argument("--lines", "-n", type=int, default=10, help="Number of lines.")
        p.add_argument("--encoding", default="utf-8", help="Text encoding.")
        p.set_defaults(func=func)

    p = sub.add_parser("wc", help="Count bytes, chars, lines, and words as JSON.")
    p.add_argument("paths", nargs="+", help="Files to count, or '-' for stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for char/word counts.")
    p.set_defaults(func=command_wc)

    hash_commands = {
        "md5sum": "md5",
        "sha1sum": "sha1",
        "sha224sum": "sha224",
        "sha256sum": "sha256",
        "sha384sum": "sha384",
        "sha512sum": "sha512",
        "b2sum": "b2sum",
    }
    for command_name, algorithm in hash_commands.items():
        p = sub.add_parser(command_name, help=f"Hash files as JSON using {algorithm}.")
        p.add_argument("paths", nargs="+", help="Files to hash, or '-' for stdin.")
        p.set_defaults(func=command_hash, algorithm=algorithm)

    p = sub.add_parser("hash", help="Hash files as JSON.")
    p.add_argument("paths", nargs="+", help="Files to hash, or '-' for stdin.")
    p.add_argument("--algorithm", default="sha256", choices=sorted(HASH_ALGORITHMS), help="Hash algorithm.")
    p.set_defaults(func=command_hash)

    p = sub.add_parser("cksum", help="Return CRC32 checksums for files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to checksum, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--raw", action="store_true", help="Write checksum size path lines without a JSON envelope.")
    p.set_defaults(func=command_cksum)

    p = sub.add_parser("sum", help="Return simple 16-bit byte sums for files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to checksum, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--block-size", type=int, default=1024, help="Block size used for reported block counts.")
    p.add_argument("--raw", action="store_true", help="Write checksum blocks path lines without a JSON envelope.")
    p.set_defaults(func=command_sum)

    p = sub.add_parser("sort", help="Sort text lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to sort, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--reverse", "-r", action="store_true", help="Reverse the sort order.")
    p.add_argument("--unique", "-u", action="store_true", help="Emit only the first of equal sorted lines.")
    p.add_argument("--numeric", "-n", action="store_true", help="Sort by the first numeric token.")
    p.add_argument("--ignore-case", "-f", action="store_true", help="Compare case-insensitively.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_sort)

    p = sub.add_parser("comm", help="Compare two sorted files and return column-tagged records.")
    p.add_argument("paths", nargs=2, help="Two files to compare.")
    p.add_argument("--suppress-1", action="store_true", help="Suppress records unique to the first file.")
    p.add_argument("--suppress-2", action="store_true", help="Suppress records unique to the second file.")
    p.add_argument("--suppress-3", action="store_true", help="Suppress records common to both files.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write column-tab-line text without a JSON envelope.")
    p.set_defaults(func=command_comm)

    p = sub.add_parser("join", help="Join two files on a selected field.")
    p.add_argument("paths", nargs=2, help="Two files to join.")
    p.add_argument("--field1", type=int, default=1, help="1-based join field for the first file.")
    p.add_argument("--field2", type=int, default=1, help="1-based join field for the second file.")
    p.add_argument("--delimiter", help="Input delimiter. Defaults to any whitespace.")
    p.add_argument("--output-delimiter", default=" ", help="Delimiter for output fields.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write joined text without a JSON envelope.")
    p.set_defaults(func=command_join)

    p = sub.add_parser("paste", help="Merge corresponding lines from files.")
    p.add_argument("paths", nargs="*", help="Files to merge, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--delimiter", "-d", default="\t", help="Delimiter inserted between columns.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write pasted text without a JSON envelope.")
    p.set_defaults(func=command_paste)

    p = sub.add_parser("shuf", help="Shuffle input lines with an optional deterministic seed.")
    p.add_argument("paths", nargs="*", help="Files to shuffle, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--count", "-n", type=int, help="Maximum lines to output.")
    p.add_argument("--seed", type=int, help="Seed for deterministic shuffling.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write shuffled text without a JSON envelope.")
    p.set_defaults(func=command_shuf)

    p = sub.add_parser("tac", help="Reverse input lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to reverse, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write reversed text without a JSON envelope.")
    p.set_defaults(func=command_tac)

    p = sub.add_parser("nl", help="Number input lines with a deterministic subset of GNU nl.")
    p.add_argument("paths", nargs="*", help="Files to number, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--number-blank", action="store_true", help="Also number blank lines.")
    p.add_argument("--start", type=int, default=1, help="Starting line number.")
    p.add_argument("--increment", type=int, default=1, help="Line number increment.")
    p.add_argument("--width", type=int, default=6, help="Minimum number width.")
    p.add_argument("--separator", "-s", default="\t", help="Separator between number and line.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write numbered text without a JSON envelope.")
    p.set_defaults(func=command_nl)

    p = sub.add_parser("fold", help="Wrap long input lines to a fixed width.")
    p.add_argument("paths", nargs="*", help="Files to fold, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=80, help="Maximum line width.")
    p.add_argument("--break-words", "-b", action="store_true", help="Break words longer than the width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write folded text without a JSON envelope.")
    p.set_defaults(func=command_fold)

    p = sub.add_parser("fmt", help="Reflow paragraphs to a fixed width.")
    p.add_argument("paths", nargs="*", help="Files to format, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=75, help="Maximum output line width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write formatted text without a JSON envelope.")
    p.set_defaults(func=command_fmt)

    p = sub.add_parser("csplit", help="Split input at regex matches with dry-run and overwrite protection.")
    p.add_argument("path", help="File to split, or '-' for stdin.")
    p.add_argument("--pattern", required=True, help="Regular expression; each match starts a new chunk.")
    p.add_argument("--prefix", default="xx", help="Output file prefix.")
    p.add_argument("--suffix-length", "-n", type=int, default=2, help="Numeric suffix length.")
    p.add_argument("--max-splits", type=int, default=0, help="Maximum regex matches to split at; 0 means all.")
    p.add_argument("--output-dir", default=".", help="Directory for split outputs.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing existing outputs.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--dry-run", action="store_true", help="Report split outputs without writing files.")
    p.set_defaults(func=command_csplit)

    p = sub.add_parser("split", help="Split input into files with dry-run and overwrite protection.")
    p.add_argument("path", nargs="?", default="-", help="File to split, or '-' for stdin. Defaults to stdin.")
    split_mode = p.add_mutually_exclusive_group()
    split_mode.add_argument("--lines", "-l", type=int, help="Lines per output file. Defaults to 1000.")
    split_mode.add_argument("--bytes", "-b", type=int, help="Bytes per output file.")
    p.add_argument("--prefix", default="x", help="Output file prefix.")
    p.add_argument("--suffix-length", "-a", type=int, default=2, help="Suffix length.")
    p.add_argument("--numeric-suffixes", "-d", action="store_true", help="Use numeric suffixes instead of aa/ab.")
    p.add_argument("--output-dir", default=".", help="Directory for split outputs.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing existing split outputs.")
    p.add_argument("--dry-run", action="store_true", help="Report split outputs without writing files.")
    p.set_defaults(func=command_split)

    p = sub.add_parser("od", help="Dump input bytes as structured rows.")
    p.add_argument("paths", nargs="*", help="Files to dump, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--format", choices=["hex", "octal", "decimal", "char"], default="hex", help="Byte rendering format.")
    p.add_argument("--offset", "-j", type=int, default=0, help="Start offset in bytes.")
    p.add_argument("--max-bytes", "-N", type=int, default=1024, help="Maximum bytes to dump.")
    p.add_argument("--bytes-per-line", type=int, default=16, help="Bytes per output row.")
    p.add_argument("--raw", action="store_true", help="Write dump rows without a JSON envelope.")
    p.set_defaults(func=command_od)

    p = sub.add_parser("numfmt", help="Convert numbers between plain, SI, and IEC units.")
    p.add_argument("numbers", nargs="*", help="Numbers to convert. Defaults to whitespace tokens from stdin.")
    p.add_argument("--from-unit", choices=["none", "si", "iec"], default="none", help="Input unit system.")
    p.add_argument("--to-unit", choices=["none", "si", "iec"], default="none", help="Output unit system.")
    p.add_argument("--precision", type=int, default=3, help="Digits after the decimal point before trimming zeros.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write converted numbers without a JSON envelope.")
    p.set_defaults(func=command_numfmt)

    p = sub.add_parser("tsort", help="Topologically sort whitespace-separated dependency pairs.")
    p.add_argument("paths", nargs="*", help="Files to sort, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write sorted nodes without a JSON envelope.")
    p.set_defaults(func=command_tsort)

    p = sub.add_parser("pr", help="Paginate text into deterministic pages.")
    p.add_argument("paths", nargs="*", help="Files to paginate, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=72, help="Maximum output line width.")
    p.add_argument("--page-length", "-l", type=int, default=66, help="Input lines per page.")
    p.add_argument("--header", help="Optional page header.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write paginated text without a JSON envelope.")
    p.set_defaults(func=command_pr)

    p = sub.add_parser("ptx", help="Build a simple permuted index from input text.")
    p.add_argument("paths", nargs="*", help="Files to index, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--context", type=int, default=3, help="Words of left/right context.")
    p.add_argument("--ignore", action="append", default=[], help="Ignore a keyword. Repeatable.")
    p.add_argument("--only", action="append", default=[], help="Only include this keyword. Repeatable.")
    p.add_argument("--ignore-case", action="store_true", help="Compare filters case-insensitively.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write index rows without a JSON envelope.")
    p.set_defaults(func=command_ptx)

    p = sub.add_parser("uniq", help="Collapse adjacent duplicate lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--count", "-c", action="store_true", help="Include duplicate counts in raw output.")
    p.add_argument("--repeated", "-d", action="store_true", help="Emit only repeated groups.")
    p.add_argument("--unique-only", "-u", action="store_true", help="Emit only non-repeated groups.")
    p.add_argument("--ignore-case", "-i", action="store_true", help="Compare case-insensitively.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON groups to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_uniq)

    p = sub.add_parser("cut", help="Select fields, characters, or bytes from each input line.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    selector = p.add_mutually_exclusive_group(required=True)
    selector.add_argument("--fields", "-f", help="1-based field ranges like '1,3-5'.")
    selector.add_argument("--chars", "-c", help="1-based character ranges like '1,3-5'.")
    selector.add_argument("--bytes", "-b", help="1-based byte ranges like '1,3-5'.")
    p.add_argument("--delimiter", "-d", default="\t", help="Field delimiter.")
    p.add_argument("--output-delimiter", default="\t", help="Delimiter for selected fields.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_cut)

    p = sub.add_parser("tr", help="Translate or delete literal characters from files or stdin.")
    p.add_argument("set1", help="Literal source/delete character set. GNU bracket/range syntax is not expanded.")
    p.add_argument("set2", nargs="?", help="Literal replacement character set for translation.")
    p.add_argument("--path", dest="paths", action="append", default=[], help="Input file. Repeat for multiple files.")
    p.add_argument("--delete", "-d", action="store_true", help="Delete characters in SET1.")
    p.add_argument("--squeeze-repeats", "-s", action="store_true", help="Squeeze repeated output characters.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_tr)

    p = sub.add_parser("expand", help="Convert tabs to spaces in files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--tabs", "-t", type=int, default=8, help="Tab stop width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write expanded text without a JSON envelope.")
    p.set_defaults(func=command_expand)

    p = sub.add_parser("unexpand", help="Convert spaces to tabs in files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--tabs", "-t", type=int, default=8, help="Tab stop width.")
    p.add_argument("--all", "-a", action="store_true", help="Convert all blank runs, not only leading spaces.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=10000, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write unexpanded text without a JSON envelope.")
    p.set_defaults(func=command_unexpand)

    for command_name in ("base64", "base32"):
        p = sub.add_parser(command_name, help=f"Encode or decode {command_name} data.")
        p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
        p.add_argument("--decode", "-d", action="store_true", help="Decode instead of encode.")
        p.add_argument("--encoding", default="utf-8", help="Text encoding for decoded JSON preview.")
        p.add_argument("--max-output-bytes", type=int, default=1024 * 1024, help="Maximum JSON bytes to emit.")
        p.add_argument("--raw", action="store_true", help="Write raw encoded/decoded bytes to stdout.")
        p.set_defaults(func=command_codec, codec=command_name)

    p = sub.add_parser("basenc", help="Encode or decode base16/base32/base64/base64url data.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--base", choices=["base16", "base32", "base64", "base64url"], default="base64", help="Base encoding.")
    p.add_argument("--decode", "-d", action="store_true", help="Decode instead of encode.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for decoded JSON preview.")
    p.add_argument("--max-output-bytes", type=int, default=1024 * 1024, help="Maximum JSON bytes to emit.")
    p.add_argument("--raw", action="store_true", help="Write raw encoded/decoded bytes to stdout.")
    p.set_defaults(func=command_basenc)

    p = sub.add_parser("date", help="Return current or supplied time as structured JSON.")
    p.add_argument("--timestamp", type=float, help="Unix timestamp to format instead of current time.")
    p.add_argument("--utc", "-u", action="store_true", help="Use UTC.")
    p.add_argument("--iso-8601", choices=["seconds", "date"], default="seconds", help="ISO output precision.")
    p.add_argument("--format", help="strftime format string.")
    p.add_argument("--raw", action="store_true", help="Write formatted time without a JSON envelope.")
    p.set_defaults(func=command_date)

    p = sub.add_parser("env", help="Return environment variables as JSON.")
    p.add_argument("names", nargs="*", help="Optional variable names to include.")
    p.add_argument("--raw", action="store_true", help="Write KEY=VALUE lines without a JSON envelope.")
    p.set_defaults(func=command_env)

    p = sub.add_parser("printenv", help="Return selected environment variables.")
    p.add_argument("names", nargs="*", help="Optional variable names to print.")
    p.add_argument("--raw", action="store_true", help="Write values or KEY=VALUE lines without a JSON envelope.")
    p.set_defaults(func=command_printenv)

    p = sub.add_parser("whoami", help="Return the current user.")
    p.add_argument("--raw", action="store_true", help="Write the user name without a JSON envelope.")
    p.set_defaults(func=command_whoami)

    p = sub.add_parser("groups", help="Return group ids/names where the platform exposes them.")
    p.add_argument("user", nargs="?", help="User name label for the result. Current user by default.")
    p.add_argument("--raw", action="store_true", help="Write group names/ids without a JSON envelope.")
    p.set_defaults(func=command_groups)

    p = sub.add_parser("id", help="Return current user and numeric identity information where available.")
    p.add_argument("--raw", action="store_true", help="Write compact identity text without a JSON envelope.")
    p.set_defaults(func=command_id)

    p = sub.add_parser("uname", help="Return platform information.")
    p.add_argument("--raw", action="store_true", help="Write uname-like text without a JSON envelope.")
    p.set_defaults(func=command_uname)

    p = sub.add_parser("arch", help="Return machine architecture.")
    p.add_argument("--raw", action="store_true", help="Write architecture without a JSON envelope.")
    p.set_defaults(func=command_arch)

    p = sub.add_parser("hostname", help="Return the host name.")
    p.add_argument("--raw", action="store_true", help="Write hostname without a JSON envelope.")
    p.set_defaults(func=command_hostname)

    p = sub.add_parser("hostid", help="Return a deterministic host identifier derived from hostname.")
    p.add_argument("--raw", action="store_true", help="Write host id hex without a JSON envelope.")
    p.set_defaults(func=command_hostid)

    p = sub.add_parser("logname", help="Return the login/user name label.")
    p.add_argument("--raw", action="store_true", help="Write logname without a JSON envelope.")
    p.set_defaults(func=command_logname)

    p = sub.add_parser("uptime", help="Return system uptime where available.")
    p.add_argument("--raw", action="store_true", help="Write uptime seconds without a JSON envelope.")
    p.set_defaults(func=command_uptime)

    p = sub.add_parser("tty", help="Report whether stdin is attached to a TTY.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when stdin is not a TTY.")
    p.add_argument("--raw", action="store_true", help="Write tty path or 'not a tty' without a JSON envelope.")
    p.set_defaults(func=command_tty)

    p = sub.add_parser("users", help="Return current active user labels known to this process.")
    p.add_argument("--raw", action="store_true", help="Write users without a JSON envelope.")
    p.set_defaults(func=command_users)

    p = sub.add_parser("who", help="Return current process user/session information.")
    p.add_argument("--raw", action="store_true", help="Write who-like rows without a JSON envelope.")
    p.set_defaults(func=command_who)

    p = sub.add_parser("nproc", help="Return available processor count.")
    p.add_argument("--raw", action="store_true", help="Write the processor count without a JSON envelope.")
    p.set_defaults(func=command_nproc)

    p = sub.add_parser("df", help="Return filesystem usage for paths.")
    p.add_argument("paths", nargs="*", help="Paths to inspect. Defaults to current directory.")
    p.set_defaults(func=command_df)

    p = sub.add_parser("du", help="Return recursive apparent disk usage for paths.")
    p.add_argument("paths", nargs="*", help="Paths to measure. Defaults to current directory.")
    p.add_argument("--max-depth", type=int, default=8, help="Maximum recursion depth.")
    p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
    p.set_defaults(func=command_du)

    p = sub.add_parser("dd", help="Copy bytes between files/stdin/stdout with bounded JSON reporting.")
    p.add_argument("--input", "-i", default="-", help="Input file, or '-' for stdin.")
    p.add_argument("--output", "-o", default="-", help="Output file, or '-' for stdout/no file output.")
    p.add_argument("--bs", type=int, default=512, help="Block size in bytes.")
    p.add_argument("--count", type=int, help="Number of input blocks to copy.")
    p.add_argument("--skip", type=int, default=0, help="Input blocks to skip.")
    p.add_argument("--seek", type=int, default=0, help="Output blocks to seek before writing.")
    p.add_argument("--parents", action="store_true", help="Create missing output parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing output file.")
    p.add_argument("--max-preview-bytes", type=int, default=4096, help="Maximum JSON preview bytes.")
    p.add_argument("--dry-run", action="store_true", help="Report without writing output.")
    p.add_argument("--raw", action="store_true", help="Write selected input bytes without a JSON envelope.")
    p.set_defaults(func=command_dd)

    p = sub.add_parser("sync", help="Flush filesystem buffers where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report without syncing.")
    p.set_defaults(func=command_sync)

    p = sub.add_parser("dircolors", help="Return an agent-safe no-color LS_COLORS configuration.")
    p.add_argument("--shell", choices=["bash", "zsh", "sh", "fish", "plain"], default="bash", help="Raw shell format.")
    p.add_argument("--raw", action="store_true", help="Write shell configuration without a JSON envelope.")
    p.set_defaults(func=command_dircolors)

    p = sub.add_parser("seq", help="Generate a bounded numeric sequence.")
    p.add_argument("numbers", type=float, nargs="+", help="[FIRST [INCREMENT]] LAST.")
    p.add_argument("--increment", "-i", type=float, default=1.0, help="Increment used with one or two positional numbers.")
    p.add_argument("--separator", "-s", default="\n", help="Raw output separator.")
    p.add_argument("--format", "-f", help="printf-style numeric format, for example %%.2f.")
    p.add_argument("--max-items", type=int, default=10000, help="Maximum items to generate.")
    p.add_argument("--raw", action="store_true", help="Write sequence text without a JSON envelope.")
    p.set_defaults(func=command_seq)

    p = sub.add_parser("printf", help="Format text with a deterministic printf-style subset.")
    p.add_argument("format_string", help="Printf-style format string.")
    p.add_argument("values", nargs="*", help="Values used by format conversions.")
    p.add_argument("--encoding", default="utf-8", help="Output encoding.")
    p.add_argument("--raw", action="store_true", help="Write formatted text without a JSON envelope.")
    p.set_defaults(func=command_printf)

    p = sub.add_parser("echo", help="Join words with spaces and emit optional newline.")
    p.add_argument("words", nargs="*", help="Words to emit.")
    p.add_argument("--no-newline", "-n", action="store_true", help="Do not append a newline.")
    p.add_argument("--escapes", "-e", action="store_true", help="Interpret common backslash escapes.")
    p.add_argument("--encoding", default="utf-8", help="Output encoding.")
    p.add_argument("--raw", action="store_true", help="Write echo text without a JSON envelope.")
    p.set_defaults(func=command_echo)

    p = sub.add_parser("pathchk", help="Validate path strings for length and portable characters.")
    p.add_argument("paths", nargs="+", help="Path strings to validate.")
    p.add_argument("--portable", "-p", action="store_true", help="Require portable POSIX filename characters.")
    p.add_argument("--max-path-length", type=int, default=4096, help="Maximum path string length.")
    p.add_argument("--max-component-length", type=int, default=255, help="Maximum path component length.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when any path is invalid.")
    p.add_argument("--raw", action="store_true", help="Write validation rows without a JSON envelope.")
    p.set_defaults(func=command_pathchk)

    p = sub.add_parser("factor", help="Return prime factors for bounded integer inputs.")
    p.add_argument("numbers", nargs="*", help="Integers to factor. Defaults to whitespace tokens from stdin.")
    p.add_argument("--max-value", type=int, default=10**12, help="Safety cap for absolute input values.")
    p.add_argument("--raw", action="store_true", help="Write factor lines without a JSON envelope.")
    p.set_defaults(func=command_factor)

    p = sub.add_parser("expr", help="Evaluate a safe arithmetic/comparison expression subset.")
    p.add_argument("tokens", nargs="+", help="Expression tokens, for example: 1 + 2 or 3 '>' 2.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when the result is false/zero/empty.")
    p.add_argument("--raw", action="store_true", help="Write the expression value without a JSON envelope.")
    p.set_defaults(func=command_expr)

    p = sub.add_parser("true", help="Return success.")
    p.set_defaults(func=command_true)

    p = sub.add_parser("false", help="Return exit code 1 with a JSON envelope.")
    p.set_defaults(func=command_false)

    p = sub.add_parser("sleep", help="Sleep for a bounded number of seconds.")
    p.add_argument("seconds", type=float, help="Seconds to sleep.")
    p.add_argument("--max-seconds", type=float, default=60.0, help="Safety cap for sleep duration.")
    p.add_argument("--dry-run", action="store_true", help="Report without sleeping.")
    p.set_defaults(func=command_sleep)

    p = sub.add_parser("timeout", help="Run a command with a bounded timeout and captured output.")
    p.add_argument("seconds", type=float, help="Timeout in seconds.")
    p.add_argument("--max-output-bytes", type=int, default=65536, help="Maximum captured stdout/stderr bytes each.")
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_timeout)

    p = sub.add_parser("nice", help="Run a command with a niceness adjustment where supported.")
    p.add_argument("--adjustment", "-n", type=int, default=10, help="Niceness adjustment.")
    p.add_argument("--timeout", type=float, default=60.0, help="Safety timeout for the command.")
    p.add_argument("--max-output-bytes", type=int, default=65536, help="Maximum captured stdout/stderr bytes each.")
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_nice)

    p = sub.add_parser("kill", help="Send process signals with dry-run and explicit confirmation.")
    p.add_argument("pids", nargs="+", help="Process ids to signal.")
    p.add_argument("--signal", "-s", default="TERM", help="Signal name or number.")
    p.add_argument("--allow-signal", action="store_true", help="Allow sending real signals.")
    p.add_argument("--dry-run", action="store_true", help="Report without signaling.")
    p.set_defaults(func=command_kill)

    p = sub.add_parser("nohup", help="Plan or start a background process with redirected output.")
    p.add_argument("--output", default="nohup.out", help="Output file for stdout/stderr.")
    p.add_argument("--append", action="store_true", help="Append to the output file.")
    p.add_argument("--parents", action="store_true", help="Create missing output parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing output file.")
    p.add_argument("--allow-background", action="store_true", help="Allow starting a real background process.")
    p.add_argument("--dry-run", action="store_true", help="Report without starting a process.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_nohup)

    p = sub.add_parser("yes", help="Generate a bounded repeated line.")
    p.add_argument("words", nargs="*", help="Words to repeat. Defaults to 'y'.")
    p.add_argument("--count", "-n", type=int, default=10, help="Number of lines to generate.")
    p.add_argument("--raw", action="store_true", help="Write repeated lines without a JSON envelope.")
    p.set_defaults(func=command_yes)

    p = sub.add_parser("mkdir", help="Create directories with dry-run support.")
    p.add_argument("paths", nargs="+", help="Directories to create.")
    p.add_argument("--parents", "-p", action="store_true", help="Create missing parents.")
    p.add_argument("--exist-ok", action="store_true", help="Do not fail if a directory exists.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mkdir)

    p = sub.add_parser("touch", help="Create files or update timestamps with dry-run support.")
    p.add_argument("paths", nargs="+", help="Files to touch.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_touch)

    p = sub.add_parser("cp", help="Copy files/directories with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path.")
    p.add_argument("destination", help="Destination path.")
    p.add_argument("--recursive", "-r", action="store_true", help="Copy directories recursively.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing/merging destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_cp)

    p = sub.add_parser("mv", help="Move a path with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path.")
    p.add_argument("destination", help="Destination path.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_mv)

    p = sub.add_parser("ln", help="Create hard or symbolic links with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path or symlink target.")
    p.add_argument("destination", help="Link path to create.")
    p.add_argument("--symbolic", "-s", action="store_true", help="Create a symbolic link.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_ln)

    p = sub.add_parser("link", help="Create a hard link with explicit overwrite and dry-run.")
    p.add_argument("source", help="Existing source file.")
    p.add_argument("destination", help="Hard link path to create.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_link)

    p = sub.add_parser("chmod", help="Change file modes using octal modes with dry-run support.")
    p.add_argument("mode", help="Octal mode such as 644, 755, or 0644.")
    p.add_argument("paths", nargs="+", help="Paths whose mode should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chmod)

    p = sub.add_parser("chown", help="Change file owner/group using numeric ids or platform lookups.")
    p.add_argument("owner", help="Owner spec such as UID, USER, UID:GID, or USER:GROUP.")
    p.add_argument("paths", nargs="+", help="Paths whose owner/group should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chown)

    p = sub.add_parser("chgrp", help="Change file group using a numeric gid or platform lookup.")
    p.add_argument("group", help="Group name or numeric gid.")
    p.add_argument("paths", nargs="+", help="Paths whose group should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chgrp)

    p = sub.add_parser("truncate", help="Set file size in bytes with dry-run support.")
    p.add_argument("paths", nargs="+", help="Files to resize.")
    p.add_argument("--size", type=int, required=True, help="Target size in bytes.")
    p.add_argument("--no-create", action="store_true", help="Fail if a target file does not exist.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_truncate)

    p = sub.add_parser("mktemp", help="Create a temporary file or directory as JSON.")
    p.add_argument("--directory", "-d", action="store_true", help="Create a temporary directory.")
    p.add_argument("--prefix", default="tmp.", help="Temporary path prefix.")
    p.add_argument("--suffix", default="", help="Temporary path suffix.")
    p.add_argument("--tmpdir", help="Directory where the temporary path should be created. Defaults to cwd.")
    p.add_argument("--dry-run", action="store_true", help="Report a candidate path without creating it.")
    p.set_defaults(func=command_mktemp)

    p = sub.add_parser("mkfifo", help="Create FIFO special files where supported, with dry-run support.")
    p.add_argument("paths", nargs="+", help="FIFO paths to create.")
    p.add_argument("--mode", "-m", default="666", help="Octal mode such as 600 or 666.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mkfifo)

    p = sub.add_parser("mknod", help="Create regular placeholder files or FIFOs with dry-run support.")
    p.add_argument("paths", nargs="+", help="Node paths to create.")
    p.add_argument("--type", dest="node_type", choices=["regular", "fifo"], default="regular", help="Node type.")
    p.add_argument("--mode", "-m", default="666", help="Octal mode such as 600 or 666.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mknod)

    for command_name in ("install", "ginstall"):
        p = sub.add_parser(command_name, help=f"{command_name} files or create directories with explicit overwrite.")
        p.add_argument("paths", nargs="*", help="SOURCE DESTINATION, or directories with --directory.")
        p.add_argument("--directory", "-d", action="store_true", help="Create directories instead of installing a file.")
        p.add_argument("--mode", "-m", default="755", help="Octal mode applied to installed paths.")
        p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
        p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
        p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
        p.set_defaults(func=command_install)

    p = sub.add_parser("tee", help="Write stdin to files and optionally echo raw stdin.")
    p.add_argument("paths", nargs="*", help="Files to write.")
    p.add_argument("--append", "-a", action="store_true", help="Append instead of replacing.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--max-preview-bytes", type=int, default=4096, help="Maximum JSON preview bytes.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without writing files.")
    p.add_argument("--raw", action="store_true", help="Echo stdin to stdout without a JSON envelope.")
    p.set_defaults(func=command_tee)

    p = sub.add_parser("rmdir", help="Remove empty directories with dry-run support.")
    p.add_argument("paths", nargs="+", help="Empty directories to remove.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_rmdir)

    p = sub.add_parser("unlink", help="Unlink files or symlinks, refusing directories.")
    p.add_argument("paths", nargs="+", help="Files or symlinks to unlink.")
    p.add_argument("--force", "-f", action="store_true", help="Ignore missing paths.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_unlink)

    p = sub.add_parser("rm", help="Remove files/directories with dry-run and safety checks.")
    p.add_argument("paths", nargs="+", help="Paths to remove.")
    p.add_argument("--recursive", "-r", action="store_true", help="Remove directories recursively.")
    p.add_argument("--force", "-f", action="store_true", help="Ignore missing files.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.add_argument(
        "--allow-outside-cwd",
        action="store_true",
        help="Allow recursive directory removal outside the current working directory.",
    )
    p.set_defaults(func=command_rm)

    p = sub.add_parser("shred", help="Destructively overwrite files with explicit confirmation.")
    p.add_argument("paths", nargs="+", help="Files to overwrite.")
    p.add_argument("--passes", "-n", type=int, default=1, help="Number of zero overwrite passes.")
    p.add_argument("--remove", "-u", action="store_true", help="Remove files after overwriting.")
    p.add_argument("--allow-destructive", action="store_true", help="Allow real destructive overwrite.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_shred)

    return parser


def dispatch(args: argparse.Namespace) -> tuple[int, dict[str, Any] | bytes]:
    result = args.func(args)
    if isinstance(result, bytes):
        return EXIT["ok"], result
    code = result.pop("_exit_code", EXIT["ok"]) if isinstance(result, dict) else EXIT["ok"]
    return code, envelope(args.command, result)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    command_name: str | None = None
    if argv is None:
        argv = sys.argv[1:]
    pretty_requested = False
    if "--pretty" in argv:
        pretty_requested = True
        argv = [arg for arg in argv if arg != "--pretty"]
    try:
        args = parser.parse_args(argv)
        args.pretty = pretty_requested or getattr(args, "pretty", False)
        command_name = args.command
        code, payload = dispatch(args)
        if isinstance(payload, bytes):
            sys.stdout.buffer.write(payload)
        else:
            write_json(sys.stdout, payload, pretty=args.pretty)
        return code
    except AgentError as exc:
        write_json(sys.stderr, error_envelope(command_name, exc))
        return exc.exit_code
    except BrokenPipeError:
        return EXIT["ok"]
    except KeyboardInterrupt:
        exc = AgentError("general_error", "Interrupted.")
        write_json(sys.stderr, error_envelope(command_name, exc))
        return exc.exit_code
    except Exception as exc:
        error = AgentError(
            "general_error",
            "Unexpected error.",
            details={"type": type(exc).__name__, "message": str(exc)},
        )
        write_json(sys.stderr, error_envelope(command_name, error))
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
