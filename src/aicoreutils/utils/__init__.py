"""Protocol subpackage: structured errors, I/O, hashing, text, system, and path utilities.

This package replaces the monolithic protocol.py (was ~1200 lines) with
focused submodules, each handling one domain:

    _parser.py    — AgentArgumentParser (argparse with JSON errors)
    _io.py        — stdin/file/line/byte reading
    _hashing.py   — HASH_ALGORITHMS + digest/sum functions
    _text.py      — escape decoding, tr/expand/wc helpers
    _ranges.py    — range parsing, suffix generation
    _printf.py    — printf format parsing and coercion
    _numfmt.py    — SI/IEC number formatting
    _system.py    — subprocess, user/group, signal, uptime
    _path.py      — disk usage, directory size, predicates, iter_directory
"""

from __future__ import annotations

# Re-export core primitives from aicoreutils.core (unchanged API surface)
from ..core.constants import HASH_CHUNK_SIZE  # noqa: F401
from ..core.envelope import deprecation_warning, envelope, error_envelope, utc_iso, write_json  # noqa: F401
from ..core.exceptions import AgentError  # noqa: F401
from ..core.exit_codes import EXIT  # noqa: F401
from ..core.path_utils import (  # noqa: F401
    ensure_exists,
    ensure_parent,
    path_type,
    resolve_path,
    stat_entry,
)
from ..core.sandbox import (  # noqa: F401
    dangerous_delete_target,
    destination_inside_directory,
    refuse_overwrite,
    remove_one,
    require_inside_cwd,
)

# ── _hashing ──
from ._hashing import (  # noqa: F401
    HASH_ALGORITHMS,
    digest_bytes,
    digest_file,
    simple_sum16,
)

# ── _io ──
from ._io import (  # noqa: F401
    bounded_lines,
    combined_lines,
    lines_to_raw,
    read_bytes,
    read_input_bytes,
    read_input_texts,
    read_stdin_bytes,
    read_text_lines,
)

# ── _numfmt ──
from ._numfmt import (  # noqa: F401
    IEC_UNITS,
    SI_UNITS,
    format_numfmt_value,
    parse_numfmt_value,
)

# ── _parser ──
from ._parser import AgentArgumentParser  # noqa: F401

# ── _path ──
from ._path import (  # noqa: F401
    directory_size,
    disk_usage_entry,
    evaluate_test_predicates,
    expression_truthy,
    iter_directory,
    path_issues,
    prime_factors,
)

# ── _printf ──
from ._printf import (  # noqa: F401
    coerce_printf_value,
    format_printf,
    printf_conversions,
)

# ── _ranges ──
from ._ranges import (  # noqa: F401
    alpha_suffix,
    numeric_suffix,
    parse_ranges,
    selected_indexes,
)

# ── _system ──
from ._system import (  # noqa: F401
    active_user_entries,
    normalize_command_args,
    parse_signal,
    resolve_group_id,
    resolve_user_id,
    run_subprocess_capture,
    selected_environment,
    split_owner_spec,
    stdin_tty_name,
    subprocess_result,
    system_uptime_seconds,
)

# ── _text ──
from ._text import (  # noqa: F401
    count_words,
    decode_standard_escapes,
    expand_tr_set,
    parse_octal_mode,
    split_fields,
    squeeze_repeats,
    transform_text,
    unexpand_line,
    wc_for_bytes,
)

# Public API surface — matches the old protocol.py __all__
__all__ = [
    "AgentArgumentParser",
    "AgentError",
    "EXIT",
    "HASH_ALGORITHMS",
    "IEC_UNITS",
    "SI_UNITS",
    "active_user_entries",
    "alpha_suffix",
    "bounded_lines",
    "coerce_printf_value",
    "combined_lines",
    "count_words",
    "dangerous_delete_target",
    "decode_standard_escapes",
    "deprecation_warning",
    "destination_inside_directory",
    "digest_bytes",
    "digest_file",
    "directory_size",
    "disk_usage_entry",
    "ensure_exists",
    "ensure_parent",
    "envelope",
    "error_envelope",
    "evaluate_test_predicates",
    "expand_tr_set",
    "expression_truthy",
    "format_numfmt_value",
    "format_printf",
    "iter_directory",
    "lines_to_raw",
    "normalize_command_args",
    "numeric_suffix",
    "parse_numfmt_value",
    "parse_octal_mode",
    "parse_ranges",
    "parse_signal",
    "path_issues",
    "path_type",
    "prime_factors",
    "printf_conversions",
    "read_bytes",
    "read_input_bytes",
    "read_input_texts",
    "read_stdin_bytes",
    "read_text_lines",
    "refuse_overwrite",
    "remove_one",
    "require_inside_cwd",
    "resolve_group_id",
    "resolve_path",
    "resolve_user_id",
    "run_subprocess_capture",
    "selected_environment",
    "selected_indexes",
    "simple_sum16",
    "split_fields",
    "split_owner_spec",
    "squeeze_repeats",
    "stat_entry",
    "stdin_tty_name",
    "subprocess_result",
    "system_uptime_seconds",
    "transform_text",
    "unexpand_line",
    "utc_iso",
    "wc_for_bytes",
    "write_json",
]
