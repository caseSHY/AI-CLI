"""Text-processing commands: sort, uniq, cut, tr, base64, comm, join, ...

文本处理命令层：实现 P2（文本转换与组合）优先级组的所有命令。

命令类型：
- 排序/去重：sort/uniq/tsort
- 比较合并：comm/join/paste
- 选择提取：cut/shuf/tac
- 格式化：nl/fold/fmt/pr
- 拆分：csplit/split
- 字符转换：tr/expand/unexpand
- 编码：codec（base64/base32）/basenc（base16/32/64/64url）
- 数值：numfmt/seq/od
- 输出：printf/echo/yes
- 索引：ptx
- 目录颜色：dircolors

每个命令支持 --raw 输出原始字节流和 --max-lines 有界输出。
排序和比较命令需处理 stdin + 多文件输入。
"""

from __future__ import annotations

import argparse
import base64
import binascii
import random
import re
import textwrap
from pathlib import Path
from typing import Any, TypedDict

from ...utils import (
    AgentError,
    alpha_suffix,
    bounded_lines,
    combined_lines,
    decode_standard_escapes,
    format_numfmt_value,
    format_printf,
    lines_to_raw,
    numeric_suffix,
    parse_numfmt_value,
    parse_ranges,
    read_input_bytes,
    read_input_texts,
    require_inside_cwd,
    resolve_path,
    selected_indexes,
    split_fields,
    transform_text,
    unexpand_line,
)


class CommRecord(TypedDict):
    column: int
    line: str


class LineCountRecord(TypedDict):
    line: str
    count: int


class JoinRecord(TypedDict):
    key: str
    fields: list[str]
    line: str


class NlRecord(TypedDict):
    number: int | None
    line: str
    output: str


class PtxRecord(TypedDict):
    keyword: str
    line_number: int
    left: str
    right: str
    line: str


# ── sort ───────────────────────────────────────────────────────────────


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


# ── comm ───────────────────────────────────────────────────────────────


