# 软件开发与审计计划 / Development and Audit Plan

## 中文说明

本计划用于把 AICoreUtils 从快速扩展阶段切换到稳定化治理阶段。计划强调可执行任务、验收标准和审计证据，不以新增命令数量作为主要目标。

动态事实（版本号、测试通过数、CI 状态、命令数、覆盖率）以 `docs/status/CURRENT_STATUS.md` 为准。本文件只定义工作安排和验收门槛。

### 目标

1. 稳定现有 Agent 工具面，减少命令、文档、schema、MCP 描述之间的事实漂移。
2. 提高 MCP 和文件系统操作的默认安全性，优先支持最小权限部署。
3. 建立可重复的开发、审计、发布流程，使每次变更都有明确证据链。
4. 将宽命令面拆成更易维护的数据驱动结构，降低后续修改风险。

### 非目标

- 不追求成为 GNU Coreutils 的完整替代品。
- 不在稳定化阶段批量新增命令。
- 不把历史报告或分析日志作为当前事实来源。
- 不把本地通过、配置完成、CI 通过混写为同一状态。

### 执行原则

| 原则 | 要求 |
|---|---|
| 范围冻结 | `1.1.x` 期间默认只接受安全修复、测试、文档一致性、架构拆分和权限治理。 |
| 单一事实源 | 版本、测试数量、CI 状态、覆盖率等动态事实只从脚本或 `CURRENT_STATUS.md` 传播。 |
| 安全默认 | MCP 集成默认推荐 `--read-only` 或 allow-list profile；危险命令必须显式授权。 |
| 证据优先 | 每个任务必须给出本地命令、CI 链接或代码 diff 作为审计证据。 |
| 兼容分层 | JSON envelope 和 MCP tool schema 强稳定；CLI 参数按稳定等级分层治理。 |

### 工作流总览

| 阶段 | 名称 | 主要产物 | 完成标准 |
|---|---|---|---|
| P0 | 基线冻结 | 基线审计记录、冻结规则 | 当前测试、lint、typecheck、schema 输出均有记录。 |
| P1 | 安全治理 | MCP profile、风险分级、生产配置示例 | 默认推荐路径为最小权限，危险工具有机器可读风险标注。 |
| P2 | 文档治理 | 自动生成状态、文档一致性检查 | 动态数字不再手写，文档治理测试覆盖新增规则。 |
| P3 | 测试治理 | 命令级测试矩阵、覆盖率口径说明 | mutating 命令和 process-exec 命令均有专项测试矩阵。 |
| P4 | 架构治理 | command spec 原型、parser/schema 生成路径 | 新命令或参数定义不再需要多处手工同步。 |
| P5 | 发布治理 | 发布清单、回滚流程、安全公告流程 | tag 前置检查、发布证据和迁移说明固定化。 |
| P6 | 外部审计 | 已取消 | 不再作为当前稳定化或发布门禁的一部分。 |

### P0：基线冻结

**任务**

1. 创建稳定化分支或 milestone，命名建议：`stabilization-1.1.x`。
2. 记录当前源码基线：commit、tag、Python matrix、CI workflow、PyPI 版本。
3. 执行完整本地验证。
4. 生成一份基线审计记录，存入 `docs/reports/project-governance/`。

**命令**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ tests -v --tb=short
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m mypy src/aicoreutils/ --strict
python -m aicoreutils schema --pretty
python scripts/generate_status.py
```

**验收标准**

- 所有命令输出已归档或在 PR 描述中引用。
- `CURRENT_STATUS.md` 与源码版本、README pin、server metadata 一致。
- 新增功能请求必须先说明是否违反范围冻结。

### P1：安全治理

**任务**

1. 为所有 MCP 工具建立风险等级：`read-only`、`write`、`destructive`、`process-exec`、`platform-sensitive`。
2. 在 tool schema 或生成层输出风险 annotation。
3. 增加内置 profile：
   - `readonly`：只暴露只读命令。
   - `workspace-write`：允许 cwd 内写入，但拒绝 destructive 和 process-exec。
   - `explicit-danger`：仅在用户明确配置时允许危险命令。
4. 将生产文档中的主推荐改为 allow-list/profile 启动。
5. 增加 MCP 安全回归测试，覆盖 deny 优先级、allow-list 优先级、read-only profile 和危险命令默认拒绝。

**命令**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_mcp_security.py tests/test_mcp_server_unit.py -v --tb=short
python -m pytest tests/test_sandbox_escape_hardening.py -v --tb=short
```

