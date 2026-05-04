# 当前项目状态 / Current Project Status

## 中文说明

> **这是项目当前状态的唯一权威来源。**
> 历史报告见 `docs/reports/`，分析日志见 `docs/analysis/`。

| 属性 | 值 |
|---|---|
| **最后验证日期** | 2026-05-04 |
| **验证对象** | 本地工作区（`be9e11f`，已推送并通过 CI 全平台验证 10/10） |
| **Python 版本** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **操作系统** | Windows 11 (开发) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + macos-latest + windows-latest |
| **项目版本** | 0.4.4 |

### 测试

| 指标 | 数值 |
|---|---|
| **推荐测试命令** | `python -m pytest project/tests/ -v --tb=short` |
| **Legacy 入口** | `python -m unittest discover -s tests -v` (部分运行器) |
| **Windows 推荐入口结果** | 343 passed, 60 skipped, 0 failed, 460 subtests passed (Python 3.14) |
| **CI 全平台结果 (最新)** | Ubuntu: 397 passed, 2 skipped; macOS: 343 passed, 56 skipped; Windows: 391 passed, 8 skipped; lint + typecheck ✅ |
| **Windows 跳过原因** | GNU 工具不可用 (Windows 无 coreutils); 无 symlink 支持; locale 相关中文排序/分词 |
| **Property-based 测试** | `python -m pytest project/tests/test_property_based_cli.py -v` (25 测试) |
| **GNU 对照测试** | `python -m pytest project/tests/test_gnu_differential.py -v`（56 测试；Ubuntu CI 通过；Windows/macOS 按平台跳过） |
| **沙箱逃逸测试** | `python -m pytest project/tests/test_sandbox_escape_hardening.py -v` (37 测试, 全部通过或 skip) |
| **文档治理测试** | `python -m pytest project/tests/test_docs_governance.py -v` (9 测试, 全部通过) |
| **双语文档测试** | `python -m pytest project/tests/test_docs_bilingual.py -v` (1 测试, 通过) |
| **版本一致性测试** | `python -m pytest tests/test_version_consistency.py -v` (4 测试, 本地通过; CI 未纳入) |
| **覆盖率** | `python -m pytest project/tests/ --cov=src/aicoreutils` (需要 pytest-cov; 阈值 25%) |
| **静态检查** | `ruff check src/ project/tests/`; `ruff format --check src/ project/tests/`; `mypy src/aicoreutils/ --strict` 全部通过 |
| **CI 平台** | GitHub Actions: ubuntu-latest (3.11/3.12/3.13), macos-latest (3.12/3.13), windows-latest (3.11/3.12/3.13) |

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
| **Agent 子集实现** | 全部 114 命令（含 5 个元命令：catalog、schema、coreutils、tool-list、hash） |
| **GNU differential verified (Windows)** | 仅 sort (5 tests), 其余 51 因缺少 GNU 工具跳过 |
| **GNU differential verified (Local WSL Ubuntu)** | 本地 WSL 已验证 — 54/56 GNU 对照测试通过，2 个中文用例硬编码跳过 |
| **GNU differential verified (CI Ubuntu)** | ✅ CI verified — CI #7 (`cb3e61e`) Ubuntu job 中 GNU 对照测试通过 |
| **兼容性表述** | "JSON-first agent-friendly subset inspired by GNU Coreutils" |

### CI 状态

