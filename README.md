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
python -m unittest discover -s tests -v
```

### 项目结构

```text
.
|-- src/agentutils/        # Python 包源码
|-- tests/                 # 子进程级行为测试
|-- docs/                  # 使用说明、协议说明、兼容性审计和测试说明
|-- vendor/gnu-coreutils/  # 本地上游源码缓存，默认被 Git 忽略
|-- pyproject.toml         # 包元数据和构建配置
`-- README.md
```

### 文档

- [Agent 协议与示例](docs/AGENTUTILS.md)
- [中英文使用说明](docs/USAGE.zh-CN.en.md)
- [GNU Coreutils 兼容性审计](docs/GNU_COMPATIBILITY_AUDIT.md)
- [测试说明](docs/TESTING.md)

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
python -m unittest discover -s tests -v
```

### Project Layout

```text
.
|-- src/agentutils/        # Python package
|-- tests/                 # subprocess-level behavior tests
|-- docs/                  # user guide, protocol notes, compatibility audit, testing guide
|-- vendor/gnu-coreutils/  # local upstream source cache, ignored by Git by default
|-- pyproject.toml         # package metadata and build config
`-- README.md
```

### Documentation

- [Agent protocol and examples](docs/AGENTUTILS.md)
- [Chinese/English user guide](docs/USAGE.zh-CN.en.md)
- [GNU Coreutils compatibility audit](docs/GNU_COMPATIBILITY_AUDIT.md)
- [Testing guide](docs/TESTING.md)

### Release Status

Current implementation: 113 CLI commands in `agentutils schema`.

Important limitation: this project is an agent-friendly subset inspired by GNU
Coreutils, not a full GNU Coreutils clone.
