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
PYTHONPATH=src python -m pytest project/tests/ -v --tb=short

# 含覆盖率
PYTHONPATH=src python -m pytest project/tests/ --cov=src/aicoreutils --cov-report=term-missing --cov-fail-under=35

# 版本一致性
PYTHONPATH=src python -m pytest tests/test_version_consistency.py -v
```

## 代码质量

```bash
ruff check src/ project/tests/
ruff format --check src/ project/tests/
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

1. 所有测试通过 (`pytest project/tests/`)
2. Lint + typecheck 通过 (`ruff` + `mypy`)
3. 覆盖率 ≥ 35%
4. 修改文档后需同步 `project/docs/status/CURRENT_STATUS.md`
5. 双语文档（中文 + English）同次更新

## 版本发布

```bash
# 1. bump 版本号
# pyproject.toml: version = "x.y.z"
# src/aicoreutils/__init__.py: __version__ = "x.y.z"
# server.json: "version": "x.y.z"

# 2. 提交并打 tag
git add pyproject.toml src/aicoreutils/__init__.py server.json
git commit -m "release: bump to x.y.z"
git tag vx.y.z
git push && git push origin vx.y.z

# 3. GitHub Actions 自动发布到 PyPI
```
