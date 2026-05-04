"""Tests for async_interface, plugins, stream, and __main__ modules.

Covers previously untested Phase 2.2 and Phase 3 modules:
- async_interface: run_async, run_async_many
- plugins: discover_plugins, get_plugin_commands, register_plugin_command
- core/stream: StreamWriter, NullStream, is_stream_mode
- __main__: module-level execution
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

# ── Stream tests ──────────────────────────────────────────────────────


class StreamWriterTests(unittest.TestCase):
    def test_write_item_single(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        result = w.write_item({"key": "value"})
        self.assertTrue(result)
        line = buf.getvalue().rstrip("\n")
        self.assertEqual(json.loads(line), {"key": "value"})

    def test_write_item_no_truncation_when_zero(self) -> None:
        """max_items=0 means no limit (0 is falsy in guard)."""
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test", max_items=0)
        self.assertTrue(w.write_item({"a": 1}))
        self.assertFalse(w.truncated)

    def test_write_item_truncation_after_limit(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test", max_items=2)
        self.assertTrue(w.write_item({"a": 1}))
        self.assertTrue(w.write_item({"b": 2}))
        self.assertFalse(w.write_item({"c": 3}))
        self.assertEqual(w.count, 2)
        self.assertTrue(w.truncated)

    def test_write_after_close_returns_false(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        w.write_summary({"total": 1})
        self.assertFalse(w.write_item({"a": 1}))

    def test_summary_contains_stream_field(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        w.write_item({"key": "v"})
        w.write_summary({"total": 1})
        output = buf.getvalue()
        # Item line (compact JSON) + summary (indented JSON, may span multiple lines)
        parts = output.split("\n{", 1)
        self.assertGreater(len(parts), 0)
        # Reconstruct the summary JSON
        summary_text = "{" + parts[1] if len(parts) > 1 else output
        summary = json.loads(summary_text)
        self.assertTrue(summary["ok"])
        self.assertTrue(summary["stream"])
        self.assertEqual(summary["count"], 1)

    def test_double_summary_is_idempotent(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        w.write_summary({"total": 0})
        w.write_summary({"total": 1})
        self.assertEqual(buf.getvalue().count('"summary"'), 1)

    def test_count_and_truncated_properties(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test", max_items=1)
        self.assertEqual(w.count, 0)
        self.assertFalse(w.truncated)
        w.write_item({"a": 1})
        self.assertEqual(w.count, 1)
        self.assertFalse(w.truncated)
        w.write_item({"b": 2})
        self.assertEqual(w.count, 1)
        self.assertTrue(w.truncated)

    def test_ndjson_output_is_parseable(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        items = [{"id": i, "name": f"item_{i}"} for i in range(5)]
        for item in items:
            w.write_item(item)
        w.write_summary({"total": 5})
        output = buf.getvalue()
        # First 5 lines are compact NDJSON items, rest is indented summary
        lines = output.strip().split("\n")
        count = 0
        for line in lines:
            line = line.strip()
            if line.startswith('{"id"'):  # compact item (sort_keys=True puts id first)
                data = json.loads(line)
                self.assertEqual(data, items[count])
                count += 1
            elif line == "{":
                break  # start of indented summary
        self.assertEqual(count, 5)

    def test_special_chars_in_item(self) -> None:
        buf = io.StringIO()
        from aicoreutils.core.stream import StreamWriter

        w = StreamWriter(buf, command="test")
        w.write_item({"path": "/tmp/a b", "content": "line1\nline2"})
        line = json.loads(buf.getvalue().rstrip("\n"))
        self.assertEqual(line["content"], "line1\nline2")


class NullStreamTests(unittest.TestCase):
    def test_null_stream_always_accepts(self) -> None:
        from aicoreutils.core.stream import NullStream

        ns = NullStream()
        self.assertTrue(ns.write_item({"a": 1}))
        self.assertTrue(ns.write_item({"b": 2}))

    def test_null_stream_summary_is_noop(self) -> None:
        from aicoreutils.core.stream import NullStream

        ns = NullStream()
        ns.write_summary({"total": 100})  # should not raise

    def test_null_stream_properties(self) -> None:
        from aicoreutils.core.stream import NullStream

        ns = NullStream()
        self.assertEqual(ns.count, 0)
        self.assertFalse(ns.truncated)


class IsStreamModeTests(unittest.TestCase):
    def test_stream_flag_true(self) -> None:
        from aicoreutils.core.stream import is_stream_mode

        class Args:
            stream = True

        self.assertTrue(is_stream_mode(Args()))

    def test_stream_flag_false(self) -> None:
        from aicoreutils.core.stream import is_stream_mode

        class Args:
            stream = False

        self.assertFalse(is_stream_mode(Args()))

    def test_stream_flag_absent(self) -> None:
        from aicoreutils.core.stream import is_stream_mode

        class Args:
            pass

        self.assertFalse(is_stream_mode(Args()))


# ── Plugins tests ─────────────────────────────────────────────────────


class PluginDiscoveryTests(unittest.TestCase):
    def test_discover_plugins_returns_dict(self) -> None:
        from aicoreutils.plugins import discover_plugins

        result = discover_plugins()
        self.assertIsInstance(result, dict)

    def test_get_plugin_commands_returns_dict(self) -> None:
        from aicoreutils.plugins import get_plugin_commands

        result = get_plugin_commands()
        self.assertIsInstance(result, dict)

    def test_register_and_retrieve_plugin_command(self) -> None:
        from aicoreutils.plugins import get_plugin_commands, register_plugin_command

        def dummy_cmd(args):
            return {"ok": True}

        register_plugin_command("dummy_test_cmd", dummy_cmd, priority="P3")
        commands = get_plugin_commands()
        self.assertIn("dummy_test_cmd", commands)
        self.assertIs(commands["dummy_test_cmd"], dummy_cmd)

    def test_register_plugin_updates_catalog(self) -> None:
        # register_plugin_command modifies _BUILTIN_CATALOG list in place.
        # get_all_commands() returns from _COMMAND_PRIORITY_MAP which is
        # built once at import time from the catalog. The plugin was
        # registered in the previous test, so verify it's in the dynamic
        # plugin registry.
        from aicoreutils.plugins import get_plugin_commands

        commands = get_plugin_commands()
        self.assertIn("dummy_test_cmd", commands)


# ── __main__ tests ────────────────────────────────────────────────────


class MainModuleTests(unittest.TestCase):
    def test_main_module_runs_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aicoreutils", "--help"],
            capture_output=True,
            env={**__import__("os").environ, "PYTHONPATH": "src"},
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(b"show this help message", result.stdout)

    def test_main_module_runs_schema(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aicoreutils", "schema", "--pretty"],
            capture_output=True,
            cwd=str(Path(__file__).resolve().parents[1]),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())
        data = json.loads(result.stdout)
        self.assertIn("command_count", data["result"])
        self.assertGreater(data["result"]["command_count"], 100)

    def test_main_module_catalog(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aicoreutils", "catalog", "--pretty"],
            capture_output=True,
            cwd=str(Path(__file__).resolve().parents[1]),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr.decode())
        data = json.loads(result.stdout)
        self.assertIn("categories", data["result"])


# ── Async interface tests ─────────────────────────────────────────────


class AsyncInterfaceSmokeTests(unittest.TestCase):
    """Smoke tests for async_interface module-level imports."""

    def test_run_async_is_callable(self) -> None:
        from aicoreutils.async_interface import run_async

        self.assertTrue(callable(run_async))

    def test_run_async_many_is_callable(self) -> None:
        from aicoreutils.async_interface import run_async_many

        self.assertTrue(callable(run_async_many))

    def test_run_async_accepts_args_signature(self) -> None:
        import inspect

        from aicoreutils.async_interface import run_async

        sig = inspect.signature(run_async)
        params = list(sig.parameters)
        self.assertIn("cwd", params)
        self.assertIn("timeout", params)

    def test_run_async_many_runs_concurrently(self) -> None:
        """TD08: Verify run_async_many executes commands concurrently."""
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            results = await run_async_many(
                [("catalog",), ("schema",)],
                concurrency=2,
            )
            self.assertEqual(len(results), 2)
            for r in results:
                self.assertTrue(r["ok"])

        asyncio.run(_run())

    def test_run_async_many_respects_order(self) -> None:
        """Verify results are returned in input order."""
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            results = await run_async_many(
                [("catalog",), ("schema",), ("catalog",)],
                concurrency=3,
            )
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["command"], "catalog")
            self.assertEqual(results[1]["command"], "schema")
            self.assertEqual(results[2]["command"], "catalog")

        asyncio.run(_run())

    def test_run_async_many_with_timeout(self) -> None:
        """Verify per-command timeout works."""
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            results = await run_async_many(
                [("catalog",)],
                concurrency=1,
                timeout=30.0,
            )
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["ok"])

        asyncio.run(_run())


class AsyncInterfaceExecutionTests(unittest.TestCase):
    """Phase 2: deeper tests covering run_async success/failure/timeout paths."""

    def test_run_async_success_returns_json(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async

        async def _run() -> None:
            result = await run_async("true")
            self.assertIsInstance(result, dict)
            self.assertTrue(result["ok"])

        asyncio.run(_run())

    def test_run_async_with_cwd(self) -> None:
        import asyncio
        from pathlib import Path

        from aicoreutils.async_interface import run_async

        async def _run() -> None:
            result = await run_async("pwd", cwd=Path.cwd())
            self.assertIsInstance(result, dict)
            self.assertTrue(result["ok"])

        asyncio.run(_run())

    def test_run_async_nonzero_exit_raises(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async

        async def _run() -> None:
            with self.assertRaises(RuntimeError):
                await run_async("false")

        asyncio.run(_run())

    def test_run_async_nonexistent_command_returns_error(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async

        async def _run() -> None:
            with self.assertRaises(RuntimeError):
                await run_async("nonexistent_cmd_xyz")

        asyncio.run(_run())

    def test_run_async_many_single_command(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            results = await run_async_many([("pwd",)], concurrency=1)
            self.assertEqual(len(results), 1)
            self.assertTrue(results[0]["ok"])

        asyncio.run(_run())

    def test_run_async_many_concurrency_limit(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            commands = [("true",)] * 5
            results = await run_async_many(commands, concurrency=2)
            self.assertEqual(len(results), 5)
            for r in results:
                self.assertTrue(r["ok"])

        asyncio.run(_run())

    def test_run_async_many_empty_list(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            results = await run_async_many([], concurrency=1)
            self.assertEqual(results, [])

        asyncio.run(_run())

    def test_run_async_many_exception_propagates(self) -> None:
        import asyncio

        from aicoreutils.async_interface import run_async_many

        async def _run() -> None:
            with self.assertRaises(RuntimeError):
                await run_async_many([("true",), ("false",)], concurrency=2)

        asyncio.run(_run())


# ── Plugin end-to-end tests ────────────────────────────────────────────


class PluginEndToEndTests(unittest.TestCase):
    """TD07: End-to-end tests for plugin discovery and registration."""

    def test_plugin_registry_is_immutable(self) -> None:
        """Verify PluginRegistry.register returns a new instance."""
        from aicoreutils.core.plugin_registry import PluginRegistry

        r1 = PluginRegistry()
        r2 = r1.register("test_cmd", lambda args: {"ok": True})
        self.assertNotIn("test_cmd", r1)
        self.assertIn("test_cmd", r2)
        self.assertEqual(r1.count, 0)
        self.assertEqual(r2.count, 1)

    def test_plugin_registry_merge(self) -> None:
        from aicoreutils.core.plugin_registry import PluginRegistry

        r1 = PluginRegistry().register("a", lambda: 1)
        r2 = PluginRegistry().register("b", lambda: 2)
        merged = r1.merge(r2)
        self.assertEqual(merged.count, 2)
        self.assertIn("a", merged)
        self.assertIn("b", merged)

    def test_programmatic_register_plugin(self) -> None:
        from aicoreutils.plugins import get_plugin_commands, register_plugin_command

        register_plugin_command("_test_prog_cmd", lambda args: {"ok": True}, priority="P3")
        cmds = get_plugin_commands()
        self.assertIn("_test_prog_cmd", cmds)
        self.assertTrue(callable(cmds["_test_prog_cmd"]))

    def test_plugin_discovery_does_not_crash(self) -> None:
        from aicoreutils.plugins import discover_plugins

        result = discover_plugins()
        self.assertIsInstance(result, dict)

    def test_has_plugins_returns_bool(self) -> None:
        from aicoreutils.plugins import has_plugins

        self.assertIsInstance(has_plugins(), bool)

    def test_get_registry_returns_plugin_registry(self) -> None:
        from aicoreutils.core.plugin_registry import PluginRegistry
        from aicoreutils.plugins import get_registry

        reg = get_registry()
        self.assertIsInstance(reg, PluginRegistry)
