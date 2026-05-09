# 当前项目状态 / Current Project Status

## 中文说明

> **这是项目当前状态的唯一权威来源。**
> 历史报告见 `docs/reports/`，分析日志见 `docs/analysis/`。
> `项目版本`、`验证对象 commit`、命令数和 coverage gate 由 `scripts/generate_status.py` 检查；修改后必须运行该脚本。

| 属性 | 值 |
|---|---|
<!-- status-managed:start cn-baseline -->
| **最后验证日期** | 2026-05-06 |
| **验证对象** | 本地工作区（`2f91744`，已推送至 GitHub，GitHub Actions CI 运行中） |
| **Python 版本** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **操作系统** | Windows 11 (开发) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + macos-latest + windows-latest |
| **项目版本** | 1.1.2 |
<!-- status-managed:end cn-baseline -->

### 测试

| 指标 | 数值 |
|---|---|
| **推荐测试命令** | `uv run pytest tests/ -v --tb=short` |
| **Legacy 入口** | `uv run python -m unittest discover -s tests -v` (部分运行器) |
| **Windows 推荐入口结果** | 781 passed, 56 skipped, 0 failed |
| **CI 全平台结果 (最新)** | Ubuntu: 781 passed, 56 skipped; macOS: 781 passed, 56 skipped; Windows: 816 passed, 13 skipped; lint + typecheck ✅ |
| **Windows 跳过原因** | chown/chgrp 不支持; symlink 需 admin; mkfifo 不可用 |
| **Property-based 测试** | `uv run pytest tests/test_property_based_cli.py -v` (34 测试) |
| **GNU 对照测试** | `uv run pytest tests/test_gnu_differential.py -v`（56 测试；需 GNU coreutils；Ubuntu CI 通过；Windows/macOS 按平台跳过） |
| **沙箱逃逸测试** | `python -m pytest tests/test_sandbox_escape_hardening.py -v` (58 测试, 全部通过或 skip) |
| **文档治理测试** | `python -m pytest tests/test_docs_governance.py -v` (8 测试, 全部通过) |
| **双语文档测试** | `python -m pytest tests/test_docs_bilingual.py -v` (1 测试, 通过) |
| **版本一致性测试** | `python -m pytest tests/test_version_consistency.py -v` (4 测试; 已在 CI pipeline 中) |
| **覆盖率** | `python -m pytest tests/ --cov=src/aicoreutils` (需要 pytest-cov; 阈值 77%) |
| **静态检查** | `ruff check src/ tests/`; `ruff format --check src/ tests/`; `mypy src/aicoreutils/ --strict` 全部通过 |
| **CI 平台** | GitHub Actions: ubuntu-latest (3.11/3.12/3.13), macos-latest (3.11/3.12/3.13), windows-latest (3.11/3.12/3.13) |

### 安全状态