**验收标准**

- `tools/list` 可以让调用方识别工具风险。
- 没有 profile 时的文档示例不得暗示生产环境可无隔离开放全工具。
- mutating、destructive、process-exec 三类工具都有至少一条拒绝路径测试。

### P2：文档治理

**任务**

1. 扩展 `scripts/generate_status.py`，集中生成版本、测试命令、CI matrix、覆盖率门槛和命令数。
2. 将 `CURRENT_STATUS.md` 中动态字段标记为生成区块。
3. 增加 CI 检查：运行生成脚本后 git diff 必须为空。
4. 清理 README 中容易漂移的静态状态数字，只保留安装、定位和稳定性说明。
5. 对所有当前文档执行 stale fact 搜索。

**命令**

```powershell
$env:PYTHONPATH = "src"
python scripts/generate_status.py --write
git diff -- docs/status/CURRENT_STATUS.md
python -m pytest tests/test_docs_bilingual.py tests/test_docs_governance.py tests/test_version_consistency.py -v --tb=short
```

**验收标准**

- 动态事实从脚本生成或由测试阻断漂移。
- 中文段和 English 段对同一事实没有冲突。
- 历史报告继续保留，但文档索引明确标记为历史归档。

### P3：测试治理

**任务**

1. 建立命令级测试矩阵：每个命令至少标注 happy path、error path、JSON contract、platform behavior。
2. 为所有 mutating 命令补齐五类测试：路径越界、dry-run 零副作用、覆盖保护、危险目标、symlink/junction。
3. 为 process-exec 命令补齐 timeout、输出上限、dry-run/allow gate 测试。
4. 明确覆盖率口径：黑盒 subprocess 行为测试与 in-process coverage 分开报告。
5. 逐步提高覆盖率门槛，先保证稳定超过当前门槛，再评估下一阶段目标。

**命令**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ tests/test_version_consistency.py -v --tb=short --cov=src/aicoreutils --cov-report=term-missing
python -m pytest tests/test_property_based_cli.py -v --tb=short
python -m pytest tests/test_gnu_differential.py -v --tb=short
```

**验收标准**

- 每个跳过项都有平台或依赖原因。
- GNU differential 在具备 GNU 工具的平台实际运行，不把 skip 计为兼容性通过。
- 覆盖率报告中的低覆盖模块有对应补测 issue 或明确的口径说明。

### P4：架构治理

**任务**

1. 提取 command spec 数据结构，字段至少包含：命令名、分类、稳定等级、风险等级、参数定义、handler、MCP 描述、GNU 兼容说明。
2. 从 command spec 生成 argparse parser、MCP tool schema、tool-list 和命令清单。
3. 先选择 3 个低风险命令试点迁移，例如 `pwd`、`basename`、`seq`。
4. 在试点通过后，再分批迁移 text、fs、system 命令。
5. 保留兼容测试，防止迁移改变 JSON envelope。

**命令**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_cli_black_box.py tests/test_golden_outputs.py tests/test_mcp_server.py -v --tb=short
python -m aicoreutils schema --pretty
python -m aicoreutils tool-list --format openai
```

**验收标准**

- 新增参数只需要改一处 spec。
- schema、catalog、README、MCP 描述不再依赖手工重复维护。
- 试点命令 golden 输出不发生非预期变化。

### P5：发布治理

**任务**

1. 制定 release checklist，放入 `CONTRIBUTING.md` 或独立 `RELEASE.md`。
2. tag 前必须完成本地完整验证和远程 CI 验证。
3. 安全修复单独标注影响范围、是否需要升级、是否存在绕过风险。
4. 建立回滚策略：PyPI yanked 条件、GitHub Release 注记、README pin 回退规则。
5. 考虑启用包发布 provenance、tag 签名或 trusted publishing 证据。

