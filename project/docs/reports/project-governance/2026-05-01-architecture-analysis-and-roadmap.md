# Agentutils 架构分析与开发路线图 / Architecture Analysis & Development Roadmap

> **Status: historical archive** ⚠️
> This document describes a point-in-time state (pre-refactoring, v0.1.0-era module structure) and may be outdated.
> For current project status, see `docs/status/CURRENT_STATUS.md`.

> 创建日期: 2026-05-01 | 版本: 0.1.0 | 作者: AI 辅助分析

---

## 一、项目现状总览 / Current State Overview

| 维度 | 现状 |
|---|---|
| **版本** | v0.1.0 |
| **命令数** | 114 (含 5 个元命令) |
| **测试通过** | 136 (54 skipped, 0 failed) |
| **Python** | >=3.11, 开发环境 3.14.4 |
| **平台** | Windows 11 (dev), Ubuntu + Windows (CI) |
| **核心定位** | JSON-first CLI toolkit for LLM Agents, inspired by GNU Coreutils |
| **安全模型** | cwd sandbox + dry-run + 危险命令门控 + 覆盖保护 |

---

## 二、架构分析 / Architecture Analysis

### 2.1 当前模块结构

```
src/agentutils/
├── __init__.py        # 版本号
├── __main__.py        # 入口: from .parser import main
├── cli.py             # ⚠️ 向后兼容重导出模块 (冗余层)
├── parser.py          # CLI 解析、命令调度、schema/catalog 辅助函数
├── protocol.py        # ⚠️ 超大类: AgentError、JSON envelope、路径工具、哈希、
│                      #   文本处理、子进程工具、sandbox 校验...
├── registry.py        # 命令注册表 + P0-P3 优先级分类
├── catalog.py         # 优先级编目定义
├── fs_commands.py     # 文件系统命令 (~800+ 行)
├── text_commands.py   # 文本转换命令 (~700+ 行)
└── system_commands.py # 系统信息/进程命令 (~600+ 行)
```

### 2.2 架构优势 / Strengths

| 优势 | 说明 |
|---|---|
| **清晰的命令分层** | P0(观察)→P1(修改)→P2(文本)→P3(系统) 优先级模型设计合理 |
| **安全优先设计** | cwd sandbox、dry-run、危险命令门控构成了深度防御 |
| **Protocol 一致性** | 统一的 JSON envelope + 语义化退出码，适合机器消费 |
| **测试矩阵完备** | property-based + golden + GNU differential + sandbox escape + CI config |
| **文档治理严格** | 双语镜像规则 + 事实传播矩阵，防止文档漂移 |
| **零外部依赖** | 核心运行时无三方依赖，仅测试依赖 pytest + hypothesis |

### 2.3 架构问题 / Architectural Issues

#### 🔴 严重问题

| 编号 | 问题 | 影响 |
|---|---|---|
| **A-001** | `cli.py` 是纯重导出模块，`pyproject.toml` 入口指向 `aicoreutils.cli:main`，但真正的 main 在 `parser.py` | 多一层无意义间接，增大维护负担 |
| **A-002** | `protocol.py` 是"上帝模块"：混合了异常类、JSON 工具、路径解析、哈希计算、文本处理、子进程管理、sandbox 校验、用户信息查询等数十个函数 | 单文件过大(预估 600+ 行)，职责不清，难以测试和维护 |
| **A-003** | 三个命令模块 (`fs_commands.py`, `text_commands.py`, `system_commands.py`) 各包含 20-50 个命令函数，文件体积过大 | 新增命令困难，合并冲突风险高 |
| **A-004** | `registry.py` 的 `_COMMAND_PRIORITY_MAP` 与 `catalog.py` 的 `CATALOG` 是手工维护的冗余数据源 | 新增命令需同时修改两处，易遗漏 |

#### 🟡 中等问题

