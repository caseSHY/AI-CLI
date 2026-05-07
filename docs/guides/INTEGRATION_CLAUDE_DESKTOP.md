# Claude Desktop 集成 / Claude Desktop Integration

## 中文说明

使用 aicoreutils MCP Server 让 Claude Desktop 安全地操作你的文件系统。

### 配置步骤

1. 安装 aicoreutils：

```bash
pip install aicoreutils
```

2. 编辑 Claude Desktop 配置文件，路径因系统而异：

| 系统 | 配置文件位置 |
|------|-------------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

写入以下内容：

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

3. 重启 Claude Desktop，即可在对话中直接使用：

> "列出当前目录下的所有 Python 文件，统计代码行数"

Claude 会自动调用 `aicoreutils ls` + `aicoreutils wc`，输出结构化 JSON。

如果确实需要让 Claude 在工作区内创建文件或目录，把 profile 改成 `workspace-write`。不要在生产环境中无 profile 暴露全量工具。

### 安全特性

- 所有修改命令默认 dry-run，需显式确认
- 推荐 `--profile readonly`；需要低风险写入时使用 `--profile workspace-write`
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

2. Edit Claude Desktop config file, location varies by OS:

| OS | Config path |
|----|------------|
| **macOS** | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| **Windows** | `%APPDATA%\Claude\claude_desktop_config.json` |
| **Linux** | `~/.config/Claude/claude_desktop_config.json` |

Add the following:

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

3. Restart Claude Desktop. Ask:

> "List all Python files in my project and count total lines of code"

Claude calls `aicoreutils ls` + `aicoreutils wc` automatically.

If Claude must create files or directories inside the workspace, switch the profile to `workspace-write`. Do not expose the full tool surface without a profile in production.

### Safety

- All mutation commands default to dry-run
- Recommended profile is `--profile readonly`; use `--profile workspace-write` only for low-risk writes
- Sandbox: cannot operate outside working directory
- Dangerous commands require explicit `--allow-*` flags
