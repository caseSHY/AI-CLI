# AIBaseCLI-ABC 全面重构计划 / Comprehensive Refactoring Plan

> **日期**：2026-05-02 | **基准 commit**：`cb3e61e` | **项目版本**：0.2.0
>
> 本计划基于对项目全部 18 个源文件、17 个测试文件、8+ 份文档及 CI/CD 基础设施的
> 全面审计编写。遵循「摸底→保底→定策→清扫→治本→固化→监控」七步方法论。

---

## 1. 摸底：读懂业务，锁定边界

### 1.1 业务功能全景

**agentutils** 是一个面向 LLM Agent 的 JSON 优先命令行工具包。它不是人用的 shell，
而是**机器调用的确定性接口层**。

```
┌─────────────────────────────────────────────────────────┐
│                    LLM Agent (调用方)                     │
│   function_call → subprocess.run(["agentutils", ...])   │
├─────────────────────────────────────────────────────────┤
│                 agentutils CLI 层                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │ 114 命令  │ │ JSON 协议│ │ 安全沙箱  │ │ 插件系统   │ │
│  │ (4 优先级)│ │ (信封格式)│ │ (cwd 边界)│ │ (命名空间)  │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
├─────────────────────────────────────────────────────────┤
│              操作系统（文件系统、进程、系统信息）           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 功能边界清单

#### 核心功能点（用户可见）

| 编号 | 功能域 | 命令数 | 说明 |
|------|--------|--------|------|
| F01 | 文件观察与读取 | 17 | ls/stat/cat/head/tail/wc/pwd/basename/dirname/realpath/readlink/test/[/md5sum/sha256sum/hash |
| F02 | 安全文件修改 | 20 | cp/mv/rm/mkdir/touch/ln/link/chmod/chown/chgrp/truncate/mktemp/mkfifo/mknod/install/tee/rmdir/unlink/shred |
| F03 | 文本转换与组合 | 30 | sort/uniq/cut/tr/comm/join/paste/shuf/tac/nl/fold/fmt/csplit/split/od/pr/ptx/numfmt/tsort/expand/unexpand/base64/base32/basenc/seq/cksum/sum/b2sum/sha1sum/sha224sum/sha384sum/sha512sum |
| F04 | 系统上下文与执行 | 42 | date/env/printenv/whoami/groups/id/uname/arch/hostname/hostid/logname/uptime/tty/users/who/nproc/df/du/dd/sync/dircolors/printf/echo/pathchk/factor/expr/true/false/sleep/yes/timeout/nice/nohup/kill/chroot/stdbuf/stty/chcon/runcon/coreutils/pinky |
| F05 | 元命令（Agent 内省） | 5 | catalog/schema/coreutils/tool-list/hash（二级） |

#### 输入输出契约

```
成功 → stdout: {"ok":true, "tool":"agentutils", "version":"0.2.0", "command":"...", "result":{...}, "warnings":[...]}
失败 → stderr: {"ok":false, "tool":"agentutils", "version":"0.2.0", "command":"...", "error":{"code":"...", "message":"...", ...}}
--raw → stdout: 原始字节流（绕过 JSON 信封）
--dry-run → 仅输出计划，零文件系统副作用
```

#### 退出码语义

| 码 | 语义 | 码 | 语义 |
|----|------|----|------|
| 0 | ok | 6 | conflict |
| 1 | predicate_false / general_error | 7 | partial_failure |
| 2 | usage | 8 | unsafe_operation (安全策略阻止) |
| 3 | not_found | 10 | io_error |
| 4 | permission_denied | | |
| 5 | invalid_input | | |

### 1.3 核心路径与"雷区"

#### 🔴 不能随意动的模块（安全关键）

| 模块 | 原因 | 修改要求 |
|------|------|----------|
| `core/sandbox.py` | cwd 边界校验、危险删除保护、覆盖保护 | 修改后必须跑全部 37 个沙箱逃逸测试 |
| `core/path_utils.py` | 路径解析、符号链接跟随、跨平台兼容 | 静默 PermissionError 需要显式警告标记 |
| `core/exceptions.py` + `core/exit_codes.py` | 退出码语义是协议级契约 | 修改退出码需更新安全模型文档 |
| `core/envelope.py` | JSON 信封格式是 Agent 协议的一部分 | 修改需同步 AGENTUTILS.md 协议说明 |

#### 🟡 经常出问题的模块

| 模块 | 典型问题 |
|------|----------|
| `parser.py` (3000+ 行) | 新增命令容易在 1500+ 行参数定义中出错 |
| `text_commands.py` (1800+ 行) | 文本处理边界条件（空输入、超长行、编码） |
| `protocol.py` (1200+ 行) | 工具函数散落，无清晰分组 |
| `plugins.py` | 可变全局状态，非线程安全 |

### 1.4 资产清单

#### 源代码资产

```
src/agentutils/              18 文件  ~8000+ 行 Python
├── __init__.py               55 行    公共 API 导出
├── __main__.py                5 行    CLI 入口
├── parser.py              3000+ 行  参数解析 + 分发（God File）
├── protocol.py            1200+ 行  工具函数 + 协议层（God File）
├── fs_commands.py         1500+ 行  文件系统命令（God File）
├── system_commands.py     1200+ 行  系统命令（God File）
├── text_commands.py       1800+ 行  文本处理命令（God File）
├── catalog.py              110 行   命令目录/优先级
├── registry.py              18 行   注册表（从 catalog 导出）
├── plugins.py               85 行   插件发现/注册
├── async_interface.py       60 行   异步接口
└── core/
    ├── __init__.py           40 行   核心子模块聚合
    ├── envelope.py           50 行   JSON 信封/序列化
    ├── exceptions.py         45 行   AgentError 异常类
    ├── exit_codes.py         18 行   语义退出码映射
    ├── path_utils.py        220 行   安全路径操作
    ├── sandbox.py           120 行   沙箱边界/安全校验
    └── stream.py             95 行   流式 NDJSON 输出