| 编号 | 问题 | 影响 |
|---|---|---|
| **B-001** | 无插件/扩展机制，新增命令需要修改核心代码 | 社区贡献门槛高 |
| **B-002** | 无流式输出支持，大文件/大目录结果一次性加载到内存 | 内存风险，Agent 等待时间长 |
| **B-003** | 无异步支持，所有 I/O 操作阻塞 | 不适合高并发 Agent 场景 |
| **B-004** | 无类型检查（mypy/pyright）集成到 CI | 类型错误只能在运行时发现 |
| **B-005** | 无 linting（ruff/flake8）集成到 CI | 代码风格不一致风险 |
| **B-006** | 无代码覆盖率追踪 | 无法量化测试质量 |
| **B-007** | 无性能基准测试 | 无法检测性能退化 |
| **B-008** | `--raw` 模式的管道组合能力弱，仅支持简单字节输出 | 复杂管道场景不如原生 GNU |

#### 🟢 轻微问题

| 编号 | 问题 | 影响 |
|---|---|---|
| **C-001** | 缺少 Sphinx/API 文档自动生成 | 开发者上手成本高 |
| **C-002** | 无命令补全（shell completion） | 用户体验受限 |
| **C-003** | 无 Docker 化部署方案 | CI/部署一致性不足 |
| **C-004** | `MANIFEST.in` 存在但未验证 sdist 构建 | 发布可能缺文件 |
| **C-005** | Windows symlink 测试全部 skip，未在 CI Ubuntu 实际验证 | 安全关键路径未全覆盖 |

---

## 三、开发方向规划 / Development Directions

### 3.1 战略方向 / Strategic Directions

```
          稳定性 ──────────── 功能深度
            │                    │
            │   Phase 1          │   Phase 2
            │   (v0.2)           │   (v0.3)
            │   架构清理         │   功能增强
            │   CI 完善          │   GNU 兼容深化
            │   代码质量         │   流式/异步
            │                    │
   ─────────┼────────────────────┼──────────
            │                    │
            │   Phase 3          │   Phase 4
            │   (v0.4)           │   (v1.0)
            │   生态建设         │   稳定发布
            │   插件系统         │   性能优化
            │   API 文档         │   长期支持
            │                    │
          简洁性 ──────────── 生态广度
```

### 3.2 四大支柱 / Four Pillars

1. **代码质量 (Code Quality)**: 类型安全、linting、覆盖率、基准测试
2. **架构健壮 (Architecture)**: 模块化、去冗余、可测试性
3. **功能深度 (Feature Depth)**: 流式输出、异步支持、GNU 兼容深化
4. **生态完善 (Ecosystem)**: 插件系统、API 文档、Shell 补全、Docker

---

## 四、分阶段实施计划 / Phased Implementation Plan

### Phase 1: 架构清理与质量基础设施 (v0.2.0) 🎯 建议优先

> **目标**: 清理技术债务，建立 CI 质量门禁，为后续开发奠定基础
> **预估周期**: 2-4 周

| 任务 | 优先级 | 说明 |
|---|---|---|
| **1.1 消除 cli.py 冗余** | P0 | 将 `pyproject.toml` 入口点改为 `agentutils.parser:main`，删除 `cli.py` |
| **1.2 拆分 protocol.py** | P0 | 拆为 `exceptions.py`, `envelope.py`, `path_utils.py`, `hash_utils.py`, `text_utils.py`, `sandbox.py` |
| **1.3 拆分大命令模块** | P1 | `fs_commands/` 按命令组拆分 (如 `read.py`, `write.py`, `metadata.py`)；`text_commands/` 和 `system_commands/` 同理 |
| **1.4 统一 registry 数据源** | P1 | `catalog.py` 的 `CATALOG` 作为唯一数据源，`registry.py` 从 catalog 自动派生 |
| **1.5 CI 集成类型检查** | P0 | 添加 `mypy --strict` 到 CI workflow |
| **1.6 CI 集成 linting** | P0 | 添加 `ruff check` 到 CI workflow |
| **1.7 CI 集成覆盖率** | P1 | 添加 `pytest-cov` + 覆盖率报告 |
| **1.8 触发 CI GNU 对照验证** | P1 | Push 代码触发 CI，验证 Ubuntu 上 50+ GNU 对照测试通过 |
| **1.9 修复类型注解** | P1 | 补全所有函数签名、返回值类型 |
| **1.10 验证 sdist 构建** | P2 | `python -m build` 验证 `MANIFEST.in` |

