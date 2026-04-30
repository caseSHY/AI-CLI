# 安全模型 / Security Model

## 中文说明

安全策略优先于 GNU 行为兼容。当安全要求与 GNU Coreutils 原生行为冲突时，agentutils 选择安全。

### 1. Sandbox 边界

agentutils 对所有写入、删除、截断、安装类命令强制执行 **cwd 边界校验**。

**规则**：
- 目标路径必须位于当前工作目录（cwd）内（解析符号链接后的真实路径）。
- 相对路径遍历（`../outside/file`）→ 拒绝（exit code 8, `unsafe_operation`）。
- 绝对路径（`C:\outside\file` 或 `/outside/file`）→ 拒绝（exit code 8）。
- 符号链接/junction 指向 cwd 外 → 拒绝（`resolve_path` 解析真实路径后校验）。

**例外**：用户通过 `--allow-outside-cwd` 显式授权可以绕过此限制。

**覆盖的命令**：
`rm`, `tee`, `truncate`, `install`, `ginstall`, `dd`, `cp`, `mv`, `shred`, `mkdir`, `touch`, `ln`, `link`, `chmod`, `chown`, `chgrp`, `mktemp`, `mkfifo`, `mknod`, `rmdir`, `unlink`

### 2. 路径安全策略

| 路径类型 | 策略 |
|---|---|
| 相对路径 (cwd 内) | ✅ 允许 |
| 相对路径遍历 (`../`) | ❌ 拒绝（exit 8） |
| 绝对路径 (cwd 内) | ✅ 允许 |
| 绝对路径 (cwd 外) | ❌ 拒绝（exit 8） |
| 符号链接 (目标在 cwd 内) | ✅ 允许（解析后校验） |
| 符号链接 (目标在 cwd 外) | ❌ 拒绝（exit 8） |
| Windows junction | ❌ 拒绝（解析后校验，同 symlink） |
| 硬链接 (目标在 cwd 外) | ❌ 拒绝 |
| UNC 路径 | ❌ 拒绝 |
| Extended path | ❌ 拒绝 |
| Drive-relative path | ❌ 拒绝（解析为绝对路径后校验） |

### 3. 文件操作安全

**dry-run 规则**：所有 mutating 命令支持 `--dry-run`，输出计划执行的操作（JSON），不产生任何文件系统副作用。

**覆盖保护**：默认拒绝覆盖已存在的目标文件（exit code 6），需要 `--allow-overwrite` 显式授权。

**危险删除保护**：`dangerous_delete_target()` 拒绝删除根目录、用户家目录、当前工作目录、关键系统目录。

### 4. 危险命令门控

| 命令 | 门控参数 | 默认行为 |
|---|---|---|
| `shred` | `--allow-destructive` | 拒绝真实销毁（exit 8） |
| `kill` | `--allow-signal` | dry-run 模式 |
| `nice` | （去掉 `--dry-run`） | dry-run 模式 |
| `nohup` | （去掉 `--dry-run`） | dry-run 模式 |
| `chroot` | `--allow-chroot` | dry-run 模式 |
| `chcon` | `--allow-context` | dry-run 模式 |
| `runcon` | `--allow-context` | dry-run 模式 |
| `stty` | `--allow-change` | dry-run 模式 |
| `stdbuf` | — | 有界子进程捕获，不等同 GNU LD_PRELOAD |

### 5. 退出码

| 退出码 | 语义 | 说明 |
|---|---|---|
| 0 | `ok` | 成功 |
| 1 | `predicate_false` / `general_error` | 谓词为假或一般错误 |
| 2 | `usage` | 参数或用法错误 |
| 3 | `not_found` | 路径不存在 |
| 4 | `permission_denied` | 权限不足 |
| 5 | `invalid_input` | 输入无效 |
| 6 | `conflict` | 目标冲突 |
| 7 | `partial_failure` | 部分失败 |
| **8** | **`unsafe_operation`** | **被安全策略阻止** |
| 10 | `io_error` | I/O 错误 |

### 6. 测试要求

每个 mutating command 必须通过以下安全测试：

1. **路径遍历拒绝**：`../outside` / 绝对路径被拒绝（exit 8）。
2. **dry-run 零副作用**：`--dry-run` 不产生文件变更。
3. **危险命令默认拒绝**：无 `--allow-*` 时被拒绝。
4. **符号链接逃逸**：symlink 指向 cwd 外被拒绝（Unix CI 环境）。
5. **覆盖保护**：已存在目标文件默认拒绝。

### 7. 已知限制

| 限制 | 说明 |
|---|---|
| Windows symlink | Windows 开发环境默认无 symlink 创建权限，相关测试跳过。Ubuntu CI 上应验证。 |
| GNU 完整兼容 | 安全策略优先于 GNU 行为兼容。 |
| 平台差异 | `os.name == "nt"` 和 POSIX 的行为差异在代码中以 `try/except` 防御。 |

---

## English

Security policy takes precedence over GNU behavioral compatibility.

---

## 1. Sandbox 边界 / Sandbox Boundary

agentutils 对所有写入、删除、截断、安装类命令强制执行 **cwd 边界校验**。

