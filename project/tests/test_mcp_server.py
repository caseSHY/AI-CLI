"""Unit tests for tool_schema and mcp_server modules."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

from aicoreutils.parser._parser import build_parser
from aicoreutils.tool_schema import _command_tools, tools_anthropic, tools_openai

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


# ── tool_schema ──


class ToolSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parser = build_parser()
        cls.tools = _command_tools(cls.parser)

    def test_returns_114_tools(self) -> None:
        self.assertGreaterEqual(len(self.tools), 114)  # allow plugin commands to increase total

    def test_each_tool_has_required_fields(self) -> None:
        for tool in self.tools:
            with self.subTest(name=tool["name"]):
                self.assertIn("name", tool)
                self.assertIn("description", tool)
                self.assertIn("inputSchema", tool)
                self.assertIsInstance(tool["name"], str)
                self.assertIsInstance(tool["description"], str)
                self.assertIsInstance(tool["inputSchema"], dict)

    def test_input_schema_has_type_object(self) -> None:
        for tool in self.tools:
            with self.subTest(name=tool["name"]):
                self.assertEqual(tool["inputSchema"].get("type"), "object")
                self.assertIsInstance(tool["inputSchema"].get("properties"), dict)
                self.assertIsInstance(tool["inputSchema"].get("required"), list)

    def test_properties_exclude_help(self) -> None:
        for tool in self.tools:
            with self.subTest(name=tool["name"]):
                self.assertNotIn("help", tool["inputSchema"]["properties"])

    def test_all_names_are_unique(self) -> None:
        names = [t["name"] for t in self.tools]
        self.assertEqual(len(names), len(set(names)))

    def test_cat_has_path_required(self) -> None:
        cat = next(t for t in self.tools if t["name"] == "cat")
        self.assertIn("path", cat["inputSchema"]["properties"])
        self.assertIn("path", cat["inputSchema"]["required"])

    def test_ls_has_path_property(self) -> None:
        ls_ = next(t for t in self.tools if t["name"] == "ls")
        self.assertIn("path", ls_["inputSchema"]["properties"])

    def test_boolean_flag_has_boolean_type(self) -> None:
        cat = next(t for t in self.tools if t["name"] == "cat")
        self.assertEqual(cat["inputSchema"]["properties"]["raw"].get("type"), "boolean")

    def test_choices_become_enum(self) -> None:
        tl = next(t for t in self.tools if t["name"] == "tool-list")
        fmt_prop = tl["inputSchema"]["properties"].get("format", {})
        self.assertIn("enum", fmt_prop)

    def test_descriptions_are_non_empty(self) -> None:
        empty = [
            t["name"]
            for t in self.tools
            if not t["description"]
            and not t["name"].startswith("_")
            and "dummy" not in t["name"]
            and "test" not in t["name"]
        ]
        self.assertEqual(empty, [], f"Tools with empty descriptions: {empty}")

    def test_openai_format(self) -> None:
        result = tools_openai(self.tools)
        self.assertGreaterEqual(len(result), 114)  # plugin commands may increase total
        self.assertEqual(result[0]["type"], "function")
        self.assertIn("name", result[0]["function"])
        self.assertIn("description", result[0]["function"])
        self.assertIn("parameters", result[0]["function"])

    def test_anthropic_format(self) -> None:
        result = tools_anthropic(self.tools)
        self.assertGreaterEqual(len(result), 114)  # plugin commands may increase total
        self.assertIn("name", result[0])
        self.assertIn("description", result[0])
        self.assertIn("input_schema", result[0])

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, "-m", "aicoreutils", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
            env=env,
            timeout=30,
        )

    def test_tool_list_openai_cli(self) -> None:
        cp = self._run_cli("tool-list", "--format", "openai", "--raw")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertGreaterEqual(len(data), 114)  # allow plugin commands to increase total
        self.assertEqual(data[0]["type"], "function")

    def test_tool_list_anthropic_cli(self) -> None:
        cp = self._run_cli("tool-list", "--format", "anthropic", "--raw")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertGreaterEqual(len(data), 114)  # allow plugin commands to increase total
        self.assertIn("input_schema", data[0])

    def test_tool_list_default_format(self) -> None:
        cp = self._run_cli("tool-list", "--raw")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertIn("tools", data)
        self.assertIn("count", data)


# ── mcp_server ──


def _mcp_request(proc: subprocess.Popen[Any], method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    proc.stdin.write(msg + "\n")  # type: ignore[union-attr]
    proc.stdin.flush()  # type: ignore[union-attr]
    return json.loads(proc.stdout.readline())  # type: ignore[union-attr]


class McpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.env = {**dict(subprocess.os.environ), "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}

    def _start_server(self) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=self.env,
            cwd=str(ROOT),
        )

    def test_initialize(self) -> None:
        proc = self._start_server()
        try:
            resp = _mcp_request(proc, "initialize", {"protocolVersion": "2024-11-05"})
            self.assertIn("result", resp)
            info = resp["result"].get("serverInfo", {})
            self.assertEqual(info.get("name"), "aicoreutils")
            self.assertIn("tools", resp["result"].get("capabilities", {}))
        finally:
            proc.terminate()

    def test_tools_list(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/list")
            tools = resp["result"]["tools"]
            self.assertEqual(len(tools), 114)  # allow plugin commands to increase total
        finally:
            proc.terminate()

    def test_tools_call_pwd(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "pwd", "arguments": {}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), data)
        finally:
            proc.terminate()

    def test_tools_call_ls(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "ls", "arguments": {"path": "project"}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), data)
            self.assertGreater(data.get("result", {}).get("count", 0), 0)
        finally:
            proc.terminate()

    def test_tools_call_cat(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(
                proc, "tools/call", {"name": "cat", "arguments": {"path": "README.md", "max_bytes": "100"}}
            )
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), data)
        finally:
            proc.terminate()

    def test_tools_call_seq(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "seq", "arguments": {"numbers": ["1", "2", "5"]}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertTrue(data.get("ok"), data)
            self.assertEqual(data.get("result", {}).get("values", []), [1.0, 3.0, 5.0])
        finally:
            proc.terminate()

    def test_tools_call_unknown_command(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "tools/call", {"name": "nonexistent_cmd", "arguments": {}})
            content = resp["result"]["content"][0]["text"]
            data = json.loads(content)
            self.assertFalse(data.get("ok"))
        finally:
            proc.terminate()

    def test_unknown_method_returns_error(self) -> None:
        proc = self._start_server()
        try:
            _mcp_request(proc, "initialize")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()
            resp = _mcp_request(proc, "unknown/method")
            self.assertIn("error", resp)
            self.assertEqual(resp["error"]["code"], -32601)
        finally:
            proc.terminate()


if __name__ == "__main__":
    unittest.main()
