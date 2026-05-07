# 文档治理规则 / Documentation Governance Rules

## 中文说明

本文件约束文档、CI、测试状态和治理报告的修改流程。它补充
`docs/architecture/CLAUDE.md`：`CLAUDE.md` 是通用行为准则，本文件是本项目的
硬性治理规则。

### 触发条件

只要修改以下任一事实，必须执行本规则：

- 测试命令、通过数量、跳过数量、失败数量。
- CI runner、Python matrix、系统依赖或 GitHub Actions job 名称。
- GNU differential 测试状态。
- 安全状态、sandbox 状态、known gaps。
- 当前状态文件、治理报告、测试报告。
- docs 目录结构和归档状态。

### 权威来源

- 当前状态唯一权威来源：`docs/status/CURRENT_STATUS.md`。
- 历史报告和分析日志只可作为时间点证据，不可作为当前事实来源。
- 新事实写入当前文档前，必须确认它来自实际命令输出、CI 结果或源码配置。

### 双语镜像规则

修改中文段时，必须检查对应 English 段。修改 English 段时，必须检查对应中文段。

不得出现以下状态：

- 中文说已安装，English 说未安装。
- 中文说已验证，English 说 pending。
- 中文测试数量和 English 测试数量不同。
- 中文 next actions 和 English next actions 指向不同工作。

### 搜索规则

禁止只搜索一种形式。至少同时覆盖：

- 数字形式：`99`, `120`, `126`, `132`, `54 skipped`。
- 英文自然语言：`passed`, `skipped`, `failed`, `not installed`, `No Windows runner`。
- 中文自然语言：`通过`, `跳过`, `失败`, `未安装`, `无 Windows CI`, `现有`。
- 领域关键词：`coreutils`, `GNU differential`, `CI`, `Windows runner`, `CURRENT_STATUS`。

### 验证状态词规则

必须区分以下状态层级：

- **Configured**：配置已经写入。
- **Runnable**：依赖已经具备，理论上可以运行。
- **Locally verified**：本地命令已经实际运行并通过。
- **CI verified**：GitHub Actions 已经实际运行并通过。

不得把 Configured 或 Runnable 写成 Verified。安装 `coreutils` 只能说明
GNU differential tests 在 Ubuntu CI 中可运行，不能说明 CI 已验证。

### 最低验证要求

文档治理变更至少运行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_docs_bilingual.py tests/test_docs_governance.py -v --tb=short
```

如果修改了测试入口、测试数量、CI 或安全状态，还应运行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ -v --tb=short
```

### 版本治理规则

版本号、PyPI 发布号、Git tag、README pin、CURRENT_STATUS 均属于**强治理事实**，
任何一处修改必须同步更新其他所有位置。

强制规则：

1. **单一版本来源**：`pyproject.toml` `[project].version` 是源码版本权威来源。
   `src/aicoreutils/__init__.py` 的 `__version__` 必须与之完全一致。
2. **Bump 版本必须同步 5 个位置**：`pyproject.toml`、`__init__.py`、`server.json`、
   `CHANGELOG.md`（新增版本条目）、`CURRENT_STATUS.md`（项目版本字段）。
3. **README pin 不得落后**：README 中 `pip install aicoreutils==X.Y.Z` 的版本号
   必须与当前 `pyproject.toml` 版本一致。新增 `test_readme_pin_version` 后会阻断漂移。
4. **CURRENT_STATUS 不得自相矛盾**：同一文档中两处对同一事实的描述不得冲突。
   例如"CI 未纳入"与 CI 命令中已包含该测试的矛盾。
5. **CI commit 不得过时**：CURRENT_STATUS 中引用的 commit hash 必须为最近一次
   推送或 tag。读者应能通过该 hash 定位到真实的 CI 运行。
6. **Unverified 必须标记**：无法本地确认的事实（如远程 CI 的最新通过状态），
   必须标记为 "CI 运行中" 或 "Not verified"，不得写成 "CI verified"。
7. **Bump 后必须运行版本一致性测试**：
   ```powershell
   $env:PYTHONPATH = "src"
   python -m pytest tests/test_version_consistency.py -v
   ```

## English

This file governs changes to documentation, CI, test status, and governance
reports. It complements `docs/architecture/CLAUDE.md`: `CLAUDE.md` contains
general behavior guidance, while this file contains project-specific mandatory
governance rules.

### Trigger Conditions

Run this workflow whenever changing any of these facts:

- Test command, passed count, skipped count, or failed count.
- CI runner, Python matrix, system dependencies, or GitHub Actions job names.
- GNU differential test status.
- Security status, sandbox status, or known gaps.
- Current status files, governance reports, or test reports.
- docs directory structure and archive status.

### Authoritative Sources

- Single authority for current status: `docs/status/CURRENT_STATUS.md`.
- Historical reports and analysis logs are point-in-time evidence only; they are
  not current factual sources.
- Before writing a new current fact, verify that it comes from command output,
  CI results, or source configuration.

### Bilingual Mirror Rule

When editing Chinese sections, check the corresponding English section. When
editing English sections, check the corresponding Chinese section.

The following states are forbidden:

- Chinese says installed while English says not installed.
- Chinese says verified while English says pending.
- Chinese and English test counts differ.
- Chinese and English next actions point to different work.

### Search Rule

Do not search only one phrasing. Cover all of these forms:

- Numeric forms: `99`, `120`, `126`, `132`, `54 skipped`.
- English natural language: `passed`, `skipped`, `failed`, `not installed`,
  `No Windows runner`.
- Chinese natural language: `通过`, `跳过`, `失败`, `未安装`, `无 Windows CI`, `现有`.
- Domain keywords: `coreutils`, `GNU differential`, `CI`, `Windows runner`,
  `CURRENT_STATUS`.

### Verification Vocabulary Rule

Always distinguish these status levels:

- **Configured**: configuration was written.
- **Runnable**: dependencies are available and the action can run in principle.
- **Locally verified**: the local command actually completed successfully.
- **CI verified**: GitHub Actions actually completed successfully.

Do not describe Configured or Runnable as Verified. Installing `coreutils` only
means GNU differential tests are runnable in Ubuntu CI; it does not mean CI has
verified them.

### Minimum Verification

For documentation governance changes, run at least:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/test_docs_bilingual.py tests/test_docs_governance.py -v --tb=short
```

If test entry points, test counts, CI, or security status changed, also run:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests/ -v --tb=short
```
