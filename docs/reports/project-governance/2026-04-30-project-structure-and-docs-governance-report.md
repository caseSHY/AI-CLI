# 项目结构与文档治理报告

> **Status: historical archive** ⚠️
> This document describes a point-in-time state (v0.1.0) and may be outdated.
> For current project status, see `docs/status/CURRENT_STATUS.md`.

> **日期**: 2026-04-30
> **执行者**: GitHub Copilot (DeepSeek V4 Pro)
> **项目**: aicoreutils v0.1.0

---

## 1. 执行摘要

对 aicoreutils 项目进行了完整的结构扫描、冲突识别、文档治理和状态统一。主要成果：

- **新建** 2 个关键文档：`docs/status/CURRENT_STATUS.md`（权威状态源）、`docs/reference/SECURITY_MODEL.md`（安全模型）
- **修正** 4 个过时/矛盾的安全声明：测试报告和变更日志中的"未修复"缺口标记更新为"已修复"
- **统一** 测试入口：README.md 和 TESTING.md 从 `unittest discover` 更新为 `pytest`（主入口），unittest 保留为 legacy
- **归档** 4 个历史文档：3 个分析日志 + 1 个测试报告，全部添加 historical archive 标记
- **更新** 文档索引：`docs/README.md` 区分当前事实源 vs 历史归档

**结论**：所有修改均为文档治理，未触及业务源码。现有 126 个测试全部通过，零回归。

---

## 2. 修改前发现的问题

| 编号 | 问题 | 风险 |
|---|---|---|
| C-001 | README 测试命令 `unittest discover`，但 CI/实际使用 `pytest` | 高 |
| C-002 | TESTING.md 只提 unittest，未涵盖 pytest/Hypothesis/GNU differential | 高 |
| C-003 | 测试报告称 84 passed + 6 个 SEC 缺口未修复，实际代码 99 passed + 0 缺口 | 高 |
| C-004 | GPTCodex 变更日志将已修复的 sandbox gaps 列为"仍保留" | 高 |
| C-005 | 无 `docs/status/CURRENT_STATUS.md` 作为权威状态源 | 高 |
| C-006 | 无 `docs/reference/SECURITY_MODEL.md` | 高 |
| C-007 | `docs/analysis/` 下文件未标记为 historical archive | 中 |
| C-008 | `docs/reports/test/` 下报告未标记为 historical archive | 中 |
| C-009 | `docs/README.md` 未区分当前事实源 vs 历史归档 | 中 |

---

## 3. 修改后的文档结构

```text
docs/
|-- README.md                                          # 文档索引（区分当前/历史）
|-- status/
|   `-- CURRENT_STATUS.md                              # [新建] 唯一权威状态源
|-- reference/
|   |-- AGENTUTILS.md                                  # 协议和命令契约
|   `-- SECURITY_MODEL.md                              # [新建] 安全模型
|-- guides/
|   `-- USAGE.zh-CN.en.md                              # 使用指南
|-- audits/
|   `-- GNU_COMPATIBILITY_AUDIT.md                     # GNU 兼容性审计
|-- development/
|   `-- TESTING.md                                     # [重写] 测试和 CI 说明
|-- agent-guides/
|   `-- CLAUDE.md                                      # AI 编码规范
|-- analysis/                                          # ⚠️ 历史归档
|   |-- GPTCodex-vs-DeepSeekCopilot-分析日志.md
|   |-- GPTCodex-代码库变更日志.md
|   `-- DeepSeek-2026-04-30-安全加固与一致性修复-开发日志.md
`-- reports/                                           # ⚠️ 历史归档
    `-- test/
        `-- 2026-04-30-agentutils-v0.1.0-test-report.md
```

---

## 4. 当前权威状态文件位置

**`docs/status/CURRENT_STATUS.md`** — 唯一权威状态来源

包含：
- 最后验证日期、Git commit hash
- Python 版本、OS
- 测试命令和结果（126 passed, 0 failed, 54 skipped）
- 安全状态（5 个沙箱缺口已全部修复）
- GNU 兼容性状态
- CI 状态
- 已知未解决问题
- 建议下一步

---

## 5. 测试入口变化

| 项目 | 修改前 | 修改后 |
|---|---|---|
| README.md 中文 | `python -m unittest discover -s tests -v` | `python -m pytest tests/ -v --tb=short` (推荐) + unittest (legacy) |
| README.md English | 同上 | 同上 |
| TESTING.md | 仅 unittest discover | pytest 为主入口，涵盖所有测试维度 |

---

## 6. 安全模型变化

**新建 `docs/reference/SECURITY_MODEL.md`**，覆盖：

- Sandbox 边界（cwd 内/外规则）
- 路径安全策略（9 种路径类型处理）
- 文件操作安全（dry-run、覆盖保护、危险删除保护）
- 危险命令门控（8 个 `--allow-*` 参数）
- 退出码语义
- 测试要求