**Phase 1 验收标准**:
- [ ] `mypy --strict` 零错误
- [ ] `ruff check` 零警告
- [ ] 测试通过数 ≥ 当前 (136)
- [ ] CI 全部通过 (Ubuntu + Windows, 3 Python versions)
- [ ] GNU 对照测试在 Ubuntu CI 上 ≥ 50 通过
- [ ] CLI 入口无冗余模块

### Phase 2: 功能增强与 GNU 兼容深化 (v0.3.0)

> **目标**: 提升 Agent 使用体验，缩小 GNU 兼容差距
> **预估周期**: 4-8 周

| 任务 | 优先级 | 说明 |
|---|---|---|
| **2.1 流式 JSON 输出** | P0 | 大目录 `ls`、长文件 `cat` 支持 `--stream` 逐条输出 NDJSON |
| **2.2 异步命令接口** | P1 | 提供 `async def` 命令变体，支持 `asyncio` 并发调用 |
| **2.3 输出分页** | P1 | `ls`/`cat` 大量结果支持 `--page N` 分页，配合 `--cursor` 续取 |
| **2.4 GNU 关键缺口补齐** | P1 | 优先补齐 P0/P1 命令的高频选项: `cat` 多文件、`sort` key/stable、`chmod` 递归、`cp` preserve |
| **2.5 管道增强** | P2 | `--raw` 模式下支持真正的 stdin→stdout 管道传递 (如 `aicoreutils cat a.txt --raw | aicoreutils sort --raw`) |
| **2.6 输入校验增强** | P2 | 统一参数校验层，每个命令自动校验必填参数和类型 |
| **2.7 错误信息国际化** | P3 | 错误 message 支持中/英双语切换 |
| **2.8 性能基准套件** | P2 | 添加 `pytest-benchmark`，CI 中追踪关键命令性能 |

**Phase 2 验收标准**:
- [ ] 流式输出在 10 万文件目录下内存 ≤ 50MB
- [ ] GNU 对照测试通过率 ≥ 80% (Ubuntu CI)
- [ ] 性能基准 CI 可运行

### Phase 3: 生态建设与可扩展性 (v0.4.0)

> **目标**: 建立插件生态，完善开发体验
> **预估周期**: 4-8 周

| 任务 | 优先级 | 说明 |
|---|---|---|
| **3.1 插件系统** | P0 | `agentutils` 发现 `agentutils_*` 命名空间包，自动注册命令 |
| **3.2 API 文档生成** | P0 | Sphinx 自动生成 API 参考文档 |
| **3.3 Shell 补全** | P1 | 支持 bash/zsh/powershell 的 `--install-completion` |
| **3.4 Docker 镜像** | P1 | 提供 `ghcr.io/.../aicoreutils` 容器镜像 |
| **3.5 命令别名系统** | P2 | `aicoreutils config set alias.ll "ls --recursive --max-depth 1"` |
| **3.6 配置文件支持** | P2 | `~/.aicoreutils.toml` 全局默认参数 |
| **3.7 交互式 schema 浏览器** | P3 | `agentutils schema --interactive` 在终端浏览命令树 |

### Phase 4: 稳定化与 1.0 (v1.0.0)

> **目标**: 达到生产级稳定，承诺 API 兼容
> **预估周期**: 4-8 周

| 任务 | 优先级 | 说明 |
|---|---|---|
| **4.1 API 稳定性审查** | P0 | 冻结 public API，标记 `@deprecated` |
| **4.2 安全审计** | P0 | 第三方安全审计，覆盖所有 mutating 命令 |
| **4.3 性能优化** | P1 | 热点路径 profile + 优化 |
| **4.4 长期支持策略** | P1 | 制定 LTS 发布周期、backport 策略 |
| **4.5 迁移指南** | P2 | v0.x → v1.0 迁移文档 |
| **4.6 合规审查** | P2 | 许可证合规、依赖审计 |

