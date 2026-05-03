"""Unit tests for core layer: exit_codes, exceptions, envelope, config, plugin_registry."""

from __future__ import annotations

import dataclasses
import io
import json
import os
import unittest

from agentutils.core.config import DEFAULT_CONFIG, AgentConfig
from agentutils.core.envelope import _TOOL_VERSION, envelope, error_envelope, utc_iso, write_json
from agentutils.core.exceptions import AgentError
from agentutils.core.exit_codes import EXIT
from agentutils.core.plugin_registry import PluginRegistry

# ── exit_codes ──


class ExitCodesTests(unittest.TestCase):
    def test_all_keys_map_to_int(self) -> None:
        for code, val in EXIT.items():
            self.assertIsInstance(code, str)
            self.assertIsInstance(val, int)

    def test_ok_is_zero(self) -> None:
        self.assertEqual(EXIT["ok"], 0)

    def test_unique_exit_values_for_distinct_semantics(self) -> None:
        unique_vals = {v for k, v in EXIT.items() if k not in ("predicate_false", "general_error")}
        vals_list = [v for k, v in EXIT.items() if k not in ("predicate_false", "general_error")]
        self.assertEqual(len(unique_vals), len(vals_list))

    def test_unsafe_operation_uses_8(self) -> None:
        self.assertEqual(EXIT["unsafe_operation"], 8)


# ── exceptions ──


class AgentErrorTests(unittest.TestCase):
    def test_minimal_error(self) -> None:
        e = AgentError("not_found", "File does not exist")
        self.assertEqual(e.code, "not_found")
        self.assertEqual(e.message, "File does not exist")
        self.assertEqual(e.path, None)
        self.assertEqual(e.suggestion, None)
        self.assertEqual(e.details, {})

    def test_full_error(self) -> None:
        e = AgentError(
            "conflict",
            "Target exists",
            path="/tmp/foo",
            suggestion="Pass --allow-overwrite",
            details={"target": "/tmp/foo"},
        )
        self.assertEqual(e.path, "/tmp/foo")
        self.assertEqual(e.suggestion, "Pass --allow-overwrite")
        self.assertEqual(e.details, {"target": "/tmp/foo"})

    def test_exit_code_mapping(self) -> None:
        self.assertEqual(AgentError("ok", "").exit_code, 0)
        self.assertEqual(AgentError("not_found", "").exit_code, 3)
        self.assertEqual(AgentError("unsafe_operation", "").exit_code, 8)

    def test_unknown_code_falls_back_to_general_error(self) -> None:
        self.assertEqual(AgentError("nonexistent_code", "").exit_code, EXIT["general_error"])

    def test_to_dict_minimal(self) -> None:
        d = AgentError("usage", "Missing argument").to_dict()
        self.assertEqual(d, {"code": "usage", "message": "Missing argument"})

    def test_to_dict_with_optional_fields(self) -> None:
        d = AgentError("not_found", "Missing", path="/tmp/x", suggestion="Check path").to_dict()
        self.assertEqual(d["path"], "/tmp/x")
        self.assertEqual(d["suggestion"], "Check path")
        self.assertNotIn("details", d)

    def test_to_dict_with_details(self) -> None:
        d = AgentError("io_error", "Disk full", details={"errno": 28}).to_dict()
        self.assertEqual(d["details"], {"errno": 28})

    def test_is_exception(self) -> None:
        e = AgentError("usage", "test")
        self.assertIsInstance(e, Exception)
        self.assertEqual(str(e), "test")


# ── envelope ──


class EnvelopeTests(unittest.TestCase):
    def test_utc_iso_format(self) -> None:
        result = utc_iso(1700000000.0)
        self.assertTrue(result.endswith("Z"))
        self.assertIn("T", result)

    def test_utc_iso_roundtrip(self) -> None:
        import datetime as dt

        ts = 1700000000.0
        result = utc_iso(ts)
        parsed = dt.datetime.fromisoformat(result.replace("Z", "+00:00"))
        self.assertEqual(parsed.timestamp(), ts)

    def test_envelope_basic(self) -> None:
        env = envelope("ls", {"entries": []})
        self.assertTrue(env["ok"])
        self.assertEqual(env["command"], "ls")
        self.assertEqual(env["tool"], "agentutils")
        self.assertEqual(env["version"], _TOOL_VERSION)
        self.assertIsInstance(env["warnings"], list)

    def test_envelope_with_warnings(self) -> None:
        env = envelope("rm", {"removed": 1}, warnings=["skipped read-only file"])
        self.assertEqual(env["warnings"], ["skipped read-only file"])

    def test_error_envelope(self) -> None:
        e = AgentError("not_found", "No such file")
        env = error_envelope("cat", e)
        self.assertFalse(env["ok"])
        self.assertEqual(env["command"], "cat")
        self.assertEqual(env["error"]["code"], "not_found")

    def test_error_envelope_command_none(self) -> None:
        e = AgentError("usage", "Bad arguments")
        env = error_envelope(None, e)
        self.assertIsNone(env["command"])
        self.assertFalse(env["ok"])

    def test_write_json_compact(self) -> None:
        buf = io.StringIO()
        write_json(buf, {"a": 1, "b": 2})
        output = buf.getvalue()
        self.assertIn("\n", output)
        parsed = json.loads(output)
        self.assertEqual(parsed, {"a": 1, "b": 2})

    def test_write_json_pretty(self) -> None:
        buf = io.StringIO()
        write_json(buf, {"a": 1}, pretty=True)
        output = buf.getvalue()
        self.assertIn("  ", output)
        self.assertGreater(output.count("\n"), 1)

    def test_write_json_unicode(self) -> None:
        buf = io.StringIO()
        write_json(buf, {"key": "\u4e2d\u6587"})
        output = buf.getvalue()
        self.assertIn("\u4e2d\u6587", output)