**命令**

```powershell
python scripts/bump_version.py --help
python scripts/generate_status.py --write
python -m build
python -m twine check dist/*
```

**验收标准**

- 每个 release 都能从 tag 追溯到 CI、changelog、status 和 PyPI artifact。
- patch/minor/major 的兼容含义在文档中明确。
- 发布失败时有可执行回滚路径。

### P6：外部审计（已取消）

**任务**

外部审计已于 2026-05-06 取消，不再作为当前稳定化或发布门禁的一部分。
原审计准备材料保留为历史参考，不代表未完成开发项。

**验收标准**

- 当前发布门禁以 `scripts/release_gate.py --full` 和 CI governance gate 为准。
- 如未来恢复外部审计，需要重新建立审计范围、owner 和风险接受规则。

### 每次 PR 的最低检查清单

- [ ] 变更是否违反 `1.1.x` 范围冻结。
- [ ] 是否修改了 JSON envelope、MCP schema 或 CLI 参数稳定性。
- [ ] 是否影响 mutating、destructive 或 process-exec 命令。
- [ ] 是否新增或修改了动态事实。
- [ ] 是否同步了中文和 English 文档。
- [ ] 是否运行了相关测试并记录命令。
- [ ] 是否需要更新 `CURRENT_STATUS.md`、`SECURITY_MODEL.md`、`GNU_COMPATIBILITY_AUDIT.md` 或 release notes。

### 风险登记规则

| 优先级 | 含义 | 处理要求 |
|---|---|---|
| P0 | 可导致越权写入、删除、命令执行或发布错误包 | 立即阻断发布，修复后补回归测试。 |
| P1 | 可导致 Agent 错误决策、schema 破坏、文档严重误导 | 当前 milestone 内修复。 |
| P2 | 可维护性、覆盖率、平台差异或文档漂移风险 | 排入稳定化计划并指定 owner。 |
| P3 | 体验、示例、措辞或低风险兼容缺口 | 进入 backlog。 |

### 推荐执行顺序

1. P0 基线冻结。
2. P1 MCP 风险分级和 profile。
3. P2 状态文档自动生成。
4. P3 命令级测试矩阵。
5. P4 command spec 试点。
6. P5 发布清单。
7. P6 外部审计已取消；不作为当前发布门禁。

## English

This plan moves AICoreUtils from rapid expansion to stabilization governance. It focuses on executable tasks, acceptance criteria, and audit evidence instead of increasing command count.

Dynamic facts such as version, test counts, CI status, command count, and coverage must come from `docs/status/CURRENT_STATUS.md`. This document defines work plans and acceptance gates only.

### Goals

1. Stabilize the existing agent tool surface and reduce drift across commands, docs, schemas, and MCP descriptions.
2. Improve default safety for MCP and filesystem operations with least-privilege deployment as the primary path.
3. Establish repeatable development, audit, and release workflows with clear evidence for each change.
4. Move the broad command surface toward a maintainable data-driven architecture.

### Non-Goals

- Do not claim to be a complete GNU Coreutils replacement.
- Do not add large batches of commands during the stabilization phase.
- Do not treat historical reports or analysis logs as current facts.
- Do not mix local pass, configured state, and CI pass as one verification level.

### Execution Principles

| Principle | Requirement |
|---|---|
| Scope freeze | During `1.1.x`, accept security fixes, tests, docs consistency, architecture splitting, and permission governance by default. |
| Single fact source | Version, test counts, CI status, coverage, and similar dynamic facts must flow from scripts or `CURRENT_STATUS.md`. |
| Secure by default | MCP integration should recommend `--read-only` or allow-list profiles first; dangerous commands require explicit authorization. |
| Evidence first | Every task must provide local command output, CI links, or code diffs as audit evidence. |
| Layered compatibility | JSON envelope and MCP tool schema are strongly stable; CLI flags are governed by per-command stability levels. |

### Workflow Overview

