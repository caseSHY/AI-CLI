# Agentutils

## 中文说明

Agentutils 是一个面向 LLM Agent 的 JSON 优先命令行工具包原型。它参考
GNU Coreutils 的常用命令，但不是完整的 GNU 兼容替代品。

项目目标是给机器调用方提供确定、低噪音、易解析的 CLI 接口：

- 默认输出 JSON
- 错误以 JSON 写入 stderr
- 退出码语义稳定
- 修改文件的命令支持 `--dry-run`
- 需要管道组合时显式使用 `--raw`

### 快速开始

```powershell
python -m pip install -e .
agentutils schema --pretty
agentutils ls . --limit 20
agentutils rm build --recursive --dry-run
```

不安装、直接从源码运行：

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema --pretty
```

运行测试：

```powershell
# 推荐主入口（pytest，含 Hypothesis property-based 测试和 GNU 对照测试）
python -m pytest tests/ -v --tb=short

# Legacy 入口（unittest，部分运行器）
python -m unittest discover -s tests -v
```

### 项目结构

```text
.
|-- src/agentutils/        # Python 包源码
|-- tests/                 # 子进程级行为测试
|-- docs/                  # 文档入口和分类文档目录
|   |-- reference/         # 协议、命令面和安全生产契约
|   |-- guides/            # 使用指南
|   |-- audits/            # 兼容性和质量审计
|   |-- development/       # 测试和开发说明
|   |-- status/            # 当前项目状态（唯一权威来源）
|   |-- analysis/          # 项目分析日志（历史归档）
|   |-- agent-guides/      # AI 辅助编码规范
|   `-- reports/           # 测试报告等生成/归档文档
|-- vendor/gnu-coreutils/  # 本地上游源码缓存，默认被 Git 忽略
|-- pyproject.toml         # 包元数据和构建配置
`-- README.md
```

### 文档

- [文档索引](docs/README.md)
- [当前项目状态](docs/status/CURRENT_STATUS.md) ← 权威状态来源
- [Agent 协议与示例](docs/reference/AGENTUTILS.md)
- [安全模型](docs/reference/SECURITY_MODEL.md)
- [中英文使用说明](docs/guides/USAGE.zh-CN.en.md)
- [GNU Coreutils 兼容性审计](docs/audits/GNU_COMPATIBILITY_AUDIT.md)
- [测试说明](docs/development/TESTING.md)

### 发布状态

当前实现：`agentutils schema` 中登记 113 个 CLI 命令。

重要限制：本项目是受 GNU Coreutils 启发的 Agent 友好子集，不是完整的
GNU Coreutils 克隆。

---

## English

Agentutils is a JSON-first command-line toolkit prototype for LLM agents. It is
inspired by common GNU Coreutils commands, but it is not a complete GNU-compatible
replacement.

The goal is a deterministic, low-noise interface for machine callers:

- JSON output by default
- JSON errors on stderr
- Stable semantic exit codes
- `--dry-run` for mutation commands
- Explicit `--raw` output for pipeline composition

### Quick Start

```powershell
python -m pip install -e .
agentutils schema --pretty
agentutils ls . --limit 20
agentutils rm build --recursive --dry-run
```

Run from a source checkout without installing:

```powershell
$env:PYTHONPATH = "src"
python -m agentutils schema --pretty
```

Run tests:

```powershell
# Recommended primary entry (pytest, includes Hypothesis property-based and GNU differential tests)
python -m pytest tests/ -v --tb=short

# Legacy entry (unittest, partial runner)
python -m unittest discover -s tests -v
```

### Project Layout

```text
.
|-- src/agentutils/        # Python package
|-- tests/                 # subprocess-level behavior tests
|-- docs/                  # document, command-surface and security contracts
|   |-- guides/            # usage guides
|   |-- audits/            # compatibility and quality audits
|   |-- development/       # testing and development notes
|   |-- status/            # current project status (single authoritative source)
|   |-- analysis/          # project analysis logs (historical archive)nt notes
|   |-- analysis/          # project analysis logs
|   |-- agent-guides/      # AI coding assistant guidance
|   `-- reports/           # test reports and archived generated docs
|-- vendor/gnu-coreutils/  # local upstream source cache, ignored by Git by default
|-- pyproject.toml         # package metadata and build config
`-- README.md
```

### Documentation

- [Documentation index](docs/README.md)
- [Current project status](docs/status/CURRENT_STATUS.md) ← authoritative status source
- [Agent protocol and examples](docs/reference/AGENTUTILS.md)
- [Security model](docs/reference/SECURITY_MODEL.md)
- [Chinese/English user guide](docs/guides/USAGE.zh-CN.en.md)
- [GNU Coreutils compatibility audit](docs/audits/GNU_COMPATIBILITY_AUDIT.md)
- [Testing guide](docs/development/TESTING.md)

### Release Status

Current implementation: 113 CLI commands in `agentutils schema`.

Important limitation: this project is an agent-friendly subset inspired by GNU
Coreutils, not a full GNU Coreutils clone.
