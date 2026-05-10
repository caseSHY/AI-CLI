"""Command base classes — the OO foundation for aicoreutils commands.

Provides:
- CommandResult: unified execution result replacing dict|bytes ambiguity
- BaseCommand: minimal ABC, __call__ bridges to old dispatch protocol
- TextFilterCommand: read → transform → bounded_lines → return (19 commands)
- FileInfoCommand: iterate paths → compute entry → {count, entries} (7 commands)
- MutatingCommand: resolve → sandbox → dry_run → execute → operations (~15 commands)

All base classes keep their abstract surface small — typically one hook method
per concrete command.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import argparse


@dataclass
class CommandResult:
    """Unified execution result.  A command returns this from execute();
    BaseCommand.__call__ converts it to the legacy dict|bytes shape that
    dispatch() expects.
    """

    data: dict[str, Any] | None = None
    raw_bytes: bytes | None = None
    exit_code: int = 0
    warnings: list[str] = field(default_factory=list)
    encoding_meta: dict[str, Any] | None = None

    @property
    def is_raw(self) -> bool:
        return self.raw_bytes is not None

    def to_dict(self) -> dict[str, Any]:
        """Build the legacy-style result dict (never returns None)."""
        d = dict(self.data) if self.data else {}
        if self.exit_code:
            d["_exit_code"] = self.exit_code
        return d


# ── Base command (minimal surface) ───────────────────────────────────


class BaseCommand(ABC):
    """Abstract base for all commands.

    Subclasses override execute().  __call__ is the bridge between the
    OO world and the legacy dispatch protocol — it converts CommandResult
    back to dict|bytes so that dispatch() and MCP _call_tool continue to work.
    """

    name: str = ""

    def __call__(self, args: argparse.Namespace) -> dict[str, Any] | bytes:
        result = self.execute(args)
        if result.is_raw:
            return result.raw_bytes  # type: ignore[return-value]
        d = result.to_dict()
        if result.encoding_meta:
            d["_encoding_info"] = result.encoding_meta
        return d

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> CommandResult:
        """Run the command and return a unified result."""
        ...


# ── Text filter pipeline (Cluster A: 19 commands) ─────────────────────


class TextFilterCommand(BaseCommand):
    """Commands that read lines, transform them, and emit bounded output.

    Pattern: combined_lines() → transform() → bounded_lines() → dict | bytes.

    Subclasses override transform() (or read_input() for non-standard reading).
    """

    def execute(self, args: argparse.Namespace) -> CommandResult:
        from ..utils._io import bounded_lines, lines_to_raw

        lines, source_paths = self._read_input(args)
        output_lines = self.transform(lines, args)
        if getattr(args, "raw", False):
            enc = getattr(args, "encoding", "utf-8")
            return CommandResult(raw_bytes=lines_to_raw(output_lines, encoding=enc))
        emitted, truncated = bounded_lines(output_lines, args.max_lines)
        return CommandResult(
            data={
                "source_paths": source_paths,
                "returned_lines": len(emitted),
                "total_output_lines": len(output_lines),
                "truncated": truncated,
                "lines": emitted,
            }
        )

    def _read_input(self, args: argparse.Namespace) -> tuple[list[str], list[str]]:
        """Default input: combined_lines with encoding."""
        from ..utils._io import combined_lines

        return combined_lines(args.paths, encoding=args.encoding)

    @abstractmethod
    def transform(self, lines: list[str], args: argparse.Namespace) -> list[str]:
        """Apply the per-command transformation to input lines."""
        ...


# ── File info query (Cluster B: 7 commands) ───────────────────────────


class FileInfoCommand(BaseCommand):
    """Commands that iterate paths, compute a result per path, and emit.

    Pattern: for raw in paths: entry, raw_str = process_path(raw) →
    {count, entries} | bytes.

    Subclasses override process_path().
    """

    def execute(self, args: argparse.Namespace) -> CommandResult:
        from ..utils._io import lines_to_raw

        entries: list[dict[str, Any]] = []
        raw_lines: list[str] = []
        for raw in args.paths:
            entry, raw_str = self.process_path(raw, args)
            entries.append(entry)
            raw_lines.append(raw_str)
        if getattr(args, "raw", False):
            enc = getattr(args, "encoding", "utf-8")
            return CommandResult(raw_bytes=lines_to_raw(raw_lines, encoding=enc))
        return CommandResult(data={"count": len(entries), "entries": entries})

    @abstractmethod
    def process_path(self, raw: str, args: argparse.Namespace) -> tuple[dict[str, Any], str]:
        """Compute (entry_dict, raw_line_string) for a single path."""
        ...


# ── File mutation (Cluster C: ~15 commands) ───────────────────────────


class MutatingCommand(BaseCommand):
    """Commands that modify the filesystem with safety checks.

    Pattern: for each path → resolve → sandbox → dry_run guard → execute →
    {count, operations}.

    Subclasses override _execute_one(). The base handles path resolution,
    sandbox validation, and dry_run passthrough.
    """

    def execute(self, args: argparse.Namespace) -> CommandResult:
        from pathlib import Path

        from ..core.path_utils import resolve_path
        from ..core.sandbox import require_inside_cwd

        cwd = Path.cwd().resolve()
        operations: list[dict[str, Any]] = []
        for raw in self._target_paths(args):
            path = resolve_path(raw)
            require_inside_cwd(path, cwd, allow_outside_cwd=getattr(args, "allow_outside_cwd", False))
            self._execute_one(path, args, operations)
        return CommandResult(data={"count": len(operations), "operations": operations})

    def _target_paths(self, args: argparse.Namespace) -> list[Any]:
        """Paths to operate on. Default reads args.paths; override for variadic sources."""
        return list(args.paths)

    @abstractmethod
    def _execute_one(self, path: Any, args: argparse.Namespace, operations: list[dict[str, Any]]) -> None:
        """Execute the mutation for a single resolved path, appending an operation dict."""
        ...
