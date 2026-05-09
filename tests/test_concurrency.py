"""Concurrency tests for async_interface and MCP server.

Verifies:
- async_interface.run_async_many can run multiple commands concurrently
- Commands don't interfere with each other
- MCP server handles concurrent JSON-RPC requests without response interleaving
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


def _mcp_env() -> dict[str, str]:
    from support import test_env as _te

    return _te({"PYTHONIOENCODING": "utf-8"})


class AsyncInterfaceConcurrencyTests(unittest.TestCase):
    def test_run_async_many_concurrent_sort(self) -> None:
        async def _run() -> None:
            from aicoreutils.async_interface import run_async_many

            with TemporaryDirectory() as raw:
                root = Path(raw)
                for i in range(10):
                    (root / f"file_{i:02d}.txt").write_text(
                        f"zebra\nalpha\nbeta\ngamma\nline_{i:04d}\n", encoding="utf-8"
                    )

                commands = [("sort", str(root / f"file_{i:02d}.txt")) for i in range(10)]
                t0 = time.monotonic()
                results = await run_async_many(commands, concurrency=10)
                elapsed = time.monotonic() - t0

                self.assertEqual(len(results), 10)
                for r in results:
                    self.assertTrue(r["ok"])
                self.assertLess(elapsed, 30.0, f"Concurrent sort took {elapsed:.1f}s")

        asyncio.run(_run())

    def test_run_async_single_command(self) -> None:
        async def _run() -> None:
            from aicoreutils.async_interface import run_async

            with TemporaryDirectory() as raw:
                root = Path(raw)
                (root / "test.txt").write_text("hello world\n", encoding="utf-8")
                result = await run_async("cat", str(root / "test.txt"))
                self.assertTrue(result["ok"])
                self.assertIn("hello world", result["result"]["content"])

        asyncio.run(_run())

    def test_run_async_many_with_semaphore(self) -> None:
        async def _run() -> None:
            from aicoreutils.async_interface import run_async_many

            with TemporaryDirectory() as raw:
                root = Path(raw)
                for i in range(5):
                    (root / f"f{i}.txt").write_text(f"content_{i}\n", encoding="utf-8")

                # concurrency=1 forces sequential execution
                commands = [("cat", str(root / f"f{i}.txt")) for i in range(5)]
                results = await run_async_many(commands, concurrency=1)
                self.assertEqual(len(results), 5)
                for _i, r in enumerate(results):
                    self.assertTrue(r["ok"])

        asyncio.run(_run())

    def test_run_async_timeout(self) -> None:
        async def _run() -> None:
            from aicoreutils.async_interface import run_async

            with self.assertRaises(TimeoutError):
                await run_async("sleep", "10", timeout=0.5)

        asyncio.run(_run())


class MCPConcurrencyTests(unittest.TestCase):
    def _mcp_request(self, method: str, params: dict | None = None, request_id: int = 1) -> str:
        msg = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            msg["params"] = params
        return json.dumps(msg, ensure_ascii=False) + "\n"

    def test_mcp_server_handles_sequential_requests(self) -> None:
        """Send multiple requests one after another, verify each gets a valid response."""
        requests = [
            self._mcp_request("initialize", {"protocolVersion": "2024-11-05"}, 1),
            self._mcp_request("tools/list", request_id=2),
            self._mcp_request("tools/call", {"name": "echo", "arguments": {"text": ["hello"]}}, 3),
        ]

        proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", "--read-only"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_mcp_env(),
        )

        try:
            for req in requests:
                proc.stdin.write(req.encode("utf-8"))  # type: ignore[union-attr]
                proc.stdin.flush()  # type: ignore[union-attr]
                line = proc.stdout.readline()  # type: ignore[union-attr]
                self.assertTrue(line, f"No response for request: {req[:50]}")
                resp = json.loads(line)
                self.assertIn("id", resp)
                self.assertNotIn("error", resp)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_mcp_server_rejects_denied_command(self) -> None:
        """Verify MCP server rejects destructive commands in read-only mode."""
        req = self._mcp_request(
            "tools/call",
            {"name": "rm", "arguments": {"target": ["/tmp/nonexistent_xyz"]}},
            1,
        )

        proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", "--read-only"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_mcp_env(),
        )

        try:
            # First send initialize
            proc.stdin.write(self._mcp_request("initialize", {"protocolVersion": "2024-11-05"}, 1).encode())  # type: ignore[union-attr]
            proc.stdin.flush()  # type: ignore[union-attr]
            proc.stdout.readline()  # type: ignore[union-attr]
            # Then the rm request
            proc.stdin.write(req.encode())  # type: ignore[union-attr]
            proc.stdin.flush()  # type: ignore[union-attr]
            line = proc.stdout.readline()  # type: ignore[union-attr]
            resp = json.loads(line)
            self.assertIn("result", resp)
            self.assertTrue(resp["result"].get("isError"))
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_mcp_server_handles_burst_requests(self) -> None:
        """Send a burst of 50 requests without waiting, verify all get responses."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", "--read-only"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_mcp_env(),
        )

        try:
            # Initialize
            proc.stdin.write(self._mcp_request("initialize", {"protocolVersion": "2024-11-05"}, 1).encode())  # type: ignore[union-attr]
            proc.stdin.flush()  # type: ignore[union-attr]
            proc.stdout.readline()  # type: ignore[union-attr]

            # Send burst of echo requests
            burst_count = 50
            for i in range(burst_count):
                req = self._mcp_request("tools/call", {"name": "echo", "arguments": {"text": [f"msg{i}"]}}, i + 2)
                proc.stdin.write(req.encode())  # type: ignore[union-attr]
            proc.stdin.flush()  # type: ignore[union-attr]

            # Collect all responses
            responses = []
            for _ in range(burst_count):
                line = proc.stdout.readline()  # type: ignore[union-attr]
                self.assertTrue(line, f"Missing response after {len(responses)} received")
                resp = json.loads(line)
                self.assertNotIn("error", resp)
                responses.append(resp)

            self.assertEqual(len(responses), burst_count)
            # Verify no response interleaving (each response is a single valid JSON line)
            result_ids = {r["id"] for r in responses}
            self.assertEqual(len(result_ids), burst_count, "Duplicate or missing response IDs")
        finally:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
