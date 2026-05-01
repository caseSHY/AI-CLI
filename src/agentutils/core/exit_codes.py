"""Core exit codes for agentutils."""

from __future__ import annotations

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
