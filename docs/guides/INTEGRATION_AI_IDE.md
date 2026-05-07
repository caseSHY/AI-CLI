# Cursor / Windsurf / Continue.dev MCP 集成指南

## 中文说明

aicoreutils 通过 MCP 协议向 AI 编程助手暴露 114 个系统命令，
让 Agent 能直接 ls、cat、grep、chmod 而不用猜 shell 输出格式。

## English

This guide shows how to connect aicoreutils MCP server to AI coding assistants.
All 114 commands become available as structured tools with JSON output.

---

### Cursor

编辑 Cursor 的 MCP 配置文件（`~/.cursor/mcp.json`）：

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": ["-m", "aicoreutils.mcp_server", "--profile", "readonly"]
    }
  }
}
```

重启 Cursor，打开 AI 面板说：

> "List all Python files in this project and count lines"

Cursor 自动调用 `aicoreutils ls` + `aicoreutils wc`。

---

### Windsurf

编辑 `~/.codeium/windsurf/mcp.json`：

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": ["-m", "aicoreutils.mcp_server", "--profile", "readonly"]
    }
  }
}
```

---

### Continue.dev

编辑 `~/.continue/config.json`，在 `experimental.mcpServers` 中添加：

```json
{
  "experimental": {
    "mcpServers": [
      {
        "name": "aicoreutils",
        "command": "python",
        "args": ["-m", "aicoreutils.mcp_server", "--profile", "readonly"]
      }
    ]
  }
}
```

---

### 常见 Agent 任务示例

```
"Read README.md and tell me the project version" → aicoreutils cat README.md
"Create a directory for logs" → aicoreutils mkdir logs --parents
"Check if tests directory exists" → aicoreutils test tests --is_dir
"List all JSON files recursively" → aicoreutils ls . --recursive --limit 50
"Count lines in all Python files" → aicoreutils wc src/ --recursive
"Find files larger than 1MB" → aicoreutils du src/ --recursive
"Check disk space before build" → aicoreutils df
"Get file permissions" → aicoreutils stat pyproject.toml
"Format current time" → aicoreutils date
"Verify file checksums" → aicoreutils sha256sum dist/*
```

### 安全特性

Agent 请求的所有修改操作（rm、chmod、cp、mv 等）都默认安全：
- 默认集成示例使用 `--profile readonly`
- 需要创建文件或目录时改用 `--profile workspace-write`
- `--dry-run` 预览操作不执行
- cwd 沙箱防止越界访问
- 覆盖保护需显式 `--allow-overwrite`
- `shred` 需 `--allow-destructive` 确认
