# 版本与状态治理修复报告

**日期**: 2026-05-05 | **修复后 commit**: `16d46ba` (v1.1.0)

---

## 发现的不一致

| # | 位置 | 问题 | 当前值 | 修正值 |
|---|---|---|---|---|
| 1 | `README.md:262` | 生产 pin 版本过时 | `aicoreutils==1.0.1` | `aicoreutils==1.1.0` |
| 2 | `CURRENT_STATUS.md` CN/EN | commit hash 过时 | `5c8d941` | `16d46ba` |
| 3 | `CURRENT_STATUS.md` CN/EN | 虚假 CI verified 声明 | "已推送并通过 CI 全平台验证 11/11" | "已推送至 GitHub，GitHub Actions CI 运行中" |
| 4 | `CURRENT_STATUS.md` CN line 30 / EN line 112 | 自相矛盾 | "CI 未纳入" / "not yet in CI" | "已在 CI pipeline 中" / "in CI pipeline" |
| 5 | `CURRENT_STATUS.md` CN/EN macOS runner | Python 版本不准确 | 3.12/3.13 | 3.11/3.12/3.13 |
| 6 | `tests/test_version_consistency.py` | 未覆盖 CURRENT_STATUS 和 README | 仅 4 个来源 | 新增 3 个测试，共 7 个来源 |

## 修改的文件

| 文件 | 修改内容 |
|---|---|
| `README.md` | 262 行 pin 版本 `1.0.1` → `1.1.0` |
| `project/docs/status/CURRENT_STATUS.md` | commit hash、CI 状态措辞、版本一致性状态、macOS runner 矩阵 |
| `tests/test_version_consistency.py` | 新增 `test_current_status_version`、`test_readme_pin_version`、`test_current_status_ci_includes_version_consistency` |
| `project/docs/agent-guides/DOC_GOVERNANCE_RULES.md` | 新增版本治理规则（7 条强制规则） |
| `project/docs/reports/version_status_governance_fix.md` | 本文档 |

## 新增的测试

| 测试 | 验证内容 |
|---|---|
| `test_current_status_version` | CURRENT_STATUS.md 中 CN/EN 版本字段与 `__version__` 一致 |
| `test_readme_pin_version` | README 中所有 `aicoreutils==X.Y.Z` 均与当前版本匹配 |
| `test_current_status_ci_includes_version_consistency` | CURRENT_STATUS 不包含 "CI 未纳入"/"not yet in CI" 等过期措辞 |

## 防回归机制

1. **CI 已包含版本一致性测试**：`python -m pytest tests/test_version_consistency.py` 在 CI pipeline 中自动运行
2. **test_readme_pin_version**：README 中任何过期的 `aicoreutils==X.Y.Z` 会被自动检测
3. **test_current_status_ci_includes_version_consistency**：CURRENT_STATUS 中任何 "CI 未纳入" 之类的过期措辞会被自动检测
4. **DOC_GOVERNANCE_RULES.md 新增 7 条版本治理强制规则**：Bump 版本时必须同步 5 个位置，Bump 后必须运行版本一致性测试

## 仍需人工确认的事实

| 事实 | 原因 |
|---|---|
| 远程 CI 的最新通过状态 | v1.1.0 推送后 GitHub Actions 尚未完成运行，CURRENT_STATUS 标注为 "CI 运行中" |
| GNU differential 在 Windows 上的通过数 | choco coreutils 安装需在 CI 中实际验证 |

## 后续建议

1. 每次 bump 版本后运行 `python -m pytest tests/test_version_consistency.py -v` 确认 7 个来源一致
2. 远程 CI 通过后，更新 CURRENT_STATUS 的 commit hash 和 CI 结果
3. 考虑使用 `setuptools_scm` 从 Git tag 自动推导版本，减少手动同步点
