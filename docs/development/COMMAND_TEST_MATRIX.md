# 命令测试矩阵 / Command Test Matrix

## 中文说明

本文件定义命令级测试治理规则。矩阵的机器检查入口是 `scripts/audit_command_matrix.py`，它从 parser 和 tool schema 中读取命令、风险等级和测试通道，避免手写命令清单漂移。

动态命令数以 `aicoreutils schema` 和 `CURRENT_STATUS.md` 为准。

### 检查命令

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_matrix.py
python scripts/audit_command_matrix.py --format markdown
```

### 风险等级到测试通道

| 风险等级 | 必要测试通道 | 验收重点 |
|---|---|---|
| `read-only` | CLI 黑盒、golden、property-based | JSON envelope、稳定输出、错误路径。 |
| `write` | sandbox/side-effect、sandbox escape、file admin | cwd 边界、dry-run 零副作用、覆盖保护。 |
| `destructive` | sandbox escape、error exit codes | 危险目标拒绝、显式授权、语义退出码。 |
| `process-exec` | execution/page commands、remaining coreutils、MCP security | timeout、输出上限、默认拒绝或 dry-run。 |
| `platform-sensitive` | remaining coreutils、system aliases、GNU differential | skip 原因、平台差异、GNU 对照边界。 |

### PR 规则

修改命令实现、参数、MCP schema 或风险分类时，必须执行：

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_matrix.py
python -m pytest tests/test_project_consistency.py tests/test_mcp_server.py -v --tb=short
```

如果命令属于 `write`、`destructive` 或 `process-exec`，还必须运行对应专项测试：

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_sandbox_escape_hardening.py tests/test_mcp_security.py -v --tb=short
```

### 验收标准

- 所有 parser 注册命令必须属于 read-only 或 effectful 分类。
- 所有命令必须有非 `unknown` 的 `riskLevel`。
- 所有风险等级必须映射到至少一个测试通道。
- 声明的测试通道文件必须存在。
- skip 只能表示平台或依赖不可用，不得作为兼容性通过证据。

---

## English

This document defines command-level test governance. The machine-checkable entry point is `scripts/audit_command_matrix.py`; it reads commands, risk levels, and test lanes from the parser and tool schema to avoid hand-maintained command-list drift.

Dynamic command count comes from `aicoreutils schema` and `CURRENT_STATUS.md`.

### Check Commands

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_matrix.py
python scripts/audit_command_matrix.py --format markdown
```

### Risk Levels To Test Lanes

| Risk Level | Required Test Lanes | Acceptance Focus |
|---|---|---|
| `read-only` | CLI black-box, golden, property-based | JSON envelope, stable output, error paths. |
| `write` | sandbox/side-effect, sandbox escape, file admin | cwd boundary, dry-run zero side effects, overwrite protection. |
| `destructive` | sandbox escape, error exit codes | dangerous target denial, explicit authorization, semantic exit codes. |
| `process-exec` | execution/page commands, remaining coreutils, MCP security | timeout, output bounds, default denial or dry-run. |
| `platform-sensitive` | remaining coreutils, system aliases, GNU differential | skip reasons, platform differences, GNU differential boundaries. |

### PR Rules

When changing command implementation, flags, MCP schema, or risk classification, run:

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_matrix.py
python -m pytest tests/test_project_consistency.py tests/test_mcp_server.py -v --tb=short
```

If the command is `write`, `destructive`, or `process-exec`, also run the focused safety tests:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_sandbox_escape_hardening.py tests/test_mcp_security.py -v --tb=short
```

### Acceptance Criteria

- Every parser-registered command must belong to read-only or effectful classification.
- Every command must have a non-`unknown` `riskLevel`.
- Every risk level must map to at least one test lane.
- Declared test lane files must exist.
- Skips only indicate unavailable platform/dependency conditions; they are not compatibility proof.
