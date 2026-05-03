# Claude Desktop 集成 / Claude Desktop Integration

## 中文说明

使用 aicoreutils MCP Server 让 Claude Desktop 安全地操作你的文件系统。

### 配置步骤

1. 安装 aicoreutils：

```bash
pip install aicoreutils
```

2. 编辑 Claude Desktop 配置：

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

3. 重启 Claude Desktop，即可在对话中直接使用：

> "列出当前目录下的所有 Python 文件，统计代码行数"

Claude 会自动调用 `aicoreutils ls` + `aicoreutils wc`，输出结构化 JSON。

### 安全特性

- 所有修改命令默认 dry-run，需显式确认
- 沙箱保护：无法操作工作目录外的文件
- 危险命令（shred, kill, chroot 等）需 `--allow-*` 授权

---

## English

Let Claude Desktop safely operate your filesystem via aicoreutils MCP Server.

### Setup

1. Install:

```bash
pip install aicoreutils
```

2. Edit Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

3. Restart Claude Desktop. Ask:

> "List all Python files in my project and count total lines of code"

Claude calls `aicoreutils ls` + `aicoreutils wc` automatically.

### Safety

- All mutation commands default to dry-run
- Sandbox: cannot operate outside working directory
- Dangerous commands require explicit `--allow-*` flags
