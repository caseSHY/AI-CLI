# Quickstart / 快速开始

## 中文

### 安装

```bash
pip install aicoreutils
```

零依赖，仅需 Python >= 3.11。

### 第一个命令

```bash
aicoreutils ls .
```

输出 JSON 信封：

```json
{
  "ok": true,
  "tool": "aicoreutils",
  "version": "1.2.3",
  "command": "ls",
  "result": { "entries": [...] },
  "warnings": []
}
```

### 理解 JSON 信封

- **`ok: true`** → 成功，结果在 `result` 中
- **`ok: false`** → 失败，错误在 `error` 中，写入 stderr
- `--raw` 绕过信封，直接输出纯文本（管道组合用）

### MCP 模式

启动 MCP server：

```bash
aicoreutils-mcp --read-only
```

在 Claude Desktop 的 `claude_desktop_config.json` 中配置：

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "aicoreutils-mcp",
      "args": ["--read-only"]
    }
  }
}
```

三条安全模式：
- `--read-only`：只读命令
- `--profile workspace-write`：工作区读写
- `--profile explicit-danger`：全部命令（需显式授权危险命令）

### 常用命令速览

| 场景 | 命令 |
|---|---|
| 看目录 | `aicoreutils ls . --recursive` |
| 读文件 | `aicoreutils cat README.md --max-bytes 4096` |
| 文本搜索 | `aicoreutils grep pattern file.txt` |
| 统计行数 | `aicoreutils wc file.txt` |
| 排序 | `aicoreutils sort file.txt` |
| 发现命令 | `aicoreutils catalog --search keyword` |
| 查看 schema | `aicoreutils schema --pretty` |

### 下一步

- [完整安全模型](./reference/SECURITY_MODEL.md)
- [生产部署指南](./guides/PRODUCTION_SECURITY.md)
- [兼容性承诺](./COMPATIBILITY.md)

---

## English

### Install

```bash
pip install aicoreutils
```

Zero dependencies. Requires Python >= 3.11.

### Your First Command

```bash
aicoreutils ls .
```

Outputs a JSON envelope:

```json
{
  "ok": true,
  "tool": "aicoreutils",
  "version": "1.2.3",
  "command": "ls",
  "result": { "entries": [...] },
  "warnings": []
}
```

### Understanding the JSON Envelope

- **`ok: true`** → success, result in `result`
- **`ok: false`** → failure, error in `error`, written to stderr
- `--raw` bypasses the envelope for plain-text pipeline composition

### MCP Mode

Start the MCP server:

```bash
aicoreutils-mcp --read-only
```

Configure in Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "aicoreutils": {
      "command": "aicoreutils-mcp",
      "args": ["--read-only"]
    }
  }
}
```

Three security modes:
- `--read-only`: read-only commands
- `--profile workspace-write`: workspace read/write
- `--profile explicit-danger`: all commands (dangerous commands require explicit `--allow-*` flags)

### Quick Reference

| Task | Command |
|---|---|
| List directory | `aicoreutils ls . --recursive` |
| Read file | `aicoreutils cat README.md --max-bytes 4096` |
| Count lines | `aicoreutils wc file.txt` |
| Sort | `aicoreutils sort file.txt` |
| Discover commands | `aicoreutils catalog --search keyword` |
| View schema | `aicoreutils schema --pretty` |

### Next Steps

- [Security Model](./reference/SECURITY_MODEL.md)
- [Production Deployment Guide](./guides/PRODUCTION_SECURITY.md)
- [Compatibility Policy](./COMPATIBILITY.md)
