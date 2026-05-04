"""Unit tests for mcp_server.py: _call_tool, protocol handling, server loop."""

from __future__ import annotations

import io
import json
import sys
import unittest
from unittest.mock import patch

from aicoreutils.mcp_server import _call_tool, _read_request, _send, server_loop


class CallToolTests(unittest.TestCase):
    """Unit tests for _call_tool function."""

    def test_known_command_cat_returns_result(self) -> None:
        result = _call_tool("cat", {"path": "pyproject.toml"})
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)

    def test_unknown_command_returns_error(self) -> None:
        result = _call_tool("nonexistent_cmd", {})
        self.assertEqual(result["ok"], False)
        self.assertIn("Unknown command", result["error"])

    def test_empty_arguments(self) -> None:
        result = _call_tool("pwd", {})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["ok"], True)

    def test_boolean_flag(self) -> None:
        result = _call_tool("ls", {"path": ".", "include_hidden": True})
        self.assertIsInstance(result, dict)

    def test_list_argument(self) -> None:
        result = _call_tool("echo", {"text": "hello world"})
        self.assertIsInstance(result, dict)
        self.assertEqual(result["ok"], True)

    def test_command_list_tools_returns_tools(self) -> None:
        result = _call_tool("tool-list", {})
        self.assertEqual(result["ok"], True)
        self.assertIn("result", result)
        self.assertIn("tools", result["result"])

    def test_command_schema_returns_schema(self) -> None:
        result = _call_tool("schema", {})
        self.assertEqual(result["ok"], True)
        self.assertIn("result", result)
        self.assertIn("command_count", result["result"])

    def test_command_true_returns_ok(self) -> None:
        result = _call_tool("true", {})
        self.assertIn("ok", result)

    def test_streaming_command_ls(self) -> None:
        result = _call_tool("ls", {"path": ".", "max_depth": 1, "limit": 3})
        self.assertIsInstance(result, dict)

    def test_call_tool_with_raw_output(self) -> None:
        result = _call_tool("base64", {"paths": ["pyproject.toml"], "raw": True})
        self.assertIsInstance(result, dict)

    def test_argument_builds_correctly_for_sort(self) -> None:
        result = _call_tool("sort", {"paths": ["pyproject.toml"], "numeric": True})
        self.assertIsInstance(result, dict)


class SendTests(unittest.TestCase):
    """Unit tests for _send function (JSON-RPC response writing)."""

    def test_send_writes_json_line_to_stdout(self) -> None:
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            _send({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})
        line = buf.getvalue().strip()
        data = json.loads(line)
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["result"]["ok"], True)

    def test_send_handles_non_ascii(self) -> None:
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            _send({"jsonrpc": "2.0", "id": 1, "result": {"text": "中文测试"}})
        line = buf.getvalue().strip()
        data = json.loads(line)
        self.assertEqual(data["result"]["text"], "中文测试")


class ReadRequestTests(unittest.TestCase):
    """Unit tests for _read_request function (JSON-RPC request reading)."""

    def test_read_valid_json_request(self) -> None:
        fake_stdin = io.StringIO('{"jsonrpc":"2.0","method":"tools/list","id":1}\n')
        with patch.object(sys, "stdin", fake_stdin):
            result = _read_request()
        self.assertIsNotNone(result)
        self.assertEqual(result["method"], "tools/list")
        self.assertEqual(result["id"], 1)

    def test_read_invalid_json_returns_none(self) -> None:
        fake_stdin = io.StringIO("not valid json\n")
        with patch.object(sys, "stdin", fake_stdin):
            result = _read_request()
        self.assertIsNone(result)

    def test_read_eof_returns_none(self) -> None:
        fake_stdin = io.StringIO("")
        with patch.object(sys, "stdin", fake_stdin):
            result = _read_request()
        self.assertIsNone(result)