def command_comm(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if len(args.paths) != 2:
        raise AgentError("invalid_input", "comm requires exactly two input files.")
    left_lines, left_sources = combined_lines([args.paths[0]], encoding=args.encoding)
    right_lines, right_sources = combined_lines([args.paths[1]], encoding=args.encoding)
    records: list[CommRecord] = []
    counts = {"only_first": 0, "only_second": 0, "common": 0}
    left_index = 0
    right_index = 0
    while left_index < len(left_lines) and right_index < len(right_lines):
        left = left_lines[left_index]
        right = right_lines[right_index]
        if left < right:
            counts["only_first"] += 1
            if not args.suppress_1:
                records.append({"column": 1, "line": left})
            left_index += 1
        elif left > right:
            counts["only_second"] += 1
            if not args.suppress_2:
                records.append({"column": 2, "line": right})
            right_index += 1
        else:
            counts["common"] += 1
            if not args.suppress_3:
                records.append({"column": 3, "line": left})
            left_index += 1
            right_index += 1
    for line in left_lines[left_index:]:
        counts["only_first"] += 1
        if not args.suppress_1:
            records.append({"column": 1, "line": line})
    for line in right_lines[right_index:]:
        counts["only_second"] += 1
        if not args.suppress_2:
            records.append({"column": 2, "line": line})
    if args.raw:
        prefixes = {1: "", 2: "\t", 3: "\t\t"}
        raw_lines = [f"{prefixes[record['column']]}{record['line']}" for record in records]
        return lines_to_raw(raw_lines, encoding=args.encoding)
    emitted, truncated = bounded_lines(records, args.max_lines)
    return {
        "source_paths": left_sources + right_sources,
        "counts": counts,
        "returned_records": len(emitted),
        "total_records": len(records),
        "truncated": truncated,
        "records": emitted,
    }


# ── join ───────────────────────────────────────────────────────────────


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
    records: list[JoinRecord] = []
    output_lines: list[str] = []
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


# ── paste ──────────────────────────────────────────────────────────────


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


# ── shuf ───────────────────────────────────────────────────────────────


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


# ── tac ────────────────────────────────────────────────────────────────


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


# ── nl ─────────────────────────────────────────────────────────────────


def command_nl(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.start < 0:
        raise AgentError("invalid_input", "--start must be >= 0.")
    if args.increment < 1:
        raise AgentError("invalid_input", "--increment must be >= 1.")
    if args.width < 1:
        raise AgentError("invalid_input", "--width must be >= 1.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    records: list[NlRecord] = []
    output_lines: list[str] = []
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


# ── fold ───────────────────────────────────────────────────────────────


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


# ── fmt ────────────────────────────────────────────────────────────────


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


# ── csplit ─────────────────────────────────────────────────────────────


def command_csplit(args: argparse.Namespace) -> dict[str, Any]:
    if args.pattern == "":
        raise AgentError("invalid_input", "--pattern cannot be empty.")
    cwd = Path.cwd().resolve()
    label, data = read_input_bytes(args.path)
    text = data.decode(args.encoding, errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    try:
        regex = re.compile(args.pattern, re.MULTILINE)
    except re.error as exc:
        raise AgentError(
            "invalid_input", "Invalid csplit regular expression.", details={"pattern": args.pattern}
        ) from exc
    matches = list(regex.finditer(text))
    if args.max_splits < 0:
        raise AgentError("invalid_input", "--max-splits must be >= 0.")
    if args.max_splits:
        matches = matches[: args.max_splits]
    boundaries = [0] + [match.start() for match in matches] + [len(text)]
    chunks = [text[boundaries[index] : boundaries[index + 1]] for index in range(len(boundaries) - 1)]
    output_dir = resolve_path(args.output_dir, strict=True)
    require_inside_cwd(output_dir, cwd, allow_outside_cwd=False)
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
                raise AgentError(
                    "permission_denied", "Permission denied while writing csplit output.", path=str(destination)
                ) from exc
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


# ── split ──────────────────────────────────────────────────────────────


def split_chunks_by_lines(data: bytes, lines_per_file: int) -> list[tuple[bytes, int]]:
    if lines_per_file < 1:
        raise AgentError("invalid_input", "--lines must be >= 1.")
    lines = data.splitlines(keepends=True)
    return [
        (b"".join(lines[index : index + lines_per_file]), len(lines[index : index + lines_per_file]))
        for index in range(0, len(lines), lines_per_file)
    ]


def split_chunks_by_bytes(data: bytes, bytes_per_file: int) -> list[tuple[bytes, int]]:
    if bytes_per_file < 1:
        raise AgentError("invalid_input", "--bytes must be >= 1.")
    return [(data[index : index + bytes_per_file], 0) for index in range(0, len(data), bytes_per_file)]


def command_split(args: argparse.Namespace) -> dict[str, Any]:
    if args.lines is None and args.bytes is None:
        args.lines = 1000
    cwd = Path.cwd().resolve()
    label, data = read_input_bytes(args.path)
    output_dir = resolve_path(args.output_dir, strict=True)
    require_inside_cwd(output_dir, cwd, allow_outside_cwd=False)
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
        suffix = (
            numeric_suffix(index, args.suffix_length)
            if args.numeric_suffixes
            else alpha_suffix(index, args.suffix_length)
        )
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
                raise AgentError(
                    "permission_denied", "Permission denied while writing split file.", path=str(destination)
                ) from exc
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


# ── od ─────────────────────────────────────────────────────────────────


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


# ── pr ─────────────────────────────────────────────────────────────────


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


# ── ptx ────────────────────────────────────────────────────────────────


def command_ptx(args: argparse.Namespace) -> dict[str, Any] | bytes:
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    ignore = {item.lower() if args.ignore_case else item for item in args.ignore}
    only = {item.lower() if args.ignore_case else item for item in args.only}
    records: list[PtxRecord] = []
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
            record: PtxRecord = {
                "keyword": word,
                "line_number": line_number,
                "left": left,
                "right": right,
                "line": line,
            }
            records.append(record)
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


# ── tsort ──────────────────────────────────────────────────────────────


def command_tsort(args: argparse.Namespace) -> dict[str, Any] | bytes:
    sources = read_input_texts(args.paths, encoding=args.encoding)
    tokens: list[str] = []
    for source in sources:
        tokens.extend(source["text"].split())
    if len(tokens) % 2 != 0:
        raise AgentError("invalid_input", "tsort input must contain whitespace-separated node pairs.")

    nodes = set(tokens)
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    indegree = dict.fromkeys(nodes, 0)
    edges = []
    for left, right in zip(tokens[0::2], tokens[1::2], strict=True):
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


# ── uniq ───────────────────────────────────────────────────────────────


def command_uniq(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.repeated and args.unique_only:
        raise AgentError("invalid_input", "--repeated and --unique-only cannot be used together.")
    lines, source_paths = combined_lines(args.paths, encoding=args.encoding)
    records: list[LineCountRecord] = []
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


# ── cut ────────────────────────────────────────────────────────────────


def cut_line(args: argparse.Namespace, line: str, ranges: list[tuple[int | None, int | None]]) -> str:
    if args.fields:
        fields = line.split(args.delimiter)
        selected_fields = [fields[index] for index in selected_indexes(len(fields), ranges)]
        return str(args.output_delimiter).join(selected_fields)
    if args.chars:
        chars = list(line)
        selected_chars = [chars[index] for index in selected_indexes(len(chars), ranges)]
        return "".join(selected_chars)
    data = line.encode(args.encoding)
    selected_bytes = bytes(data[index] for index in selected_indexes(len(data), ranges))
    return selected_bytes.decode(args.encoding, errors="replace")


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


# ── tr ─────────────────────────────────────────────────────────────────


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


# ── expand / unexpand ──────────────────────────────────────────────────


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
    output_parts: list[str] = []
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


# ── codec commands (base64, base32, basenc) ────────────────────────────


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
        return output if args.decode or not output else output + b"\n"

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


# ── numfmt ─────────────────────────────────────────────────────────────


def command_numfmt(args: argparse.Namespace) -> dict[str, Any] | bytes:
    import sys as _sys

    raw_values = args.numbers or _sys.stdin.read().split()
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


# ── seq / printf / echo / yes ──────────────────────────────────────────


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
    values: list[float] = []
    current = first
    forward = increment > 0
    while (current <= last if forward else current >= last) and len(values) < args.max_items:
        values.append(current)
        current += increment
    would_continue = current <= last if forward else current >= last

    def format_value(value: float) -> str:
        if args.format:
            try:
                return str(args.format % value)
            except (TypeError, ValueError) as exc:
                raise AgentError("invalid_input", "Invalid printf-style --format for seq.") from exc
        return str(int(value)) if value == int(value) else str(value)

    lines = [format_value(value) for value in values]
    if args.raw:
        return (str(args.separator).join(lines) + ("\n" if lines else "")).encode("utf-8")
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


def command_yes(args: argparse.Namespace) -> dict[str, Any] | bytes:
    if args.count < 0:
        raise AgentError("invalid_input", "--count must be >= 0.")
    line = " ".join(args.words) if args.words else "y"
    lines = [line] * args.count
    if args.raw:
        return lines_to_raw(lines, encoding="utf-8")
    return {"line": line, "count": args.count, "lines": lines}


# ── dircolors ──────────────────────────────────────────────────────────


def command_dircolors(args: argparse.Namespace) -> dict[str, Any] | bytes:
    result = {
        "colors_enabled": False,
        "ls_colors": "",
        "reason": "aicoreutils disables color by default to keep output machine-readable.",
    }
    if args.raw:
        shell = args.shell
        if shell in ("bash", "zsh", "sh"):
            return b"LS_COLORS=''; export LS_COLORS\n"
        if shell == "fish":
            return b"set -gx LS_COLORS ''\n"
        return b"LS_COLORS=\n"
    return result
