# GPTCodex 代码库变更日志 / GPTCodex Codebase Changelog

> **Status: historical archive**
> This document describes a point-in-time state and may be outdated.
> For current project status, see `docs/status/CURRENT_STATUS.md`.
>
> **Note (2026-04-30)**: The "remaining known gaps" section below was written
> before the sandbox hardening fixes were applied. All 5 sandbox escape gaps
> (dd, install, rm non-recursive, tee, truncate) have since been fixed in
> `src/agentutils/fs_commands.py`. The current test count is 99 passed, 0 failed.
> See `docs/analysis/DeepSeek-2026-04-30-安全加固与一致性修复-开发日志.md` for the fix details.

> 日期：2026-04-30
> 参考文档：`docs/analysis/GPTCodex-vs-DeepSeekCopilot-分析日志.md`
> 视角约定：本文中的 GPTCodex 指当前会话中的我；DeepSeekCopilot 指用户指定的另一方及既有分析日志视角。

## 中文说明

### 归因口径

本仓库的 git 作者信息不能直接证明某一段代码由哪个模型生成。因此本文采用可验证口径：

- **GPTCodex 已完成**：当前会话中我明确实现、重构、移动或验证过的内容。
- **DeepSeekCopilot / 既有实现**：我接手时已经存在，或由参考分析日志明确标记为 DeepSeekCopilot 视角的内容。
- **不确定来源**：git 历史能看到提交，但无法从本地证据判断具体模型来源的内容，按既有实现记录，不做强归因。

### 当前代码库状态

- `agentutils schema` 当前登记 113 个 CLI 命令。
- `src/agentutils/` 已拆分为协议、解析、文件系统、文本处理、系统命令、目录和注册表等模块。
- 当前测试入口覆盖 18 个 `test_*.py` 文件。
- 最新完整验证结果：`120 passed, 60 skipped`。
- Markdown 文档已重新按用途归档到 `docs/reference`、`docs/guides`、`docs/audits`、`docs/development`、`docs/agent-guides`、`docs/analysis`、`docs/reports`。

### DeepSeekCopilot / 既有实现：接手时已存在的主要内容

以下内容在我重新分析项目时已经存在，不能归为本轮 GPTCodex 生成：

- 初始项目骨架：`README.md`、`pyproject.toml`、`MANIFEST.in`、`.gitignore`、GitHub Actions CI、基础测试和 golden 文件。
- 早期文档基线：协议说明、使用说明、GNU 兼容性审计、测试说明。
- 核心 CLI 模块化实现：`protocol.py`、`parser.py`、`fs_commands.py`、`text_commands.py`、`system_commands.py`、`catalog.py`、`registry.py`。
- 大批 GNU/Coreutils 风格命令的初始实现，包括文件观察、文本处理、安全修改、系统上下文、执行控制等命令族。
- 早期分层测试体系：黑盒 CLI 测试、Agent 调用流测试、错误码测试、side-effect 测试、GNU 差分测试、property-based 测试、sandbox escape hardening 测试。
- `docs/agent-guides/CLAUDE.md`：AI 编码行为准则文档，已存在；当前只移动位置。
- `docs/reports/test/2026-04-30-agentutils-v0.1.0-test-report.md`：既有测试报告归档，当前只移动位置。
- `docs/analysis/GPTCodex-vs-DeepSeekCopilot-分析日志.md`：参考分析日志本身声明“分析者：DeepSeekCopilot”；它不是当前 GPTCodex 生成的原始内容，当前只作为分析输入并移动位置。

### GPTCodex 已完成：解析器、命令面和测试修正

当前会话中已经完成的代码层改动：

- 重构 `parser.py` 的 schema 命令清单生成逻辑，移除手写命令列表，改为从 argparse 注册结果自动获取。
- 修复 `--pretty` 的位置兼容问题，支持 `agentutils --pretty schema` 和 `agentutils schema --pretty`。
- 修复 `argparse.REMAINDER` 场景下 `--pretty` 被错误吞掉的问题，保证 `timeout ... -- --pretty` 能把参数传给子命令。
- 补齐测试依赖声明，将 `pytest>=8.0` 加入 `pyproject.toml` 的 test extra。
- 修复 Windows 下子进程测试输出的 UTF-8 解码和换行归一化问题。
- 收紧 property-based 测试策略，降低无效输入导致的误报和长耗时。
- 修正 raw 输出测试：raw 文本可以合法以 `{` 开头，测试应验证内容直通，而不是假设它不可能像 JSON。

### GPTCodex 已完成：新增剩余 CLI 命令

新增并注册了 7 个此前兼容性审计中标为缺失的 GNU/Coreutils 命令名：

