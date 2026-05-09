"""Random command + argument generation for stress testing.

Reuses Hypothesis strategies where possible, falls back to hardcoded
command templates for commands without existing strategies.
"""

from __future__ import annotations

import random
import string

# High-frequency read-only commands (safe for random invocation)
READ_ONLY_COMMANDS = [
    "pwd",
    "whoami",
    "date",
    "uname",
    "hostname",
    "arch",
    "id",
    "groups",
    "uptime",
    "nproc",
    "tty",
    "printenv",
    "ls",
    "stat",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "tac",
    "nl",
    "fold",
    "base64",
    "expand",
    "unexpand",
    "md5sum",
    "sha256sum",
    "echo",
    "seq",
    "printf",
    "dirname",
    "basename",
    "realpath",
    "env",
    "df",
    "du",
    "catalog",
    "schema",
    "coreutils",
    "tool-list",
    "pathchk",
    "factor",
    "expr",
    "shuf",
    "dircolors",
]

# Mutating commands with safe dry-run defaults
DRY_RUN_COMMANDS = [
    "touch",
    "mkdir",
    "cp",
    "mv",
    "rm",
    "rmdir",
    "unlink",
    "ln",
    "chmod",
    "truncate",
    "mktemp",
    "tee",
]

# Commands with simple args that don't need files
NO_FILE_COMMANDS: dict[str, list[list[str]]] = {
    "echo": [["hello"], ["--raw", "test"], ["hello", "world"]],
    "date": [[], ["--utc"], ["--iso-8601", "date"], ["--raw"]],
    "seq": [["1", "10"], ["1", "100", "2"]],
    "printf": [["%s", "hello"], ["%d", "42"]],
    "factor": [["42"], ["97"], ["1000"]],
    "sleep": [["0"], ["0.01"]],
    "true": [[]],
    "false": [[]],
    "whoami": [[]],
    "pwd": [[]],
    "uname": [[]],
    "arch": [[]],
    "id": [[]],
    "groups": [[]],
    "uptime": [[]],
    "nproc": [[]],
    "tty": [[]],
    "printenv": [[]],
    "hostname": [[]],
    "dircolors": [[]],
    "env": [[]],
    "catalog": [[], ["--pretty"], ["--category", "fs"], ["--search", "sort"]],
    "schema": [[], ["--pretty"]],
    "coreutils": [["--list"]],
    "tool-list": [[]],
    "pathchk": [],
}


class CommandFuzzer:
    """Generates random valid aicoreutils commands with arguments."""

    def __init__(self, temp_dir: str, seed: int | None = None) -> None:
        self._temp_dir = temp_dir
        self._rng = random.Random(seed)
        self._file_counter = 0

    def _make_file(self) -> str:
        """Create a small random text file and return its path."""

        self._file_counter += 1
        name = f"{self._temp_dir}/fuzz_{self._file_counter:06d}.txt"
        lines = []
        for _ in range(self._rng.randint(1, 20)):
            chars = string.ascii_letters + string.digits + " "
            line = "".join(self._rng.choice(chars) for _ in range(self._rng.randint(0, 80)))
            lines.append(line)
        with open(name, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return name

    def _make_dir(self) -> str:
        import os

        self._file_counter += 1
        name = f"{self._temp_dir}/dir_{self._file_counter:06d}"
        os.makedirs(name, exist_ok=True)
        return name

    def random_command(self) -> tuple[str, list[str]]:
        """Return (command_name, args_list) for a random valid invocation."""
        choice = self._rng.random()

        # 40%: no-file command with pre-defined args
        if choice < 0.4:
            cmds = [c for c in NO_FILE_COMMANDS if NO_FILE_COMMANDS[c]]
            if cmds:
                cmd = self._rng.choice(cmds)
                args = self._rng.choice(NO_FILE_COMMANDS[cmd])
                return cmd, args

        # 30%: read-only command with a random file
        if choice < 0.7:
            cmd = self._rng.choice(READ_ONLY_COMMANDS)
            f = self._make_file()
            if cmd == "stat":
                return cmd, [f]
            elif cmd == "ls":
                return cmd, ["--limit", "100", f]
            elif cmd in ("cat", "head", "tail") or cmd in ("sort", "uniq", "tac", "nl", "shuf", "fold"):
                return cmd, [f]
            elif cmd in ("cut",):
                return cmd, ["--chars", "1-10", f]
            elif cmd in ("tr",):
                return cmd, ["a-z", "A-Z", "--path", f]
            elif (
                cmd in ("base64",)
                or cmd in ("expand", "unexpand")
                or cmd in ("md5sum", "sha256sum")
                or cmd in ("wc",)
                or cmd in ("dirname", "basename", "realpath")
                or cmd in ("df", "du")
                or cmd == "pathchk"
            ):
                return cmd, [f]
            elif cmd == "expr":
                return cmd, ["1", "+", "1"]
            else:
                return cmd, [f]

        # 15%: dry-run mutating command
        if choice < 0.85:
            cmd = self._rng.choice(DRY_RUN_COMMANDS)
            if cmd == "touch":
                f = f"{self._temp_dir}/new_{self._file_counter:06d}.txt"
                self._file_counter += 1
                return cmd, ["--dry-run", f]
            elif cmd == "mkdir":
                d = f"{self._temp_dir}/newdir_{self._file_counter:06d}"
                self._file_counter += 1
                return cmd, ["--dry-run", d]
            elif cmd == "rm":
                f = self._make_file()
                return cmd, ["--dry-run", f]
            elif cmd == "rmdir":
                d = self._make_dir()
                return cmd, ["--dry-run", d]
            elif cmd == "unlink":
                f = self._make_file()
                return cmd, ["--dry-run", f]
            elif cmd == "cp":
                src = self._make_file()
                dst = f"{self._temp_dir}/cpy_{self._file_counter:06d}.txt"
                self._file_counter += 1
                return cmd, ["--dry-run", src, dst]
            elif cmd == "mv":
                src = self._make_file()
                dst = f"{self._temp_dir}/mvd_{self._file_counter:06d}.txt"
                self._file_counter += 1
                return cmd, ["--dry-run", src, dst]
            elif cmd in ("ln",):
                src = self._make_file()
                dst = f"{self._temp_dir}/lnk_{self._file_counter:06d}"
                self._file_counter += 1
                return cmd, ["--dry-run", "--symbolic", src, dst]
            elif cmd == "chmod":
                f = self._make_file()
                return cmd, ["--dry-run", "644", f]
            elif cmd == "truncate":
                f = self._make_file()
                return cmd, ["--dry-run", "--size", "0", f]
            elif cmd == "mktemp":
                return cmd, ["--dry-run"]
            elif cmd == "tee":
                f = self._make_file()
                return cmd, ["--dry-run", f]
            return cmd, ["--dry-run", self._make_file()]

        # 15%: command with stdin input
        cmd = self._rng.choice(["sort", "uniq", "wc", "cat", "tac", "nl", "cut", "tr"])
        if cmd == "tr":
            return cmd, ["a-z", "A-Z", "--path", "-"]
        elif cmd == "cut":
            return cmd, ["--chars", "1-10", "-"]
        else:
            return cmd, ["-"]
