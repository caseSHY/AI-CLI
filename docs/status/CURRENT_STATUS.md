# 当前项目状态 / Current Project Status

> **这是项目当前状态的唯一权威来源。**
> 历史报告见 `docs/reports/`，分析日志见 `docs/analysis/`。
>
> **This is the single authoritative source for current project status.**
> Historical reports are in `docs/reports/`, analysis logs in `docs/analysis/`.

---

| 属性 / Property | 值 / Value |
|---|---|
| **最后验证日期 / Last verified** | 2026-04-30 |
| **Git commit hash** | `11f8cd139d0268a82efcaa505b978e49218b2e01` |
| **Python 版本 / Python version** | 3.14.4 (开发), CI: 3.11/3.12/3.13 |
| **操作系统 / OS** | Windows 11 (开发), Ubuntu latest (CI) |
| **项目版本 / Project version** | 0.1.0 |

---

## 测试 / Tests

| 指标 / Metric | 数值 / Value |
|---|---|
| **推荐测试命令 / Recommended command** | `python -m pytest tests/ -v --tb=short` |
| **Legacy 入口 / Legacy entry** | `python -m unittest discover -s tests -v` (部分运行器) |
| **通过 / Passed** | 99 |
| **跳过 / Skipped** | 54 |
| **失败 / Failed** | 0 |
| **跳过原因 / Skip reasons** | 51: GNU 工具在 Windows 不可用; 3: Windows 无 symlink 支持 |
| **Property-based 测试** | `python -m pytest tests/test_property_based_cli.py -v` (25 测试, max_examples=100) |
| **GNU 对照测试** | `python -m pytest tests/test_gnu_differential.py -v` (56 测试, Windows 上仅 5 可运行) |
| **沙箱逃逸测试** | `python -m pytest tests/test_sandbox_escape_hardening.py -v` (37 测试, 全部通过或 skip) |
| **覆盖率 / Coverage** | `python -m pytest tests/ --cov=src/agentutils` (需要 pytest-cov) |

---

## 安全状态 / Security Status

| 项目 / Item | 状态 / Status |
|---|---|
| **沙箱逃逸漏洞 / Sandbox escape gaps** | ✅ 全部 5 个已知漏洞已于 2026-04-30 修复 |
| **cwd 边界校验** | ✅ 所有写入/删除/截断命令均校验目标路径在 cwd 内 |
| **符号链接逃逸** | ✅ `resolve_path` 解析真实路径后校验; Windows 跳过(symlink 不可用) |
| **dry-run 零副作用** | ✅ 12 个 mutating 命令 dry-run 均通过零副作用验证 |
| **危险命令默认拒绝** | ✅ shred/kill/nice/nohup 需要显式 `--allow-*` 确认 |
| **安全模型文档** | `docs/reference/SECURITY_MODEL.md` |

---

## GNU 兼容性状态 / GNU Differential Status

| 项目 / Item | 状态 / Status |
|---|---|
| **GNU 命令名覆盖** | 109/109 |
| **Agent 子集实现** | 全部 113 命令（含 4 个元命令） |
| **GNU differential verified (Windows)** | 仅 sort (5 tests), 其余 51 因缺少 GNU 工具跳过 |
| **GNU differential verified (CI Ubuntu)** | 未验证 — CI 未安装 coreutils 包 |
| **兼容性表述** | "JSON-first agent-friendly subset inspired by GNU Coreutils" |

---

## CI 状态 / CI Status

| 项目 / Item | 状态 / Status |
|---|---|
| **CI 平台** | GitHub Actions, ubuntu-latest |
| **Python 矩阵** | 3.11, 3.12, 3.13 |
| **CI 测试命令** | `python -m pytest tests/ -v` |
| **GNU coreutils 已安装?** | ❌ 否 — 需添加 `apt-get install coreutils` |
| **Windows CI** | ❌ 无 — 无 Windows runner |
| **CI status: not verified in this run** | — |

---

## 已知未解决问题 / Known Open Issues

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-001 | CI 未安装 GNU coreutils，导致 GNU 对照测试被跳过 | P2 |
| K-002 | 无 Windows CI runner | P3 |
| K-003 | Property-based 测试在 CI 中耗时长（max_examples=100） | P3 |
| K-004 | CI 中的 GNU differential tests 未实际运行过 | P2 |

---

## 建议下一步 / Next Required Actions

1. **CI 中安装 coreutils**: 在 `.github/workflows/ci.yml` 中添加 `sudo apt-get install -y coreutils`
2. **设定 CI property-test max_examples=50**: 减少耗时
3. **考虑增加 Windows CI runner**: 覆盖路径、编码、权限测试
4. **更新 golden files**: 如有行为变更需要重新生成