# ── config ──


class AgentConfigTests(unittest.TestCase):
    def test_default_values(self) -> None:
        c = AgentConfig()
        self.assertEqual(c.max_lines, 10_000)
        self.assertEqual(c.max_bytes, 1_048_576)
        self.assertEqual(c.tab_size, 8)
        self.assertEqual(c.async_concurrency, 10)

    def test_default_config_instance(self) -> None:
        self.assertIsInstance(DEFAULT_CONFIG, AgentConfig)
        self.assertEqual(DEFAULT_CONFIG.max_lines, 10_000)

    def test_frozen_no_mutate(self) -> None:
        c = AgentConfig()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            c.max_lines = 999  # type: ignore[misc]

    def test_from_env_no_overrides(self) -> None:
        c = AgentConfig.from_env()
        self.assertEqual(c.max_lines, 10_000)

    def test_from_env_int_override(self) -> None:
        os.environ["AGENTUTILS_MAX_LINES"] = "500"
        try:
            c = AgentConfig.from_env()
            self.assertEqual(c.max_lines, "500")
        finally:
            del os.environ["AGENTUTILS_MAX_LINES"]

    def test_from_env_float_override(self) -> None:
        os.environ["AGENTUTILS_ASYNC_TIMEOUT"] = "60.5"
        try:
            c = AgentConfig.from_env()
            self.assertEqual(c.async_timeout, "60.5")
        finally:
            del os.environ["AGENTUTILS_ASYNC_TIMEOUT"]

    def test_from_env_path_override(self) -> None:
        os.environ["AGENTUTILS_CWD"] = "/tmp/test"
        try:
            c = AgentConfig.from_env()
            self.assertEqual(str(c.cwd), "/tmp/test")
        finally:
            del os.environ["AGENTUTILS_CWD"]

    def test_from_env_unknown_type_passed_as_string(self) -> None:
        os.environ["AGENTUTILS_CWD"] = "just_string_for_unknown_type"
        try:
            c = AgentConfig.from_env()
            self.assertIsInstance(c.cwd, str)
        finally:
            del os.environ["AGENTUTILS_CWD"]


# ── plugin_registry ──


def _dummy_cmd(args: object) -> dict:
    return {"ok": True}


class PluginRegistryTests(unittest.TestCase):
    def test_empty_registry(self) -> None:
        r = PluginRegistry()
        self.assertEqual(r.count, 0)
        self.assertEqual(r.names, set())
        self.assertEqual(r.items(), [])

    def test_contains(self) -> None:
        r = PluginRegistry().register("test", _dummy_cmd)
        self.assertIn("test", r)
        self.assertNotIn("nope", r)

    def test_getitem(self) -> None:
        r = PluginRegistry().register("test", _dummy_cmd)
        self.assertIs(r["test"], _dummy_cmd)

    def test_get_with_default(self) -> None:
        r = PluginRegistry()
        self.assertIsNone(r.get("nope"))
        self.assertIs(r.get("nope", _dummy_cmd), _dummy_cmd)

    def test_register_returns_new_instance(self) -> None:
        r1 = PluginRegistry()
        r2 = r1.register("cmd", _dummy_cmd)
        self.assertEqual(r1.count, 0)
        self.assertEqual(r2.count, 1)

    def test_register_overwrite(self) -> None:
        def alt_cmd(args: object) -> dict:
            return {"different": True}

        r = PluginRegistry().register("cmd", _dummy_cmd).register("cmd", alt_cmd)
        self.assertEqual(r.count, 1)
        self.assertIs(r["cmd"], alt_cmd)

    def test_merge(self) -> None:
        r1 = PluginRegistry().register("a", _dummy_cmd)
        r2 = PluginRegistry().register("b", _dummy_cmd)
        r3 = r1.merge(r2)
        self.assertEqual(r3.count, 2)
        self.assertIn("a", r3)
        self.assertIn("b", r3)
        self.assertEqual(r1.count, 1)

    def test_merge_returns_new_instance(self) -> None:
        r1 = PluginRegistry().register("x", _dummy_cmd)
        r2 = PluginRegistry().register("y", _dummy_cmd)
        r3 = r1.merge(r2)
        self.assertIsNot(r3, r1)
        self.assertIsNot(r3, r2)

    def test_names_is_set(self) -> None:
        r = PluginRegistry().register("a", _dummy_cmd).register("b", _dummy_cmd)
        self.assertEqual(r.names, {"a", "b"})

    def test_count_reflects_commands(self) -> None:
        r = PluginRegistry().register("a", _dummy_cmd).register("b", _dummy_cmd)
        self.assertEqual(r.count, 2)

    def test_items_returns_list_of_tuples(self) -> None:
        r = PluginRegistry().register("cmd", _dummy_cmd)
        items = r.items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], "cmd")

    def test_repr(self) -> None:
        r = PluginRegistry().register("b", _dummy_cmd).register("a", _dummy_cmd)
        self.assertIn("PluginRegistry", repr(r))
        self.assertIn("a", repr(r))

    def test_discover_no_plugins(self) -> None:
        r = PluginRegistry.discover()
        self.assertIsInstance(r, PluginRegistry)
        self.assertEqual(r.count, 0)

    def test_init_with_dict(self) -> None:
        r = PluginRegistry({"x": _dummy_cmd})
        self.assertEqual(r.count, 1)
        self.assertIn("x", r)


if __name__ == "__main__":
    unittest.main()
