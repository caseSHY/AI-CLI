# AICoreUtils

[![AI-CLI MCP server](https://glama.ai/mcp/servers/caseSHY/AI-CLI/badges/card.svg)](https://glama.ai/mcp/servers/caseSHY/AI-CLI)
[![Glama Score](https://glama.ai/mcp/servers/caseSHY/AI-CLI/badges/score.svg)](https://glama.ai/mcp/servers/caseSHY/AI-CLI/score)
[![PyPI](https://img.shields.io/pypi/v/aicoreutils)](https://pypi.org/project/aicoreutils/)

[![CI](https://github.com/caseSHY/AI-CLI/actions/workflows/ci.yml/badge.svg)](https://github.com/caseSHY/AI-CLI/actions/workflows/ci.yml)
> **Glama 92%** | TDQS A 级 (均值 4.6) | 114 工具全部 A 级 | CI 全平台通过

> ⚠️ **Stability**: This project is actively evolving. While the JSON output schema and MCP tool interface are stable, internal CLI argument parsing and per-command flags may change. 阅读 [稳定性说明](#稳定性和-semver) 了解详情。

🤖 MCP 目录已收录：**Glama** · **ModelScope** · **awesome-mcp-servers**

## 中文说明

AICoreUtils 是一个面向 LLM Agent 的 JSON 优先命令行工具包原型。它参考
GNU Coreutils 的常用命令，但不是完整的 GNU 兼容替代品。

项目目标是给机器调用方提供确定、低噪音、易解析的 CLI 接口：

- 默认输出 JSON
- 错误以 JSON 写入 stderr
- 退出码语义稳定
- 修改文件的命令支持 `--dry-run`
- 需要管道组合时显式使用 `--raw`

### 快速开始

```bash
pip install aicoreutils
aicoreutils schema --pretty
aicoreutils ls . --limit 20
aicoreutils rm build --recursive --dry-run
```

### 🤖 Claude Desktop / MCP 集成

一行配置，让 Claude 直接操作你的文件系统：

编辑 Claude Desktop 配置文件（[详细说明 →](project/docs/guides/INTEGRATION_CLAUDE_DESKTOP.md)）：

| 系统 | 配置文件 |
|------|---------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": ["-m", "aicoreutils.mcp_server"]
    }
  }
}
```

重启 Claude Desktop，然后对它说：

> "列出项目里所有 Python 文件，统计代码行数"

Claude 自动调用 `aicoreutils ls` + `aicoreutils wc`，全程 JSON 交互。

更多集成方式：`aicoreutils tool-list --format openai` 输出 OpenAI Function Calling 格式，可直接用于任意 Agent 框架。

> ⚠️ **安全提示**：生产环境建议以最低权限运行。
> ```bash
> aicoreutils-mcp --read-only                           # 只读模式
> aicoreutils-mcp --deny-command rm --deny-command shred  # 禁止危险命令
> ```
> 详见 [生产安全部署指南 →](project/docs/guides/PRODUCTION_SECURITY.md)

### 🤖 AI IDE 集成

在 Cursor / Windsurf / Continue.dev 中直接使用 aicoreutils：[AI IDE 集成指南 →](project/docs/guides/INTEGRATION_AI_IDE.md)

```json
// ~/.cursor/mcp.json
{ "mcpServers": { "aicoreutils": { "command": "python", "args": ["-m", "aicoreutils.mcp_server"] } } }
```

🔗 更多：Claude Desktop 集成 | [AI IDE 集成](project/docs/guides/INTEGRATION_AI_IDE.md) | [Agent 任务示例](project/examples/AGENT_TASKS.md) | [LangChain 包装器](project/examples/langchain_wrapper.py)

### 运行测试

```powershell
# 推荐主入口（pytest，含 Hypothesis property-based 测试和 GNU 对照测试）
python -m pytest project/tests/ -v --tb=short

# Legacy 入口（unittest，部分运行器）
python -m unittest discover -s project/tests -v
```

### 项目结构

```text
.
|-- src/aicoreutils/        # Python 包源码
|-- .github/               # CI、Copilot 指令和开发脚本
|-- pyproject.toml         # 包元数据和构建配置
|-- README.md              # 项目入口
`-- project/               # 项目附属资源
    |-- tests/             # 子进程级行为测试
    |-- docs/              # 文档入口和分类文档目录
    |   |-- reference/     # 协议、命令面和安全生产契约
    |   |-- guides/        # 使用指南
    |   |-- audits/        # 兼容性和质量审计
    |   |-- development/   # 测试和开发说明
    |   |-- status/        # 当前项目状态（唯一权威来源）
    |   |-- analysis/      # 项目分析日志（历史归档）
    |   |-- agent-guides/  # AI 辅助编码与文档治理规则
    |   `-- reports/       # 测试报告等生成/归档文档
    |-- vendor/gnu-coreutils/  # 本地上游源码缓存，默认被 Git 忽略
    `-- AGENTS.md          # 仓库级 Agent 入口规则
```

### 文档

- [文档索引](project/docs/README.md)
- [当前项目状态](project/docs/status/CURRENT_STATUS.md) ← 权威状态来源
- [Agent 协议与示例](project/docs/reference/AGENTUTILS.md)
- [安全模型](project/docs/reference/SECURITY_MODEL.md)
- [中英文使用说明](project/docs/guides/USAGE.zh-CN.en.md)
- [GNU Coreutils 兼容性审计](project/docs/audits/GNU_COMPATIBILITY_AUDIT.md)
- [测试说明](project/docs/development/TESTING.md)
- [WSL 本地 CI](project/docs/development/WSL_CI.md)
- [文档治理规则](project/docs/agent-guides/DOC_GOVERNANCE_RULES.md)
- [事实传播矩阵](project/docs/agent-guides/FACT_PROPAGATION_MATRIX.md)

### 发布状态

当前实现：`aicoreutils schema` 中登记 114 个 CLI 命令（含 `tool-list` 等 Agent 元命令）。

重要限制：本项目是受 GNU Coreutils 启发的 Agent 友好子集，不是完整的
GNU Coreutils 克隆。

---

## English

AICoreUtils is a JSON-first command-line toolkit prototype for LLM agents. It is
inspired by common GNU Coreutils commands, but it is not a complete GNU-compatible
replacement.

The goal is a deterministic, low-noise interface for machine callers:

- JSON output by default
- JSON errors on stderr
- Stable semantic exit codes
- `--dry-run` for mutation commands
- Explicit `--raw` output for pipeline composition

### Quick Start

```bash
pip install aicoreutils
aicoreutils schema --pretty
aicoreutils ls . --limit 20
aicoreutils rm build --recursive --dry-run
```

### 🤖 Claude Desktop / MCP Integration

One config line to let Claude operate your filesystem:

Edit Claude Desktop config ([full guide →](project/docs/guides/INTEGRATION_CLAUDE_DESKTOP.md)):

| OS | Config File |
|----|------------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": ["-m", "aicoreutils.mcp_server"]
    }
  }
}
```

Restart Claude Desktop, then ask:

> "List all Python files in the project and count lines of code"

Claude calls `aicoreutils ls` + `aicoreutils wc` automatically.

For other frameworks: `aicoreutils tool-list --format openai` outputs OpenAI Function Calling format directly.

> ⚠️ **Security**: Run with least privilege in production.
> ```bash
> aicoreutils-mcp --read-only                           # Read-only mode
> aicoreutils-mcp --deny-command rm --deny-command shred  # Block dangerous commands
> ```
> See [Production Security Guide →](project/docs/guides/PRODUCTION_SECURITY.md)

### Run tests

```powershell
# Recommended primary entry (pytest, includes Hypothesis property-based and GNU differential tests)
python -m pytest project/tests/ -v --tb=short

# Legacy entry (unittest, partial runner)
python -m unittest discover -s project/tests -v
```

### Project Layout

```text
.
|-- src/aicoreutils/        # Python package
|-- .github/               # CI, Copilot instructions and development scripts
|-- pyproject.toml         # package metadata and build config
|-- README.md              # project entry point
`-- project/               # project collateral
    |-- tests/             # subprocess-level behavior tests
    |-- docs/              # documentation index and categorized docs
    |   |-- reference/     # protocol, command-surface and security contracts
    |   |-- guides/        # usage guides
    |   |-- audits/        # compatibility and quality audits
    |   |-- development/   # testing and development notes
    |   |-- status/        # current project status (single authoritative source)
    |   |-- analysis/      # project analysis logs (historical archive)
    |   |-- agent-guides/  # AI coding assistant and docs governance rules
    |   `-- reports/       # test reports and archived generated docs
    |-- vendor/gnu-coreutils/  # local upstream source cache, ignored by Git by default
    `-- AGENTS.md          # repository-level agent entry rules
```

### Documentation

- [Documentation index](project/docs/README.md)
- [Current project status](project/docs/status/CURRENT_STATUS.md) ← authoritative status source
- [Agent protocol and examples](project/docs/reference/AGENTUTILS.md)
- [Security model](project/docs/reference/SECURITY_MODEL.md)
- [Chinese/English user guide](project/docs/guides/USAGE.zh-CN.en.md)
- [GNU Coreutils compatibility audit](project/docs/audits/GNU_COMPATIBILITY_AUDIT.md)
- [Testing guide](project/docs/development/TESTING.md)
- [WSL local CI](project/docs/development/WSL_CI.md)
- [Documentation governance rules](project/docs/agent-guides/DOC_GOVERNANCE_RULES.md)
- [Fact propagation matrix](project/docs/agent-guides/FACT_PROPAGATION_MATRIX.md)

### Release Status

Current implementation: 114 CLI commands in `aicoreutils schema` (including agent-native meta-commands like `tool-list`).

Important limitation: this project is an agent-friendly subset inspired by GNU
Coreutils, not a full GNU Coreutils clone.

### 稳定性和 SemVer

aicoreutils 从 v1.0.0 起采用语义化版本控制，承诺如下：

- **Patch (1.0.x)**：修复 bug、改进错误消息、补充文档。JSON 输出结构不变。
- **Minor (1.x.0)**：新增命令、新增参数。已有命令的 JSON 输出结构保持向后兼容。
- **Major (x.0.0)**：破坏性变更 — JSON schema 变化、命令重命名、MCP tool schema 变化。

⚠️ 当前状态：项目仍在活跃开发中。CLI 内部参数解析和 per-command flag 可能因 argparse 重构频繁变化，但 JSON envelope（`ok`, `result`, `error`, `command`, `version`）和 MCP tool schema 是稳定的。生产使用前请固定版本号 (`pip install aicoreutils==1.1.0`)。