- `coreutils`：输出当前 agentutils 命令面，支持 `--list` 和 `--raw`。
- `pinky`：返回轻量用户/会话记录。
- `stdbuf`：提供跨平台 buffering hints，并使用有界子进程捕获；不声称等同 GNU LD_PRELOAD 语义。
- `stty`：支持检查和 dry-run；真实修改需要 `--allow-change`。
- `chroot`：支持 dry-run 计划；真实执行需要 `--allow-chroot` 且依赖平台支持。
- `chcon`：支持 SELinux context dry-run；真实修改需要 `--allow-context`。
- `runcon`：支持 dry-run 计划；真实执行需要 `--allow-context` 且依赖平台 `runcon`。

同步更新：

- `src/agentutils/parser.py`
- `src/agentutils/system_commands.py`
- `src/agentutils/catalog.py`
- `src/agentutils/registry.py`
- `tests/test_remaining_coreutils_commands.py`
- `README.md`
- `docs/audits/GNU_COMPATIBILITY_AUDIT.md`

### GPTCodex 已完成：Markdown 存储结构调整

为避免 `docs/` 平铺文件过多，已按用途重组 Markdown：

```text
docs/
|-- README.md
|-- reference/AGENTUTILS.md
|-- guides/USAGE.zh-CN.en.md
|-- audits/GNU_COMPATIBILITY_AUDIT.md
|-- development/TESTING.md
|-- agent-guides/CLAUDE.md
|-- analysis/GPTCodex-vs-DeepSeekCopilot-分析日志.md
`-- reports/test/2026-04-30-agentutils-v0.1.0-test-report.md
```

同步处理：

- 更新根目录 README 中的文档链接和目录结构说明。
- 新增 `docs/README.md` 作为文档索引。
- 更新文档内部示例路径，例如 `docs/reference/AGENTUTILS.md`。
- 更新双语文档测试，排除 `docs/reports/` 中的归档报告。
- 验证 Markdown 相对链接可解析。

### 仍保留的已知缺口

这些缺口来自现有 skipped 测试和兼容性审计，当前未在本轮解决：

- `dd` 不阻止输出到工作区外路径。
- `install` 不阻止安装到工作区外目标。
- `rm` 对部分绝对路径/非递归外部文件删除仍有已知边界。
- `tee` 不阻止写入工作区外路径，也未完整解析符号链接目标。
- `truncate` 不阻止工作区外路径或符号链接目标。
- GNU 选项兼容性仍是子集级别，不是完整 GNU Coreutils replacement。

### 变更结论

参考日志中的核心判断仍成立：项目方向是“JSON-first、Agent-friendly、GNU Coreutils inspired subset”。但需要修正两点：

- 命令覆盖从参考日志中的 106 个提升到当前 113 个；原先列出的 7 个缺失命令名已经补齐为安全子集。
- 参考日志本身是 DeepSeekCopilot 视角产物，不应被误记为当前 GPTCodex 生成内容；当前 GPTCodex 的新增贡献主要集中在解析器修正、测试稳定化、剩余命令补齐和文档结构整理。

## English

### Attribution Rule

Git author metadata does not prove which model generated a specific change. This changelog uses a conservative rule:

- **Completed by GPTCodex**: changes explicitly implemented, moved, or verified by me in the current session.
- **DeepSeekCopilot / pre-existing implementation**: content that already existed when I took over, or content whose reference log states a DeepSeekCopilot perspective.
- **Unknown source**: changes visible in git history but not attributable to a specific model from local evidence.

### Current State

- `agentutils schema` now exposes 113 CLI commands.
- The codebase is organized into protocol, parser, filesystem, text, system, catalog, and registry modules.
- The test suite contains 18 `test_*.py` files.
- Latest full verification: `120 passed, 60 skipped`.
- Markdown documentation has been reorganized into purpose-specific directories under `docs/`.

### Pre-Existing / DeepSeekCopilot-Side Content

The following existed before this GPTCodex pass and should not be attributed to this current GPTCodex work:

- Initial project scaffold, package metadata, CI, baseline docs, and baseline tests.
- Core modular CLI implementation across `protocol.py`, `parser.py`, `fs_commands.py`, `text_commands.py`, `system_commands.py`, `catalog.py`, and `registry.py`.
- Early layered test suite, including GNU differential tests, property-based tests, and sandbox escape hardening tests.
- `docs/agent-guides/CLAUDE.md`, the archived test report, and the original `GPTCodex-vs-DeepSeekCopilot` analysis log.

### GPTCodex Changes

GPTCodex changes in this pass include:

- Parser schema introspection instead of a hardcoded command list.
- `--pretty` handling fixes for both global and subcommand positions.
- Test dependency and Windows subprocess encoding fixes.
- Property-test corrections for raw output and line handling.
- Seven additional command names implemented as safety-first subsets: `coreutils`, `pinky`, `stdbuf`, `stty`, `chroot`, `chcon`, and `runcon`.
- Documentation restructuring into categorized directories plus a new docs index.

### Remaining Known Gaps

The project still intentionally documents and skips several hardening gaps around outside-workspace writes, symlink target handling, and full GNU option compatibility. The project remains an agent-friendly subset inspired by GNU Coreutils, not a full GNU Coreutils replacement.
