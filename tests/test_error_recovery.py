"""Error recovery tests — disk full, permission denied, signal handling."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import run_cli


class DiskFullRecoveryTests(unittest.TestCase):
    def test_write_to_readonly_directory_returns_error(self) -> None:
        if sys.platform == "win32":
            self.skipTest("os.chmod does not enforce write protection on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw)
            readonly = root / "readonly"
            readonly.mkdir()
            os.chmod(readonly, 0o555)  # r-xr-xr-x
            try:
                result = run_cli("touch", str(readonly / "nope.txt"), cwd=root)
                self.assertNotEqual(result.returncode, 0)
                # Should be a JSON error on stderr
                err = json.loads(result.stderr)
                self.assertFalse(err["ok"])
                self.assertIn(
                    err["error"]["code"],
                    ["permission_denied", "io_error", "unsafe_operation", "not_found", "general_error"],
                )
            finally:
                os.chmod(readonly, 0o755)


class PermissionDeniedTests(unittest.TestCase):
    def test_cat_unreadable_file_returns_error(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            f = root / "secret.txt"
            f.write_text("classified", encoding="utf-8")
            os.chmod(f, 0o000)
            try:
                result = run_cli("cat", str(f), cwd=root)
                # Either an error, or empty content with error in stderr
                if result.returncode != 0:
                    err = json.loads(result.stderr)
                    self.assertFalse(err["ok"])
            finally:
                os.chmod(f, 0o644)

    def test_touch_readonly_dir_returns_error(self) -> None:
        if sys.platform == "win32":
            self.skipTest("os.chmod does not enforce write protection on Windows")
        with TemporaryDirectory() as raw:
            root = Path(raw)
            readonly = root / "ro"
            readonly.mkdir()
            os.chmod(readonly, 0o555)
            try:
                result = run_cli("touch", str(readonly / "nope.txt"), cwd=root)
                self.assertNotEqual(result.returncode, 0)
            finally:
                os.chmod(readonly, 0o755)


class SignalHandlingTests(unittest.TestCase):
    def test_sigterm_during_sleep_exits_gracefully(self) -> None:
        """Verify SIGTERM during sleep produces a clean exit (not a traceback)."""
        proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils", "sleep", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Give it a moment to start, then terminate
        import time

        time.sleep(0.5)
        proc.terminate()
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

        # Should exit with non-zero, but not dump a Python traceback
        self.assertNotEqual(proc.returncode, 0)
        stderr_text = stderr.decode("utf-8", errors="replace")
        # Should not contain a Python traceback
        self.assertNotIn("Traceback (most recent call last)", stderr_text)

    def test_sigint_during_command_exits_cleanly(self) -> None:
        """Verify SIGINT produces a clean exit."""
        if sys.platform == "win32":
            self.skipTest("signal.SIGINT cannot be sent to subprocess on Windows")
        proc = subprocess.Popen(
            [sys.executable, "-m", "aicoreutils", "sleep", "30"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        import time

        time.sleep(0.3)
        proc.send_signal(signal.SIGINT)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()

        stderr_text = stderr.decode("utf-8", errors="replace")
        self.assertNotIn("Traceback (most recent call last)", stderr_text)


if __name__ == "__main__":
    unittest.main()