```

#### 测试资产

```
tests/                       17 文件  ~3000+ 行
├── support.py                        测试工具函数
├── test_agentutils.py                基础命令 (19 测试)
├── test_more_agent_commands.py       附加命令 (4 测试)
├── test_even_more_agent_commands.py  更多文本命令 (3 测试)
├── test_execution_and_page_commands.py 执行命令 (3 测试)
├── test_file_admin_commands.py       文件管理命令 (3 测试)
├── test_remaining_coreutils_commands.py 剩余命令 (7 测试)
├── test_system_alias_and_encoding_commands.py 系统别名 (3 测试)
├── test_error_exit_codes.py          错误码测试 (6 测试)
├── test_cli_black_box.py             CLI 黑盒 (5 测试)
├── test_agent_call_flow.py           Agent 流程 (1 测试)
├── test_golden_outputs.py            黄金样本 (2 测试)
├── test_core_and_extras.py           核心模块 (21 测试)
├── test_unit_protocol.py             协议单元 (3 测试)
├── test_property_based_cli.py        属性测试 (25 x 24 strategies)
├── test_gnu_differential.py          GNU 对照 (56 测试)
├── test_sandbox_escape_hardening.py  沙箱安全 (37 测试)
├── test_sandbox_and_side_effects.py  副作用 (3 测试)
├── test_docs_governance.py           文档治理 (9 测试)
├── test_docs_bilingual.py            双语验证 (1 测试)
├── test_ci_config.py                 CI 配置 (3 测试)
└── golden/
    ├── base64_hello.json
    └── seq_1_2_5.json