| 项目 | 状态 |
|---|---|
| **沙箱逃逸漏洞** | ✅ 全部 5 个已知漏洞已于 2026-04-30 修复 |
| **cwd 边界校验** | ✅ 全 20 个 mutating 命令均校验目标路径在 cwd 内（含 cp/mv/ln/link/mkdir/touch/chmod/chown/chgrp/shred/mktemp/mkfifo/mknod/rmdir/unlink/csplit/split/nohup） |
| **符号链接逃逸** | ✅ `resolve_path` 解析真实路径后校验; Windows 跳过(symlink 不可用) |
| **dry-run 零副作用** | ✅ 20 个 mutating 命令 dry-run 均通过零副作用验证 |
| **危险命令默认拒绝** | ✅ shred/kill/nice/nohup/stty/chcon/runcon/chroot 需要显式 `--allow-*` 确认 |
| **MCP 安全控制** | ✅ `--read-only`/`--allow-command`/`--deny-command` 三级权限 |

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
| **macOS runner** | macos-latest, Python 3.11/3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **Lint + Typecheck** | ruff check + ruff format --check + mypy --strict, Python 3.13 |
| **CI 测试命令** | `uv run pytest tests/ tests/test_version_consistency.py -v --tb=short --cov=src/aicoreutils --cov-fail-under=77` |
| **GNU coreutils** | ✅ Ubuntu job 已安装（`apt-get update && apt-get install coreutils`）; macOS: `brew install coreutils` |
| **最新 CI 结果** | ✅ 13/13 全平台通过: lint, typecheck, status-check, governance-gate, test-ubuntu (3.11/3.12/3.13), test-macos (3.11/3.12/3.13), test-windows (3.11/3.12/3.13) |
| **本地 WSL CI 入口** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` |

### 已知未解决问题

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-003 | CI Node.js 20 deprecation 警告 — 需等 GitHub Actions 发布 Node.js 24 版本的 checkout/setup-python | P4 |

### 建议下一步

1. **持续提升覆盖率**：fs/_core.py (77%), system/_core.py (52%) 仍有提升空间
2. **MCP 安全增强**：tool annotations 和更细粒度的权限控制
3. **状态文档自动化**：让 CI 自动同步动态数字到 CURRENT_STATUS.md

---

## English

> **This is the single authoritative source for current project status.**
> Historical reports are in `docs/reports/`, analysis logs in `docs/analysis/`.
> `Project version`, `verified-target commit`, command count, and coverage gate are checked by `scripts/generate_status.py`; run it after edits.

| Property | Value |
|---|---|
<!-- status-managed:start en-baseline -->
| **Last verified** | 2026-05-06 |
| **Verified target** | local working tree (`2f91744`, pushed to GitHub, GitHub Actions CI in progress) |
| **Python version** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **OS** | Windows 11 (dev) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + macos-latest + windows-latest |
| **Project version** | 1.1.2 |
<!-- status-managed:end en-baseline -->

### Tests

| Metric | Value |
|---|---|
| **Recommended command** | `uv run pytest tests/ -v --tb=short` |
| **Legacy entry** | `uv run python -m unittest discover -s tests -v` (partial runner) |
| **Windows recommended-entry result** | 781 passed, 56 skipped, 0 failed |
| **CI all-platform results (latest)** | Ubuntu: 781 passed, 56 skipped; macOS: 781 passed, 56 skipped; Windows: 816 passed, 13 skipped; lint + typecheck ✅ |
| **Windows skip reasons** | chown/chgrp unsupported; symlink needs admin; mkfifo unavailable |
| **Property-based** | `uv run pytest tests/test_property_based_cli.py -v` (34 tests) |
| **GNU differential** | `uv run pytest tests/test_gnu_differential.py -v` (56 tests; needs GNU coreutils; Ubuntu CI passes; Windows/macOS skip per platform) |
| **Sandbox escape** | `python -m pytest tests/test_sandbox_escape_hardening.py -v` (58 tests, all pass or skip) |
| **Docs governance** | `python -m pytest tests/test_docs_governance.py -v` (8 tests, all pass) |
| **Bilingual docs** | `python -m pytest tests/test_docs_bilingual.py -v` (1 test, passes) |
| **Version consistency** | `python -m pytest tests/test_version_consistency.py -v` (4 tests; in CI pipeline) |
| **Coverage** | `python -m pytest tests/ --cov=src/aicoreutils` (requires pytest-cov; threshold 77%) |
| **Static checks** | `ruff check src/ tests/`; `ruff format --check src/ tests/`; `mypy src/aicoreutils/ --strict` all pass |
| **CI platform** | GitHub Actions: ubuntu-latest (3.11/3.12/3.13), macos-latest (3.11/3.12/3.13), windows-latest (3.11/3.12/3.13) |

### Security Status

| Item | Status |
|---|---|
| **Sandbox escape gaps** | ✅ All 5 known gaps fixed 2026-04-30 |
| **cwd boundary checks** | ✅ All 20 mutating commands validate paths inside cwd (including cp/mv/ln/link/mkdir/touch/chmod/chown/chgrp/shred/mktemp/mkfifo/mknod/rmdir/unlink/csplit/split/nohup) |
| **Symlink escape** | ✅ `resolve_path` resolves then checks; Windows skips (no symlink) |
| **dry-run zero side-effects** | ✅ 20 mutating commands verified |
| **Dangerous command gates** | ✅ shred/kill/nice/nohup/stty/chcon/runcon/chroot require explicit `--allow-*` |
| **MCP security controls** | ✅ `--read-only`/`--allow-command`/`--deny-command` three-tier access |
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
| **macOS runner** | macos-latest, Python 3.11/3.12/3.13 |
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **Lint + Typecheck** | ruff check + ruff format --check + mypy --strict, Python 3.13 |
| **CI test command** | `uv run pytest tests/ tests/test_version_consistency.py -v --tb=short --cov=src/aicoreutils --cov-fail-under=77` |
| **GNU coreutils** | ✅ Ubuntu: `apt-get update && apt-get install coreutils`; macOS: `brew install coreutils` |
| **Latest CI result** | ✅ 13/13 all platforms pass: lint, typecheck, status-check, governance-gate, test-ubuntu (3.11/3.12/3.13), test-macos (3.11/3.12/3.13), test-windows (3.11/3.12/3.13) |
| **Local WSL CI entry** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` |

### Known Open Issues

| # | Issue | Priority |
|---|---|---|
| K-003 | CI Node.js 20 deprecation warnings — awaiting GitHub Actions Node.js 24 checkout/setup-python releases | P4 |

### Next Required Actions

1. **Continue coverage improvement**: fs/_core.py (77%), system/_core.py (52%) still have gaps
2. **MCP security hardening**: Tool annotations and finer-grained access control
3. **Status doc automation**: Have CI auto-sync dynamic numbers to CURRENT_STATUS.md
