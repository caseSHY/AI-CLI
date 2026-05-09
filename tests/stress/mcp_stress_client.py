"""MCP JSON-RPC stress client — generates random valid MCP requests."""

from __future__ import annotations

import json
import random


class MCPStressClient:
    """Generates and sends random MCP JSON-RPC requests to a server process.

    Manages the lifecycle: initialize → random tools/list + tools/call → shutdown.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._next_id = 1

    def _req_id(self) -> int:
        rid = self._next_id
        self._next_id += 1
        return rid

    def initialize_request(self) -> str:
        msg = {
            "jsonrpc": "2.0",
            "id": self._req_id(),
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
        return json.dumps(msg, ensure_ascii=False) + "\n"

    def tools_list_request(self) -> str:
        msg = {"jsonrpc": "2.0", "id": self._req_id(), "method": "tools/list"}
        return json.dumps(msg, ensure_ascii=False) + "\n"

    def random_tool_call(self) -> str:
        """Generate a tools/call request for a random safe command."""
        tool = self._rng.choice(
            [
                ("echo", {"text": ["hello", "stress"]}),
                ("date", {}),
                ("pwd", {}),
                ("whoami", {}),
                ("uname", {}),
                ("hostname", {}),
                ("uptime", {}),
                ("nproc", {}),
                ("true", {}),
                ("false", {}),
                ("id", {}),
                ("groups", {}),
                ("env", {}),
                ("printenv", {}),
                ("catalog", {}),
                ("schema", {}),
                ("coreutils", {"list": True}),
                ("tool-list", {}),
                ("sleep", {"duration": "0.01"}),
                ("seq", {"first": "1", "last": "3"}),
            ]
        )
        msg = {
            "jsonrpc": "2.0",
            "id": self._req_id(),
            "method": "tools/call",
            "params": {"name": tool[0], "arguments": tool[1]},
        }
        return json.dumps(msg, ensure_ascii=False) + "\n"


def send_request(proc: object, request: str) -> None:
    """Write a JSON-RPC request to an MCP server subprocess."""
    proc.stdin.write(request.encode("utf-8"))  # type: ignore[union-attr]
    proc.stdin.flush()  # type: ignore[union-attr]


def read_response(proc: object) -> dict | None:
    """Read a single JSON-RPC response line from an MCP server subprocess."""
    line = proc.stdout.readline()  # type: ignore[union-attr]
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"error": "JSON decode failure", "raw": line.strip()}
