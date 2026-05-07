# Contributing

## 开发环境

```bash
git clone https://github.com/caseSHY/AI-CLI.git
cd AI-CLI
python -m pip install -e ".[dev]"
```

## 运行测试

```bash
# 主测试入口
PYTHONPATH=src python -m pytest tests/ -v --tb=short

# 含覆盖率
PYTHONPATH=src python -m pytest tests/ --cov=src/aicoreutils --cov-report=term-missing --cov-fail-under=45

# 版本一致性
PYTHONPATH=src python -m pytest tests/test_version_consistency.py -v
```

## 代码质量

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
mypy src/aicoreutils/ --strict
```

## 提交规范

- `fix:` — Bug 修复
- `feat:` — 新功能
- `test:` — 测试
- `ci:` — CI/CD
- `docs:` — 文档
- `release:` — 版本发布

## PR 要求

1. 所有测试通过 (`pytest tests/`)
2. Lint + typecheck 通过 (`ruff` + `mypy`)
3. 覆盖率 ≥ 45%
4. 修改文档后需同步 `docs/status/CURRENT_STATUS.md`
5. 双语文档（中文 + English）同次更新

## 版本发布

完整发布治理清单见 `docs/development/RELEASE_GOVERNANCE.md`。Tag 前先运行：

```bash
PYTHONPATH=src python scripts/release_gate.py --full
```

```bash
# 1. bump 版本号（自动修改 5 个文件 + CHANGELOG 模板）
python scripts/bump_version.py x.y.z
# 预览：python scripts/bump_version.py x.y.z --dry-run

# 2. 编辑 CHANGELOG.md 填写实际变更内容

# 3. 更新 CURRENT_STATUS.md 动态字段
python scripts/generate_status.py --write

# 4. 运行版本一致性测试
PYTHONPATH=src python scripts/release_gate.py

# 5. 提交并打 tag
git add pyproject.toml src/aicoreutils/__init__.py server.json CHANGELOG.md docs/status/CURRENT_STATUS.md
git commit -m "release: bump to x.y.z"
git tag vx.y.z
git push && git push origin vx.y.z

# 6. GitHub Actions 自动：
#    - 构建 wheel/sdist
#    - 发布到 TestPyPI → PyPI (Trusted Publishing)
#    - 创建 GitHub Release（notes 从 CHANGELOG 自动提取）
```
