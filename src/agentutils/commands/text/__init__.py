"""Text-processing commands: sort, uniq, cut, tr, base64, comm, join, ..."""

from __future__ import annotations

from ._core import (
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

__all__ = ['command_basenc', 'command_codec', 'command_comm', 'command_csplit', 'command_cut', 'command_dircolors', 'command_echo', 'command_expand', 'command_fmt', 'command_fold', 'command_join', 'command_nl', 'command_numfmt', 'command_od', 'command_paste', 'command_pr', 'command_printf', 'command_ptx', 'command_seq', 'command_shuf', 'command_sort', 'command_split', 'command_tac', 'command_tr', 'command_tsort', 'command_unexpand', 'command_uniq', 'command_yes']
