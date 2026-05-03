# 测试说明 / Testing

> 当前测试状态见 `docs/status/CURRENT_STATUS.md`
> For current test status see `docs/status/CURRENT_STATUS.md`

## 中文说明

### 推荐测试入口

**pytest 是主入口**，覆盖所有测试维度（unittest + pytest + Hypothesis + GNU differential）：

```powershell
# 完整测试套件
python -m pytest project/tests/ -v --tb=short

# 不含 property-based 测试（快速反馈，约 20-30 秒）
python -m pytest project/tests/ -v --tb=short -k "not (property_based or Hypothesis)"

# 不含 GNU 对照测试（Windows 环境，GNU 工具通常不可用）
python -m pytest project/tests/ -v --tb=short -k "not (Gnu or gnu_differential)"
```

如果没有执行 editable install，而是直接从源码目录运行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest project/tests/ -v --tb=short
```

**Legacy 入口 (unittest, 部分运行器)**：

```powershell
python -m unittest discover -s tests -v
```

> unittest discover 只能运行 `unittest.TestCase` 子类的测试。pytest-native 测试（如有）、
> Hypothesis 测试中的 pytest 风格 fixture 等在 unittest discover 下不会执行。
> **推荐使用 pytest 作为主入口。**

### 测试分类 / Test Categories

| 分类 | 测试文件 | 测试类型 | 说明 |
|---|---|---|---|
| **单元测试** | `test_unit_protocol.py` | unittest | 协议信封、JSON 写出、AgentError |
| **CLI 黑盒** | `test_cli_black_box.py` | unittest | 子进程调用、stdout/stderr 契约 |
| **Agent 调用流** | `test_agent_call_flow.py` | unittest | 观察→决策→dry-run→写入→校验 |
| **错误码** | `test_error_exit_codes.py` | unittest | JSON 错误和语义化退出码 |
| **沙箱与副作用** | `test_sandbox_and_side_effects.py` | unittest | dry-run 不改文件、写操作只产生预期副作用 |
| **沙箱逃逸硬化** | `test_sandbox_escape_hardening.py` | unittest | 路径遍历、symlink 逃逸、文件名注入、dry-run 零副作用、危险命令拒绝 |
| **Golden file** | `test_golden_outputs.py` + `tests/golden/` | unittest | 稳定输出与 golden 文件对比 |
| **GNU 对照测试** | `test_gnu_differential.py` | unittest + skip | 与真实 GNU Coreutils 输出对比（需要 GNU 工具） |
| **Property-based** | `test_property_based_cli.py` | pytest + Hypothesis | 随机输入验证数学/逻辑不变量 |
| **功能命令** | `test_agentutils.py`, `test_more_agent_commands.py`, `test_even_more_agent_commands.py`, `test_file_admin_commands.py`, `test_execution_and_page_commands.py`, `test_system_alias_and_encoding_commands.py`, `test_remaining_coreutils_commands.py` | unittest | 各类命令的功能验证 |
| **CI 配置** | `test_ci_config.py` | unittest | GitHub Actions 配置存在性验证 |
| **文档双语** | `test_docs_bilingual.py` | unittest | Markdown 文档中英双语格式检查 |
| **文档治理** | `test_docs_governance.py` | unittest | Copilot/Agent 规则、CI 状态和 stale 文案检查 |
| **命令清单一致性** | （分布于多个文件） | 隐式 | Schema 输出与 catalog.py 定义一致 |

### Property-Based 测试 / Property-Based Tests

使用 Hypothesis 框架，验证数学/逻辑不变量（如 sort 输出有序、base64 编解码往返还原）。

```powershell
# 单独运行 property-based 测试
python -m pytest project/tests/test_property_based_cli.py -v --tb=short
```

- `max_examples` 由 `PROPERTY_EXAMPLES = 25` 和 `ENVELOPE_EXAMPLES = 15` 控制（定义在 `tests/test_property_based_cli.py` 顶部）。
- CI 中当前值已可用，无需额外调整。

### GNU 对照测试 / GNU Differential Tests

对比 aicoreutils `--raw` 输出与 GNU Coreutils 原生命令，是最强的正确性验证。

```powershell
# 单独运行 GNU 对照测试
python -m pytest project/tests/test_gnu_differential.py -v --tb=short
```

**Windows 环境**：
- 几乎所有 GNU 工具不可用（仅 `C:\Windows\system32\sort.exe` 可用且功能受限）。
- 51/56 测试被 `@unittest.skipIf` 跳过。
- **skip 不等于兼容性已验证**。

**Ubuntu CI 环境**：
- 应在 CI 中安装 `coreutils` 包使测试可运行：
  ```bash
  sudo apt-get install -y coreutils
  ```
- 安装后预计 50+ 测试可实际执行。

### Golden File 更新 / Golden File Update

当命令行为有预期变更时，重新生成 golden 文件：

```powershell
# 手动更新 golden 输出
$env:PYTHONPATH = "src"
python -c "from tests.test_golden_outputs import ..."
```

### 命令清单一致性 / Command List Consistency

命令清单与 `catalog.py` 中定义必须一致。执行以下命令验证：

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema  # 应输出 114 个命令
python -m agentutils catalog --pretty  # 应与 schema 输出一致
```

