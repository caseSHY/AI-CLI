#!/usr/bin/env python3
"""Generate shell completion scripts for aicoreutils.

Usage:
    python scripts/generate_completions.py bash > aicoreutils-complete.bash
    python scripts/generate_completions.py zsh  > _aicoreutils
    python scripts/generate_completions.py fish > aicoreutils.fish
"""

from __future__ import annotations

import sys

from aicoreutils.parser._parser import build_parser


def _all_commands() -> list[str]:
    parser = build_parser()
    for action in parser._actions:
        if hasattr(action, "choices"):
            return sorted(action.choices)  # type: ignore[return-value]
    return []


def _generate_bash(commands: list[str]) -> str:
    cmds = " ".join(commands)
    return f"""# aicoreutils bash completion
_aicoreutils() {{
    local cur prev words cword
    _init_completion || return
    local commands="{cmds}"
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    else
        COMPREPLY=($(compgen -W "--help --pretty --raw" -- "$cur"))
    fi
}}
complete -F _aicoreutils aicoreutils aicoreutils-mcp agentutils
"""


def _generate_zsh(commands: list[str]) -> str:
    cmds = "\n".join(f"    '{c}'" for c in commands)
    return f"""#compdef aicoreutils

local -a commands
commands=(
{cmds}
)

_arguments -C \\
    '1:command:->command' \\
    '*::arg:->args'

case $state in
    command)
        _describe 'command' commands
        ;;
    args)
        _arguments '--help[show help]' '--pretty[pretty-print]' '--raw[raw output]'
        ;;
esac
"""


def _generate_fish(commands: list[str]) -> str:
    cmds = " ".join(commands)
    return f"""# aicoreutils fish completion
complete -c aicoreutils -f
complete -c aicoreutils -n "not __fish_seen_subcommand_from {cmds}" -a "{cmds}"
complete -c aicoreutils -a "--help" -d "Show help"
complete -c aicoreutils -a "--pretty" -d "Pretty-print output"
complete -c aicoreutils -a "--raw" -d "Raw output"
"""


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("bash", "zsh", "fish"):
        print(f"Usage: {sys.argv[0]} bash|zsh|fish", file=sys.stderr)
        sys.exit(1)

    commands = _all_commands()
    shell = sys.argv[1]

    generators = {"bash": _generate_bash, "zsh": _generate_zsh, "fish": _generate_fish}
    print(generators[shell](commands))


if __name__ == "__main__":
    main()
