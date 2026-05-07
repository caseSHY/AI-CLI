# External Audit Readiness Report

## 中文说明

本报告原为稳定化治理 P6 的外部审计准备材料。外部审计已于 2026-05-06 取消；本报告仅作为历史参考保留，不再代表未完成开发项或发布阻塞项。

> 重要：本报告是时间点快照，不是当前状态权威来源。当前状态以 `docs/status/CURRENT_STATUS.md` 为准。

### 1. 审计入口

| 领域 | 入口 | 说明 |
|---|---|---|
| 当前状态 | `docs/status/CURRENT_STATUS.md` | 当前事实来源。 |
| 安全模型 | `docs/reference/SECURITY_MODEL.md` | cwd sandbox、危险命令门控、MCP 安全控制。 |
| 生产安全 | `docs/guides/PRODUCTION_SECURITY.md` | MCP 部署和最低权限建议。 |
| GNU 兼容性 | `docs/audits/GNU_COMPATIBILITY_AUDIT.md` | GNU 子集边界和缺口。 |
| 开发审计计划 | `docs/development/DEVELOPMENT_AUDIT_PLAN.md` | P0-P6 工作计划。 |
| 命令测试矩阵 | `docs/development/COMMAND_TEST_MATRIX.md` | 风险等级和测试通道。 |
| 命令规格试点 | `docs/development/COMMAND_SPEC_PILOT.md` | command spec 原型。 |
| 发布治理 | `docs/development/RELEASE_GOVERNANCE.md` | 发布 gate 和回滚策略。 |

### 2. 可执行证据命令

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py
python scripts/audit_command_matrix.py
python scripts/audit_command_specs.py
python scripts/generate_status.py
python -m pytest tests/test_sandbox_escape_hardening.py tests/test_mcp_security.py -v --tb=short
```

完整发布前验证：

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py --full
```

### 3. 已完成治理项

| 编号 | 项目 | 状态 |
|---|---|---|
| P1 | MCP 工具风险 annotation | 已完成：`riskLevel`、`riskCategory`、`requiresExplicitAllow`。 |
| P1 | MCP profile | 已完成：`readonly`、`workspace-write`、`explicit-danger`。 |
| P2 | 动态事实检查 | 已完成：版本、server metadata、README pin、命令数、coverage gate。 |
| P3 | 命令测试矩阵 | 已完成：`scripts/audit_command_matrix.py`。 |
| P4 | Command spec 试点 | 已完成：`pwd`、`basename`、`seq` 三命令原型。 |
| P5 | 发布 gate | 已完成：`scripts/release_gate.py` 和发布治理文档。 |

### 4. 已取消的外部审计范围（历史参考）

1. **MCP 权限模型**：检查 profile 合并顺序、deny 优先级、allow-list 覆盖 read-only 的预期是否清晰。
2. **路径安全**：审查 `resolve_path`、cwd 边界、symlink/junction、UNC/extended path 处理。
3. **高风险命令**：重点审查 `rm`、`shred`、`dd`、`timeout`、`nohup`、`kill`、`chroot`、`runcon`。
4. **文档承诺**：确认 README 和指南没有暗示 GNU 完整兼容或无隔离生产部署。
5. **发布供应链**：审查 GitHub Actions、PyPI trusted publishing、Docker base image、Dependabot。

### 5. 剩余风险

| 编号 | 风险 | 优先级 | 建议 |
|---|---|---|---|
| A-001 | `allow-command` 可覆盖 read-only，这是设计行为，但需要在生产文档中持续强调。 | P1 | 已由生产安全文档和 MCP 安全测试覆盖；发布前继续运行 release gate。 |
| A-002 | command spec 仍是试点，parser/schema 事实仍有多处来源。 | P2 | 完成更多命令迁移后再提升为权威生成源。 |
| A-003 | coverage gate 仍偏低，黑盒测试和 in-process coverage 口径需要持续分离。 | P2 | 按命令矩阵补核心模块单元测试。 |
| A-004 | Windows symlink/junction 验证依赖环境权限。 | P2 | 在具备权限的 Windows runner 或专项环境中补测。 |
| A-005 | 社区外部验证仍少。 | P3 | 外部审计已取消；作为社区反馈和后续 reviewer backlog 保留。 |

### 6. 当前发布通过标准