### Mutating Command 审计 / Mutating Command Audit

每个 mutating command 必须通过：
1. **dry-run 零副作用**：`test_sandbox_escape_hardening.py::DryRunZeroSideEffectTests`
2. **路径遍历拒绝**：`test_sandbox_escape_hardening.py::PathTraversalBlockedTests`
3. **危险命令拒绝**：`test_sandbox_escape_hardening.py::DangerousCommandDefaultDenyTests`

### CI

GitHub Actions 工作流：`.github/workflows/ci.yml`

- **平台**：ubuntu-latest（test-ubuntu）+ windows-latest（test-windows）
- **Python 版本**：3.11, 3.12, 3.13
- **安装**：`python -m pip install -e ".[test]"`
- **测试命令**：`python -m pytest project/tests/ -v`
- **Ubuntu job**：已安装 GNU coreutils（`apt-get install coreutils`），GNU 对照测试可运行
- **Windows job**：覆盖路径/编码/sandbox 测试，GNU 对照测试因缺少 GNU 工具跳过

### WSL 本地 CI / WSL Local CI

Windows 开发机应使用 WSL/Ubuntu 复现 GitHub Actions 的 Ubuntu job，尤其用于验证 GNU differential 测试：

```powershell
# 首次运行，安装 WSL 内的 coreutils 和 Python venv 支持
.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps

# 后续复用 .venv-wsl
.\.github\scripts\run-ci-wsl.ps1 -SkipInstall
```

WSL 内实际执行：

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/agentutils/ --strict
PYTHONPATH=src python -m pytest project/tests/ -v --tb=short --cov=src/agentutils --cov-report=term-missing
```

详细说明见 `project/docs/development/WSL_CI.md`。WSL 本地通过不等于远程 CI 已通过；远程 GitHub Actions 仍是最终发布门禁。

### 覆盖率 / Coverage

```powershell
python -m pytest project/tests/ --cov=src/agentutils --cov-report=term-missing
```

需要 `pytest-cov` 包。

---

## English

### Recommended Test Entry Point

**pytest is the primary entry point**, covering all test dimensions:

```powershell
# Full test suite
python -m pytest project/tests/ -v --tb=short

# Without property-based tests (fast feedback, ~20-30s)
python -m pytest project/tests/ -v --tb=short -k "not (property_based or Hypothesis)"

