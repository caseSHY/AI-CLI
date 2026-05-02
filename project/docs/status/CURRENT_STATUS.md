# 当前项目状态 / Current Project Status

## 中文说明

> **这是项目当前状态的唯一权威来源。**
> 历史报告见 `docs/reports/`，分析日志见 `docs/analysis/`。

| 属性 | 值 |
|---|---|
| **最后验证日期** | 2026-05-02 |
| **验证对象** | 本地工作区（`cb3e61e`，已推送并通过 CI #7 全平台验证） |
| **Python 版本** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **操作系统** | Windows 11 (开发) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + windows-latest |
| **项目版本** | 0.2.0 |

### 测试

| 指标 | 数值 |
|---|---|
| **推荐测试命令** | `python -m pytest project/tests/ -v --tb=short` |
| **Legacy 入口** | `python -m unittest discover -s tests -v` (部分运行器) |
| **Windows 推荐入口结果** | 169 passed, 59 skipped, 0 failed, 118 subtests passed |
| **WSL 本地 CI 结果** | 190 passed, 1 skipped, 0 failed, 118 subtests passed |
| **Windows 跳过原因** | 51: GNU 工具在 Windows 不可用; 3: Windows 无 symlink 支持 |
| **WSL 跳过原因** | 2: `test_sort_chinese_utf8`（locale 相关中文排序）和 `test_wc_chinese_text`（locale 相关中文分词）硬编码跳过 |
| **Property-based 测试** | `python -m pytest project/tests/test_property_based_cli.py -v` (25 测试, PROPERTY_EXAMPLES=25) |
| **GNU 对照测试** | `python -m pytest project/tests/test_gnu_differential.py -v`（56 测试；WSL 本地运行 54 个，2 个硬编码跳过） |
| **沙箱逃逸测试** | `python -m pytest project/tests/test_sandbox_escape_hardening.py -v` (37 测试, 全部通过或 skip) |
| **文档治理测试** | `python -m pytest project/tests/test_docs_governance.py -v` (9 测试, 全部通过) |
| **覆盖率** | `python -m pytest project/tests/ --cov=src/agentutils` (需要 pytest-cov) |
| **静态检查** | `ruff check src/ tests/`; `ruff format --check src/ tests/`; `mypy src/agentutils/ --strict` 全部通过 |
| **WSL 本地 CI** | `.\.github\scripts\run-ci-wsl.ps1 -Distro Ubuntu-24.04 -SkipInstall`（2026-05-02 已通过） |

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
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **CI 测试命令** | `python -m pytest project/tests/ -v` |
| **GNU coreutils** | ✅ Ubuntu job 已安装（`apt-get install coreutils`） |
| **本地 WSL CI 入口** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` 已添加 |
| **本机 WSL 状态** | ✅ Ubuntu-24.04 已安装，WSL 版本 2，Ubuntu 24.04.4 LTS |
| **本地 WSL CI 结果** | ✅ 2026-05-02 通过：190 passed, 1 skipped, 0 failed, 118 subtests passed |
| **远程最新 push CI** | ✅ #7 (`cb3e61e`) 全部通过：lint、typecheck、test-ubuntu (3.11/3.12/3.13)、test-windows (3.11/3.12/3.13) |
| **本地修复状态** | ✅ 已推送并通过 CI #7 全平台验证（Ubuntu + Windows, Python 3.11/3.12/3.13） |

### 已知未解决问题

| 编号 | 问题 | 优先级 |
|---|---|---|
| K-003 | 8 条 CI Node.js 20 deprecation 警告，需等 GitHub 官方更新 actions/checkout 和 actions/setup-python 版本 | P4 |

### 建议下一步

1. **补充测试覆盖**：为 `async_interface`、`plugins`、`stream` 模块添加单元测试
2. **修复代码质量**：`path_utils.py` 中静默 PermissionError 应添加警告标记
3. **覆盖率子进程模式**：启用 coverage.py 的 `concurrency=multiprocessing` 以反映真实测试覆盖
4. **添加 macOS CI**：扩展平台矩阵以验证 macOS 兼容性

---

## English

> **This is the single authoritative source for current project status.**
> Historical reports are in `docs/reports/`, analysis logs in `docs/analysis/`.

| Property | Value |
|---|---|
| **Last verified** | 2026-05-02 |
| **Verified target** | local working tree (`cb3e61e`, pushed and verified by CI #7 on all platforms) |
| **Python version** | Windows: 3.14.4; WSL: 3.12.3; CI: 3.11/3.12/3.13 |
| **OS** | Windows 11 (dev) + WSL Ubuntu-24.04 (Ubuntu 24.04.4 LTS), CI: ubuntu-latest + windows-latest |
| **Project version** | 0.2.0 |

### Tests

| Metric | Value |
|---|---|
| **Recommended command** | `python -m pytest project/tests/ -v --tb=short` |
| **Legacy entry** | `python -m unittest discover -s tests -v` (partial runner) |
| **Windows recommended-entry result** | 169 passed, 59 skipped, 0 failed, 118 subtests passed |
| **WSL local CI result** | 190 passed, 1 skipped, 0 failed, 118 subtests passed |
| **Windows skip reasons** | 51: GNU tools unavailable on Windows; 3: Windows no symlink support |
| **WSL skip reason** | 2: `test_sort_chinese_utf8` (locale-dependent Chinese sort) and `test_wc_chinese_text` (locale-dependent Chinese word count) are hard-skipped |
| **Property-based** | `python -m pytest project/tests/test_property_based_cli.py -v` (25 tests, PROPERTY_EXAMPLES=25) |
| **GNU differential** | `python -m pytest project/tests/test_gnu_differential.py -v` (56 tests; WSL ran 54 locally, 2 hard-skipped) |
| **Sandbox escape** | `python -m pytest project/tests/test_sandbox_escape_hardening.py -v` (37 tests, all pass or skip) |
| **Docs governance** | `python -m pytest project/tests/test_docs_governance.py -v` (9 tests, all pass) |
| **Coverage** | `python -m pytest project/tests/ --cov=src/agentutils` (requires pytest-cov) |
| **Static checks** | `ruff check src/ tests/`; `ruff format --check src/ tests/`; `mypy src/agentutils/ --strict` all pass |
| **WSL local CI** | `.\.github\scripts\run-ci-wsl.ps1 -Distro Ubuntu-24.04 -SkipInstall` (passed on 2026-05-02) |

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
| **Windows runner** | windows-latest, Python 3.11/3.12/3.13 |
| **CI test command** | `python -m pytest project/tests/ -v` |
| **GNU coreutils** | ✅ Installed in Ubuntu job |
| **Local WSL CI entry** | ✅ `.github/scripts/run-ci-wsl.ps1` + `.github/scripts/wsl-ci.sh` added |
| **Machine WSL status** | ✅ Ubuntu-24.04 installed, WSL version 2, Ubuntu 24.04.4 LTS |
| **Local WSL CI result** | ✅ Passed on 2026-05-02: 190 passed, 1 skipped, 0 failed, 118 subtests passed |
| **Latest remote push CI** | ✅ #7 (`cb3e61e`) all passed: lint, typecheck, test-ubuntu (3.11/3.12/3.13), test-windows (3.11/3.12/3.13) |
| **Local fix status** | ✅ Pushed and verified by CI #7 on all platforms (Ubuntu + Windows, Python 3.11/3.12/3.13) |

### Known Open Issues

| # | Issue | Priority |
|---|---|---|
| K-003 | 8 CI Node.js 20 deprecation warnings; requires upstream actions/checkout and actions/setup-python version updates | P4 |

### Next Required Actions

1. **Add test coverage**: Unit tests for `async_interface`, `plugins`, `stream` modules
2. **Fix code quality**: Silent `PermissionError` in `path_utils.py` should add warning markers
3. **Coverage subprocess mode**: Enable `concurrency=multiprocessing` to reflect true test coverage
4. **Add macOS CI**: Extend platform matrix to verify macOS compatibility
