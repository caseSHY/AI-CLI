"""Parser, dispatch, and main entry point for agentutils CLI."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from .. import __version__
from ..catalog import get_commands_by_priority, get_priority, priority_catalog
from ..commands.fs import (
    command_basename,
    command_bracket,
    command_cat,
    command_chgrp,
    command_chmod,
    command_chown,
    command_cksum,
    command_cp,
    command_dd,
    command_df,
    command_dir,
    command_dirname,
    command_du,
    command_hash,
    command_head,
    command_install,
    command_link,
    command_ln,
    command_ls,
    command_mkdir,
    command_mkfifo,
    command_mknod,
    command_mktemp,
    command_mv,
    command_pwd,
    command_readlink,
    command_realpath,
    command_rm,
    command_rmdir,
    command_shred,
    command_stat,
    command_sum,
    command_sync,
    command_tail,
    command_tee,
    command_test,
    command_touch,
    command_truncate,
    command_unlink,
    command_vdir,
    command_wc,
)
from ..commands.system import (
    command_arch,
    command_chcon,
    command_chroot,
    command_coreutils,
    command_date,
    command_env,
    command_expr,
    command_factor,
    command_false,
    command_groups,
    command_hostid,
    command_hostname,
    command_id,
    command_kill,
    command_logname,
    command_nice,
    command_nohup,
    command_nproc,
    command_pathchk,
    command_pinky,
    command_printenv,
    command_runcon,
    command_sleep,
    command_stdbuf,
    command_stty,
    command_timeout,
    command_true,
    command_tty,
    command_uname,
    command_uptime,
    command_users,
    command_who,
    command_whoami,
)
from ..commands.text import (
    command_basenc,
    command_codec,
    command_comm,
    command_csplit,
    command_cut,
    command_dircolors,
    command_echo,
    command_expand,
    command_fmt,
    command_fold,
    command_join,
    command_nl,
    command_numfmt,
    command_od,
    command_paste,
    command_pr,
    command_printf,
    command_ptx,
    command_seq,
    command_shuf,
    command_sort,
    command_split,
    command_tac,
    command_tr,
    command_tsort,
    command_unexpand,
    command_uniq,
    command_yes,
)
from ..core.constants import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_ITEMS,
    DEFAULT_MAX_LINES,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_PATH_LENGTH,
    DEFAULT_MAX_PREVIEW_BYTES,
    DEFAULT_TAB_SIZE,
    FACTOR_MAX,
)
from ..protocol import (
    EXIT,
    HASH_ALGORITHMS,
    AgentArgumentParser,
    AgentError,
    envelope,
    error_envelope,
    write_json,
)


def parser_command_names(parser: argparse.ArgumentParser) -> list[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return list(action.choices)
    return []


def schema_command_names(args: argparse.Namespace) -> list[str]:
    commands = getattr(args, "implemented_commands", None)
    if commands:
        return list(commands)
    return parser_command_names(build_parser())


# ═══════════════════════════════════════════════════════════════════════
#  schema / catalog helpers
# ═══════════════════════════════════════════════════════════════════════


def command_catalog(args: argparse.Namespace) -> dict[str, Any]:
    return priority_catalog()


def command_schema(args: argparse.Namespace) -> dict[str, Any]:
    implemented_commands = schema_command_names(args)
    prioritized = get_commands_by_priority()
    return {
        "protocol": {
            "stdout_success": {
                "ok": True,
                "tool": "agentutils",
                "version": __version__,
                "command": "<subcommand>",
                "result": {},
                "warnings": [],
            },
            "stderr_error": {
                "ok": False,
                "tool": "agentutils",
                "version": __version__,
                "command": "<subcommand>",
                "error": {
                    "code": "<semantic_code>",
                    "message": "<clear human and machine readable message>",
                    "path": "<optional path>",
                    "suggestion": "<optional fix>",
                },
            },
        },
        "exit_codes": EXIT,
        "command_count": len(implemented_commands),
        "implemented_commands": implemented_commands,
        "commands_by_priority": prioritized,
        "safety": {
            "json_default": True,
            "colors": False,
            "progress_bars": False,
            "mutation_commands_support_dry_run": True,
            "overwrite_requires_explicit_flag": True,
            "recursive_rm_outside_cwd_requires_explicit_flag": True,
            "raw_pipeline_output_requires_explicit_flag": True,
        },
    }


def command_tool_list(args: argparse.Namespace) -> dict[str, Any] | bytes:
    """Return a compact tool list suitable for LLM function-calling context."""
    implemented = schema_command_names(args)
    prioritized = get_commands_by_priority()
    tools: list[dict[str, Any]] = []
    for name in sorted(implemented):
        tools.append(
            {
                "name": name,
                "priority": get_priority(name),
            }
        )
    if args.raw:
        import json as _json

        return _json.dumps(
            {"tools": tools, "count": len(tools)},
            ensure_ascii=False,
        ).encode("utf-8")
    return {
        "tools": tools,
        "count": len(tools),
        "priorities": prioritized,
    }


# ═══════════════════════════════════════════════════════════════════════
#  parser
# ═══════════════════════════════════════════════════════════════════════


def build_parser() -> AgentArgumentParser:
    parser = AgentArgumentParser(
        prog="agentutils",
        description="Agent-friendly CLI layer inspired by GNU Coreutils. Outputs JSON by default.",
        epilog=(
            "Examples:\n"
            "  python -m agentutils catalog --pretty\n"
            "  python -m agentutils ls . --recursive --max-depth 1\n"
            "  python -m agentutils cat README.md --max-bytes 4096\n"
            "  python -m agentutils rm build --recursive --dry-run\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"agentutils {__version__}")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=AgentArgumentParser)
    registered_commands: list[str] = []
    pretty_parent = argparse.ArgumentParser(add_help=False)
    pretty_parent.add_argument(
        "--pretty",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Pretty-print JSON output.",
    )

    def add_subparser(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        registered_commands.append(name)
        parents = list(kwargs.pop("parents", []))
        kwargs["parents"] = [pretty_parent, *parents]
        return sub.add_parser(name, **kwargs)

    p = add_subparser("catalog", help="List prioritized GNU Coreutils categories for agents.")
    p.set_defaults(func=command_catalog)

    p = add_subparser("schema", help="Print the agentutils JSON protocol and exit codes.")
    p.set_defaults(func=command_schema)

    p = add_subparser("coreutils", help="Describe or list the agentutils coreutils-inspired command surface.")
    p.add_argument("--list", action="store_true", help="List registered command names.")
    p.add_argument("--raw", action="store_true", help="Write one command name per line without a JSON envelope.")
    p.set_defaults(func=command_coreutils)

    p = add_subparser("tool-list", help="Return a compact tool list for LLM function-calling context.")
    p.add_argument("--raw", action="store_true", help="Write tools JSON directly without a JSON envelope.")
    p.set_defaults(func=command_tool_list)

    p = add_subparser("pwd", help="Print the current working directory as JSON.")
    p.set_defaults(func=command_pwd)

    p = add_subparser("basename", help="Return final path components.")
    p.add_argument("paths", nargs="+", help="Paths to transform.")
    p.add_argument("--suffix", help="Remove suffix from each basename when present.")
    p.add_argument("--raw", action="store_true", help="Write one basename per line without a JSON envelope.")
    p.set_defaults(func=command_basename)

    p = add_subparser("dirname", help="Return parent path components.")
    p.add_argument("paths", nargs="+", help="Paths to transform.")
    p.add_argument("--raw", action="store_true", help="Write one dirname per line without a JSON envelope.")
    p.set_defaults(func=command_dirname)

    p = add_subparser("realpath", help="Resolve paths deterministically.")
    p.add_argument("paths", nargs="+", help="Paths to resolve.")
    p.add_argument("--strict", action="store_true", help="Fail if any path does not exist.")
    p.set_defaults(func=command_realpath)

    p = add_subparser("readlink", help="Read symbolic link targets or canonicalize paths.")
    p.add_argument("paths", nargs="+", help="Symlinks to inspect, or paths to canonicalize.")
    p.add_argument("--canonicalize", "-f", action="store_true", help="Return canonical resolved paths.")
    p.add_argument("--strict", action="store_true", help="With --canonicalize, fail if a path does not exist.")
    p.add_argument("--raw", action="store_true", help="Write one target/path per line without a JSON envelope.")
    p.set_defaults(func=command_readlink)

    p = add_subparser("test", help="Evaluate path predicates as structured JSON.")
    p.add_argument("path", help="Path to test.")
    p.add_argument("--exists", "-e", action="store_true", help="Path exists. This is the default predicate.")
    p.add_argument("--file", "-f", action="store_true", help="Path is a regular file.")
    p.add_argument("--directory", "-d", action="store_true", help="Path is a directory.")
    p.add_argument("--symlink", "-L", action="store_true", help="Path is a symbolic link.")
    p.add_argument("--readable", "-r", action="store_true", help="Path is readable.")
    p.add_argument("--writable", "-w", action="store_true", help="Path is writable.")
    p.add_argument("--executable", "-x", action="store_true", help="Path is executable.")
    p.add_argument("--empty", action="store_true", help="Path is an empty regular file.")
    p.add_argument("--non-empty", "-s", action="store_true", help="Path is a non-empty regular file.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when predicates do not match.")
    p.set_defaults(func=command_test)

    p = add_subparser("[", help="Evaluate a small test/[ expression subset.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when the expression is false.")
    p.add_argument("-e", dest="bracket_exists", action="store_true", help="Path exists.")
    p.add_argument("-f", dest="bracket_file", action="store_true", help="Path is a file.")
    p.add_argument("-d", dest="bracket_directory", action="store_true", help="Path is a directory.")
    p.add_argument("-L", dest="bracket_symlink", action="store_true", help="Path is a symlink.")
    p.add_argument("-r", dest="bracket_readable", action="store_true", help="Path is readable.")
    p.add_argument("-w", dest="bracket_writable", action="store_true", help="Path is writable.")
    p.add_argument("-x", dest="bracket_executable", action="store_true", help="Path is executable.")
    p.add_argument("-s", dest="bracket_non_empty", action="store_true", help="Path is non-empty.")
    p.add_argument("tokens", nargs=argparse.REMAINDER, help="Expression tokens, optionally ending with ']'.")
    p.set_defaults(func=command_bracket)

    p = add_subparser("ls", help="List files as structured JSON.")
    p.add_argument("path", nargs="?", default=".", help="File or directory to list.")
    p.add_argument("--recursive", action="store_true", help="Recurse into directories.")
    p.add_argument("--max-depth", type=int, default=2, help="Maximum recursive depth.")
    p.add_argument("--include-hidden", action="store_true", help="Include names starting with '.'.")
    p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
    p.add_argument("--limit", type=int, default=1000, help="Maximum entries to emit.")
    p.add_argument("--stream", action="store_true", help="Emit NDJSON one entry per line for large directories.")
    p.set_defaults(func=command_ls)

    for command_name, dir_func in (("dir", command_dir), ("vdir", command_vdir)):
        p = add_subparser(command_name, help=f"{command_name} alias for structured directory listing.")
        p.add_argument("path", nargs="?", default=".", help="File or directory to list.")
        p.add_argument("--recursive", action="store_true", help="Recurse into directories.")
        p.add_argument("--max-depth", type=int, default=2, help="Maximum recursive depth.")
        p.add_argument("--include-hidden", action="store_true", help="Include names starting with '.'.")
        p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
        p.add_argument("--limit", type=int, default=1000, help="Maximum entries to emit.")
        p.add_argument("--stream", action="store_true", help="Emit NDJSON one entry per line for large directories.")
        p.set_defaults(func=dir_func)

    p = add_subparser("stat", help="Return metadata for paths as JSON.")
    p.add_argument("paths", nargs="+", help="Paths to inspect.")
    p.set_defaults(func=command_stat)

    p = add_subparser("cat", help="Read a file with bounded JSON output by default.")
    p.add_argument("path", help="File to read.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for JSON content.")
    p.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum bytes to return.")
    p.add_argument("--offset", type=int, default=0, help="Byte offset to start reading from.")
    p.add_argument("--raw", action="store_true", help="Write raw bytes to stdout without a JSON envelope.")
    p.set_defaults(func=command_cat)

    for name, line_func in (("head", command_head), ("tail", command_tail)):
        p = add_subparser(name, help=f"Return {name} lines as JSON.")
        p.add_argument("path", help="File to read.")
        p.add_argument("--lines", "-n", type=int, default=10, help="Number of lines.")
        p.add_argument("--encoding", default="utf-8", help="Text encoding.")
        p.add_argument("--raw", action="store_true", help="Write raw selected lines without a JSON envelope.")
        p.set_defaults(func=line_func)

    p = add_subparser("wc", help="Count bytes, chars, lines, and words as JSON.")
    p.add_argument("paths", nargs="+", help="Files to count, or '-' for stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for char/word counts.")
    p.add_argument("--raw", action="store_true", help="Write GNU-style count lines without a JSON envelope.")
    p.set_defaults(func=command_wc)

    hash_commands = {
        "md5sum": "md5",
        "sha1sum": "sha1",
        "sha224sum": "sha224",
        "sha256sum": "sha256",
        "sha384sum": "sha384",
        "sha512sum": "sha512",
        "b2sum": "b2sum",
    }
    for command_name, algorithm in hash_commands.items():
        p = add_subparser(command_name, help=f"Hash files as JSON using {algorithm}.")
        p.add_argument("paths", nargs="+", help="Files to hash, or '-' for stdin.")
        p.set_defaults(func=command_hash, algorithm=algorithm)

    p = add_subparser("hash", help="Hash files as JSON.")
    p.add_argument("paths", nargs="+", help="Files to hash, or '-' for stdin.")
    p.add_argument("--algorithm", default="sha256", choices=sorted(HASH_ALGORITHMS), help="Hash algorithm.")
    p.set_defaults(func=command_hash)

    p = add_subparser("cksum", help="Return CRC32 checksums for files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to checksum, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--raw", action="store_true", help="Write checksum size path lines without a JSON envelope.")
    p.set_defaults(func=command_cksum)

    p = add_subparser("sum", help="Return simple 16-bit byte sums for files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to checksum, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--block-size", type=int, default=1024, help="Block size used for reported block counts.")
    p.add_argument("--raw", action="store_true", help="Write checksum blocks path lines without a JSON envelope.")
    p.set_defaults(func=command_sum)

    p = add_subparser("sort", help="Sort text lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to sort, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--reverse", "-r", action="store_true", help="Reverse the sort order.")
    p.add_argument("--unique", "-u", action="store_true", help="Emit only the first of equal sorted lines.")
    p.add_argument("--numeric", "-n", action="store_true", help="Sort by the first numeric token.")
    p.add_argument("--ignore-case", "-f", action="store_true", help="Compare case-insensitively.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_sort)

    p = add_subparser("comm", help="Compare two sorted files and return column-tagged records.")
    p.add_argument("paths", nargs=2, help="Two files to compare.")
    p.add_argument("--suppress-1", action="store_true", help="Suppress records unique to the first file.")
    p.add_argument("--suppress-2", action="store_true", help="Suppress records unique to the second file.")
    p.add_argument("--suppress-3", action="store_true", help="Suppress records common to both files.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write column-tab-line text without a JSON envelope.")
    p.set_defaults(func=command_comm)

    p = add_subparser("join", help="Join two files on a selected field.")
    p.add_argument("paths", nargs=2, help="Two files to join.")
    p.add_argument("--field1", type=int, default=1, help="1-based join field for the first file.")
    p.add_argument("--field2", type=int, default=1, help="1-based join field for the second file.")
    p.add_argument("--delimiter", help="Input delimiter. Defaults to any whitespace.")
    p.add_argument("--output-delimiter", default=" ", help="Delimiter for output fields.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write joined text without a JSON envelope.")
    p.set_defaults(func=command_join)

    p = add_subparser("paste", help="Merge corresponding lines from files.")
    p.add_argument("paths", nargs="*", help="Files to merge, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--delimiter", "-d", default="\t", help="Delimiter inserted between columns.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write pasted text without a JSON envelope.")
    p.set_defaults(func=command_paste)

    p = add_subparser("shuf", help="Shuffle input lines with an optional deterministic seed.")
    p.add_argument("paths", nargs="*", help="Files to shuffle, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--count", "-n", type=int, help="Maximum lines to output.")
    p.add_argument("--seed", type=int, help="Seed for deterministic shuffling.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write shuffled text without a JSON envelope.")
    p.set_defaults(func=command_shuf)

    p = add_subparser("tac", help="Reverse input lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to reverse, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write reversed text without a JSON envelope.")
    p.set_defaults(func=command_tac)

    p = add_subparser("nl", help="Number input lines with a deterministic subset of GNU nl.")
    p.add_argument("paths", nargs="*", help="Files to number, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--number-blank", action="store_true", help="Also number blank lines.")
    p.add_argument("--start", type=int, default=1, help="Starting line number.")
    p.add_argument("--increment", type=int, default=1, help="Line number increment.")
    p.add_argument("--width", type=int, default=6, help="Minimum number width.")
    p.add_argument("--separator", "-s", default="\t", help="Separator between number and line.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write numbered text without a JSON envelope.")
    p.set_defaults(func=command_nl)

    p = add_subparser("fold", help="Wrap long input lines to a fixed width.")
    p.add_argument("paths", nargs="*", help="Files to fold, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=80, help="Maximum line width.")
    p.add_argument("--break-words", "-b", action="store_true", help="Break words longer than the width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write folded text without a JSON envelope.")
    p.set_defaults(func=command_fold)

    p = add_subparser("fmt", help="Reflow paragraphs to a fixed width.")
    p.add_argument("paths", nargs="*", help="Files to format, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=75, help="Maximum output line width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write formatted text without a JSON envelope.")
    p.set_defaults(func=command_fmt)

    p = add_subparser("csplit", help="Split input at regex matches with dry-run and overwrite protection.")
    p.add_argument("path", help="File to split, or '-' for stdin.")
    p.add_argument("--pattern", required=True, help="Regular expression; each match starts a new chunk.")
    p.add_argument("--prefix", default="xx", help="Output file prefix.")
    p.add_argument("--suffix-length", "-n", type=int, default=2, help="Numeric suffix length.")
    p.add_argument("--max-splits", type=int, default=0, help="Maximum regex matches to split at; 0 means all.")
    p.add_argument("--output-dir", default=".", help="Directory for split outputs.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing existing outputs.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--dry-run", action="store_true", help="Report split outputs without writing files.")
    p.set_defaults(func=command_csplit)

    p = add_subparser("split", help="Split input into files with dry-run and overwrite protection.")
    p.add_argument("path", nargs="?", default="-", help="File to split, or '-' for stdin. Defaults to stdin.")
    split_mode = p.add_mutually_exclusive_group()
    split_mode.add_argument("--lines", "-l", type=int, help="Lines per output file. Defaults to 1000.")
    split_mode.add_argument("--bytes", "-b", type=int, help="Bytes per output file.")
    p.add_argument("--prefix", default="x", help="Output file prefix.")
    p.add_argument("--suffix-length", "-a", type=int, default=2, help="Suffix length.")
    p.add_argument("--numeric-suffixes", "-d", action="store_true", help="Use numeric suffixes instead of aa/ab.")
    p.add_argument("--output-dir", default=".", help="Directory for split outputs.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing existing split outputs.")
    p.add_argument("--dry-run", action="store_true", help="Report split outputs without writing files.")
    p.set_defaults(func=command_split)

    p = add_subparser("od", help="Dump input bytes as structured rows.")
    p.add_argument("paths", nargs="*", help="Files to dump, or '-' for stdin. Defaults to stdin.")
    p.add_argument(
        "--format", choices=["hex", "octal", "decimal", "char"], default="hex", help="Byte rendering format."
    )
    p.add_argument("--offset", "-j", type=int, default=0, help="Start offset in bytes.")
    p.add_argument("--max-bytes", "-N", type=int, default=1024, help="Maximum bytes to dump.")
    p.add_argument("--bytes-per-line", type=int, default=16, help="Bytes per output row.")
    p.add_argument("--raw", action="store_true", help="Write dump rows without a JSON envelope.")
    p.set_defaults(func=command_od)

    p = add_subparser("numfmt", help="Convert numbers between plain, SI, and IEC units.")
    p.add_argument("numbers", nargs="*", help="Numbers to convert. Defaults to whitespace tokens from stdin.")
    p.add_argument("--from-unit", choices=["none", "si", "iec"], default="none", help="Input unit system.")
    p.add_argument("--to-unit", choices=["none", "si", "iec"], default="none", help="Output unit system.")
    p.add_argument("--precision", type=int, default=3, help="Digits after the decimal point before trimming zeros.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write converted numbers without a JSON envelope.")
    p.set_defaults(func=command_numfmt)

    p = add_subparser("tsort", help="Topologically sort whitespace-separated dependency pairs.")
    p.add_argument("paths", nargs="*", help="Files to sort, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write sorted nodes without a JSON envelope.")
    p.set_defaults(func=command_tsort)

    p = add_subparser("pr", help="Paginate text into deterministic pages.")
    p.add_argument("paths", nargs="*", help="Files to paginate, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--width", "-w", type=int, default=72, help="Maximum output line width.")
    p.add_argument("--page-length", "-l", type=int, default=66, help="Input lines per page.")
    p.add_argument("--header", help="Optional page header.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write paginated text without a JSON envelope.")
    p.set_defaults(func=command_pr)

    p = add_subparser("ptx", help="Build a simple permuted index from input text.")
    p.add_argument("paths", nargs="*", help="Files to index, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--context", type=int, default=3, help="Words of left/right context.")
    p.add_argument("--ignore", action="append", default=[], help="Ignore a keyword. Repeatable.")
    p.add_argument("--only", action="append", default=[], help="Only include this keyword. Repeatable.")
    p.add_argument("--ignore-case", action="store_true", help="Compare filters case-insensitively.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON records to emit.")
    p.add_argument("--raw", action="store_true", help="Write index rows without a JSON envelope.")
    p.set_defaults(func=command_ptx)

    p = add_subparser("uniq", help="Collapse adjacent duplicate lines from files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--count", "-c", action="store_true", help="Include duplicate counts in raw output.")
    p.add_argument("--repeated", "-d", action="store_true", help="Emit only repeated groups.")
    p.add_argument("--unique-only", "-u", action="store_true", help="Emit only non-repeated groups.")
    p.add_argument("--ignore-case", "-i", action="store_true", help="Compare case-insensitively.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON groups to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_uniq)

    p = add_subparser("cut", help="Select fields, characters, or bytes from each input line.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    selector = p.add_mutually_exclusive_group(required=True)
    selector.add_argument("--fields", "-f", help="1-based field ranges like '1,3-5'.")
    selector.add_argument("--chars", "-c", help="1-based character ranges like '1,3-5'.")
    selector.add_argument("--bytes", "-b", help="1-based byte ranges like '1,3-5'.")
    p.add_argument("--delimiter", "-d", default="\t", help="Field delimiter.")
    p.add_argument("--output-delimiter", default="\t", help="Delimiter for selected fields.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_cut)

    p = add_subparser("tr", help="Translate or delete literal characters from files or stdin.")
    p.add_argument("set1", help="Literal source/delete character set. GNU bracket/range syntax is not expanded.")
    p.add_argument("set2", nargs="?", help="Literal replacement character set for translation.")
    p.add_argument("--path", dest="paths", action="append", default=[], help="Input file. Repeat for multiple files.")
    p.add_argument("--delete", "-d", action="store_true", help="Delete characters in SET1.")
    p.add_argument("--squeeze-repeats", "-s", action="store_true", help="Squeeze repeated output characters.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write plain transformed text to stdout.")
    p.set_defaults(func=command_tr)

    p = add_subparser("expand", help="Convert tabs to spaces in files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--tabs", "-t", type=int, default=DEFAULT_TAB_SIZE, help="Tab stop width.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write expanded text without a JSON envelope.")
    p.set_defaults(func=command_expand)

    p = add_subparser("unexpand", help="Convert spaces to tabs in files or stdin.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument("--tabs", "-t", type=int, default=DEFAULT_TAB_SIZE, help="Tab stop width.")
    p.add_argument("--all", "-a", action="store_true", help="Convert all blank runs, not only leading spaces.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding.")
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="Maximum JSON lines to emit.")
    p.add_argument("--raw", action="store_true", help="Write unexpanded text without a JSON envelope.")
    p.set_defaults(func=command_unexpand)

    for command_name in ("base64", "base32"):
        p = add_subparser(command_name, help=f"Encode or decode {command_name} data.")
        p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
        p.add_argument("--decode", "-d", action="store_true", help="Decode instead of encode.")
        p.add_argument("--encoding", default="utf-8", help="Text encoding for decoded JSON preview.")
        p.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum JSON bytes to emit.")
        p.add_argument("--raw", action="store_true", help="Write raw encoded/decoded bytes to stdout.")
        p.set_defaults(func=command_codec, codec=command_name)

    p = add_subparser("basenc", help="Encode or decode base16/base32/base64/base64url data.")
    p.add_argument("paths", nargs="*", help="Files to read, or '-' for stdin. Defaults to stdin.")
    p.add_argument(
        "--base", choices=["base16", "base32", "base64", "base64url"], default="base64", help="Base encoding."
    )
    p.add_argument("--decode", "-d", action="store_true", help="Decode instead of encode.")
    p.add_argument("--encoding", default="utf-8", help="Text encoding for decoded JSON preview.")
    p.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_BYTES, help="Maximum JSON bytes to emit.")
    p.add_argument("--raw", action="store_true", help="Write raw encoded/decoded bytes to stdout.")
    p.set_defaults(func=command_basenc)

    p = add_subparser("date", help="Return current or supplied time as structured JSON.")
    p.add_argument("--timestamp", type=float, help="Unix timestamp to format instead of current time.")
    p.add_argument("--utc", "-u", action="store_true", help="Use UTC.")
    p.add_argument("--iso-8601", choices=["seconds", "date"], default="seconds", help="ISO output precision.")
    p.add_argument("--format", help="strftime format string.")
    p.add_argument("--raw", action="store_true", help="Write formatted time without a JSON envelope.")
    p.set_defaults(func=command_date)

    p = add_subparser("env", help="Return environment variables as JSON.")
    p.add_argument("names", nargs="*", help="Optional variable names to include.")
    p.add_argument("--raw", action="store_true", help="Write KEY=VALUE lines without a JSON envelope.")
    p.set_defaults(func=command_env)

    p = add_subparser("printenv", help="Return selected environment variables.")
    p.add_argument("names", nargs="*", help="Optional variable names to print.")
    p.add_argument("--raw", action="store_true", help="Write values or KEY=VALUE lines without a JSON envelope.")
    p.set_defaults(func=command_printenv)

    p = add_subparser("whoami", help="Return the current user.")
    p.add_argument("--raw", action="store_true", help="Write the user name without a JSON envelope.")
    p.set_defaults(func=command_whoami)

    p = add_subparser("groups", help="Return group ids/names where the platform exposes them.")
    p.add_argument("user", nargs="?", help="User name label for the result. Current user by default.")
    p.add_argument("--raw", action="store_true", help="Write group names/ids without a JSON envelope.")
    p.set_defaults(func=command_groups)

    p = add_subparser("id", help="Return current user and numeric identity information where available.")
    p.add_argument("--raw", action="store_true", help="Write compact identity text without a JSON envelope.")
    p.set_defaults(func=command_id)

    p = add_subparser("uname", help="Return platform information.")
    p.add_argument("--raw", action="store_true", help="Write uname-like text without a JSON envelope.")
    p.set_defaults(func=command_uname)

    p = add_subparser("arch", help="Return machine architecture.")
    p.add_argument("--raw", action="store_true", help="Write architecture without a JSON envelope.")
    p.set_defaults(func=command_arch)

    p = add_subparser("hostname", help="Return the host name.")
    p.add_argument("--raw", action="store_true", help="Write hostname without a JSON envelope.")
    p.set_defaults(func=command_hostname)

    p = add_subparser("hostid", help="Return a deterministic host identifier derived from hostname.")
    p.add_argument("--raw", action="store_true", help="Write host id hex without a JSON envelope.")
    p.set_defaults(func=command_hostid)

    p = add_subparser("logname", help="Return the login/user name label.")
    p.add_argument("--raw", action="store_true", help="Write logname without a JSON envelope.")
    p.set_defaults(func=command_logname)

    p = add_subparser("uptime", help="Return system uptime where available.")
    p.add_argument("--raw", action="store_true", help="Write uptime seconds without a JSON envelope.")
    p.set_defaults(func=command_uptime)

    p = add_subparser("tty", help="Report whether stdin is attached to a TTY.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when stdin is not a TTY.")
    p.add_argument("--raw", action="store_true", help="Write tty path or 'not a tty' without a JSON envelope.")
    p.set_defaults(func=command_tty)

    p = add_subparser("users", help="Return current active user labels known to this process.")
    p.add_argument("--raw", action="store_true", help="Write users without a JSON envelope.")
    p.set_defaults(func=command_users)

    p = add_subparser("pinky", help="Return lightweight user/session records.")
    p.add_argument("users", nargs="*", help="Optional users to include.")
    p.add_argument("--long", "-l", action="store_true", help="Include the long-output intent in the JSON result.")
    p.add_argument("--raw", action="store_true", help="Write tab-separated user rows without a JSON envelope.")
    p.set_defaults(func=command_pinky)

    p = add_subparser("who", help="Return current process user/session information.")
    p.add_argument("--raw", action="store_true", help="Write who-like rows without a JSON envelope.")
    p.set_defaults(func=command_who)

    p = add_subparser("nproc", help="Return available processor count.")
    p.add_argument("--raw", action="store_true", help="Write the processor count without a JSON envelope.")
    p.set_defaults(func=command_nproc)

    p = add_subparser("df", help="Return filesystem usage for paths.")
    p.add_argument("paths", nargs="*", help="Paths to inspect. Defaults to current directory.")
    p.set_defaults(func=command_df)

    p = add_subparser("du", help="Return recursive apparent disk usage for paths.")
    p.add_argument("paths", nargs="*", help="Paths to measure. Defaults to current directory.")
    p.add_argument("--max-depth", type=int, default=8, help="Maximum recursion depth.")
    p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories.")
    p.set_defaults(func=command_du)

    p = add_subparser("dd", help="Copy bytes between files/stdin/stdout with bounded JSON reporting.")
    p.add_argument("--input", "-i", default="-", help="Input file, or '-' for stdin.")
    p.add_argument("--output", "-o", default="-", help="Output file, or '-' for stdout/no file output.")
    p.add_argument("--bs", type=int, default=512, help="Block size in bytes.")
    p.add_argument("--count", type=int, help="Number of input blocks to copy.")
    p.add_argument("--skip", type=int, default=0, help="Input blocks to skip.")
    p.add_argument("--seek", type=int, default=0, help="Output blocks to seek before writing.")
    p.add_argument("--parents", action="store_true", help="Create missing output parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing output file.")
    p.add_argument(
        "--max-preview-bytes", type=int, default=DEFAULT_MAX_PREVIEW_BYTES, help="Maximum JSON preview bytes."
    )
    p.add_argument("--dry-run", action="store_true", help="Report without writing output.")
    p.add_argument("--raw", action="store_true", help="Write selected input bytes without a JSON envelope.")
    p.set_defaults(func=command_dd)

    p = add_subparser("sync", help="Flush filesystem buffers where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report without syncing.")
    p.set_defaults(func=command_sync)

    p = add_subparser("dircolors", help="Return an agent-safe no-color LS_COLORS configuration.")
    p.add_argument("--shell", choices=["bash", "zsh", "sh", "fish", "plain"], default="bash", help="Raw shell format.")
    p.add_argument("--raw", action="store_true", help="Write shell configuration without a JSON envelope.")
    p.set_defaults(func=command_dircolors)

    p = add_subparser("seq", help="Generate a bounded numeric sequence.")
    p.add_argument("numbers", type=float, nargs="+", help="[FIRST [INCREMENT]] LAST.")
    p.add_argument(
        "--increment", "-i", type=float, default=1.0, help="Increment used with one or two positional numbers."
    )
    p.add_argument("--separator", "-s", default="\n", help="Raw output separator.")
    p.add_argument("--format", "-f", help="printf-style numeric format, for example %%.2f.")
    p.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS, help="Maximum items to generate.")
    p.add_argument("--raw", action="store_true", help="Write sequence text without a JSON envelope.")
    p.set_defaults(func=command_seq)

    p = add_subparser("printf", help="Format text with a deterministic printf-style subset.")
    p.add_argument("format_string", help="Printf-style format string.")
    p.add_argument("values", nargs="*", help="Values used by format conversions.")
    p.add_argument("--encoding", default="utf-8", help="Output encoding.")
    p.add_argument("--raw", action="store_true", help="Write formatted text without a JSON envelope.")
    p.set_defaults(func=command_printf)

    p = add_subparser("echo", help="Join words with spaces and emit optional newline.")
    p.add_argument("words", nargs="*", help="Words to emit.")
    p.add_argument("--no-newline", "-n", action="store_true", help="Do not append a newline.")
    p.add_argument("--escapes", "-e", action="store_true", help="Interpret common backslash escapes.")
    p.add_argument("--encoding", default="utf-8", help="Output encoding.")
    p.add_argument("--raw", action="store_true", help="Write echo text without a JSON envelope.")
    p.set_defaults(func=command_echo)

    p = add_subparser("pathchk", help="Validate path strings for length and portable characters.")
    p.add_argument("paths", nargs="+", help="Path strings to validate.")
    p.add_argument("--portable", "-p", action="store_true", help="Require portable POSIX filename characters.")
    p.add_argument("--max-path-length", type=int, default=DEFAULT_MAX_PATH_LENGTH, help="Maximum path string length.")
    p.add_argument("--max-component-length", type=int, default=255, help="Maximum path component length.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when any path is invalid.")
    p.add_argument("--raw", action="store_true", help="Write validation rows without a JSON envelope.")
    p.set_defaults(func=command_pathchk)

    p = add_subparser("factor", help="Return prime factors for bounded integer inputs.")
    p.add_argument("numbers", nargs="*", help="Integers to factor. Defaults to whitespace tokens from stdin.")
    p.add_argument("--max-value", type=int, default=FACTOR_MAX, help="Safety cap for absolute input values.")
    p.add_argument("--raw", action="store_true", help="Write factor lines without a JSON envelope.")
    p.set_defaults(func=command_factor)

    p = add_subparser("expr", help="Evaluate a safe arithmetic/comparison expression subset.")
    p.add_argument("tokens", nargs="+", help="Expression tokens, for example: 1 + 2 or 3 '>' 2.")
    p.add_argument("--exit-code", action="store_true", help="Return exit code 1 when the result is false/zero/empty.")
    p.add_argument("--raw", action="store_true", help="Write the expression value without a JSON envelope.")
    p.set_defaults(func=command_expr)

    p = add_subparser("true", help="Return success.")
    p.set_defaults(func=command_true)

    p = add_subparser("false", help="Return exit code 1 with a JSON envelope.")
    p.set_defaults(func=command_false)

    p = add_subparser("sleep", help="Sleep for a bounded number of seconds.")
    p.add_argument("seconds", type=float, help="Seconds to sleep.")
    p.add_argument("--max-seconds", type=float, default=60.0, help="Safety cap for sleep duration.")
    p.add_argument("--dry-run", action="store_true", help="Report without sleeping.")
    p.set_defaults(func=command_sleep)

    p = add_subparser("timeout", help="Run a command with a bounded timeout and captured output.")
    p.add_argument("seconds", type=float, help="Timeout in seconds.")
    p.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum captured stdout/stderr bytes each.",
    )
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_timeout)

    p = add_subparser("stdbuf", help="Run a command with portable buffering hints and bounded capture.")
    p.add_argument("--input", "-i", help="Requested stdin buffering mode: 0, L, or a byte size.")
    p.add_argument("--output", "-o", help="Requested stdout buffering mode: 0, L, or a byte size.")
    p.add_argument("--error", "-e", help="Requested stderr buffering mode: 0, L, or a byte size.")
    p.add_argument("--timeout", type=float, default=60.0, help="Safety timeout for the command.")
    p.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum captured stdout/stderr bytes each.",
    )
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_stdbuf)

    p = add_subparser("chroot", help="Plan or run a command inside a changed root with explicit confirmation.")
    p.add_argument("root", help="Directory to use as the new root.")
    p.add_argument("--timeout", type=float, default=60.0, help="Safety timeout for the command.")
    p.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum captured stdout/stderr bytes each.",
    )
    p.add_argument("--allow-chroot", action="store_true", help="Allow a real chroot execution where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run inside the root.")
    p.set_defaults(func=command_chroot)

    p = add_subparser("stty", help="Inspect or safely plan terminal setting changes.")
    p.add_argument("--file", "-F", dest="device", help="Terminal device to inspect or change.")
    p.add_argument("--allow-change", action="store_true", help="Allow applying supported terminal changes.")
    p.add_argument("--dry-run", action="store_true", help="Report planned settings without changing the terminal.")
    p.add_argument("--raw", action="store_true", help="Write a compact status line without a JSON envelope.")
    p.add_argument("settings", nargs=argparse.REMAINDER, help="Settings such as raw, sane, echo, or -echo.")
    p.set_defaults(func=command_stty)

    p = add_subparser("nice", help="Run a command with a niceness adjustment where supported.")
    p.add_argument("--adjustment", "-n", type=int, default=10, help="Niceness adjustment.")
    p.add_argument("--timeout", type=float, default=60.0, help="Safety timeout for the command.")
    p.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum captured stdout/stderr bytes each.",
    )
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_nice)

    p = add_subparser("kill", help="Send process signals with dry-run and explicit confirmation.")
    p.add_argument("pids", nargs="+", help="Process ids to signal.")
    p.add_argument("--signal", "-s", default="TERM", help="Signal name or number.")
    p.add_argument("--allow-signal", action="store_true", help="Allow sending real signals.")
    p.add_argument("--dry-run", action="store_true", help="Report without signaling.")
    p.set_defaults(func=command_kill)

    p = add_subparser("nohup", help="Plan or start a background process with redirected output.")
    p.add_argument("--output", default="nohup.out", help="Output file for stdout/stderr.")
    p.add_argument("--append", action="store_true", help="Append to the output file.")
    p.add_argument("--parents", action="store_true", help="Create missing output parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing output file.")
    p.add_argument("--allow-background", action="store_true", help="Allow starting a real background process.")
    p.add_argument("--dry-run", action="store_true", help="Report without starting a process.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_nohup)

    p = add_subparser("chcon", help="Plan or change SELinux security contexts with explicit confirmation.")
    p.add_argument("context", help="Security context to apply.")
    p.add_argument("paths", nargs="+", help="Paths whose security context should change.")
    p.add_argument("--recursive", "-R", action="store_true", help="Apply to directory contents recursively.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--allow-context", action="store_true", help="Allow real SELinux context changes where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing contexts.")
    p.add_argument("--raw", action="store_true", help="Write context/path rows without a JSON envelope.")
    p.set_defaults(func=command_chcon)

    p = add_subparser("runcon", help="Plan or run a command under an SELinux context where available.")
    p.add_argument("context", help="Security context for the command.")
    p.add_argument("--timeout", type=float, default=60.0, help="Safety timeout for the command.")
    p.add_argument(
        "--max-output-bytes",
        type=int,
        default=DEFAULT_MAX_OUTPUT_BYTES,
        help="Maximum captured stdout/stderr bytes each.",
    )
    p.add_argument("--allow-context", action="store_true", help="Allow invoking the platform runcon command.")
    p.add_argument("--dry-run", action="store_true", help="Report without running the command.")
    p.add_argument("command_args", nargs=argparse.REMAINDER, help="Command and arguments to run.")
    p.set_defaults(func=command_runcon)

    p = add_subparser("yes", help="Generate a bounded repeated line.")
    p.add_argument("words", nargs="*", help="Words to repeat. Defaults to 'y'.")
    p.add_argument("--count", "-n", type=int, default=10, help="Number of lines to generate.")
    p.add_argument("--raw", action="store_true", help="Write repeated lines without a JSON envelope.")
    p.set_defaults(func=command_yes)

    p = add_subparser("mkdir", help="Create directories with dry-run support.")
    p.add_argument("paths", nargs="+", help="Directories to create.")
    p.add_argument("--parents", "-p", action="store_true", help="Create missing parents.")
    p.add_argument("--exist-ok", action="store_true", help="Do not fail if a directory exists.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mkdir)

    p = add_subparser("touch", help="Create files or update timestamps with dry-run support.")
    p.add_argument("paths", nargs="+", help="Files to touch.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_touch)

    p = add_subparser("cp", help="Copy files/directories with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path.")
    p.add_argument("destination", help="Destination path.")
    p.add_argument("--recursive", "-r", action="store_true", help="Copy directories recursively.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing/merging destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_cp)

    p = add_subparser("mv", help="Move a path with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path.")
    p.add_argument("destination", help="Destination path.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_mv)

    p = add_subparser("ln", help="Create hard or symbolic links with explicit overwrite and dry-run.")
    p.add_argument("source", help="Source path or symlink target.")
    p.add_argument("destination", help="Link path to create.")
    p.add_argument("--symbolic", "-s", action="store_true", help="Create a symbolic link.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_ln)

    p = add_subparser("link", help="Create a hard link with explicit overwrite and dry-run.")
    p.add_argument("source", help="Existing source file.")
    p.add_argument("destination", help="Hard link path to create.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
    p.add_argument("--dry-run", action="store_true", help="Report operation without changing files.")
    p.set_defaults(func=command_link)

    p = add_subparser("chmod", help="Change file modes using octal modes with dry-run support.")
    p.add_argument("mode", help="Octal mode such as 644, 755, or 0644.")
    p.add_argument("paths", nargs="+", help="Paths whose mode should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chmod)

    p = add_subparser("chown", help="Change file owner/group using numeric ids or platform lookups.")
    p.add_argument("owner", help="Owner spec such as UID, USER, UID:GID, or USER:GROUP.")
    p.add_argument("paths", nargs="+", help="Paths whose owner/group should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chown)

    p = add_subparser("chgrp", help="Change file group using a numeric gid or platform lookup.")
    p.add_argument("group", help="Group name or numeric gid.")
    p.add_argument("paths", nargs="+", help="Paths whose group should change.")
    p.add_argument("--no-follow", action="store_true", help="Do not follow symlinks where supported.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_chgrp)

    p = add_subparser("truncate", help="Set file size in bytes with dry-run support.")
    p.add_argument("paths", nargs="+", help="Files to resize.")
    p.add_argument("--size", type=int, required=True, help="Target size in bytes.")
    p.add_argument("--no-create", action="store_true", help="Fail if a target file does not exist.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_truncate)

    p = add_subparser("mktemp", help="Create a temporary file or directory as JSON.")
    p.add_argument("--directory", "-d", action="store_true", help="Create a temporary directory.")
    p.add_argument("--prefix", default="tmp.", help="Temporary path prefix.")
    p.add_argument("--suffix", default="", help="Temporary path suffix.")
    p.add_argument("--tmpdir", help="Directory where the temporary path should be created. Defaults to cwd.")
    p.add_argument("--dry-run", action="store_true", help="Report a candidate path without creating it.")
    p.set_defaults(func=command_mktemp)

    p = add_subparser("mkfifo", help="Create FIFO special files where supported, with dry-run support.")
    p.add_argument("paths", nargs="+", help="FIFO paths to create.")
    p.add_argument("--mode", "-m", default="666", help="Octal mode such as 600 or 666.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mkfifo)

    p = add_subparser("mknod", help="Create regular placeholder files or FIFOs with dry-run support.")
    p.add_argument("paths", nargs="+", help="Node paths to create.")
    p.add_argument("--type", dest="node_type", choices=["regular", "fifo"], default="regular", help="Node type.")
    p.add_argument("--mode", "-m", default="666", help="Octal mode such as 600 or 666.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_mknod)

    for command_name in ("install", "ginstall"):
        p = add_subparser(command_name, help=f"{command_name} files or create directories with explicit overwrite.")
        p.add_argument("paths", nargs="*", help="SOURCE DESTINATION, or directories with --directory.")
        p.add_argument(
            "--directory", "-d", action="store_true", help="Create directories instead of installing a file."
        )
        p.add_argument("--mode", "-m", default="755", help="Octal mode applied to installed paths.")
        p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
        p.add_argument("--allow-overwrite", action="store_true", help="Allow replacing an existing destination.")
        p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
        p.set_defaults(func=command_install)

    p = add_subparser("tee", help="Write stdin to files and optionally echo raw stdin.")
    p.add_argument("paths", nargs="*", help="Files to write.")
    p.add_argument("--append", "-a", action="store_true", help="Append instead of replacing.")
    p.add_argument("--parents", action="store_true", help="Create missing parent directories.")
    p.add_argument(
        "--max-preview-bytes", type=int, default=DEFAULT_MAX_PREVIEW_BYTES, help="Maximum JSON preview bytes."
    )
    p.add_argument("--dry-run", action="store_true", help="Report operations without writing files.")
    p.add_argument("--raw", action="store_true", help="Echo stdin to stdout without a JSON envelope.")
    p.set_defaults(func=command_tee)

    p = add_subparser("rmdir", help="Remove empty directories with dry-run support.")
    p.add_argument("paths", nargs="+", help="Empty directories to remove.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_rmdir)

    p = add_subparser("unlink", help="Unlink files or symlinks, refusing directories.")
    p.add_argument("paths", nargs="+", help="Files or symlinks to unlink.")
    p.add_argument("--force", "-f", action="store_true", help="Ignore missing paths.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_unlink)

    p = add_subparser("rm", help="Remove files/directories with dry-run and safety checks.")
    p.add_argument("paths", nargs="+", help="Paths to remove.")
    p.add_argument("--recursive", "-r", action="store_true", help="Remove directories recursively.")
    p.add_argument("--force", "-f", action="store_true", help="Ignore missing files.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.add_argument(
        "--allow-outside-cwd",
        action="store_true",
        help="Allow recursive directory removal outside the current working directory.",
    )
    p.set_defaults(func=command_rm)

    p = add_subparser("shred", help="Destructively overwrite files with explicit confirmation.")
    p.add_argument("paths", nargs="+", help="Files to overwrite.")
    p.add_argument("--passes", "-n", type=int, default=1, help="Number of zero overwrite passes.")
    p.add_argument("--remove", "-u", action="store_true", help="Remove files after overwriting.")
    p.add_argument("--allow-destructive", action="store_true", help="Allow real destructive overwrite.")
    p.add_argument("--dry-run", action="store_true", help="Report operations without changing files.")
    p.set_defaults(func=command_shred)

    parser.set_defaults(implemented_commands=registered_commands)
    return parser


# ═══════════════════════════════════════════════════════════════════════
#  dispatch & main
# ═══════════════════════════════════════════════════════════════════════


def dispatch(args: argparse.Namespace) -> tuple[int, dict[str, Any] | bytes]:
    result = args.func(args)
    if isinstance(result, bytes):
        return EXIT["ok"], result
    code = result.pop("_exit_code", EXIT["ok"]) if isinstance(result, dict) else EXIT["ok"]
    return code, envelope(args.command, result)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    command_name: str | None = None
    if argv is None:
        argv = sys.argv[1:]
    try:
        args = parser.parse_args(argv)
        args.pretty = getattr(args, "pretty", False)
        args.implemented_commands = parser_command_names(parser)
        command_name = args.command
        code, payload = dispatch(args)
        if isinstance(payload, bytes):
            sys.stdout.buffer.write(payload)
        else:
            write_json(sys.stdout, payload, pretty=args.pretty)
        return code
    except AgentError as exc:
        write_json(sys.stderr, error_envelope(command_name, exc))
        return exc.exit_code
    except BrokenPipeError:
        return EXIT["ok"]
    except KeyboardInterrupt:
        interrupt_error = AgentError("general_error", "Interrupted.")
        write_json(sys.stderr, error_envelope(command_name, interrupt_error))
        return interrupt_error.exit_code
    except Exception as exc:
        error = AgentError(
            "general_error",
            "Unexpected error.",
            details={"type": type(exc).__name__, "message": str(exc)},
        )
        write_json(sys.stderr, error_envelope(command_name, error))
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