# Without GNU differential tests (Windows, where GNU tools are unavailable)
python -m pytest project/tests/ -v --tb=short -k "not (Gnu or gnu_differential)"
```

From a source checkout without editable install:

```powershell
$env:PYTHONPATH = "src"
python -m pytest project/tests/ -v --tb=short
```

**Legacy entry (unittest, partial runner)**:

```powershell
python -m unittest discover -s tests -v
```

> unittest discover only runs `unittest.TestCase` subclasses. pytest-native tests and
> Hypothesis tests with pytest-style fixtures will not execute.
> **Prefer pytest as the primary entry point.**

### Test Categories

| Category | Test file | Type | Description |
|---|---|---|---|
| **Unit** | `test_unit_protocol.py` | unittest | Protocol envelopes, JSON writing, AgentError |
| **CLI black-box** | `test_cli_black_box.py` | unittest | Subprocess calls, stdout/stderr contracts |
| **Agent call flow** | `test_agent_call_flow.py` | unittest | Observe→decide→dry-run→write→verify |
| **Error codes** | `test_error_exit_codes.py` | unittest | JSON errors and semantic exit codes |
| **Sandbox & side effects** | `test_sandbox_and_side_effects.py` | unittest | dry-run produces no mutations; writes only expected targets |
| **Sandbox escape hardening** | `test_sandbox_escape_hardening.py` | unittest | Path traversal, symlink escape, filename injection, dry-run zero-side-effect, dangerous command deny |
| **Golden file** | `test_golden_outputs.py` + `tests/golden/` | unittest | Stable output compared to golden files |
| **GNU differential** | `test_gnu_differential.py` | unittest + skip | Output comparison with real GNU Coreutils (needs GNU tools) |
| **Property-based** | `test_property_based_cli.py` | pytest + Hypothesis | Random input validation of mathematical/logical invariants |
| **Feature commands** | `test_agentutils.py`, `test_more_agent_commands.py`, `test_even_more_agent_commands.py`, `test_file_admin_commands.py`, `test_execution_and_page_commands.py`, `test_system_alias_and_encoding_commands.py`, `test_remaining_coreutils_commands.py` | unittest | Functional verification of various command groups |
| **CI config** | `test_ci_config.py` | unittest | GitHub Actions config existence check |
| **Bilingual docs** | `test_docs_bilingual.py` | unittest | Markdown bilingual format verification |
| **Docs governance** | `test_docs_governance.py` | unittest | Copilot/Agent rules, CI status, and stale wording checks |
| **Command list consistency** | (distributed) | implicit | Schema output matches catalog.py definitions |

### Property-Based Tests

Uses Hypothesis framework to verify mathematical/logical invariants.

```powershell
python -m pytest project/tests/test_property_based_cli.py -v --tb=short
```

- `max_examples` is controlled by `PROPERTY_EXAMPLES = 25` and `ENVELOPE_EXAMPLES = 15` (defined at the top of `tests/test_property_based_cli.py`).
- Current values are suitable for CI without adjustment.

### GNU Differential Tests

Compares aicoreutils `--raw` output against real GNU Coreutils.

```powershell
python -m pytest project/tests/test_gnu_differential.py -v --tb=short
```

**Windows**: Almost all GNU tools unavailable. 51/56 tests skipped.
**skip does NOT mean compatibility is verified.**

**Ubuntu CI**: Should install coreutils:
```bash
sudo apt-get install -y coreutils
```

### Golden File Update

When command behavior changes intentionally, regenerate golden files.

### Command List Consistency

Commands must be consistent with the definitions in `catalog.py`:

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema  # should output 114 commands
python -m agentutils catalog --pretty  # should match schema output
```

### Mutating Command Audit

Every mutating command must pass:
1. **dry-run zero side-effects**: `test_sandbox_escape_hardening.py::DryRunZeroSideEffectTests`
2. **Path traversal rejection**: `test_sandbox_escape_hardening.py::PathTraversalBlockedTests`
3. **Dangerous command denial**: `test_sandbox_escape_hardening.py::DangerousCommandDefaultDenyTests`

### CI

GitHub Actions workflow: `.github/workflows/ci.yml`

- **Platform**: ubuntu-latest (test-ubuntu) + windows-latest (test-windows)
- **Python versions**: 3.11, 3.12, 3.13
- **Install**: `python -m pip install -e ".[test]"`
- **Test command**: `python -m pytest project/tests/ -v`
- **Ubuntu job**: GNU coreutils installed (`apt-get install coreutils`), GNU differential tests runnable
- **Windows job**: path/encoding/sandbox coverage; GNU differential tests skipped (no GNU tools)

### WSL Local CI

Windows developers should use WSL/Ubuntu to reproduce the GitHub Actions Ubuntu job, especially for GNU differential tests:

```powershell
# First run: install coreutils and Python venv support inside WSL
.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps

# Later runs can reuse .venv-wsl
.\.github\scripts\run-ci-wsl.ps1 -SkipInstall
```

The WSL script runs:

```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/agentutils/ --strict
PYTHONPATH=src python -m pytest project/tests/ -v --tb=short --cov=src/agentutils --cov-report=term-missing
```

See `project/docs/development/WSL_CI.md` for details. Passing locally in WSL is not the same as passing remote CI; GitHub Actions remains the release gate.

### Coverage

```powershell
python -m pytest project/tests/ --cov=src/agentutils --cov-report=term-missing
```

Requires `pytest-cov`.
