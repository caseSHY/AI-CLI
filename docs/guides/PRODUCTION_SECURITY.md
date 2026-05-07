# 生产安全部署指南 / Production Security Guide

## 中文

AICoreUtils 设计为 AI Agent 用工具箱，接入 Claude Desktop、Cursor、Windsurf 等环境时，
**必须**以最小权限运行。本文档提供安全配置建议。

### 推荐配置

#### 最小权限：readonly profile

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

只读模式下，Agent 可读取文件、列表目录、统计行数，但**无法写入、删除或修改任何文件**。

#### 低风险工作区写入：workspace-write profile

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": ["-m", "aicoreutils.mcp_server", "--profile", "workspace-write"]
    }
  }
}
```

`workspace-write` 只允许 cwd 内的低风险写入命令，例如 `mkdir`、`touch`、`cp`、`tee`。它仍拒绝 `rm`、`shred`、`kill`、`timeout`、`nohup` 等 destructive 或 process-exec 命令。

#### 显式 allow-list

如果需要更窄的权限面，优先使用 allow-list，而不是全量暴露后再 deny：

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "python",
      "args": [
        "-m", "aicoreutils.mcp_server",
        "--allow-command", "ls",
        "--allow-command", "cat",
        "--allow-command", "wc"
      ]
    }
  }
}
```

`--deny-command` 仍可作为额外防线；deny list 优先级高于 allow-list。

### 工作目录选择

始终将 Agent 工作目录限定在项目目录内：

```json
// Claude Desktop config: 在 claude_desktop_config.json 同级目录运行
// Cursor: 在项目根目录打开工作区
```

aicoreutils 的 cwd sandbox 会拒绝所有 cwd 外的写入操作（exit code 8），无需额外配置。

### Docker 部署

```bash
# 构建
docker build -t aicoreutils .

# 只读 profile 运行
docker run --rm -v $(pwd):/workspace -w /workspace aicoreutils aicoreutils-mcp --profile readonly
```

### OS 级安全加强

- 使用专用系统用户运行 Agent
- 设置文件系统权限：Agent 用户只读项目目录
- 启用 SELinux / AppArmor 限制子进程执行
- 监控 Agent 进程的系统调用

---

## English

AICoreUtils is designed for AI agents. When connecting to Claude Desktop, Cursor,
Windsurf, or similar environments, it **must** run with least privilege.

### Recommended Configs

See the JSON examples above for:
- **Read-only profile** (`--profile readonly`)
- **Low-risk workspace writes** (`--profile workspace-write`)
- **Narrow allow-list** (`--allow-command ls --allow-command cat`)

Use allow-lists as the primary production control. `--deny-command` remains an additional defense and always takes priority.

### Working Directory

Always bind the agent's working directory to the project root. The cwd sandbox
rejects all writes outside the working directory with exit code 8.

### Docker

```bash
docker build -t aicoreutils .
docker run --rm -v $(pwd):/workspace -w /workspace aicoreutils aicoreutils-mcp --profile readonly
```

### OS-Level Hardening

- Run the agent under a dedicated system user
- Set filesystem permissions: agent user has read-only access to the project
- Enable SELinux/AppArmor to restrict subprocess execution
- Monitor agent process syscalls
