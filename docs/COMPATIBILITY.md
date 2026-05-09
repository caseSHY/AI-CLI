# Compatibility Policy / 兼容性策略

## 中文

AICoreUtils 从 v1.1.2 开始遵循本兼容性策略。我们的目标是让 Agent 和外部工具可以安全地依赖 aicoreutils，不会因为小版本升级而意外 break。

### 稳定性承诺

| 项目 | 承诺级别 | 说明 |
|---|---|---|
| JSON envelope 结构 | **稳定** | `ok`, `tool`, `version`, `command`, `result`, `warnings`, `error` 字段只增不删 |
| 语义退出码 | **稳定** | 0-8 及 10 的语义保持不变（8 = unsafe_operation） |
| CLI 参数名 | **稳定** | `--raw`, `--limit`, `--max-bytes`, `--recursive` 等跨命令通用参数不会 rename |
| 命令名 | **稳定** | 109 个 GNU 兼容命令名保持不变 |
| 命令输出结构 | **渐进** | `result` 内部字段可能新增，但不删除已有字段 |
| MCP 协议 | **渐进** | JSON-RPC 2.0 协议不变，tool schema 字段只增不删 |

### 什么算 Breaking Change

以下变更视为 breaking change，只在主版本号升级时允许：

1. 删除或重命名 JSON envelope 的顶层字段（`ok`, `result`, `error`, `warnings`）
2. 修改语义退出码的数字值
3. 删除已发布的命令
4. 重命名 CLI 参数
5. 修改 MCP JSON-RPC 协议版本或请求/响应结构
6. 提高 Python 最低版本要求

### 弃用流程

当需要变更 CLI 参数或命令行为时：

1. **标记弃用**：在 JSON envelope 的 `warnings` 字段中增加弃用提示
2. **保留一个版本**：弃用项在弃用后的第一个次版本中仍然工作
3. **在主版本中移除**：弃用项在下一次主版本升级时删除

示例弃用警告：

```json
{
  "ok": true,
  "tool": "aicoreutils",
  "command": "some_cmd",
  "result": { ... },
  "warnings": [
    {
      "type": "deprecation",
      "message": "--old-flag is deprecated, use --new-flag instead.",
      "removal_version": "2.0.0"
    }
  ]
}
```

### 版本号规则

遵循 [Semantic Versioning](https://semver.org/)：

- **主版本（MAJOR）**：breaking change
- **次版本（MINOR）**：新功能（向后兼容）
- **修订版本（PATCH）**：bug 修复

---

## English

AICoreUtils follows this compatibility policy starting from v1.1.2. Our goal is to let agents and external tools safely depend on aicoreutils without breakage from minor upgrades.

### Stability Commitments

| Item | Level | Notes |
|---|---|---|
| JSON envelope structure | **Stable** | `ok`, `tool`, `version`, `command`, `result`, `warnings`, `error` fields are add-only |
| Semantic exit codes | **Stable** | 0-8 and 10 semantics are frozen (8 = unsafe_operation) |
| CLI argument names | **Stable** | `--raw`, `--limit`, `--max-bytes`, `--recursive` etc. will not be renamed |
| Command names | **Stable** | 109 GNU-compatible command names are frozen |
| Command output structure | **Evolving** | Fields inside `result` may be added but never removed |
| MCP protocol | **Evolving** | JSON-RPC 2.0 is frozen; tool schema fields are add-only |

### What Counts as a Breaking Change

The following are breaking changes, permitted only in major version bumps:

1. Removing or renaming JSON envelope top-level fields (`ok`, `result`, `error`, `warnings`)
2. Changing semantic exit code numeric values
3. Removing a published command
4. Renaming CLI arguments
5. Changing MCP JSON-RPC protocol version or request/response structure
6. Raising the minimum Python version

### Deprecation Process

When a CLI argument or command behavior needs to change:

1. **Mark deprecated**: Add a deprecation entry to the JSON envelope `warnings` field
2. **Keep for one version**: The deprecated item still works in the next minor version
3. **Remove in major version**: The deprecated item is removed at the next major version bump

Example deprecation warning:

```json
{
  "ok": true,
  "tool": "aicoreutils",
  "command": "some_cmd",
  "result": { ... },
  "warnings": [
    {
      "type": "deprecation",
      "message": "--old-flag is deprecated, use --new-flag instead.",
      "removal_version": "2.0.0"
    }
  ]
}
```

### Versioning

Follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: breaking change
- **MINOR**: new functionality (backward-compatible)
- **PATCH**: bug fixes