---

## 五、架构重构详细方案 / Architecture Refactoring Blueprint

### 5.1 目标架构 / Target Architecture

```
src/agentutils/
├── __init__.py                # 版本号 + public API 重导出
├── __main__.py                # from .parser import main
├── parser.py                  # CLI 解析 + 命令调度
│
├── core/                      # 核心协议层 (从 protocol.py 拆分)
│   ├── __init__.py
│   ├── exceptions.py          # AgentError
│   ├── envelope.py            # envelope(), error_envelope(), write_json(), utc_iso()
│   ├── exit_codes.py          # EXIT 字典
│   ├── path_utils.py          # resolve_path(), path_type(), stat_entry()
│   └── sandbox.py             # require_inside_cwd(), dangerous_delete_target()
│
├── hashing/                   # 哈希/校验子模块
│   ├── __init__.py
│   ├── algorithms.py          # HASH_ALGORITHMS, digest_file(), digest_bytes()
│   └── checksums.py           # simple_sum16(), cksum 逻辑
│
├── text/                      # 文本处理子模块
│   ├── __init__.py
│   ├── lines.py               # bounded_lines(), combined_lines(), lines_to_raw()
│   ├── formatting.py          # format_printf(), format_numfmt_value(), decode_standard_escapes()
│   └── transforms.py          # transform_text(), split_fields(), parse_ranges()
│
├── system/                    # 系统工具子模块
│   ├── __init__.py
│   ├── users.py               # active_user_entries(), resolve_user_id(), resolve_group_id()
│   ├── process.py             # run_subprocess_capture(), subprocess_result()
│   └── platform_info.py       # system_uptime_seconds(), stdin_tty_name()
│
├── commands/                  # 命令实现 (按域分包)
│   ├── __init__.py            # 命令注册 + 自动发现
│   ├── fs/                    # 文件系统命令
│   │   ├── __init__.py
│   │   ├── read.py            # ls, stat, cat, head, tail, wc
│   │   ├── path.py            # pwd, basename, dirname, realpath, readlink
│   │   ├── write.py           # cp, mv, rm, mkdir, touch, truncate
│   │   ├── link.py            # ln, link, unlink, readlink
│   │   ├── permission.py      # chmod, chown, chgrp
│   │   └── special.py         # mkfifo, mknod, mktemp, install, shred, dd
│   ├── text/                  # 文本命令
│   │   ├── __init__.py
│   │   ├── transform.py       # sort, uniq, tac, shuf, tr
│   │   ├── field.py           # cut, paste, join, comm
│   │   ├── format.py          # fmt, fold, nl, pr, ptx
│   │   ├── split.py           # split, csplit
│   │   ├── codec.py           # base64, base32, basenc
│   │   └── checksum.py        # cksum, sum, b2sum, md5sum, sha*sum, hash
│   └── system/                # 系统命令
│       ├── __init__.py
│       ├── info.py            # uname, arch, hostname, uptime, ...
│       ├── user.py            # whoami, id, groups, users, who, ...
│       ├── process.py         # kill, nice, nohup, timeout, sleep
│       ├── env.py             # env, printenv, date
│       └── misc.py            # true, false, yes, seq, printf, echo, expr, factor
│
├── registry.py                # 从 catalog 自动推导 + 命令注册表
└── catalog.py                 # 唯一优先级定义源
```

### 5.2 关键重构步骤

#### 步骤 1: 拆分 protocol.py → core/ 包

这是最重要的重构。`protocol.py` 当前混合了 7 类功能：

| 功能域 | 行数 (估) | 目标模块 |
|---|---|---|
| AgentError 异常类 | ~60 | `core/exceptions.py` |
| JSON envelope 工具 | ~40 | `core/envelope.py` |
| 退出码常量 | ~20 | `core/exit_codes.py` |
| 路径工具函数 | ~80 | `core/path_utils.py` |
| 文件系统 stat | ~60 | `core/path_utils.py` |
| Sandbox 边界校验 | ~100 | `core/sandbox.py` |
| 哈希算法 + digest | ~80 | `hashing/` |
| 文本处理工具 | ~150 | `text/` |
| 用户/组/进程工具 | ~100 | `system/` |

