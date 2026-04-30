# 当前项目状态 / Current Project Status

## 中文说明

> **这是项目当前状态的唯一权威来源。**
> 历史报告见 `docs/reports/`，分析日志见 `docs/analysis/`。

| 属性 | 值 |
|---|---|
| **最后验证日期** | 2026-05-01 |
| **验证对象** | 本地工作区（基于 `07a289b`，含本轮治理规则变更） |
| **Python 版本** | 3.14.4 (开发), CI: 3.11/3.12/3.13 |
| **操作系统** | Windows 11 (开发), CI: ubuntu-latest + windows-latest |
| **项目版本** | 0.1.0 |

### 测试

| 指标 | 数值 |
|---|---|
| **推荐测试命令** | `python -m pytest tests/ -v --tb=short` |
| **Legacy 入口** | `python -m unittest discover -s tests -v` (部分运行器) |
| **通过** | 132 |
| **跳过** | 54 |
| **失败** | 0 |
| **跳过原因** | 51: GNU 工具在 Windows 不可用（CI Ubuntu 已安装 coreutils，可运行）; 3: Windows 无 symlink 支持 |
| **Property-based 测试** | `python -m pytest tests/test_property_based_cli.py -v` (25 测试, PROPERTY_EXAMPLES=25) |
| **GNU 对照测试** | `python -m pytest tests/test_gnu_differential.py -v` (56 测试, CI Ubuntu 可运行) |
| **沙箱逃逸测试** | `python -m pytest tests/test_sandbox_escape_hardening.py -v` (37 测试, 全部通过或 skip) |
| **文档治理测试** | `python -m pytest tests/test_docs_governance.py -v` (6 测试, 全部通过) |
| **覆盖率** | `python -m pytest tests/ --cov=src/agentutils` (需要 pytest-cov) |

### 安全状态

| 项目 | 状态 |
|---|---|
| **沙箱逃逸漏洞** | ✅ 全部 5 个已知漏洞已于 2026-04-30 修复 |
| **cwd 边界校验** | ✅ 所有写入/删除/截断命令均校验目标路径在 cwd 内 |
| **符号链接逃逸** | ✅ `resolve_path` 解析真实路径后校验; Windows 跳过(symlink 不可用) |
| **dry-run 零副作用** | ✅ 12 个 mutating 命令 dry-run 均通过零副作用验证 |
| **危险命令默认拒绝** | ✅ shred/kill/nice/nohup 需要显式 `--allow-*` 确认 |
| **安全模型文档** | `docs/reference/SECURITY_MODEL.md` |

### GNU 兼容性状态

| 项目 | 状态 |
|---|---|
| **GNU 命令名覆盖** | 109/109 |
| **Agent 子集实现** | 全部 113 命令（含 4 个元命令） |
| **GNU differential verified (Windows)** | 仅 sort (5 tests), 其余 51 因缺少 GNU 工具跳过 |
| **GNU differential verified (CI Ubuntu)** | 待验证 — coreutils 已安装，需 CI 触发 |
| **兼容性表述** | "JSON-first agent-friendly subset inspired by GNU Coreutils" |

### CI 状态

| 项目 | 状态 |
|---|---|
| **CI 平台** | GitHub Actions |
| **Ubuntu runner** | ubuntu-latest, Python 3.11/3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **CI 测试命令** | `python -m pytest tests/ -v` |
| **GNU coreutils** | ✅ Ubuntu job 已安装（`apt-get install coreutils`） |
| **CI status: not verified in this run** | — |

### 已知未解决问题

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-001 | CI 中 GNU 对照测试需要实际触发验证 | P3 |

### 建议下一步

1. **触发 CI 运行**：push 后观察 Ubuntu job 中 GNU 对照测试是否从 skip 变为 pass
2. **观察 Windows CI**：关注路径/编码/sandbox 测试在 Windows runner 上的表现
3. **更新 golden files**: 如有行为变更需要重新生成

---

## English

> **This is the single authoritative source for current project status.**
> Historical reports are in `docs/reports/`, analysis logs in `docs/analysis/`.

| Property | Value |
|---|---|
| **Last verified** | 2026-05-01 |
| **Verified target** | local working tree (based on `07a289b`, including this governance-rule change) |
| **Python version** | 3.14.4 (dev), CI: 3.11/3.12/3.13 |
| **OS** | Windows 11 (dev), CI: ubuntu-latest + windows-latest |
| **Project version** | 0.1.0 |

### Tests

| Metric | Value |
|---|---|
| **Recommended command** | `python -m pytest tests/ -v --tb=short` |
| **Legacy entry** | `python -m unittest discover -s tests -v` (partial runner) |
| **Passed** | 132 |
| **Skipped** | 54 |
| **Failed** | 0 |
| **Skip reasons** | 51: GNU tools unavailable on Windows; 3: Windows no symlink support |
| **Property-based** | `python -m pytest tests/test_property_based_cli.py -v` (25 tests, PROPERTY_EXAMPLES=25) |
| **GNU differential** | `python -m pytest tests/test_gnu_differential.py -v` (56 tests, only 5 runnable on Windows) |
| **Sandbox escape** | `python -m pytest tests/test_sandbox_escape_hardening.py -v` (37 tests, all pass or skip) |
| **Docs governance** | `python -m pytest tests/test_docs_governance.py -v` (6 tests, all pass) |
| **Coverage** | `python -m pytest tests/ --cov=src/agentutils` (requires pytest-cov) |

### Security Status

| Item | Status |
|---|---|
| **Sandbox escape gaps** | ✅ All 5 known gaps fixed 2026-04-30 |
| **cwd boundary checks** | ✅ All write/delete/truncate commands validate paths inside cwd |
| **Symlink escape** | ✅ `resolve_path` resolves then checks; Windows skips (no symlink) |
| **dry-run zero side-effects** | ✅ 12 mutating commands verified |
| **Dangerous command gates** | ✅ shred/kill/nice/nohup require explicit `--allow-*` |
| **Security model doc** | `docs/reference/SECURITY_MODEL.md` |

### GNU Compatibility Status

| Item | Status |
|---|---|
| **GNU command name coverage** | 109/109 |
| **Agent subset implemented** | All 113 commands (incl. 4 meta-commands) |
| **GNU differential verified (Windows)** | sort only (5 tests), 51 skipped (no GNU tools) |
| **GNU differential verified (CI Ubuntu)** | Pending — coreutils installed, needs CI trigger |
| **Compatibility description** | "JSON-first agent-friendly subset inspired by GNU Coreutils" |

### CI Status

| Item | Status |
|---|---|
| **CI platform** | GitHub Actions |
| **Ubuntu runner** | ubuntu-latest, Python 3.11/3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **CI test command** | `python -m pytest tests/ -v` |
| **GNU coreutils** | ✅ Installed in Ubuntu job |
| **CI status: not verified in this run** | — |

### Known Open Issues

| # | Issue | Priority |
|---|---|---|
| K-001 | GNU differential tests need CI trigger to verify | P3 |

### Next Required Actions

1. **Trigger CI**: Push to observe GNU differential tests and Windows runner results
2. **Update golden files**: If behavior changes intentionally