```

#### 外部系统依赖

| 依赖 | 用途 | 平台 |
|------|------|------|
| GNU Coreutils 9.10 | 对照测试 (test_gnu_differential.py) | Ubuntu/WSL |
| Python 3.11+ | 运行时 | 全平台 |
| GitHub Actions | CI/CD | 远程 |
| WSL Ubuntu-24.04 | 本地 CI | Windows 开发机 |
| pip packages: hypothesis, pytest, pytest-cov, ruff, mypy | 测试/静态检查 | 全平台 |

#### 配置文件

| 文件 | 用途 |
|------|------|
| `pyproject.toml` | 包构建、工具链配置 |
| `MANIFEST.in` | 分发文件清单 |
| `.github/workflows/ci.yml` | CI 流水线 |
| `.github/dependabot.yml` | 依赖自动更新 |
| `.github/copilot-instructions.md` | AI 编码行为准则 |
| `.github/instructions/*.instructions.md` | 文档/测试治理规则 |
| `AGENTS.md` | 仓库级 Agent 入口规则 |
| `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` | WSL 本地 CI |

#### 定时任务 / 自动化

| 机制 | 内容 |
|------|------|
| Dependabot (每周一) | pip 包 + GitHub Actions 版本更新 |
| GitHub Actions (push/PR) | 全平台 CI 流水线 |

#### 部署方式

- **当前**：开发原型，`pip install -e .` 本地可编辑安装
- **分发**：`pip install agentutils`（通过 PyPI 或源码）
- **无容器化/编排**：纯 Python 包，无 Docker/K8s

---

## 2. 保底：建立安全网

### 2.1 版本控制状态

✅ **已就绪**。项目已在 Git 仓库中，commit `cb3e61e` 已推送并通过 CI #7 全平台验证。

### 2.2 特征测试（Golden Tests）

✅ **已存在但可增强**。

**现有黄金样本**：
| 文件 | 命令 | 覆盖 |
|------|------|------|
| `tests/golden/base64_hello.json` | `base64` | 编码输出格式 |
| `tests/golden/seq_1_2_5.json` | `seq 1 2 5` | 序列输出格式 |

**建议扩展**（按优先级）：
| 优先级 | 新增黄金样本 | 原因 |
|--------|-------------|------|
| P0 | `ls --recursive` 输出 | 最高频调用，输出结构敏感 |
| P0 | `cat` 输出 (小文件) | 最基础读取命令 |
| P1 | `sort --numeric` 输出 | 排序稳定性关键 |
| P1 | `wc` 输出 (中英文混合) | 字符计数边界 |
| P1 | `stat` 输出 | 元数据结构契约 |
| P2 | `cp --dry-run` 输出 | 安全关键路径 |

### 2.3 一键回归机制

✅ **已存在**。

```powershell
# 完整回归（Windows 约 132 passed, 59 skipped）
$env:PYTHONPATH = "src"
python -m pytest tests/ -v --tb=short

# 快速回归（跳过 property-based 和 GNU differential）
python -m pytest tests/ -v --tb=short -k "not (property_based or Hypothesis or Gnu or gnu_differential)"

# WSL 完整回归（模拟 Ubuntu CI）
.\.github\scripts\run-ci-wsl.ps1 -Distro Ubuntu-24.04 -SkipInstall
```

### 2.4 关键路径集成测试

✅ **大部分已覆盖**。

| 路径 | 测试覆盖 | 状态 |
|------|---------|------|
| 文件读写 | test_agentutils, test_property_based_cli, test_gnu_differential | ✅ |
| 安全沙箱 | test_sandbox_escape_hardening (37), test_sandbox_and_side_effects (3) | ✅ |
| JSON 协议 | test_cli_black_box, test_unit_protocol, test_golden_outputs | ✅ |
| 错误码 | test_error_exit_codes (6) | ✅ |
| GNU 兼容 | test_gnu_differential (56) | ✅ (WSL/Ubuntu) |
| 文档治理 | test_docs_governance (9), test_docs_bilingual (1) | ✅ |
| 插件系统 | test_core_and_extras (基础) | ⚠️ 缺少端到端 |
| 异步接口 | test_core_and_extras (基础) | ⚠️ 缺少并发测试 |
| 流式输出 | test_core_and_extras (基础) | ⚠️ 缺少大容量测试 |

**需要补充的集成测试**：

1. **插件端到端测试**：创建临时 `agentutils_test_plugin` 包并验证发现/注册/调用
2. **异步并发测试**：`run_async_many` 的并发正确性和错误隔离
3. **流式大数据测试**：NDJSON 输出在 10万+ 条目的行为

---

## 3. 定策：选择重构策略

### 3.1 推荐策略：绞杀者模式 (Strangler Fig)

**结论：渐进替换，不是推倒重来。**

**理由**：
- 项目已在运行（CI 通过、测试覆盖良好）
- 核心协议（JSON 信封、退出码、沙箱）已稳定，不宜大改
- 重构目标主要是改善内部结构，不改变外在行为
- 五层优先级模型天然适合分模块替换
- 测试安全网已就绪，可支持小步迭代

### 3.2 为什么不做全量重写

| 条件 | 评估 |
|------|------|
| 项目极小 | ❌ 8000+ 行，114 命令，非微小项目 |
| 可停工数月 | ❌ 作为 Agent CLI 层，下游依赖方可能已在集成 |
| 原班业务专家深度参与 | ❌ 单人项目，知识集中在代码中 |
| 测试安全网完善 | ✅ 但重写意味着测试也需重写，安全网失效 |

### 3.3 分阶段路线图

```
Phase 0 (1-2 周): 清扫低风险项
  └── 死代码删除、命名统一、格式净化、Magic Number 常量化

Phase 1 (2-3 周): 拆分 God Files
  └── parser.py → parser/ 子包
  └── protocol.py → protocol/ 子包

Phase 2 (2-3 周): 命令模块重组
  └── fs_commands.py → commands/fs/ 子包
  └── text_commands.py → commands/text/ 子包
  └── system_commands.py → commands/system/ 子包

Phase 3 (1-2 周): 架构改善
  └── 配置对象集中化
  └── 插件系统线程安全化
  └── 错误处理模式统一

Phase 4 (持续): 固化与监控
  └── 补充测试覆盖
  └── CI 增强（macOS、覆盖率门禁）
  └── 开发者文档
```

---

## 4. 清扫：从风险最低的地方动手

以下每一项都是独立的、可回退的、低风险的改进。每完成一项，立即运行测试安全网。

### 4.1 🔴 死代码 / 废弃功能删除

| 编号 | 位置 | 问题 | 动作 | 风险 |
|------|------|------|------|------|
| D01 | `protocol.py` | `remove_one()` 重复定义（sandbox.py 中也有） | 合并到 sandbox.py，protocol.py 改为 re-export | 低 |
| D02 | `registry.py` | 18 行仅做 re-export，无实质逻辑 | 评估：可合并到 catalog.py | 极低 |
| D03 | `pyproject.toml` | `pytest-benchmark` 在 dev 依赖中但未见使用 | 移除或添加性能测试 | 极低 |
| D04 | 命令函数 | 多个命令函数的未使用参数 | 用 ruff + mypy 检测后清理 | 低 |
| D05 | `plugins.py` | `_PLUGIN_COMMANDS` 全局可变字典 | 改为不可变注册（见 5.4） | 中 |

### 4.2 🟡 命名净化

| 编号 | 当前命名 | 建议命名 | 位置 | 原因 |
|------|---------|---------|------|------|
| N01 | `CATALOG` (全局 list) | `_COMMAND_CATALOG` | catalog.py | 下划线前缀表明内部使用 |
| N02 | `_BUILTIN_CATALOG` | 统一为 `_CATALOG` | plugins.py | 与 catalog.py 一致 |
| N03 | `command_*` 函数 | 保持不变 | 各处 | 当前命名模式一致 ✅ |
| N04 | `HASH_ALGORITHMS` | `_HASH_ALGORITHM_MAP` | protocol.py | 表明是内部映射表 |
| N05 | `EXIT` (dict) | `EXIT_CODE_MAP` | exit_codes.py | 更明确 |

### 4.3 🟡 统一格式

✅ **已通过 ruff 强制执行**，无需额外工作。当前配置：

- 行长度 120
- 双引号
- isort 导入排序
- pyupgrade 语法现代化
- flake8-bugbear / comprehensions / simplify 规则

### 4.4 🟠 Magic Number 常量化

在 `core/` 或 `protocol.py` 中创建集中常量模块：

```python
# 建议: src/agentutils/core/constants.py 或直接在 protocol.py 顶部

# 输出限制
DEFAULT_MAX_LINES = 10_000
DEFAULT_MAX_BYTES = 65_536  # 64 KiB
DEFAULT_MAX_OUTPUT_BYTES = 65_536
DEFAULT_MAX_PATH_LENGTH = 4_096

# 文本处理
DEFAULT_TAB_SIZE = 8
DEFAULT_WIDTH = 80

# 计算限制
FACTOR_MAX = 10**12

# 并发
ASYNC_DEFAULT_CONCURRENCY = 10
ASYNC_DEFAULT_TIMEOUT = 30.0
```

**影响文件**：`parser.py` (20+ 处), `text_commands.py` (15+ 处), `fs_commands.py` (10+ 处), `protocol.py` (5+ 处)

| 编号 | 值 | 出现次数 | 位置 |
|------|-----|---------|------|
| M01 | `10000` (max-lines 默认值) | 20+ | parser.py, text_commands.py, fs_commands.py |
| M02 | `65536` / `1024*64` (max-bytes 默认值) | 10+ | parser.py, fs_commands.py, system_commands.py |
| M03 | `4096` (max-path-length 默认值) | 3 | parser.py |
| M04 | `8` (tab size 默认值) | 4 | text_commands.py |
| M05 | `1024*1024` (1 MiB) | 5+ | protocol.py, text_commands.py |
| M06 | `10**12` (factor 上限) | 2 | system_commands.py |
| M07 | `10` (async concurrency) | 1 | async_interface.py |
| M08 | `30.0` (async timeout) | 1 | async_interface.py |

### 4.5 🟠 重复代码合并

| 编号 | 模式 | 出现位置 | 合并建议 |
|------|------|---------|---------|
| C01 | `remove_one()` | sandbox.py:50-70, protocol.py:1020-1040 | 统一到 sandbox.py，protocol.py 改为 re-export |
| C02 | `--dry-run` 参数定义 | parser.py ~50 处重复 | 提取为 `add_dry_run_argument(parser)` |
| C03 | `--raw` 参数定义 | parser.py ~40 处重复 | 提取为 `add_raw_argument(parser)` |
| C04 | `--encoding` 参数定义 | parser.py ~30 处重复 | 提取为 `add_encoding_argument(parser)` |
| C05 | `try/except OSError → AgentError` | 各处 ~80 处 | 评估是否可用上下文管理器/decorator |

### 4.6 🟠 错误处理模式统一

当前三种模式：

```python
# 模式 A: try/except → AgentError (最常见)
try:
    path.mkdir(...)
except PermissionError as exc:
    raise AgentError("permission_denied", ...) from exc

# 模式 B: if-check → AgentError (条件判断)
if not args.allow_overwrite:
    raise AgentError("conflict", ...)

# 模式 C: Silent swallow (静默吞掉，仅在 iter_directory 中)
except PermissionError:
    return
```

**建议**：
- 模式 C 应添加 `warnings` 标记，告知 Agent "有部分目录因权限不足被跳过"
- 所有模式 C 处加 `# SECURITY: silent skip is intentional` 注释

### 4.7 🟡 访问控制收紧

| 位置 | 当前 | 建议 |
|------|------|------|
| catalog.py | `CATALOG` 公开 | 改为 `_CATALOG`，通过 `get_*` 函数访问 |
| plugins.py | `_PLUGIN_COMMANDS` 全局可变 | 改为类属性（见 5.4） |
| protocol.py | `HASH_ALGORITHMS` 公开 dict | 改为 `_HASH_ALGORITHMS` |
| 各命令模块 | 内部辅助函数公开 | 评估加 `_` 前缀 |

---

## 5. 治本：改善架构与数据

### 5.1 God File 拆分计划

#### 5.1.1 parser.py (3000+ 行) → `parser/` 子包

```
src/agentutils/parser/
├── __init__.py          # 导出 build_parser(), dispatch(), main()
├── _specs.py            # 命令参数规格（声明式定义，替代 1500+ 行 inline argparse）
├── _dispatch.py         # 命令分发逻辑
├── _shared_args.py      # 共享参数（--dry-run, --raw, --encoding, --max-lines...）
├── _introspection.py    # catalog/schema/coreutils/tool-list 子命令
├── _fs_subparsers.py    # 文件系统相关子命令
├── _text_subparsers.py  # 文本处理相关子命令
├── _system_subparsers.py # 系统相关子命令
└── _meta_subparsers.py  # 元命令子命令
```

**规格声明式定义示例**：

```python
# _specs.py
COMMAND_SPECS: dict[str, dict] = {
    "ls": {
        "help": "List directory contents.",
        "priority": "P0",
        "arguments": [
            {"name": "path", "nargs": "?", "default": ".", "help": "Directory or file to list."},
            {"name": "--recursive", "action": "store_true", "help": "Recurse into directories."},
            {"name": "--max-depth", "type": int, "default": None},
            {"name": "--max-lines", "type": int, "default": DEFAULT_MAX_LINES},
            {"name": "--limit", "type": int, "default": DEFAULT_MAX_LINES},
            {"name": "--all", "action": "store_true", "help": "Include hidden files."},
            {"name": "--raw", "action": "store_true"},
        ],
        "func": "agentutils.fs_commands.command_ls",
    },
    # ... 114 个命令的声明式定义
}
```

#### 5.1.2 protocol.py (1200+ 行) → `protocol/` 子包

```
src/agentutils/protocol/
├── __init__.py          # Re-export 所有公共 API
├── _io.py               # read_stdin_bytes, read_input_bytes, combined_lines, bounded_lines...
├── _hashing.py          # digest_file, digest_bytes, simple_sum16, HASH_ALGORITHMS
├── _text.py             # decode_standard_escapes, split_fields, squeeze_repeats, expand_tr_set...
├── _numfmt.py           # parse_numfmt_value, format_numfmt_value
├── _printf.py           # printf_conversions, coerce_printf_value, format_printf
├── _system.py           # resolve_user_id, resolve_group_id, subprocess helpers, uptime...
├── _path.py             # path_issues, evaluate_test_predicates, prime_factors
├── _ranges.py           # parse_ranges, selected_indexes, alpha_suffix, numeric_suffix
└── _parser.py           # AgentArgumentParser 类
```

#### 5.1.3 命令模块 → `commands/` 子包

```
src/agentutils/commands/
├── __init__.py
├── fs/
│   ├── __init__.py
│   ├── _read.py        # cat, head, tail, wc
│   ├── _list.py        # ls, dir, vdir, stat
│   ├── _navigate.py    # pwd, realpath, readlink, basename, dirname
│   ├── _create.py      # mkdir, touch, mktemp, mkfifo, mknod
│   ├── _copy.py        # cp, mv, ln, link, install
│   ├── _permissions.py # chmod, chown, chgrp
│   ├── _delete.py      # rm, rmdir, unlink, shred
│   ├── _hash.py        # hash, md5sum, sha*sum, b2sum, cksum, sum
│   ├── _disk.py        # df, du, dd, sync
│   └── _test.py        # test, [
├── text/
│   ├── __init__.py
│   ├── _sort.py        # sort, uniq, tsort
│   ├── _compare.py     # comm, join
│   ├── _merge.py       # paste
│   ├── _select.py      # cut, shuf, tac
│   ├── _format.py      # nl, fold, fmt, pr
│   ├── _split.py       # csplit, split
│   ├── _transform.py   # tr, expand, unexpand
│   ├── _encode.py      # codec, basenc
│   ├── _numeric.py     # numfmt, seq, od
│   ├── _output.py      # printf, echo, yes
│   └── _index.py       # ptx
└── system/
    ├── __init__.py
    ├── _info.py         # date, uname, arch, hostname, hostid, uptime, nproc
    ├── _user.py         # whoami, groups, id, logname, pinky, users, who
    ├── _env.py          # env, printenv
    ├── _tty.py          # tty
    ├── _exec.py         # timeout, nice, nohup, stdbuf, chroot
    ├── _signal.py       # kill
    ├── _terminal.py     # stty
    ├── _security.py     # chcon, runcon
    └── _math.py         # sleep, true, false, expr, factor, pathchk, seq
```

### 5.2 配置对象集中化

```python
# 建议: src/agentutils/core/config.py
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True)
class AgentConfig:
    """Immutable configuration for agentutils commands."""

    # Output bounds
    max_lines: int = 10_000
    max_bytes: int = 65_536
    max_output_bytes: int = 65_536
    max_path_length: int = 4_096

    # Text processing
    tab_size: int = 8
    default_width: int = 80

    # Computation limits
    factor_max: int = 10**12

    # Concurrency
    async_concurrency: int = 10
    async_timeout: float = 30.0

    # Paths
    cwd: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Overrides from AGENTUTILS_* environment variables."""
        # ...
```

### 5.3 插件系统线程安全化（当前已知问题）

**问题**：
- `_PLUGIN_COMMANDS` 是模块级全局字典
- `register_plugin_command()` 会修改 `CATALOG` 列表（可变全局状态）
- 无锁保护，import 时注册可能产生竞争

**修复方案**：

```python
# 改为不可变的注册表
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class PluginRegistry:
    commands: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def register(self, name: str, func: Callable[..., Any]) -> "PluginRegistry":
        new_cmds = dict(self.commands)
        new_cmds[name] = func
        return PluginRegistry(commands=new_cmds)

    def discover(self) -> "PluginRegistry":
        """Discover and merge plugins."""
        # ... 返回新的不可变实例

# 全局单例在 main() 中初始化，不作为模块级可变状态
```

### 5.4 N+1 问题检查

✅ **本项目不涉及数据库**，无 N+1 问题。但存在类似的循环 I/O 模式：

| 模式 | 位置 | 风险 |
|------|------|------|
| `iter_directory()` 用 `rglob("*")` | protocol.py:1070 | 大目录 OOM |
| `ls --recursive` 先收集全量再返回 | fs_commands.py | 大目录 OOM |
| `StreamWriter` 定义了但几乎未用 | stream.py | 浪费设计 |

**修复**：`iter_directory()` 改用迭代式 `scandir()` + 手动深度跟踪，配合 `StreamWriter` 流式输出。

### 5.5 外部依赖管理

✅ **零运行时依赖** — 这是优势，需保持。

- 测试依赖：hypothesis, pytest, pytest-cov, ruff, mypy → 在 `[project.optional-dependencies]` 中定义
- 开发依赖：同上 + pytest-benchmark → 在使用前保留但标记为 `# TODO: add benchmark tests or remove`

---

## 6. 固化：防止再次腐烂

### 6.1 CI 流水线增强

| 编号 | 增强项 | 优先级 | 说明 |
|------|--------|--------|------|
| CI01 | 添加 macOS runner | P2 | 扩展到 `macos-latest`, Python 3.12/3.13 |
| CI02 | 覆盖率门禁 | P2 | `--cov-fail-under=70` 阻断低于 70% 的 PR |
| CI03 | 静态检查到 Windows | P3 | ruff + mypy 目前只在 ubuntu 跑 |
| CI04 | 自动化黄金样本更新 | P3 | `python -m agentutils ... > tests/golden/xxx.json` 脚本化 |
| CI05 | Node.js 20 警告修复 | P4 | 等待上游 actions/checkout 和 actions/setup-python 更新 |

### 6.2 开发者文档补充

#### 需要写的文档（按价值排序）

1. **架构决策记录 (ADR)** — `docs/development/adr/`
   - 为什么选择 JSON 优先而非兼容 GNU 输出？
   - 为什么安全策略优先于 GNU 行为兼容？
   - 为什么零运行时依赖？
   - 为什么退出码是 0/1/2/3/4/5/6/7/8/10 而不是 POSIX 标准码？

2. **关键概念解释** — `docs/development/CONCEPTS.md`
   - JSON 信封协议
   - dry-run 语义
   - 沙箱边界模型
   - 优先级模型 (P0-P3)

3. **本地开发快速启动** — 更新时间 < 5 分钟可启动
   ```powershell
   git clone ...
   cd AIBaseCLI-ABC
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   python -m pytest tests/ -v --tb=short
   ```

### 6.3 编码规约（血泪清单）

基于本次审计，以下规则应加入 `.github/copilot-instructions.md` 或新建 `docs/development/CONVENTIONS.md`：

1. **禁止在模块级定义可变全局状态** — 使用不可变结构 + 单例初始化
2. **所有命令函数必须支持 `--dry-run`** — 即使是只读命令，也应明确返回计划
3. **新增参数优先使用声明式 spec** — 不在 `build_parser()` 中 inline 定义
4. **文件不得超过 500 行** — 超过即触发拆分讨论
5. **所有 mutating 命令的 cwd 边界校验不可绕过** — 除显式 `--allow-outside-cwd`
6. **修改安全模块后必须跑全部 37 个沙箱测试**
7. **中英文档必须同步更新** — 治理规则已强制执行
8. **测试数量变更必须通过事实传播矩阵检查**

---

## 7. 监控与循环

### 7.1 当前状态监控

| 指标 | 当前值 | 目标 | 监控方式 |
|------|--------|------|----------|
| 测试通过率 | 100% (0 failed) | ≥ 100% | CI 自动运行 |
| 覆盖率 | 未设门禁 | ≥ 70% | pytest-cov + CI 门禁 |
| ruff 违规 | 0 | 0 | CI lint job |
| mypy 类型错误 | 0 | 0 | CI typecheck job |
| 沙箱逃逸漏洞 | 0 (全部已修复) | 0 | 37 专项测试 |
| GNU 对照测试 | 54/56 (WSL) | 54/56 | WSL CI |
| 文档双语一致性 | 通过 | 通过 | test_docs_bilingual |

### 7.2 技术债务登记表

| 编号 | 问题 | 优先级 | 预计工时 | 依赖 |
|------|------|--------|---------|------|
| TD01 | parser.py God File 拆分 | P1 | 3-5 天 | 无 |
| TD02 | protocol.py 拆分子包 | P1 | 2-3 天 | TD01 |
| TD03 | Magic Number 常量化 | P1 | 1-2 天 | 无 |
| TD04 | `remove_one()` 重复代码合并 | P2 | 0.5 天 | 无 |
| TD05 | 插件系统全局状态修复 | P2 | 1-2 天 | 无 |
| TD06 | 流式输出 (`StreamWriter`) 实际应用 | P2 | 2-3 天 | TD01 |
| TD07 | 补充插件端到端测试 | P2 | 1-2 天 | TD05 |
| TD08 | 补充异步并发测试 | P2 | 1 天 | 无 |
| TD09 | 黄金样本扩展 (5 个新样本) | P3 | 1 天 | 无 |
| TD10 | 架构决策记录 (ADR) | P3 | 2 天 | 无 |
| TD11 | 开发者文档 (CONCEPTS.md) | P3 | 1 天 | 无 |
| TD12 | macOS CI runner | P3 | 0.5 天 | 无 |
| TD13 | 覆盖率门禁 (70%) | P3 | 0.5 天 | TD01-TD08 |
| TD14 | 命名净化 (5 处) | P4 | 0.5 天 | 无 |
| TD15 | `iter_directory()` OOM 修复 | P4 | 1 天 | TD01 |

### 7.3 下批迭代建议

**迭代 1 (第 1-2 周)：低风险清扫**
- TD03: Magic Number 常量化
- TD04: `remove_one()` 合并
- TD14: 命名净化
- D01-D05: 死代码清理

**迭代 2 (第 3-4 周)：God File 拆分**
- TD01: parser.py 拆分
- TD02: protocol.py 拆分
- 命令模块重组（fs/text/system → commands/ 子包）

**迭代 3 (第 5-6 周)：架构改善**
- TD05: 插件系统修复
- TD06: 流式输出应用
- TD07-TD08: 测试补充
- TD11: 开发者文档

**迭代 4 (第 7-8 周)：CI 与固化**
- TD09: 黄金样本扩展
- TD12: macOS CI
- TD13: 覆盖率门禁
- TD10: ADR 编写

---

## 附录 A：风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 重构破坏 JSON 协议格式 | 中 | 高 | Golden tests + test_cli_black_box 先跑 |
| 重构改变退出码语义 | 低 | 高 | test_error_exit_codes 保护 |
| 重构引入沙箱逃逸 | 低 | 严重 | 37 个沙箱测试必须先通过 |
| 重构改变命令输出 | 中 | 中 | test_gnu_differential 为安全网 |
| 重构破坏插件兼容 | 中 | 中 | 补充插件端到端测试 |
| 开发时间超出预期 | 高 | 低 | 每迭代独立可交付，可随时停止 |

---

## 附录 B：文件大小阈值

| 级别 | 行数 | 对应文件 | 建议动作 |
|------|------|---------|---------|
| ✅ 合理 | < 300 | envelope.py, exceptions.py, exit_codes.py, stream.py, plugins.py, async_interface.py, catalog.py, registry.py | 保持 |
| ⚠️ 偏大 | 300-800 | path_utils.py(220), sandbox.py(120) | 暂时可接受 |
| 🔴 需拆分 | > 800 | parser.py(3000+), text_commands.py(1800+), fs_commands.py(1500+), system_commands.py(1200+), protocol.py(1200+) | 按计划拆分 |

---

## 附录 C：测试统计（基准 2026-05-02）

| 平台 | passed | skipped | failed | subtests |
|------|--------|---------|--------|----------|
| Windows 本地 | 132 | 59 | 0 | 118 |
| WSL Ubuntu 本地 | 190 | 1 | 0 | 118 |
| CI Ubuntu | 190+ | 1 | 0 | 118 |
| CI Windows | 132+ | 59 | 0 | 118 |

---

> **下一步行动**：评审本计划，确认优先级和工时估算，然后从迭代 1 的 TD03 (Magic Number 常量化) 开始执行。
