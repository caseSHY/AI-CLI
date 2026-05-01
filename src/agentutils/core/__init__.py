"""Core modules for agentutils: exceptions, envelope, path utilities, sandbox, streaming."""

from __future__ import annotations

from .envelope import envelope, error_envelope, utc_iso, write_json
from .exceptions import AgentError
from .exit_codes import EXIT
from .path_utils import (
    directory_size,
    disk_usage_entry,
    ensure_exists,
    ensure_parent,
    iter_directory,
    path_type,
    resolve_path,
    stat_entry,
)
from .sandbox import (
    dangerous_delete_target,
    destination_inside_directory,
    refuse_overwrite,
    remove_one,
    require_inside_cwd,
)
from .stream import NullStream, StreamWriter, is_stream_mode

__all__ = [
    "AgentError",
    "EXIT",
    "NullStream",
    "StreamWriter",
    "dangerous_delete_target",
    "destination_inside_directory",
    "directory_size",
    "disk_usage_entry",
    "envelope",
    "ensure_exists",
    "ensure_parent",
    "error_envelope",
    "is_stream_mode",
    "iter_directory",
    "path_type",
    "refuse_overwrite",
    "remove_one",
    "require_inside_cwd",
    "resolve_path",
    "stat_entry",
    "utc_iso",
    "write_json",
]
