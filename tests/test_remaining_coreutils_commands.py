from __future__ import annotations

import base64
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from support import parse_stdout, run_cli


class RemainingCoreutilsCommandsTests(unittest.TestCase):
    def test_coreutils_lists_new_command_surface(self) -> None:
        payload = parse_stdout(run_cli("coreutils"))
        commands = payload["result"]["commands"]
        for command in ("coreutils", "chroot", "pinky", "stdbuf", "stty", "chcon", "runcon"):
            self.assertIn(command, commands)
        self.assertEqual(payload["result"]["count"], len(commands))

        raw = run_cli("coreutils", "--list", "--raw")
        self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertIn("runcon\n", raw.stdout)

    def test_pinky_returns_user_records(self) -> None:
        payload = parse_stdout(run_cli("pinky"))
        self.assertGreaterEqual(payload["result"]["count"], 1)
        self.assertIn("user", payload["result"]["entries"][0])

        raw = run_cli("pinky", "--raw")
        self.assertEqual(raw.returncode, 0, raw.stderr)
        self.assertTrue(raw.stdout.strip())

    def test_stdbuf_dry_run_and_bounded_execution(self) -> None:
        dry = parse_stdout(run_cli("stdbuf", "--output", "L", "--dry-run", "--", sys.executable, "-c", "print('ok')"))
        self.assertTrue(dry["result"]["dry_run"])
        self.assertEqual(dry["result"]["buffering"]["stdout"], "L")

        ran = parse_stdout(
            run_cli("stdbuf", "--output", "0", "--timeout", "5", "--", sys.executable, "-c", "print('ok')")
        )
        stdout = base64.b64decode(ran["result"]["stdout_base64"]).decode("utf-8")
        self.assertEqual(stdout.replace("\r\n", "\n"), "ok\n")

    def test_stty_inspect_and_dry_run_settings(self) -> None:
        inspected = parse_stdout(run_cli("stty"))
        self.assertIn("stdin_is_tty", inspected["result"])
        self.assertIn("supported", inspected["result"])

        planned = parse_stdout(run_cli("stty", "--dry-run", "--", "raw", "-echo"))
        self.assertTrue(planned["result"]["planned"])
        self.assertEqual(planned["result"]["settings"], ["raw", "-echo"])

    def test_chroot_requires_explicit_confirmation(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            dry = parse_stdout(run_cli("chroot", ".", "--dry-run", "--", sys.executable, "-c", "print('ok')", cwd=cwd))
            self.assertTrue(dry["result"]["dry_run"])
            self.assertEqual(Path(dry["result"]["root"]), cwd.resolve())

            blocked = run_cli("chroot", ".", "--", sys.executable, "-c", "print('ok')", cwd=cwd)
            self.assertEqual(blocked.returncode, 8)
            self.assertEqual(json.loads(blocked.stderr)["error"]["code"], "unsafe_operation")

    def test_chcon_dry_run_and_safety_gate(self) -> None:
        with TemporaryDirectory() as raw:
            cwd = Path(raw)
            (cwd / "item.txt").write_text("payload", encoding="utf-8")

            dry = parse_stdout(run_cli("chcon", "system_u:object_r:tmp_t:s0", "item.txt", "--dry-run", cwd=cwd))
            self.assertEqual(dry["result"]["count"], 1)
            self.assertTrue(dry["result"]["operations"][0]["dry_run"])

            blocked = run_cli("chcon", "system_u:object_r:tmp_t:s0", "item.txt", cwd=cwd)
            self.assertEqual(blocked.returncode, 8)
            self.assertEqual(json.loads(blocked.stderr)["error"]["code"], "unsafe_operation")

    def test_runcon_dry_run_and_safety_gate(self) -> None:
        dry = parse_stdout(run_cli("runcon", "system_u:system_r:init_t:s0", "--dry-run", "--", sys.executable, "-V"))
        self.assertTrue(dry["result"]["dry_run"])
        self.assertIn(sys.executable, dry["result"]["command"])

        blocked = run_cli("runcon", "system_u:system_r:init_t:s0", "--", sys.executable, "-V")
        self.assertEqual(blocked.returncode, 8)
        self.assertEqual(json.loads(blocked.stderr)["error"]["code"], "unsafe_operation")


if __name__ == "__main__":
    unittest.main()