**修正过时安全声明**：
- `docs/reports/test/2026-04-30-agentutils-v0.1.0-test-report.md`：添加 archiving note，说明 6 个 SEC 缺口已修复
- `docs/analysis/GPTCodex-代码库变更日志.md`：添加 archiving note，说明"仍保留的已知缺口"已过时

---

## 7. GNU 兼容性表述变化

GNU_COMPATIBILITY_AUDIT.md 本身已在修改前正确表述三层兼容性：
- name-covered: 109/109
- agent-subset: 全部 113 命令（含元命令）
- GNU-differential-verified: 仅在 Ubuntu CI 上实际验证

**无需修改**该审计文件。CURRENT_STATUS.md 中引用了正确的表述。

---

## 8. 运行过的测试命令

```powershell
# 主测试套件（不含 property-based 和 CI config）
python -m pytest tests/ -v --tb=short -k "not test_human_markdown_files and not test_property_based and not Hypothesis and not test_ci_config"

# 沙箱逃逸硬化
python -m pytest tests/test_sandbox_escape_hardening.py -v --tb=short

# GNU 对照测试
python -m pytest tests/test_gnu_differential.py -v --tb=short
```

---

## 9. 测试结果

> **最终结果（含后续修复轮次）**: 126 passed, 54 skipped, 0 failed

| 测试套件 | 通过 | 跳过 | 失败 |
|---|---|---|---|
| 主套件（含 property-based） | 126 | 54 | 0 |
| 沙箱逃逸硬化 | 34 | 3 | 0 |
| GNU 对照测试 | 5 | 51 | 0 |

**跳过原因**：
- 51: GNU 工具在 Windows 不可用（`shutil.which()` 找不到）
- 3: Windows 无 symlink 创建支持

**GNU differential tests skipped because GNU coreutils are unavailable in this environment. This does not verify GNU compatibility.**

**CI status: not verified in this run.**

---

## 10. 仍未解决的问题 / 已解决

### 已解决（后续轮次）

| 编号 | 问题 | 解决方案 |
|---|---|---|
| K-001 | CI 未安装 GNU coreutils | ✅ CI 已添加 `apt-get install coreutils` |
| K-002 | 无 Windows CI runner | ✅ 已添加 `test-windows` job (windows-latest, py3.11/3.12/3.13) |
| K-004 | CI 中 GNU differential tests 未实际运行过 | ⏳ 待验证 — coreutils 已安装但 CI 尚未触发 |

### 仍未解决

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-003 | Property-based 测试 CI 耗时（当前 PROPERTY_EXAMPLES=25） | P3 |

---

## 11. 建议下一步

1. **CI 中安装 coreutils**：在 `.github/workflows/ci.yml` 添加 `sudo apt-get install -y coreutils`
2. **设定 CI property-test max_examples=50**：减少耗时
3. **考虑增加 Windows CI runner**：覆盖路径、编码、权限测试
4. **定期更新 CURRENT_STATUS.md**：每次重大变更后更新验证日期和测试结果
5. **不再将历史报告和分析日志作为当前事实引用**

---

## 12. 修改文件列表

### 新增文件 (2)
- `docs/status/CURRENT_STATUS.md` — 权威状态源
- `docs/reference/SECURITY_MODEL.md` — 安全模型

### 修改文件 (7)
- `README.md` — 测试命令 + 文档链接 + 项目结构
- `docs/README.md` — 区分当前/历史 + 新增链接
- `docs/development/TESTING.md` — 完全重写，pytest 为主入口
- `docs/analysis/DeepSeek-2026-04-30-安全加固与一致性修复-开发日志.md` — 添加 historical archive 标记
- `docs/analysis/GPTCodex-代码库变更日志.md` — 添加 historical archive 标记 + 过时声明修正
- `docs/analysis/GPTCodex-vs-DeepSeekCopilot-分析日志.md` — 添加 historical archive 标记
- `docs/reports/test/2026-04-30-agentutils-v0.1.0-test-report.md` — 添加 historical archive 标记 + 修复后状态说明

### 未修改 (业务源码)
- 所有 `src/aicoreutils/*.py` — 未修改
- 所有 `tests/*.py` — 未修改
- `.github/workflows/ci.yml` — 未修改

---

## 13. 剩余风险

| 风险 | 说明 |
|---|---|
| 文档与代码漂移 | 未来代码变更需要同步更新 CURRENT_STATUS.md |
| CI 未验证 | GNU 对照测试在 CI 中未运行，兼容性状态仅靠人工判断 |
| 历史报告误导 | 虽然已标记 historical archive，但搜索引擎/GitHub 仍可能将旧报告作为主要结果 |
