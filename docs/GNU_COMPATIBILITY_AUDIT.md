# GNU Coreutils 兼容性审计 / Compatibility Audit

## 中文说明

基线：GNU Coreutils 9.10。审计依据是
`vendor/gnu-coreutils/coreutils-9.10/src/cu-progs.mk` 以及对应的
`vendor/gnu-coreutils/coreutils-9.10/src` 源码。

审计日期：2026-04-30。

### 结论摘要

`agentutils` 不是完整 GNU Coreutils 替代品。

- GNU Coreutils 基线命令数：109
- `agentutils schema` 登记命令数：106
- 与 GNU Coreutils 对应的已实现命令数：102
- `agentutils` 元命令/辅助命令：`catalog`、`schema`、`hash`、`ginstall`
- 尚未实现的 GNU Coreutils 命令数：7

已实现命令对当前 Agent 友好契约有效：成功输出 JSON、错误输出 stderr JSON、
核心行为确定、输出在相关场景下有界，并且修改类命令支持 `--dry-run`。但这些
命令不与 GNU Coreutils 完全选项兼容。

### 尚未实现的 GNU 命令

`coreutils`、`chroot`、`pinky`、`stdbuf`、`stty`、`chcon`、`runcon`。

### 已实现命令的主要缺口

| 命令 | 当前状态 | 相对 GNU 的主要缺失 |
| --- | --- | --- |
| `base32` / `base64` / `basenc` | 有效子集 | 换行宽度控制、ignore-garbage 解码、GNU 精确格式；`basenc` 只覆盖 base16/base32/base64/base64url。 |
| `basename` / `dirname` | 有效子集 | 零字节分隔和部分 GNU 路径边界行为。 |
| `cat` | 有效子集 | 多文件、默认 stdin、编号、压缩空行、显示不可见字符。 |
| `chmod` / `chown` / `chgrp` | 有效子集 | 符号模式、递归、reference mode、verbose/quiet/changes、preserve-root；owner/group 名称解析依赖平台。 |
| `cp` / `mv` | 有效子集 | archive/preserve、备份、target-directory、update、interactive/no-clobber 等。 |
| `cut` | 有效子集 | complement、only-delimited、zero-terminated、GNU 多字节边界行为。 |
| `date` | 有效子集 | GNU date parser、相对时间、reference file、RFC 模式、纳秒格式。 |
| `dd` | 有效子集 | 只支持明确的 input/output、bs/count/skip/seek、dry-run 和覆盖保护；未实现 GNU conv/iflag/oflag/status 全集。 |
| `df` / `du` | 有效子集 | block/inode 模式、human-readable、过滤器、排除规则和更多统计模式。 |
| `dircolors` | 有效子集 | 固定输出无颜色配置，避免污染 Agent stdout；未实现 GNU 数据库解析。 |
| `echo` / `printf` | 有效子集 | GNU `echo` 的兼容性边界、`printf` 的复杂格式、宽度 `*`、不完整参数默认值和本地化行为。 |
| `env` / `printenv` | 有效子集 | 修改环境后执行命令、ignore-env、chdir、信号处理、GNU 精确退出语义。 |
| `head` / `tail` | 有效子集 | byte count、多文件 header、follow/retry/pid、zero-terminated。 |
| `id` / `whoami` / `groups` | 有效子集 | 指定用户查询、SELinux context、名称/数字格式组合；Windows 上组信息受平台 API 限制。 |
| `join` / `comm` / `paste` | 有效子集 | 未实现 GNU 完整字段选择、排序检查、补全未匹配行、输出格式表达式、NUL 分隔等。 |
| `ln` / `link` | 有效子集 | target-directory、relative symlink、logical/physical、backup/interactive/verbose。 |
| `ls` / `dir` / `vdir` | 有效子集 | 长列表、格式/排序模式、颜色、引用样式、inode/block、time style、SELinux context；`dir`/`vdir` 是结构化别名。 |
| `md5sum` / `sha*sum` / `b2sum` / `cksum` / `sum` | 有效子集 | `--check`、binary/text 模式、strict/warn/status；`cksum`/`sum` 只提供 Agent 稳定校验子集。 |
| `mkdir` / `mktemp` / `mkfifo` / `mknod` / `install` / `ginstall` | 有效子集 | mode/context/verbose，GNU template、`-t`、quiet、精确 dry-run 语义；节点和安装行为只覆盖安全子集。 |
| `nl` / `fold` / `fmt` / `pr` | 有效子集 | 未实现 GNU 完整编号样式、页分隔、标题/正文/页脚区域、空白宽度和复杂段落启发式；`pr` 只覆盖简单分页和标题输出。 |
| `numfmt` / `od` | 有效子集 | 未实现字段选择、舍入模式、分组、本地化、完整 `od` 类型系统和地址基数选项。 |
| `pathchk` / `factor` / `expr` | 有效子集 | `pathchk` 为可配置静态检查；`factor` 有安全上限；`expr` 是安全 AST 子集，不是 GNU 完整字符串/正则语义。 |
| `pwd` / `realpath` / `readlink` | 有效子集 | logical/physical、relative-to/base、canonicalize-existing/missing、zero termination。 |
| `rm` / `rmdir` / `unlink` / `shred` | 有效子集 | interactive、one-file-system、preserve-root 变体、parent removal、verbose；`shred` 真实执行需要 `--allow-destructive`。 |
| `seq` / `yes` / `sleep` | 有效子集 | GNU 完整格式化/后缀解析；`yes` 和 `sleep` 为 Agent 安全默认有界。 |
| `sort` / `uniq` / `tr` / `shuf` / `tac` / `expand` / `unexpand` / `split` / `csplit` / `ptx` / `tsort` | 有效子集 | key/stable/merge/check、skip/check chars、字符类/范围/complement、随机源、记录分隔、复杂 split/csplit suffix/过滤器、完整 permuted index 选项；`tsort` 返回循环为结构化冲突错误。 |
| `stat` / `wc` | 有效子集 | format/printf、filesystem mode、selective counters、files0-from、max-line-length。 |
| `tee` / `sync` | 有效子集 | ignore-interrupts、output-error policy；默认 JSON，`--raw` 才回显 stdin；`sync` 依赖平台支持。 |
| `test` / `[` | 有效子集 | 完整表达式语法、整数比较、时间戳比较、更多文件类型谓词；`[` 是结构化输出的轻量表达式别名。 |
| `timeout` / `nice` / `nohup` / `kill` | 有效子集 | 以 Agent 安全为优先：`timeout` 捕获有界 stdout/stderr，`nice` 和 `nohup` 默认支持 dry-run/显式执行，`kill` 默认 dry-run 且真实信号需要 `--allow-signal`；未实现 GNU 完整作业控制和平台专有语义。 |
| `touch` / `truncate` | 有效子集 | date/reference/no-create/no-dereference、相对 size、block units。 |
| `true` / `false` | 有效子集 | 保留退出码语义，但 GNU 原生命令没有 JSON envelope。 |
| `uname` / `arch` / `hostname` / `hostid` / `logname` / `uptime` / `tty` / `users` / `who` / `nproc` | 有效子集 | 单独字段 flags、OMP affinity、`--all`、`--ignore`、真实登录会话数据库、平台专有 uptime/tty 语义等。 |