class ServerLoopTests(unittest.TestCase):
    """Unit tests for server_loop JSON-RPC protocol handling."""

    def _run_request(self, request_json: str) -> str | None:
        """Feed a single JSON-RPC request to server_loop, return the raw response line."""
        stdin_buf = io.StringIO(request_json + "\n")
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", stdin_buf), patch.object(sys, "stdout", stdout_buf):
            server_loop()
        output = stdout_buf.getvalue().strip()
        return output if output else None

    def test_initialize_returns_capabilities(self) -> None:
        output = self._run_request('{"jsonrpc":"2.0","method":"initialize","id":1}')
        self.assertIsNotNone(output)
        data = json.loads(output)
        self.assertEqual(data["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(data["result"]["serverInfo"]["name"], "aicoreutils")
        self.assertIn("tools", data["result"]["capabilities"])

    def test_tools_list_returns_tools_array(self) -> None:
        output = self._run_request('{"jsonrpc":"2.0","method":"tools/list","id":2}')
        self.assertIsNotNone(output)
        data = json.loads(output)
        self.assertIn("tools", data["result"])
        self.assertGreater(len(data["result"]["tools"]), 0)
        self.assertEqual(data["result"]["tools"][0]["name"], "[")

    def test_tools_call_cat(self) -> None:
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 3,
                "params": {"name": "cat", "arguments": {"path": "pyproject.toml"}},
            }
        )
        output = self._run_request(request)
        self.assertIsNotNone(output)
        data = json.loads(output)
        content = data["result"]["content"][0]
        self.assertEqual(content["type"], "text")
        inner = json.loads(content["text"])
        self.assertEqual(inner["ok"], True)

    def test_unknown_method_returns_error(self) -> None:
        output = self._run_request('{"jsonrpc":"2.0","method":"bad/method","id":4}')
        self.assertIsNotNone(output)
        data = json.loads(output)
        self.assertEqual(data["error"]["code"], -32601)
        self.assertIn("Unknown method", data["error"]["message"])

    def test_notifications_initialized_is_noop(self) -> None:
        output = self._run_request('{"jsonrpc":"2.0","method":"notifications/initialized","id":5}')
        self.assertIsNone(output)

    def test_tools_call_unknown_command(self) -> None:
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 6,
                "params": {"name": "nonexistent_cmd", "arguments": {}},
            }
        )
        output = self._run_request(request)
        self.assertIsNotNone(output)
        data = json.loads(output)
        inner = json.loads(data["result"]["content"][0]["text"])
        self.assertEqual(inner["ok"], False)

    def test_several_requests_sequential(self) -> None:
        """Verify server processes multiple requests correctly."""
        stdin_buf = io.StringIO(
            '{"jsonrpc":"2.0","method":"initialize","id":1}\n'
            '{"jsonrpc":"2.0","method":"notifications/initialized","id":2}\n'
            '{"jsonrpc":"2.0","method":"tools/list","id":3}\n'
        )
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", stdin_buf), patch.object(sys, "stdout", stdout_buf):
            server_loop()
        lines = stdout_buf.getvalue().strip().split("\n")
        self.assertEqual(len(lines), 2)
        data1 = json.loads(lines[0])
        self.assertEqual(data1["result"]["protocolVersion"], "2024-11-05")
        data2 = json.loads(lines[1])
        self.assertIn("tools", data2["result"])


class MainEntrypointTests(unittest.TestCase):
    """Unit tests for main() entry point."""

    def test_main_calls_server_loop(self) -> None:
        from aicoreutils.mcp_server import main

        with (
            patch("aicoreutils.mcp_server.server_loop", side_effect=SystemExit(0)),
            self.assertRaises(SystemExit),
        ):
            main()

    def test_main_handles_keyboard_interrupt(self) -> None:
        from aicoreutils.mcp_server import main

        with patch("aicoreutils.mcp_server.server_loop", side_effect=KeyboardInterrupt):
            main()

    def test_main_handles_broken_pipe(self) -> None:
        from aicoreutils.mcp_server import main

        with patch("aicoreutils.mcp_server.server_loop", side_effect=BrokenPipeError):
            main()


if __name__ == "__main__":
    unittest.main()