**规则**：
- 目标路径必须位于当前工作目录（cwd）内（解析符号链接后的真实路径）。
- 相对路径遍历（`../outside/file`）→ 拒绝（exit code 8, `unsafe_operation`）。
- 绝对路径（`C:\outside\file` 或 `/outside/file`）→ 拒绝（exit code 8）。
- 符号链接/junction 指向 cwd 外 → 拒绝（`resolve_path` 解析真实路径后校验）。

**例外**：用户通过 `--allow-outside-cwd` 显式授权可以绕过此限制。

**覆盖的命令**：
`rm`, `tee`, `truncate`, `install`, `ginstall`, `dd`, `cp`, `mv`, `shred`, `mkdir`, `touch`, `ln`, `link`, `chmod`, `chown`, `chgrp`, `mktemp`, `mkfifo`, `mknod`, `rmdir`, `unlink`

---

## 2. 路径安全策略 / Path Security Policy

| 路径类型 | 策略 |
|---|---|
| 相对路径 (cwd 内) | ✅ 允许 |
| 相对路径遍历 (`../`) | ❌ 拒绝（exit 8） |
| 绝对路径 (cwd 内) | ✅ 允许 |
| 绝对路径 (cwd 外) | ❌ 拒绝（exit 8） |
| 符号链接 (目标在 cwd 内) | ✅ 允许（解析后校验） |
| 符号链接 (目标在 cwd 外) | ❌ 拒绝（exit 8） |
| Windows junction | ❌ 拒绝（解析后校验，同 symlink） |
| 硬链接 (目标在 cwd 外) | ❌ 拒绝 |
| UNC 路径 (`\\server\share\...`) | ❌ 拒绝 |
| Extended path (`\\?\C:\...`) | ❌ 拒绝 |
| Drive-relative path (`C:file`) | ❌ 拒绝（解析为绝对路径后校验） |

---

## 3. 文件操作安全 / File Operation Safety

### 3.1 dry-run 规则

所有 mutating 命令支持 `--dry-run`：
- 输出计划执行的操作（JSON）。
- **不产生任何文件系统副作用**。
- `--dry-run` 输出与实际执行输出格式一致。

### 3.2 覆盖保护 / Overwrite Protection

- 默认拒绝覆盖已存在的目标文件（exit code 6, `conflict`）。
- 需要 `--allow-overwrite` 显式授权。

### 3.3 危险删除保护 / Dangerous Delete Protection

- `dangerous_delete_target()` 拒绝删除：根目录 `/`、用户家目录 `~`、当前工作目录、关键系统目录。
- `rm --recursive` 在删除目录前校验不在 cwd 外。

---

## 4. 危险命令门控 / Dangerous Command Gates

| 命令 | 门控参数 | 默认行为 |
|---|---|---|
| `shred` | `--allow-destructive` | 拒绝真实销毁（exit 8） |
| `kill` | `--allow-signal` | dry-run 模式（不发送信号） |
| `nice` | （去掉 `--dry-run`） | dry-run 模式（不执行） |
| `nohup` | （去掉 `--dry-run`） | dry-run 模式（不执行） |
| `chroot` | `--allow-chroot` | dry-run 模式（不执行） |
| `chcon` | `--allow-context` | dry-run 模式（不修改） |
| `runcon` | `--allow-context` | dry-run 模式（不执行） |
| `stty` | `--allow-change` | dry-run 模式（不修改） |
| `stdbuf` | — | 有界子进程捕获，不等同 GNU LD_PRELOAD |

---

## 5. 退出码 / Exit Codes

| 退出码 | 语义 | 说明 |
|---|---|---|
| 0 | `ok` | 成功 |
| 1 | `predicate_false` / `general_error` | 谓词为假或一般错误 |
| 2 | `usage` | 参数或用法错误 |
| 3 | `not_found` | 路径不存在 |
| 4 | `permission_denied` | 权限不足 |
| 5 | `invalid_input` | 输入无效 |
| 6 | `conflict` | 目标冲突（如文件已存在） |
| 7 | `partial_failure` | 部分失败 |
| **8** | **`unsafe_operation`** | **被安全策略阻止** |
| 10 | `io_error` | I/O 错误 |

---

## 6. 测试要求 / Testing Requirements

每个 mutating command 必须通过以下安全测试：

1. **路径遍历拒绝**：`../outside` / 绝对路径被拒绝（exit 8）。
2. **dry-run 零副作用**：`--dry-run` 不产生文件变更。
3. **危险命令默认拒绝**：无 `--allow-*` 时被拒绝。
4. **符号链接逃逸**：symlink 指向 cwd 外被拒绝（Unix CI 环境）。
5. **覆盖保护**：已存在目标文件默认拒绝。

---

## 7. 已知限制 / Known Limitations

| 限制 | 说明 |
|---|---|
| Windows symlink | Windows 开发环境默认无 symlink 创建权限，相关测试跳过。Ubuntu CI 上应验证。 |
| GNU 完整兼容 | 安全策略优先于 GNU 行为兼容。例如 `rm` 在 GNU 中可删除任意路径，agentutils 限制在 cwd 内。 |
| 平台差异 | `os.name == "nt"` 和 POSIX 的行为差异在代码中以 `try/except` 防御。 |
