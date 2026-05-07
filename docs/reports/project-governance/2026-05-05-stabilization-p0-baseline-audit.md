# Stabilization P0 Baseline Audit

## 中文说明

本报告是 AICoreUtils 稳定化治理计划的 P0 基线快照。它记录 2026-05-05 本地验证证据，用于后续安全治理、文档治理、测试治理和架构治理的对照。

> 重要：本报告是时间点证据，不是动态状态来源。当前状态以 `docs/status/CURRENT_STATUS.md` 为准。

### 1. 审计范围

| 项目 | 基线 |
|---|---|
| 代码基线 | `51076946340508d4b9292fd0abe8351a3966a007` |
| 短提交 | `5107694` |
| 提交时间 | `2026-05-05T19:48:36+08:00` |
| 提交说明 | `release: bump to 1.1.1 — security fixes, version governance, release automation` |
| 当前版本 | `1.1.1` |
| Python 要求 | `>=3.11` |
| 运行时依赖 | 无 |
| 可选依赖组 | `dev`, `test` |
| 命令面 | `aicoreutils schema` 报告 114 个命令 |
| CI 配置 | Ubuntu/macOS/Windows，Python 3.11/3.12/3.13，coverage gate 45% |

本次验证对象包含源码基线和本地新增的治理计划文档，但不包含本报告文件自身。

### 2. 验证命令与结果

| 检查 | 命令 | 结果 |
|---|---|---|
| 完整测试 | `python -m pytest tests/ tests -q --tb=short` | `425 passed, 60 skipped, 452 subtests passed` |
| Ruff lint | `python -m ruff check src/ tests/` | `All checks passed!` |
| Ruff format | `python -m ruff format --check src/ tests/` | `63 files already formatted` |
| Mypy strict | `python -m mypy src/aicoreutils/ --strict` | `Success: no issues found in 36 source files` |
| Schema | `python -m aicoreutils schema` | 成功，`command_count` 为 114 |

### 3. P0 结论

当前代码基线满足进入稳定化治理阶段的最低条件：

- 测试、lint、format、typecheck 在本地通过。
- JSON envelope、exit code、schema 命令面可由 CLI 直接取证。
- CI workflow 已配置三平台和 Python matrix。
- 项目已有安全模型、GNU 兼容性审计、测试说明和文档治理规则。

P0 不是生产安全背书。它只说明当前基线适合作为后续治理工作的起点。

### 4. 已确认风险

| 编号 | 风险 | 优先级 | 处理意见 |
|---|---|---|---|
| P0-R1 | MCP 默认暴露面过宽时，Agent 可能获得写入、删除或执行能力。 | P1 | 进入 P1：增加工具风险 annotation 和 profile。 |
| P0-R2 | 动态事实分散在 README、CURRENT_STATUS、server metadata、workflow 中，仍有漂移风险。 | P1 | 进入 P2：扩大 `generate_status.py` 和 CI diff 检查。 |
| P0-R3 | 覆盖率门槛为 45%，且核心命令模块的 in-process coverage 仍偏低。 | P2 | 进入 P3：建立命令级测试矩阵并分离黑盒覆盖口径。 |
| P0-R4 | `build_parser` 和命令实现文件较大，继续扩展会提高维护成本。 | P2 | 进入 P4：command spec 试点迁移。 |
| P0-R5 | 项目发布节奏快，社区外部验证不足。 | P2 | 进入 P5/P6：发布清单和外部审计。 |

### 5. 下一步执行入口

下一步按 `docs/development/DEVELOPMENT_AUDIT_PLAN.md` 执行：

1. P1：MCP 风险等级、tool annotation、profile 和生产配置收敛。
2. P2：状态文档自动生成和动态事实治理。
3. P3：命令级测试矩阵和覆盖率口径治理。

### 6. 审计使用规则

- 后续 PR 可引用本报告作为 P0 起点。
- 不得把本报告中的测试数量、CI 状态或覆盖率作为当前事实复用。
- 如果后续源码基线变化，应新增报告，不应覆盖本报告。

---

## English

This report is the P0 baseline snapshot for the AICoreUtils stabilization governance plan. It records local verification evidence from 2026-05-05 and serves as a comparison point for later security, documentation, test, and architecture governance work.

> Important: this report is point-in-time evidence, not a dynamic status source. Use `docs/status/CURRENT_STATUS.md` for current status.

### 1. Audit Scope

| Item | Baseline |
|---|---|
| Code baseline | `51076946340508d4b9292fd0abe8351a3966a007` |
| Short commit | `5107694` |
| Commit time | `2026-05-05T19:48:36+08:00` |
| Commit subject | `release: bump to 1.1.1 — security fixes, version governance, release automation` |
| Current version | `1.1.1` |
| Python requirement | `>=3.11` |
| Runtime dependencies | None |
| Optional dependency groups | `dev`, `test` |
| Command surface | `aicoreutils schema` reports 114 commands |
| CI topology | Ubuntu/macOS/Windows, Python 3.11/3.12/3.13, coverage gate 45% |

This verification target included the source baseline and the local governance plan documentation changes, but not this report file itself.

### 2. Verification Commands and Results

| Check | Command | Result |
|---|---|---|
| Full tests | `python -m pytest tests/ tests -q --tb=short` | `425 passed, 60 skipped, 452 subtests passed` |
| Ruff lint | `python -m ruff check src/ tests/` | `All checks passed!` |
| Ruff format | `python -m ruff format --check src/ tests/` | `63 files already formatted` |
| Mypy strict | `python -m mypy src/aicoreutils/ --strict` | `Success: no issues found in 36 source files` |
| Schema | `python -m aicoreutils schema` | Passed, `command_count` is 114 |

### 3. P0 Conclusion

The current code baseline satisfies the minimum bar for entering stabilization governance:

- Tests, lint, format, and typecheck pass locally.
- JSON envelope, exit codes, and schema command surface are directly inspectable from the CLI.
- CI workflow is configured for three platforms and the Python matrix.
- The project already has a security model, GNU compatibility audit, testing notes, and documentation governance rules.

P0 is not a production safety endorsement. It only establishes a suitable starting point for the next governance phases.

### 4. Confirmed Risks

| ID | Risk | Priority | Handling |
|---|---|---|---|
| P0-R1 | If MCP exposes the full tool surface by default, an agent may gain write, delete, or execution capabilities. | P1 | Move to P1: add tool risk annotations and profiles. |
| P0-R2 | Dynamic facts are still spread across README, CURRENT_STATUS, server metadata, and workflows, so drift remains possible. | P1 | Move to P2: expand `generate_status.py` and CI diff checks. |
| P0-R3 | The coverage gate is 45%, and core command modules still have low in-process coverage. | P2 | Move to P3: create a command test matrix and separate black-box coverage policy. |
| P0-R4 | `build_parser` and command implementation files are large, increasing maintenance cost if the surface keeps growing. | P2 | Move to P4: pilot command spec migration. |
| P0-R5 | Release cadence is fast and external community validation is still limited. | P2 | Move to P5/P6: release checklist and external audit. |

### 5. Next Execution Entry

Continue with `docs/development/DEVELOPMENT_AUDIT_PLAN.md`:

1. P1: MCP risk levels, tool annotations, profiles, and production configuration tightening.
2. P2: generated status docs and dynamic fact governance.
3. P3: command-level test matrix and coverage policy governance.

### 6. Audit Usage Rules

- Later PRs may reference this report as the P0 starting point.
- Do not reuse test counts, CI status, or coverage from this report as current facts.
- If the source baseline changes later, create a new report instead of overwriting this one.
