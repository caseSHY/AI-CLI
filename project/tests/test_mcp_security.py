"""Tests for MCP server security: --read-only, --allow-command, --deny-command."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from typing import Any

from support import ROOT

SRC = ROOT / "src"


def _mcp_request(proc: subprocess.Popen[Any], method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    proc.stdin.write(msg + "\n")  # type: ignore[union-attr]
    proc.stdin.flush()  # type: ignore[union-attr]
    return json.loads(proc.stdout.readline())  # type: ignore[union-attr]


class McpReadOnlyTests(unittest.TestCase):
    """Test MCP server --read-only mode."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}

    def _start_server(self, *extra_args: str) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self.env,
            cwd=str(ROOT),
        )

    def test_read_only_allows_read_commands(self) -> None:
        proc = self._start_server("--read-only")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "pwd", "arguments": {}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), f"Read command should succeed, got: {data}")
        finally:
            proc.terminate()

    def test_read_only_blocks_write_commands(self) -> None:
        proc = self._start_server("--read-only")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "mkdir", "arguments": {"paths": ["_test_sec"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"), f"Write command should be blocked, got: {data}")
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
        finally:
            proc.terminate()

    def test_read_only_blocks_destructive_commands(self) -> None:
        proc = self._start_server("--read-only")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "rm", "arguments": {"paths": ["_noexist"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"))
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
        finally:
            proc.terminate()


class McpAllowCommandTests(unittest.TestCase):
    """Test MCP server --allow-command."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}

    def _start_server(self, *extra_args: str) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self.env,
            cwd=str(ROOT),
        )

    def test_allow_command_permits_listed(self) -> None:
        proc = self._start_server("--allow-command", "ls", "--allow-command", "pwd")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "ls", "arguments": {"path": "src"}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), f"Allowed command should succeed: {data}")
        finally:
            proc.terminate()

    def test_allow_command_blocks_unlisted(self) -> None:
        proc = self._start_server("--allow-command", "ls")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "pwd", "arguments": {}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"))
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
        finally:
            proc.terminate()

    def test_allow_command_overrides_read_only(self) -> None:
        """--allow-command should allow a command even in read-only mode."""
        proc = self._start_server("--read-only", "--allow-command", "mkdir")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "mkdir", "arguments": {"paths": ["_test_allowed"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), f"Allow-listed command should bypass read-only: {data}")
        finally:
            proc.terminate()
            import shutil

            dst = ROOT / "_test_allowed"
            if dst.is_dir():
                shutil.rmtree(dst)


class McpDenyCommandTests(unittest.TestCase):
    """Test MCP server --deny-command."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}

    def _start_server(self, *extra_args: str) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self.env,
            cwd=str(ROOT),
        )

    def test_deny_command_blocks_specific(self) -> None:
        proc = self._start_server("--deny-command", "rm")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "rm", "arguments": {"paths": ["_noexist"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"))
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
        finally:
            proc.terminate()

    def test_deny_command_allows_others(self) -> None:
        proc = self._start_server("--deny-command", "rm")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "pwd", "arguments": {}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), f"Non-denied command should succeed: {data}")
        finally:
            proc.terminate()

    def test_deny_has_priority_over_allow(self) -> None:
        """Deny list should take priority over allow list."""
        proc = self._start_server("--allow-command", "rm", "--deny-command", "rm")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "rm", "arguments": {"paths": ["_noexist"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"))
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
        finally:
            proc.terminate()


class McpSecurityErrorFormatTests(unittest.TestCase):
    """Test structured security error format."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}

    def _start_server(self, *extra_args: str) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", *extra_args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self.env,
            cwd=str(ROOT),
        )

    def test_security_denied_error_structure(self) -> None:
        proc = self._start_server("--read-only")
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "rm", "arguments": {"paths": ["_noexist"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data["ok"])
            self.assertEqual(data["error"]["code"], "SECURITY_DENIED")
            self.assertIn("command", data["error"])
            self.assertIn("reason", data["error"])
            self.assertTrue(resp["result"]["isError"])
        finally:
            proc.terminate()
