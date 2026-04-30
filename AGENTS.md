# Agent Instructions

## 中文说明

本文件是仓库级 Agent 入口规则。修改文档、CI、测试、安全状态、治理报告或
`docs/status/CURRENT_STATUS.md` 前，必须先读取：

1. `docs/status/CURRENT_STATUS.md`
2. `docs/agent-guides/DOC_GOVERNANCE_RULES.md`
3. `docs/agent-guides/FACT_PROPAGATION_MATRIX.md`

强制规则：

- `docs/status/CURRENT_STATUS.md` 是当前状态的唯一权威来源。
- 不得把“已配置”或“可运行”写成“已验证”；只有实际运行命令或 CI 完成后才能标记 verified。
- 修改中英双语文档时，中文段和 English 段必须同次更新。
- 修改 CI、测试数量、安全状态或命令数量后，必须按事实传播矩阵检查相关文档。
- 主测试入口是 `python -m pytest tests/ -v --tb=short`。

## English

This file is the repository-level entry point for coding agents. Before changing
documentation, CI, tests, security status, governance reports, or
`docs/status/CURRENT_STATUS.md`, read:

1. `docs/status/CURRENT_STATUS.md`
2. `docs/agent-guides/DOC_GOVERNANCE_RULES.md`
3. `docs/agent-guides/FACT_PROPAGATION_MATRIX.md`

Mandatory rules:

- `docs/status/CURRENT_STATUS.md` is the single authority for current status.
- Do not label configured or runnable work as verified; only completed commands
  or completed CI runs count as verified.
- Update Chinese and English mirror sections in the same change.
- After changing CI, test counts, security status, or command counts, check the
  related documents in the fact propagation matrix.
- The main test entry point is `python -m pytest tests/ -v --tb=short`.
