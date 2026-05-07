# 发布治理 / Release Governance

## 中文说明

本文件定义 tag 和 PyPI 发布前的执行清单。发布必须能从版本号、CHANGELOG、CI、Git tag、GitHub Release 和 PyPI artifact 形成可追溯证据链。

### 发布前检查

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py
python scripts/release_gate.py --full
```

`release_gate.py` 默认执行：

- `scripts/generate_status.py`
- `scripts/audit_command_matrix.py`
- `scripts/audit_command_specs.py`
- `scripts/audit_supply_chain.py`
- `tests/test_version_consistency.py`
- `tests/test_project_consistency.py`
- `ruff check`
- `mypy --strict`

`--full` 额外执行完整测试套件。

### 版本升级步骤

```powershell
python scripts/bump_version.py x.y.z --dry-run
python scripts/bump_version.py x.y.z
python scripts/generate_status.py --write
python scripts/release_gate.py --full
```

然后检查 `CHANGELOG.md`，确保 release notes 包含：

- 兼容性影响：patch/minor/major。
- 安全影响：是否需要立即升级。
- MCP schema 或 JSON envelope 是否变化。
- 已知回归风险和回滚方式。

### Tag 前门槛

- 本地 `release_gate.py --full` 通过。
- GitHub Actions 最新 commit 通过。
- `CHANGELOG.md` 已补全实际变更，不保留空模板项。
- `CURRENT_STATUS.md` 不含已知 stale fact。
- README pin、`pyproject.toml`、`__version__`、`server.json` 版本一致。

### 回滚策略

| 场景 | 操作 |
|---|---|
| PyPI artifact 元数据错误 | yanked release，并发布修正版本。 |
| 文档错误但包可用 | 修正文档，补 patch release 或 GitHub Release note。 |
| 安全绕过 | 立即发布 security fix，必要时 GitHub Security Advisory。 |
| MCP schema 破坏 | yanked 或 major 版本重发，并在 README/CHANGELOG 标注迁移方式。 |

---

## English

This file defines the execution checklist before tagging and publishing to PyPI. A release must be traceable across version, CHANGELOG, CI, Git tag, GitHub Release, and PyPI artifact.

### Pre-Release Checks

```powershell
$env:PYTHONPATH = "src"
python scripts/release_gate.py
python scripts/release_gate.py --full
```

`release_gate.py` runs these checks by default:

- `scripts/generate_status.py`
- `scripts/audit_command_matrix.py`
- `scripts/audit_command_specs.py`
- `scripts/audit_supply_chain.py`
- `tests/test_version_consistency.py`
- `tests/test_project_consistency.py`
- `ruff check`
- `mypy --strict`

`--full` also runs the full test suite.

### Version Bump Steps

```powershell
python scripts/bump_version.py x.y.z --dry-run
python scripts/bump_version.py x.y.z
python scripts/generate_status.py --write
python scripts/release_gate.py --full
```

Then inspect `CHANGELOG.md` and make sure release notes include:

- Compatibility impact: patch/minor/major.
- Security impact: whether immediate upgrade is required.
- Whether MCP schema or JSON envelope changed.
- Known regression risk and rollback path.

### Pre-Tag Gates

- Local `release_gate.py --full` passes.
- GitHub Actions passes on the latest commit.
- `CHANGELOG.md` has real content and no empty template entries.
- `CURRENT_STATUS.md` has no known stale facts.
- README pin, `pyproject.toml`, `__version__`, and `server.json` versions match.
- Supply-chain audit passes: trusted publishing, Dependabot coverage, non-root Docker user, and read-only MCP Docker default.

### Rollback Policy

| Scenario | Action |
|---|---|
| PyPI artifact metadata is wrong | Yank the release and publish a fixed version. |
| Documentation is wrong but package is usable | Fix docs and add a patch release or GitHub Release note. |
| Security bypass | Publish a security fix immediately and use GitHub Security Advisory when needed. |
| MCP schema breaks compatibility | Yank or republish as major version and document migration in README/CHANGELOG. |
