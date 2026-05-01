"""Core exception classes for agentutils."""

from __future__ import annotations

from typing import Any

from .exit_codes import EXIT


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