- 外部审计不再作为当前发布通过条件。
- P0/P1 风险已修复或有明确风险接受记录。
- 高风险命令至少有 denied path、dry-run 或 explicit allow 测试。
- release gate 通过。
- 文档承诺与实际行为一致。
- 如果未来恢复审计并发现安全绕过，必须先修复再发布。

---

## English

This report was originally the P6 external audit readiness material for stabilization governance. External audit was canceled on 2026-05-06; this report is retained as historical reference only and no longer represents unfinished development work or a release blocker.

> Important: this report is a point-in-time snapshot, not the authoritative current status source. Use `docs/status/CURRENT_STATUS.md` for current status.

### 1. Audit Entry Points

| Area | Entry | Notes |
|---|---|---|
| Current status | `docs/status/CURRENT_STATUS.md` | Current factual source. |
| Security model | `docs/reference/SECURITY_MODEL.md` | cwd sandbox, dangerous command gates, MCP security controls. |
| Production safety | `docs/guides/PRODUCTION_SECURITY.md` | MCP deployment and least-privilege guidance. |
| GNU compatibility | `docs/audits/GNU_COMPATIBILITY_AUDIT.md` | GNU subset boundaries and gaps. |
| Development audit plan | `docs/development/DEVELOPMENT_AUDIT_PLAN.md` | P0-P6 work plan. |
| Command test matrix | `docs/development/COMMAND_TEST_MATRIX.md` | Risk levels and test lanes. |
| Command spec pilot | `docs/development/COMMAND_SPEC_PILOT.md` | Command spec prototype. |
| Release governance | `docs/development/RELEASE_GOVERNANCE.md` | Release gate and rollback policy. |

### 2. Executable Evidence Commands

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py
python scripts/audit_command_matrix.py
python scripts/audit_command_specs.py
python scripts/generate_status.py
python -m pytest tests/test_sandbox_escape_hardening.py tests/test_mcp_security.py -v --tb=short
```

Full pre-release verification:

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py --full
```

### 3. Completed Governance Items

| ID | Item | Status |
|---|---|---|
| P1 | MCP tool risk annotations | Complete: `riskLevel`, `riskCategory`, `requiresExplicitAllow`. |
| P1 | MCP profiles | Complete: `readonly`, `workspace-write`, `explicit-danger`. |
| P2 | Dynamic fact checks | Complete: version, server metadata, README pin, command count, coverage gate. |
| P3 | Command test matrix | Complete: `scripts/audit_command_matrix.py`. |
| P4 | Command spec pilot | Complete: three-command prototype for `pwd`, `basename`, and `seq`. |
| P5 | Release gate | Complete: `scripts/release_gate.py` and release governance docs. |

### 4. Canceled External Audit Scope (Historical)

1. **MCP permission model**: review profile merge order, deny priority, and the intended allow-list override of read-only mode.
2. **Path safety**: review `resolve_path`, cwd boundary checks, symlink/junction handling, UNC/extended path handling.
3. **High-risk commands**: focus on `rm`, `shred`, `dd`, `timeout`, `nohup`, `kill`, `chroot`, and `runcon`.
4. **Documentation claims**: confirm README and guides do not imply complete GNU compatibility or unisolated production deployment.
5. **Release supply chain**: review GitHub Actions, PyPI trusted publishing, Docker base image, and Dependabot.

### 5. Remaining Risks

| ID | Risk | Priority | Recommendation |
|---|---|---|---|
| A-001 | `allow-command` can override read-only. This is intentional but must remain prominent in production docs. | P1 | Covered by production safety docs and MCP security tests; keep running the release gate before release. |
| A-002 | Command spec is still a pilot; parser/schema facts still have multiple sources. | P2 | Promote only after more command migrations. |
| A-003 | Coverage gate remains modest, and black-box tests need a separate policy from in-process coverage. | P2 | Add core module unit tests according to the command matrix. |
| A-004 | Windows symlink/junction validation depends on environment privileges. | P2 | Add focused tests in a Windows environment with required privileges. |
| A-005 | External community validation is still limited. | P3 | External audit is canceled; retain as community feedback and future reviewer backlog. |

### 6. Current Release Pass Criteria

- External audit is no longer a current release pass condition.
- P0/P1 risks are fixed or explicitly accepted.
- High-risk commands have denied path, dry-run, or explicit allow tests.
- Release gate passes.
- Documentation claims match actual behavior.
- If an external audit is restored later and finds a security bypass, fix it before release.