| 项目 | 状态 |
|---|---|
| **CI 平台** | GitHub Actions |
| **Ubuntu runner** | ubuntu-latest, Python 3.11/3.12/3.13 |
| **macOS runner** | macos-latest, Python 3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **Lint + Typecheck** | ruff check + ruff format --check + mypy --strict, Python 3.13 |
| **CI 测试命令** | `python -m pytest project/tests/ -v --tb=short --cov=src/aicoreutils --cov-fail-under=25` |
| **GNU coreutils** | ✅ Ubuntu job 已安装（`apt-get update && apt-get install coreutils`）; macOS: `brew install coreutils` |
| **最新 CI 结果** | ✅ 10/10 全平台通过 (commit `be9e11f`): lint, typecheck, test-ubuntu, test-macos, test-windows |
| **本地 WSL CI 入口** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` |

### 已知未解决问题

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-003 | CI Node.js 20 deprecation 警告 — 需等 GitHub Actions 发布 Node.js 24 版本的 checkout/setup-python | P4 |
| K-004 | `tests/test_version_consistency.py` 未纳入 CI（不在 `project/tests/` 下） | P2 |
| K-005 | `mcp_server.py` 0% 测试覆盖率 — 缺少 `_call_tool` 和 `server_loop` 单元测试 | P1 |

### 建议下一步

1. **补充 MCP server 单元测试**：为 `mcp_server.py` 的 `_call_tool` 和协议解析添加测试
2. **纳入版本一致性测试**：将 `tests/test_version_consistency.py` 加入 CI pipeline
3. **补充测试覆盖**：为 `async_interface`、`plugins`、`stream` 模块添加单元测试
4. **提升覆盖率门槛**：当前 `--cov-fail-under=25` 偏低，目标提升到 35%

---

## English

> **This is the single authoritative source for current project status.**
> Historical reports are in `docs/reports/`, analysis logs in `docs/analysis/`.

| Property | Value |
|---|---|
| **Last verified** | 2026-05-04 |
| **Verified target** | local working tree (`be9e11f`, pushed and verified by CI 10/10 on all platforms) |
| **Python version** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **OS** | Windows 11 (dev) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + macos-latest + windows-latest |
| **Project version** | 0.4.4 |

### Tests

| Metric | Value |
|---|---|
| **Recommended command** | `python -m pytest project/tests/ -v --tb=short` |
| **Legacy entry** | `python -m unittest discover -s tests -v` (partial runner) |
| **Windows recommended-entry result** | 343 passed, 60 skipped, 0 failed, 460 subtests passed (Python 3.14) |
| **CI all-platform results (latest)** | Ubuntu: 397 passed, 2 skipped; macOS: 343 passed, 56 skipped; Windows: 391 passed, 8 skipped; lint + typecheck ✅ |
| **Windows skip reasons** | GNU tools unavailable on Windows; no symlink support; locale-dependent Chinese sort/word-count |
| **Property-based** | `python -m pytest project/tests/test_property_based_cli.py -v` (25 tests) |
| **GNU differential** | `python -m pytest project/tests/test_gnu_differential.py -v` (56 tests; Ubuntu CI passes; Windows/macOS skip per platform) |
| **Sandbox escape** | `python -m pytest project/tests/test_sandbox_escape_hardening.py -v` (37 tests, all pass or skip) |
| **Docs governance** | `python -m pytest project/tests/test_docs_governance.py -v` (9 tests, all pass) |
| **Bilingual docs** | `python -m pytest project/tests/test_docs_bilingual.py -v` (1 test, passes) |
| **Version consistency** | `python -m pytest tests/test_version_consistency.py -v` (4 tests, local pass; not yet in CI) |
| **Coverage** | `python -m pytest project/tests/ --cov=src/aicoreutils` (requires pytest-cov; threshold 25%) |
| **Static checks** | `ruff check src/ project/tests/`; `ruff format --check src/ project/tests/`; `mypy src/aicoreutils/ --strict` all pass |
| **CI platform** | GitHub Actions: ubuntu-latest (3.11/3.12/3.13), macos-latest (3.12/3.13), windows-latest (3.11/3.12/3.13) |

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
| **Agent subset implemented** | All 114 commands (incl. 5 meta-commands: catalog, schema, coreutils, tool-list, hash) |
| **GNU differential verified (Windows)** | sort only (5 tests), 51 skipped (no GNU tools) |
| **GNU differential verified (Local WSL Ubuntu)** | Locally verified in WSL — 54/56 GNU differential tests passed, 2 Chinese cases hard-skipped |
| **GNU differential verified (CI Ubuntu)** | ✅ CI verified — CI #7 (`cb3e61e`) GNU differential tests passed in Ubuntu job |
| **Compatibility description** | "JSON-first agent-friendly subset inspired by GNU Coreutils" |

### CI Status

| Item | Status |
|---|---|
| **CI platform** | GitHub Actions |
| **Ubuntu runner** | ubuntu-latest, Python 3.11/3.12/3.13 |
| **macOS runner** | macos-latest, Python 3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **Lint + Typecheck** | ruff check + ruff format --check + mypy --strict, Python 3.13 |
| **CI test command** | `python -m pytest project/tests/ -v --tb=short --cov=src/aicoreutils --cov-fail-under=25` |
| **GNU coreutils** | ✅ Ubuntu: `apt-get update && apt-get install coreutils`; macOS: `brew install coreutils` |
| **Latest CI result** | ✅ 10/10 all platforms pass (commit `be9e11f`): lint, typecheck, test-ubuntu, test-macos, test-windows |
| **Local WSL CI entry** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` |

### Known Open Issues

| # | Issue | Priority |
|---|---|---|
| K-003 | CI Node.js 20 deprecation warnings — awaiting GitHub Actions Node.js 24 checkout/setup-python releases | P4 |
| K-004 | `tests/test_version_consistency.py` not in CI (located outside `project/tests/`) | P2 |
| K-005 | `mcp_server.py` 0% test coverage — missing `_call_tool` and `server_loop` unit tests | P1 |

### Next Required Actions

1. **Add MCP server unit tests**: Test `_call_tool` and protocol parsing in `mcp_server.py`
2. **Include version consistency in CI**: Add `tests/test_version_consistency.py` to CI pipeline
3. **Add test coverage**: Unit tests for `async_interface`, `plugins`, `stream` modules
4. **Raise coverage threshold**: Current `--cov-fail-under=25` is low; target 35%
