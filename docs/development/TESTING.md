# 测试说明 / Testing

## 中文说明

运行完整本地测试套件：

```powershell
python -m unittest discover -s tests -v
```

如果没有执行 editable install，而是直接从源码目录运行：

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

### 测试分类

- Unit test：`tests/test_unit_protocol.py`
- CLI black-box test：`tests/test_cli_black_box.py`
- Golden file test：`tests/test_golden_outputs.py` 和 `tests/golden/`
- Sandbox test：`tests/test_sandbox_and_side_effects.py`
- Agent-call test：`tests/test_agent_call_flow.py`
- Error / exit-code test：`tests/test_error_exit_codes.py`
- Filesystem side-effect test：`tests/test_sandbox_and_side_effects.py`
- CI test：`tests/test_ci_config.py`

### CI

GitHub Actions 工作流文件：

```text
.github/workflows/ci.yml
```

CI 会以 editable mode 安装包，并运行：

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

---

## English

Run the full local test suite:

```powershell
python -m unittest discover -s tests -v
```

For a source checkout without editable install:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

### Test Categories

- Unit test: `tests/test_unit_protocol.py`
- CLI black-box test: `tests/test_cli_black_box.py`
- Golden file test: `tests/test_golden_outputs.py` and `tests/golden/`
- Sandbox test: `tests/test_sandbox_and_side_effects.py`
- Agent-call test: `tests/test_agent_call_flow.py`
- Error / exit-code test: `tests/test_error_exit_codes.py`
- Filesystem side-effect test: `tests/test_sandbox_and_side_effects.py`
- CI test: `tests/test_ci_config.py`

### CI

GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The workflow installs the package in editable mode and runs:

```bash
PYTHONPATH=src python -m unittest discover -s tests
```
