#!/usr/bin/env python3
"""24-hour stress test runner for aicoreutils.

Usage:
    python tests/stress/stress_runner.py [--duration-hours 24] [--seed 42]

Runs random CLI commands and MCP requests in a loop, tracking:
- Crash count
- Memory growth
- File descriptor leaks
- Zombie child processes
- Response validity

Writes periodic checkpoints to $GITHUB_STEP_SUMMARY (when available)
and final metrics to metrics.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.stress.command_fuzzer import CommandFuzzer
from tests.stress.mcp_stress_client import MCPStressClient, read_response, send_request
from tests.stress.metrics import LeakDetector, child_count

SRC = Path(__file__).resolve().parents[3] / "src"


def _test_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return env


def _run_cli(cmd: str, args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "aicoreutils", cmd, *args],
        cwd=cwd,
        capture_output=True,
        timeout=60,
        env=_test_env(),
    )


def _checkpoint(msg: str) -> None:
    """Write checkpoint to GITHUB_STEP_SUMMARY and stderr."""
    ts = datetime.now(UTC).isoformat()
    line = f"[{ts}] {msg}"
    print(line, file=sys.stderr, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(line + "\n")


def _main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-hours", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--checkpoint-minutes", type=int, default=15)
    args = ap.parse_args()

    deadline = time.monotonic() + args.duration_hours * 3600
    leak = LeakDetector()

    # Truncate summary file
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "w") as fh:
            fh.write(f"# AICoreUtils {args.duration_hours}h Stress Test\n\n")

    _checkpoint(
        f"Starting {args.duration_hours}h stress test (seed={args.seed}, checkpoint every {args.checkpoint_minutes}min)"
    )

    leak.set_baseline()

    with TemporaryDirectory() as tmp:
        fuzzer = CommandFuzzer(tmp, seed=args.seed)
        mcp_client = MCPStressClient(seed=args.seed)

        # Start MCP server
        mcp_proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils.mcp_server", "--read-only"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_test_env(),
        )
        send_request(mcp_proc, mcp_client.initialize_request())
        resp = read_response(mcp_proc)
        if not resp or "error" in resp:
            _checkpoint(f"MCP init failed: {resp}")
            mcp_proc.terminate()
            return 1

        last_checkpoint = time.monotonic()
        stats = {
            "cli_runs": 0,
            "cli_crashes": 0,
            "mcp_requests": 0,
            "mcp_errors": 0,
            "timeouts": 0,
            "invalid_responses": 0,
        }
        crash_log: list[dict] = []

        try:
            while time.monotonic() < deadline:
                # 70% CLI, 30% MCP
                if fuzzer._rng.random() < 0.7:
                    cmd, cargs = fuzzer.random_command()
                    try:
                        result = _run_cli(cmd, cargs, tmp)
                        stats["cli_runs"] += 1
                        if result.returncode != 0 and cmd not in ("false",):
                            stats["cli_crashes"] += 1
                            crash_log.append(
                                {
                                    "command": cmd,
                                    "args": cargs,
                                    "rc": result.returncode,
                                    "stderr": result.stderr[:500],
                                }
                            )
                            if len(crash_log) <= 5:
                                _checkpoint(f"CLI crash: {cmd} {' '.join(cargs[:5])} rc={result.returncode}")
                        # Verify JSON if not raw
                        if "--raw" not in cargs and result.returncode == 0 and result.stdout.strip():
                            try:
                                data = json.loads(result.stdout)
                                if not isinstance(data, dict) or "ok" not in data:
                                    stats["invalid_responses"] += 1
                            except json.JSONDecodeError:
                                stats["invalid_responses"] += 1
                    except subprocess.TimeoutExpired:
                        stats["timeouts"] += 1
                    except Exception:
                        stats["cli_crashes"] += 1
                else:
                    # MCP request
                    req = mcp_client.random_tool_call()
                    try:
                        send_request(mcp_proc, req)
                        resp = read_response(mcp_proc)
                        stats["mcp_requests"] += 1
                        if resp is None or "error" in resp:
                            stats["mcp_errors"] += 1
                    except Exception:
                        stats["mcp_errors"] += 1

                # Checkpoint
                if time.monotonic() - last_checkpoint > args.checkpoint_minutes * 60:
                    snap = leak.check()
                    elapsed = time.monotonic() - leak.baseline.timestamp  # type: ignore[union-attr]
                    _checkpoint(
                        f"t={elapsed / 3600:.1f}h | "
                        f"CLI: {stats['cli_runs']}r/{stats['cli_crashes']}c | "
                        f"MCP: {stats['mcp_requests']}r/{stats['mcp_errors']}e | "
                        f"RSS: {snap.rss_mb:.1f}MB | FD: {snap.fd_count}"
                    )
                    last_checkpoint = time.monotonic()

            # Final snapshot
            final = leak.check()
            elapsed = time.monotonic() - leak.baseline.timestamp  # type: ignore[union-attr]

        finally:
            mcp_proc.terminate()
            try:
                mcp_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mcp_proc.kill()

        # Write metrics
        metrics = {
            "duration_hours": args.duration_hours,
            "seed": args.seed,
            "elapsed_hours": round(elapsed / 3600, 2),
            "stats": stats,
            "resources": leak.summary(),
            "final_rss_mb": round(final.rss_mb, 2),
            "final_fd": final.fd_count,
            "zombie_count": child_count(),
            "crash_log": crash_log[:20],  # keep first 20 crashes
        }
        with open("metrics.json", "w") as fh:
            json.dump(metrics, fh, indent=2)

        _checkpoint(
            f"DONE | CLI {stats['cli_runs']}r/{stats['cli_crashes']}c | "
            f"MCP {stats['mcp_requests']}r/{stats['mcp_errors']}e | "
            f"RSS {leak.baseline.rss_mb:.1f}→{final.rss_mb:.1f}MB | "  # type: ignore[union-attr]
            f"FD {leak.baseline.fd_count}→{final.fd_count}"  # type: ignore[union-attr]
        )

        # Determine pass/fail
        failed = (
            stats["cli_crashes"] > 0
            or stats["invalid_responses"] > 0
            or child_count() > 0
            or final.rss_mb > leak.baseline.rss_mb * 3  # type: ignore[union-attr]
        )
        return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