| Phase | Name | Main Deliverable | Completion Gate |
|---|---|---|---|
| P0 | Baseline freeze | Baseline audit record, freeze rules | Current tests, lint, typecheck, and schema output are recorded. |
| P1 | Security governance | MCP profiles, risk levels, production examples | Least privilege is the default recommendation and risky tools have machine-readable annotations. |
| P2 | Documentation governance | Generated status, consistency checks | Dynamic numbers are no longer hand-maintained and docs governance tests cover the rules. |
| P3 | Test governance | Command test matrix, coverage policy | Mutating and process-exec commands have dedicated test matrices. |
| P4 | Architecture governance | Command spec prototype, generated parser/schema path | New commands or flags no longer require repeated manual updates. |
| P5 | Release governance | Release checklist, rollback flow, security advisory flow | Pre-tag checks, release evidence, and migration notes are standardized. |
| P6 | External audit | Canceled | No longer part of the current stabilization or release gate. |

### P0: Baseline Freeze

**Tasks**

1. Create a stabilization branch or milestone, suggested name: `stabilization-1.1.x`.
2. Record the source baseline: commit, tag, Python matrix, CI workflow, and PyPI version.
3. Run full local verification.
4. Add a baseline audit record under `docs/reports/project-governance/`.

**Commands**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ tests -v --tb=short
python -m ruff check src/ tests/
python -m ruff format --check src/ tests/
python -m mypy src/aicoreutils/ --strict
python -m aicoreutils schema --pretty
python scripts/generate_status.py
```

**Acceptance Criteria**

- Command output is archived or referenced in the PR description.
- `CURRENT_STATUS.md` matches the source version, README pin, and server metadata.
- New feature requests explain whether they violate the scope freeze.

### P1: Security Governance

**Tasks**

1. Define risk levels for all MCP tools: `read-only`, `write`, `destructive`, `process-exec`, and `platform-sensitive`.
2. Emit risk annotations from the tool schema or generator layer.
3. Add built-in profiles:
   - `readonly`: expose read-only commands only.
   - `workspace-write`: allow cwd-local writes but reject destructive and process-exec tools.
   - `explicit-danger`: allow dangerous commands only when explicitly configured.
4. Make production docs recommend allow-list/profile startup first.
5. Add MCP security regression tests for deny priority, allow-list priority, read-only profile, and dangerous command default denial.

**Commands**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_mcp_security.py tests/test_mcp_server_unit.py -v --tb=short
python -m pytest tests/test_sandbox_escape_hardening.py -v --tb=short
```

**Acceptance Criteria**

- `tools/list` lets callers identify tool risk.
- Production examples do not imply that all tools should be exposed without isolation.
- Mutating, destructive, and process-exec tools each have at least one denied-path test.

### P2: Documentation Governance

**Tasks**

1. Extend `scripts/generate_status.py` to centralize version, test commands, CI matrix, coverage threshold, and command count.
2. Mark generated blocks inside `CURRENT_STATUS.md`.
3. Add a CI check that running the generator leaves git diff empty.
4. Remove static state numbers from README where they can drift; keep installation, positioning, and stability guidance.
5. Search all current docs for stale facts.

**Commands**

```powershell
$env:PYTHONPATH = "src"
python scripts/generate_status.py --write
git diff -- docs/status/CURRENT_STATUS.md
python -m pytest tests/test_docs_bilingual.py tests/test_docs_governance.py tests/test_version_consistency.py -v --tb=short
```

**Acceptance Criteria**

- Dynamic facts are generated by script or blocked by tests when stale.
- Chinese and English sections do not conflict on the same fact.
- Historical reports remain available but are clearly marked as archives in the docs index.

### P3: Test Governance

**Tasks**

1. Create a command-level test matrix covering happy path, error path, JSON contract, and platform behavior for each command.
2. Complete five safety tests for every mutating command: out-of-bounds path, dry-run zero side effect, overwrite protection, dangerous target, and symlink/junction behavior.
3. Add timeout, output limit, dry-run, and allow-gate tests for process-exec commands.
4. Clarify coverage policy: black-box subprocess behavior tests and in-process coverage are reported separately.
5. Raise the coverage gate gradually only after the suite stays reliably above the current threshold.

