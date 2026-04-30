# 事实传播矩阵 / Fact Propagation Matrix

## 中文说明

本矩阵用于防止“只改了一个文件，其他文档仍保留旧事实”的治理漂移。修改任一事实
后，必须检查对应的同步目标。

| 事实类型 | 权威来源 | 必须同步检查 |
|---|---|---|
| 测试入口 | `docs/status/CURRENT_STATUS.md` | `README.md`, `docs/development/TESTING.md`, `.github/workflows/ci.yml` |
| 测试数量 | 实际 pytest 输出 | `docs/status/CURRENT_STATUS.md`; 历史归档只追加 archive note，不重写快照 |
| CI 拓扑 | `.github/workflows/ci.yml` | `docs/status/CURRENT_STATUS.md`, `docs/development/TESTING.md`, project governance report |
| GNU differential 状态 | `tests/test_gnu_differential.py` + CI 结果 | `docs/status/CURRENT_STATUS.md`, `docs/development/TESTING.md`, `docs/audits/GNU_COMPATIBILITY_AUDIT.md` |
| 安全状态 | `docs/reference/SECURITY_MODEL.md` + sandbox tests | `docs/status/CURRENT_STATUS.md`, security reports, stale archive notes |
| 命令数量 | `python -m agentutils schema` | `README.md`, `docs/status/CURRENT_STATUS.md`, `docs/audits/GNU_COMPATIBILITY_AUDIT.md`, `docs/development/TESTING.md`, `docs/reference/AGENTUTILS.md` |
| 文档目录结构 | `docs/README.md` | `README.md` Project Layout, governance report, agent guidance links |
| Agent/Copilot 规则 | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` | `AGENTS.md`, `docs/README.md`, `docs/agent-guides/` |

### CI 事实传播

修改 `.github/workflows/ci.yml` 后，至少检查：

- `docs/status/CURRENT_STATUS.md` 的 CI 状态和 known issues。
- `docs/development/TESTING.md` 的 CI 章节。
- `docs/reports/project-governance/` 中是否有同名问题被错误标记为 solved。
- `.github/copilot-instructions.md` 和 `.github/instructions/` 是否仍描述正确流程。

### 测试事实传播

修改测试文件或新增测试后，至少检查：

- `docs/status/CURRENT_STATUS.md` 的通过、跳过、失败数量。
- `docs/development/TESTING.md` 的测试分类。
- `README.md` 的测试入口是否仍正确。

### 命令数量事实传播

新增 CLI 命令后必须运行验证并同步以下文件：

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema --pretty   # 确认 command_count
python -m pytest tests/ -v --tb=short  # 确认测试通过数
```

同步目标（中英双语段）：
- `README.md` 发布状态章节
- `docs/status/CURRENT_STATUS.md` GNU 兼容性状态表
- `docs/audits/GNU_COMPATIBILITY_AUDIT.md` 结论摘要
- `docs/development/TESTING.md` 注册表一致性章节

## English

This matrix prevents governance drift where one file is updated while related
documents still contain old facts. After changing any fact, check the
corresponding propagation targets.

| Fact Type | Authority | Required Sync Checks |
|---|---|---|
| Test entry point | `docs/status/CURRENT_STATUS.md` | `README.md`, `docs/development/TESTING.md`, `.github/workflows/ci.yml` |
| Test counts | Actual pytest output | `docs/status/CURRENT_STATUS.md`; only add archive notes to historical snapshots |
| CI topology | `.github/workflows/ci.yml` | `docs/status/CURRENT_STATUS.md`, `docs/development/TESTING.md`, project governance report |
| GNU differential status | `tests/test_gnu_differential.py` + CI result | `docs/status/CURRENT_STATUS.md`, `docs/development/TESTING.md`, `docs/audits/GNU_COMPATIBILITY_AUDIT.md` |
| Security status | `docs/reference/SECURITY_MODEL.md` + sandbox tests | `docs/status/CURRENT_STATUS.md`, security reports, stale archive notes |
| Command count | `python -m agentutils schema` | `README.md`, `docs/status/CURRENT_STATUS.md`, `docs/audits/GNU_COMPATIBILITY_AUDIT.md`, `docs/development/TESTING.md`, `docs/reference/AGENTUTILS.md` |
| Documentation structure | `docs/README.md` | `README.md` Project Layout, governance report, agent guidance links |
| Agent/Copilot rules | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` | `AGENTS.md`, `docs/README.md`, `docs/agent-guides/` |

### CI Fact Propagation

After changing `.github/workflows/ci.yml`, check at least:

- CI status and known issues in `docs/status/CURRENT_STATUS.md`.
- CI section in `docs/development/TESTING.md`.
- Whether a matching issue in `docs/reports/project-governance/` was incorrectly
  marked solved.
- Whether `.github/copilot-instructions.md` and `.github/instructions/` still
  describe the correct workflow.

### Test Fact Propagation

After changing tests or adding tests, check at least:

- Passed, skipped, and failed counts in `docs/status/CURRENT_STATUS.md`.
- Test categories in `docs/development/TESTING.md`.
- Test entry point in `README.md`.

### Command Count Propagation

After adding a new CLI command, run verification and sync these files:

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema --pretty   # verify command_count
python -m pytest tests/ -v --tb=short  # verify test pass count
```

Sync targets (Chinese and English sections):
- `README.md` Release Status section
- `docs/status/CURRENT_STATUS.md` GNU compatibility status table
- `docs/audits/GNU_COMPATIBILITY_AUDIT.md` Summary section
- `docs/development/TESTING.md` Registry/Catalog consistency section