### 已执行的有效性检查

自动化测试覆盖：

- Unit test：协议 envelope 和 JSON 写出
- CLI black-box test：真实子进程调用、stdout/stderr 契约
- Golden file test：稳定输出与 golden 文件对比
- Sandbox test：阻止越界递归删除
- Agent-call test：观察、决策、dry-run、实际写入、校验的完整 Agent 流
- Error / exit-code test：错误 JSON 和退出码
- Filesystem side-effect test：dry-run 不改文件，写操作只产生预期副作用
- CI test：GitHub Actions 配置存在且执行 unittest

当前验证命令：

```powershell
python -m unittest discover -s tests -v
```

当前结果：54 个测试通过。

### 客观结论

当前实现足以支撑一个明确范围内的 Agent 友好核心命令面，但相对 GNU Coreutils
仍不完整。准确描述应为：

> 受 GNU Coreutils 启发的 JSON 优先 Agent 友好子集。

不应在未加限定的情况下称为 “GNU-compatible” 或 “GNU Coreutils replacement”。

---

## English

Baseline: GNU Coreutils 9.10, using
`vendor/gnu-coreutils/coreutils-9.10/src/cu-progs.mk` and the corresponding
source files under `vendor/gnu-coreutils/coreutils-9.10/src`.

Audit date: 2026-04-30.