**Commands**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ tests/test_version_consistency.py -v --tb=short --cov=src/aicoreutils --cov-report=term-missing
python -m pytest tests/test_property_based_cli.py -v --tb=short
python -m pytest tests/test_gnu_differential.py -v --tb=short
```

**Acceptance Criteria**

- Every skipped test has a platform or dependency reason.
- GNU differential tests actually run on platforms with GNU tools; skipped tests are not counted as compatibility proof.
- Low-coverage modules in the report have matching test issues or a documented coverage policy reason.

### P4: Architecture Governance

**Tasks**

1. Extract a command spec data structure with at least: command name, category, stability level, risk level, argument definition, handler, MCP description, and GNU compatibility note.
2. Generate argparse parser, MCP tool schema, tool-list, and command inventory from the command spec.
3. Pilot the migration with three low-risk commands, for example `pwd`, `basename`, and `seq`.
4. After the pilot passes, migrate text, fs, and system commands in batches.
5. Keep compatibility tests in place to prevent JSON envelope changes during migration.

**Commands**

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_cli_black_box.py tests/test_golden_outputs.py tests/test_mcp_server.py -v --tb=short
python -m aicoreutils schema --pretty
python -m aicoreutils tool-list --format openai
```

**Acceptance Criteria**

- Adding a flag requires changing one spec location.
- Schema, catalog, README, and MCP descriptions no longer depend on repeated manual updates.
- Pilot commands keep their golden outputs unless a change is intentional and documented.

### P5: Release Governance

**Tasks**

1. Add a release checklist to `CONTRIBUTING.md` or a dedicated `RELEASE.md`.
2. Require full local verification and remote CI verification before tagging.
3. For security fixes, document impact scope, upgrade requirement, and bypass risk.
4. Define rollback policy: PyPI yanking criteria, GitHub Release notes, and README pin rollback.
5. Consider package provenance, signed tags, or trusted publishing evidence.

**Commands**

```powershell
python scripts/bump_version.py --help
python scripts/generate_status.py --write
python -m build
python -m twine check dist/*
```

**Acceptance Criteria**

- Every release can be traced from tag to CI, changelog, status, and PyPI artifact.
- Patch, minor, and major compatibility meanings are documented.
- Failed releases have an executable rollback path.

### P6: External Audit (Canceled)

**Tasks**

External audit was canceled on 2026-05-06 and is no longer part of the current stabilization or release gate.
The original readiness material is retained as historical reference and does not represent unfinished development work.

**Acceptance Criteria**

- The current release gate is `scripts/release_gate.py --full` plus the CI governance gate.
- If external audit is restored later, define a new audit scope, owner, and risk acceptance rule.

### Minimum PR Checklist

- [ ] Does the change violate the `1.1.x` scope freeze?
- [ ] Does it change JSON envelope, MCP schema, or CLI flag stability?
- [ ] Does it affect mutating, destructive, or process-exec commands?
- [ ] Does it add or modify dynamic facts?
- [ ] Are Chinese and English docs synchronized?
- [ ] Were relevant tests run and recorded?
- [ ] Does it require updates to `CURRENT_STATUS.md`, `SECURITY_MODEL.md`, `GNU_COMPATIBILITY_AUDIT.md`, or release notes?

### Risk Register Rules

| Priority | Meaning | Handling Requirement |
|---|---|---|
| P0 | Can cause unauthorized write, delete, command execution, or wrong package release | Block release immediately and add regression tests after fixing. |
| P1 | Can cause agent misbehavior, schema breakage, or serious documentation misdirection | Fix within the current milestone. |
| P2 | Maintainability, coverage, platform difference, or documentation drift risk | Add to the stabilization plan and assign an owner. |
| P3 | Experience, examples, wording, or low-risk compatibility gap | Put in backlog. |

### Recommended Order

1. P0 baseline freeze.
2. P1 MCP risk levels and profiles.
3. P2 generated status docs.
4. P3 command-level test matrix.
5. P4 command spec pilot.
6. P5 release checklist.
7. P6 external audit is canceled; it is not a current release gate.