**向后兼容策略**: 在 `protocol.py` 保留重导出 import，标记 `DeprecationWarning`，Phase 2 移除。

#### 步骤 2: 统一 registry 和 catalog 数据源

```python
# catalog.py 作为唯一定义源
CATALOG = [...]  # 保持不变

# registry.py 自动推导
def _derive_priority_map() -> dict[str, str]:
    result = {}
    for entry in CATALOG:
        for tool in entry["tools"]:
            result[tool] = entry["priority"]
    return result
```

#### 步骤 3: 命令模块拆包

按功能域拆分子模块，每个子模块 ≤ 200 行：

- `commands/fs/read.py`: ls, stat, cat, head, tail, wc (~200 行)
- `commands/fs/write.py`: cp, mv, rm, mkdir, touch, truncate (~200 行)
- 以此类推

---

## 六、风险与注意事项 / Risks & Caveats

| 风险 | 缓解措施 |
|---|---|
| 重构导致回归 | 136 个测试 + CI 矩阵 + property-based 测试作为安全网 |
| 模块拆分导致循环导入 | 使用 `TYPE_CHECKING` + 延迟导入，core/ 包零内部依赖 |
| 性能退化 | Phase 2 加入 benchmark CI，重构后对比 |
| 文档漂移 | 严格遵循事实传播矩阵 + 双语镜像规则 |
| Windows CI 不稳定 | 继续 skip symlink 测试，不依赖 Windows 特定行为 |
| 过度工程化 | 每个 Phase 有明确 DoD，避免无休止重构 |

---

## 七、建议立即执行的任务 / Recommended Immediate Actions

按优先级排序：

1. ⚡ **消除 cli.py 冗余** (改动小，收益明确)
2. ⚡ **CI 添加 mypy + ruff** (零代码改动，质量立竿见影)
3. ⚡ **触发 CI GNU 对照验证** (push 即可，验证关键假设)
4. 🔧 **拆分 protocol.py** (重构量大但收益最高)
5. 🔧 **统一 registry/catalog 数据源** (消除数据冗余)
6. 📋 **添加 pytest-cov 到 CI** (量化测试覆盖)
7. 📋 **拆分大命令模块** (渐进式，可按模块逐步完成)

---

## 附录 A: 文件行数估算 / File Size Estimates

| 文件 | 估计行数 | 状态 |
|---|---|---|
| `protocol.py` | ~600+ | ⚠️ 过大，需拆分 |
| `fs_commands.py` | ~800+ | ⚠️ 过大，需拆分 |
| `text_commands.py` | ~700+ | ⚠️ 过大，需拆分 |
| `system_commands.py` | ~600+ | ⚠️ 过大，需拆分 |
| `parser.py` | ~400+ | ⚠️ 偏大，可优化 |
| `registry.py` | ~80 | ✅ 适中 |
| `catalog.py` | ~120 | ✅ 适中 |
| `cli.py` | ~25 | 🔴 冗余，应删除 |

## 附录 B: 测试覆盖矩阵 / Test Coverage Matrix

| 维度 | 当前状态 | 目标 (v1.0) |
|---|---|---|
| 单元测试 | ✅ 已有 | 覆盖率 > 90% |
| CLI 黑盒测试 | ✅ 已有 | 每个命令 ≥ 3 个场景 |
| Property-based | ✅ 25 tests | ≥ 50 tests |
| GNU differential | ⚠️ 仅本地 Windows 5/56 | CI Ubuntu ≥ 50/56 |
| Sandbox escape | ✅ 37 tests | ≥ 50 tests |
| 性能基准 | ❌ 无 | ≥ 20 benchmarks |
| 类型检查 | ❌ 无 | mypy strict 零错误 |
| Linting | ❌ 无 | ruff 零警告 |

---

> **文档状态**: 本文档为开发路线图，不作为当前状态权威来源。
> 当前状态见 `docs/status/CURRENT_STATUS.md`。
