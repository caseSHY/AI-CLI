"""Core protocol layer: AgentError, envelopes, path utilities, and shared helpers."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import stat as statmod
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, TextIO

from . import __version__

# ── semantic exit codes ────────────────────────────────────────────────

EXIT: dict[str, int] = {
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

HASH_ALGORITHMS: dict[str, str] = {
    "md5": "md5",
    "sha1": "sha1",
    "sha224": "sha224",
    "sha256": "sha256",
    "sha384": "sha384",
    "sha512": "sha512",
    "b2sum": "blake2b",
    "blake2b": "blake2b",
}


# ── AgentError ──────────────────────────────────────────────────────────

class AgentError(Exception):
    """Semantic error with machine-readable code, optional path, and suggestion."""

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
    """ArgumentParser that raises structured AgentError on usage errors."""

    def error(self, message: str) -> None:
        error = AgentError(
            "usage",
            message,
            suggestion="Run 'agentutils schema' or '<command> --help' to discover valid usage.",
        )
        write_json(sys.stderr, error_envelope(None, error))
        raise SystemExit(EXIT["usage"])


# ── JSON / envelope helpers ────────────────────────────────────────────

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


# ── path utilities ─────────────────────────────────────────────────────

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


# ── I/O helpers ────────────────────────────────────────────────────────

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
    sources: list[dict[str, str]] = []
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


def read_text_lines(path: Path, *, encoding: str) -> list[str]:
    ensure_exists(path)
    if path.is_dir():
        raise AgentError("invalid_input", "Path is a directory, not a file.", path=str(path))
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        return handle.read().splitlines()


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


# ── text / escaping utilities ──────────────────────────────────────────

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


# ── hash / checksum utilities ──────────────────────────────────────────

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


def simple_sum16(data: bytes) -> int:
    return sum(data) & 0xFFFF


# ── split / suffix helpers ─────────────────────────────────────────────

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


# ── text transformation helpers ────────────────────────────────────────

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


def unexpand_line(line: str, *, tab_size: int, all_blanks: bool) -> str:
    def compress_spaces(match: re.Match[str]) -> str:
        width = len(match.group(0))
        return "\t" * (width // tab_size) + " " * (width % tab_size)

    if all_blanks:
        return re.sub(r" +", compress_spaces, line)
    leading = re.match(r" +", line)
    if not leading:
        return line
    return compress_spaces(leading) + line[leading.end():]


def split_fields(line: str, delimiter: str | None) -> list[str]:
    return line.split(delimiter) if delimiter is not None else line.split()


def squeeze_repeats(text: str, squeeze_set: set[str]) -> str:
    if not text:
        return text
    output = [text[0]]
    for char in text[1:]:
        if char == output[-1] and char in squeeze_set:
            continue
        output.append(char)
    return "".join(output)


def transform_text(args: Any, text: str) -> str:
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


def parse_ranges(spec: str) -> list[tuple[int | None, int | None]]:
    ranges: list[tuple[int | None, int | None]] = []
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
    seen: set[int] = set()
    for start, end in ranges:
        first = 1 if start is None else start
        last = length if end is None else end
        for one_based in range(first, min(last, length) + 1):
            zero_based = one_based - 1
            if zero_based not in seen:
                seen.add(zero_based)
                indexes.append(zero_based)
    return indexes


# ── printf helpers ─────────────────────────────────────────────────────

def printf_conversions(format_string: str) -> list[str]:
    conversions: list[str] = []
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
    output: list[str] = []
    for start in range(0, len(values), len(conversions)):
        chunk = values[start : start + len(conversions)]
        converted = tuple(coerce_printf_value(value, conversion) for value, conversion in zip(chunk, conversions))
        try:
            output.append(fmt % converted)
        except (TypeError, ValueError) as exc:
            raise AgentError("invalid_input", "printf format could not be applied to the supplied values.") from exc
    return "".join(output)


# ── numfmt helpers ─────────────────────────────────────────────────────

SI_UNITS: dict[str, float] = {"": 1.0, "K": 1000.0, "M": 1000.0**2, "G": 1000.0**3, "T": 1000.0**4, "P": 1000.0**5, "E": 1000.0**6}
IEC_UNITS: dict[str, float] = {"": 1.0, "K": 1024.0, "M": 1024.0**2, "G": 1024.0**3, "T": 1024.0**4, "P": 1024.0**5, "E": 1024.0**6}


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


# ── system / subprocess helpers ────────────────────────────────────────

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


def parse_signal(raw: str) -> int:
    value = raw.upper()
    if value.isdigit():
        return int(value)
    if not value.startswith("SIG"):
        value = f"SIG{value}"
    import signal
    signum = getattr(signal, value, None)
    if signum is None:
        raise AgentError("invalid_input", "Unknown signal.", details={"signal": raw})
    return int(signum)


def normalize_command_args(raw: list[str]) -> list[str]:
    command = list(raw)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise AgentError("invalid_input", "A command is required.")
    return command


def run_subprocess_capture(
    command: list[str],
    *,
    timeout: float | None,
    max_output_bytes: int,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[bytes] | None, bool]:
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


def subprocess_result(
    command: list[str],
    completed: subprocess.CompletedProcess[bytes],
    *,
    timed_out: bool,
    max_output_bytes: int,
) -> dict[str, Any]:
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


def active_user_entries() -> list[dict[str, Any]]:
    import getpass
    user = getpass.getuser()
    terminal = stdin_tty_name()
    return [{"user": user, "terminal": terminal, "source": "current_process"}]


def disk_usage_entry(path: Path) -> dict[str, Any]:
    import shutil
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


# ── predicate / evaluation helpers ─────────────────────────────────────

def evaluate_test_predicates(path: Path, predicates: list[str]) -> list[dict[str, Any]]:
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
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


# ── directory iteration (ls/dir/vdir) ──────────────────────────────────

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


# ── file removal helper ────────────────────────────────────────────────

def remove_one(path: Path, *, recursive: bool, force: bool) -> str:
    import shutil
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

def selected_environment(names: list[str] | None) -> dict[str, str]:
    if not names:
        return dict(sorted(os.environ.items()))
    return {name: os.environ[name] for name in names if name in os.environ}