### Summary

`agentutils` is not a complete GNU Coreutils replacement.

- GNU Coreutils command baseline: 109 commands
- `agentutils schema` commands: 106 commands
- Coreutils-equivalent commands implemented by `agentutils`: 102 commands
- `agentutils` metadata/helper commands: `catalog`, `schema`, `hash`, `ginstall`
- Missing GNU Coreutils commands: 7 commands

The implemented commands are usable for the current agent-friendly contract:
JSON success output, JSON stderr errors, deterministic core behavior, bounded
output where relevant, and `--dry-run` for mutation commands. They are not
option-compatible with GNU Coreutils.

### Missing GNU Commands

`coreutils`, `chroot`, `pinky`, `stdbuf`, `stty`, `chcon`, `runcon`.

### Main Gaps In Implemented Commands

| Command | Current status | Main GNU features not implemented |
| --- | --- | --- |
| `base32` / `base64` / `basenc` | Effective subset | Wrapping controls, ignore-garbage decode behavior, GNU exact formatting; `basenc` covers only base16/base32/base64/base64url. |
| `basename` / `dirname` | Effective subset | Zero termination and some GNU path edge-case parity. |
| `cat` | Effective subset | Multiple files, stdin default, numbering, squeeze blank, show nonprinting characters. |
| `chmod` / `chown` / `chgrp` | Effective subset | Symbolic modes, recursive traversal, reference mode, verbose/quiet/changes, preserve-root; owner/group name lookup depends on platform support. |
| `cp` / `mv` | Effective subset | Archive/preserve, backup, target-directory, update, interactive/no-clobber behavior. |
| `cut` | Effective subset | Complement, only-delimited, zero-terminated input, GNU multibyte edge behavior. |
| `date` | Effective subset | GNU date parser, relative dates, reference file, RFC modes, nanosecond formatting. |
| `dd` | Effective subset | Supports explicit input/output, bs/count/skip/seek, dry-run, and overwrite protection; GNU conv/iflag/oflag/status are not implemented. |
| `df` / `du` | Effective subset | Block/inode modes, human-readable modes, filters, exclusions, more accounting modes. |
| `dircolors` | Effective subset | Emits a no-color configuration to avoid polluting agent stdout; GNU database parsing is not implemented. |
| `echo` / `printf` | Effective subset | GNU `echo` compatibility edge cases, complex `printf` formats, `*` widths, incomplete-argument defaults, locale behavior. |
| `env` / `printenv` | Effective subset | Running commands under modified environments, ignore-env, chdir, signal handling, exact GNU exit semantics. |
| `head` / `tail` | Effective subset | Byte counts, multi-file headers, follow/retry/pid, zero-terminated records. |
| `id` / `whoami` / `groups` | Effective subset | Named user lookup, SELinux context, name/numeric formatting combinations; group data depends on platform APIs, especially on Windows. |
| `join` / `comm` / `paste` | Effective subset | Full GNU field selection, sorted-input checks, unmatched-line completion, output format expressions, NUL records. |
| `ln` / `link` | Effective subset | Target-directory option, relative symlink generation, logical/physical modes, backup/interactive/verbose. |
| `ls` / `dir` / `vdir` | Effective subset | Long listing, format/sort modes, color, quoting styles, inode/block info, time styles, SELinux context; `dir`/`vdir` are structured aliases. |
| `md5sum` / `sha*sum` / `b2sum` / `cksum` / `sum` | Effective subset | `--check`, binary/text flags, strict/warn/status handling; `cksum`/`sum` expose stable agent-oriented checksum subsets. |
| `mkdir` / `mktemp` / `mkfifo` / `mknod` / `install` / `ginstall` | Effective subset | Mode/context/verbose, GNU template syntax, `-t`, quiet mode, exact dry-run semantics; node and install behavior cover only safer subsets. |
| `nl` / `fold` / `fmt` / `pr` | Effective subset | Full GNU numbering styles, page delimiters, header/body/footer sections, blank-width handling, and complex paragraph heuristics; `pr` covers simple pagination and headers only. |
| `numfmt` / `od` | Effective subset | Field selection, rounding modes, grouping, localization, complete `od` type system, and address radix options. |
| `pathchk` / `factor` / `expr` | Effective subset | `pathchk` is configurable static validation; `factor` has a safety cap; `expr` is a safe AST subset, not full GNU string/regex semantics. |
| `pwd` / `realpath` / `readlink` | Effective subset | Logical/physical modes, relative-to/base, canonicalize-existing/missing, zero termination. |
| `rm` / `rmdir` / `unlink` / `shred` | Effective subset | Interactive modes, one-file-system, preserve-root variants, parent removal, verbose; real `shred` requires `--allow-destructive`. |
| `seq` / `yes` / `sleep` | Effective subset | Full GNU formatting/suffix parsing; `yes` and `sleep` are bounded by default for agent safety. |
| `sort` / `uniq` / `tr` / `shuf` / `tac` / `expand` / `unexpand` / `split` / `csplit` / `ptx` / `tsort` | Effective subset | Key/stable/merge/check, skip/check chars, character classes/ranges/complement, random sources, record separators, complex split/csplit suffix/filter modes, complete permuted-index options; `tsort` returns cycles as structured conflict errors. |
| `stat` / `wc` | Effective subset | Format/printf, filesystem mode, selective counters, files0-from, max-line-length. |
| `tee` / `sync` | Effective subset | Ignore interrupts, output-error policy; JSON by default, `--raw` echoes stdin; `sync` depends on platform support. |
| `test` / `[` | Effective subset | Full expression grammar, integer comparisons, timestamp comparisons, more file predicates; `[` is a lightweight structured-output expression alias. |
| `timeout` / `nice` / `nohup` / `kill` | Effective subset | Agent safety is prioritized: `timeout` captures bounded stdout/stderr, `nice` and `nohup` default to dry-run/explicit execution, and `kill` defaults to dry-run with real signals requiring `--allow-signal`; full GNU job-control and platform-specific semantics are not implemented. |
| `touch` / `truncate` | Effective subset | Date/reference/no-create/no-dereference, relative size operations, block units. |
| `true` / `false` | Effective subset | Preserves exit-code behavior, but GNU originals have no JSON envelope. |
| `uname` / `arch` / `hostname` / `hostid` / `logname` / `uptime` / `tty` / `users` / `who` / `nproc` | Effective subset | Individual field flags, OMP affinity, `--all`, `--ignore`, real login-session databases, and platform-specific uptime/TTY semantics. |

### Effectiveness Checks Performed

Automated tests cover:

- Unit tests: protocol envelopes and JSON writing
- CLI black-box tests: real subprocess calls and stdout/stderr contracts
- Golden file tests: stable output compared to golden files
- Sandbox tests: recursive delete outside the working directory is blocked
- Agent-call tests: observe, decide, dry-run, write, verify flow
- Error / exit-code tests: JSON errors and semantic exit codes
- Filesystem side-effect tests: dry-run does not mutate; writes mutate only expected targets
- CI tests: GitHub Actions config exists and runs unittest

Current verification command:

```powershell
python -m unittest discover -s tests -v
```

Current result: 54 tests passing.

### Objective Conclusion

The current implementation is complete enough for a defined agent-friendly core
surface, but incomplete relative to GNU Coreutils. The accurate description is:

> JSON-first agent-friendly subset inspired by GNU Coreutils.

Do not document it as "GNU-compatible" or "GNU Coreutils replacement" without
qualification.
