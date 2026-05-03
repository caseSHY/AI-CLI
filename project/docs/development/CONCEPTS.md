# 关键概念 / Key Concepts

> aicoreutils 开发者参考文档。解释为什么这样设计，以及核心概念的含义。

## 中文说明

## 1. JSON 信封协议 (JSON Envelope Protocol)

aicoreutils 的全部 I/O 遵循单一格式：

```
成功 → stdout: {"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}
失败 → stderr: {"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}
```

**设计决策**：Agent 不需要解析多种输出格式。stdout 永远是成功 JSON，stderr 永远是错误 JSON。唯一的例外是 `--raw` 模式（见下文）。

**warnings 字段**：非致命警告列表，如 "部分目录因权限不足被跳过"。Agent 应始终检查此字段。

---

## 2. --raw 模式

`--raw` 绕过 JSON 信封，直接输出原始字节流到 stdout。这用于：

- 管道组合：`aicoreutils sort data.txt --raw | aicoreutils head -n 5`
- 二进制输出：`aicoreutils base64 --decode payload.txt --raw > output.bin`

**警告**：`--raw` 模式下，错误仍然以 JSON 写入 stderr，但成功时不产生 JSON 信封。

---

## 3. --dry-run 语义

所有 mutating 命令（rm, cp, mv, shred, tee, truncate 等）支持 `--dry-run`：

- 执行所有校验（路径存在、权限、沙箱边界）。
- 输出计划的操作但**不产生任何文件系统副作用**。
- 返回值中 `dry_run: true` 标记。

**设计决策**：Agent 应该先 dry-run 再真实执行，这是 Agent 安全调用模式的核心。

---

## 4. 沙箱边界模型 (Sandbox / cwd boundary)

aicoreutils 默认将所有写入/删除操作限制在当前工作目录 (cwd) 内：

- `../outside` → 拒绝（exit code 8, `unsafe_operation`）
- 绝对路径指向 cwd 外 → 拒绝
- 符号链接指向 cwd 外 → 解析真实路径后拒绝

**绕过**：`--allow-outside-cwd` 显式授权。但以下保护不可绕过：
- 删除文件系统根 (C:\\ 或 /)
- 删除用户家目录
- 删除当前工作目录

---

## 5. 优先级模型 (P0-P3)

| 优先级 | 类别 | 命令数 | 说明 |
|--------|------|--------|------|
| P0 | read_observe_and_decide | ~17 | Agent 必须先观察再决策 |
| P1 | mutate_files_safely | ~20 | 安全修改，必须带 dry-run |
| P2 | transform_and_compose_text | ~33 | 管道组合和文本处理 |
| P3 | system_context_and_execution | ~44 | 系统信息、有界执行 |

**设计决策**：优先级指导 Agent 的调用顺序和依赖声明。P0 命令是无副作用的，可以任意调用。

---

## 6. 退出码语义

| 码 | 语义 | 典型场景 |
|----|------|----------|
| 0 | ok | 成功 |
| 1 | predicate_false | test/\[ 判断为假 |
| 2 | usage | 参数错误 |
| 3 | not_found | 路径不存在 |
| 4 | permission_denied | 权限不足 |
| 5 | invalid_input | 输入无效（如 base64 解码失败） |
| 6 | conflict | 目标冲突（覆盖未授权） |
| 7 | partial_failure | 部分成功 |
| 8 | unsafe_operation | 被安全策略阻止 |
| 10 | io_error | I/O 错误 |

**设计决策**：8 是安全保留码。Agent 收到 exit 8 时应立即放弃当前操作路径，不应尝试绕过。

---

## 7. 插件系统 (Plugin System)

第三方可通过 `aicoreutils_*` 命名空间包扩展命令：

```python
# aicoreutils_extra/__init__.py
COMMANDS = {
    "mycommand": lambda args: {"ok": True, "result": "hello"},
}
```

或编程式注册：

```python
from aicoreutils.plugins import register_plugin_command
register_plugin_command("mycommand", my_func, priority="P3")
```

**线程安全**：PluginRegistry 是不可变容器。每次注册返回新实例。

---

## 8. 流式输出 (NDJSON)

`--stream` 模式使用 NDJSON（newline-delimited JSON）逐行输出条目：

```json
{"type":"item","path":"file1.txt",...}
{"type":"item","path":"file2.txt",...}
{"ok":true,...,"stream":true,"count":1000,"truncated":false,"summary":{...}}
```

**优势**：Agent 可以逐行解析，无需在内存中保存整个响应。适用于大目录遍历。

---

## 9. 本地开发快速启动

```powershell
git clone <repo-url>
cd AIBaseCLI-ABC
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# 运行测试
$env:PYTHONPATH = "src"
python -m pytest tests/ -v --tb=short

# 快速验证（跳过 property-based 和 GNU 对照）
python -m pytest tests/ -v --tb=short -k "not (property_based or Hypothesis or Gnu or gnu_differential)"
```

---

## 10. 项目结构（重构后）

```
src/aicoreutils/
├── core/                 # 基础层（无业务逻辑）
│   ├── config.py         # AgentConfig 不可变配置
│   ├── constants.py      # 集中化默认值
│   ├── envelope.py       # JSON 信封
│   ├── exceptions.py     # AgentError
│   ├── exit_codes.py     # 退出码映射
│   ├── path_utils.py     # 安全路径操作
│   ├── plugin_registry.py # 不可变插件注册表
│   ├── sandbox.py        # 沙箱安全
│   └── stream.py         # NDJSON 流式输出
├── protocol/             # 共享工具函数
│   ├── _io.py, _hashing.py, _text.py, ...
├── parser/               # CLI 解析
│   └── _parser.py        # build_parser() + 命令分发
├── commands/             # 命令实现
│   ├── fs/               # 文件系统命令（ls, cat, cp, rm...）
│   ├── text/             # 文本处理命令（sort, cut, tr...）
│   └── system/           # 系统命令（date, env, kill...）
├── catalog.py            # 命令优先级目录
├── plugins.py            # 插件发现与注册
└── async_interface.py    # 异步调用接口
```

---

## English

> Developer reference for aicoreutils. Explains why things are designed this way.

### 1. JSON Envelope Protocol

All aicoreutils I/O follows a single format:

```
Success → stdout: {"ok":true, "tool":"aicoreutils", "version":"...", "command":"...", "result":..., "warnings":[...]}
Failure → stderr: {"ok":false, "tool":"aicoreutils", "version":"...", "command":"...", "error":{"code":"...", "message":"..."}}
```

**Design rationale**: Agents shouldn't parse multiple output formats. stdout is always success JSON, stderr is always error JSON. The only exception is `--raw` mode.

**warnings field**: Non-fatal warnings list, e.g., "some directories skipped due to permission". Agents should always check this field.

---

### 2. --raw Mode

`--raw` bypasses the JSON envelope and writes raw bytes directly to stdout. Used for:

- Pipeline composition: `aicoreutils sort data.txt --raw | aicoreutils head -n 5`
- Binary output: `aicoreutils base64 --decode payload.txt --raw > output.bin`

**Warning**: In `--raw` mode, errors are still written as JSON to stderr, but success produces no JSON envelope.

---

### 3. --dry-run Semantics

All mutating commands (rm, cp, mv, shred, tee, truncate, etc.) support `--dry-run`:

- All validations run (path existence, permissions, sandbox boundaries).
- Planned operations are output but **no filesystem side effects occur**.
- Return value includes `dry_run: true` flag.

**Design rationale**: Agents should dry-run first, then execute. This is the core of the Agent safety pattern.

---

### 4. Sandbox / cwd Boundary

aicoreutils confines all write/delete operations to the current working directory (cwd) by default:

- `../outside` → rejected (exit code 8, `unsafe_operation`)
- Absolute paths outside cwd → rejected
- Symlinks pointing outside cwd → resolved real path then rejected

**Override**: `--allow-outside-cwd` for explicit authorization. The following are never bypassable:
- Deleting filesystem root (C:\\ or /)
- Deleting home directory
- Deleting current working directory

---

### 5. Priority Model (P0-P3)

| Priority | Category | Count | Description |
|----------|----------|-------|-------------|
| P0 | read_observe_and_decide | ~17 | Agent must observe before deciding |
| P1 | mutate_files_safely | ~20 | Safe mutations, must support dry-run |
| P2 | transform_and_compose_text | ~33 | Pipeline composition and text processing |
| P3 | system_context_and_execution | ~44 | System info, bounded execution |

**Design rationale**: Priority guides Agent call order and dependency declarations. P0 commands are side-effect-free and can be called freely.

---

### 6. Exit Code Semantics

| Code | Semantic | Typical scenario |
|------|----------|------------------|
| 0 | ok | Success |
| 1 | predicate_false | test/\[ evaluated as false |
| 2 | usage | Argument error |
| 3 | not_found | Path does not exist |
| 4 | permission_denied | Insufficient permissions |
| 5 | invalid_input | Invalid input (e.g., base64 decode failure) |
| 6 | conflict | Target conflict (overwrite not authorized) |
| 7 | partial_failure | Partial success |
| 8 | unsafe_operation | Blocked by security policy |
| 10 | io_error | I/O error |

**Design rationale**: 8 is the security-reserved code. Agent should immediately abandon the current path on exit 8, never retry.

---

### 7. Plugin System

Third-parties can extend commands via `aicoreutils_*` namespace packages:

```python
# aicoreutils_extra/__init__.py
COMMANDS = {
    "mycommand": lambda args: {"ok": True, "result": "hello"},
}
```

Or programmatic registration:

```python
from aicoreutils.plugins import register_plugin_command
register_plugin_command("mycommand", my_func, priority="P3")
```

**Thread safety**: PluginRegistry is an immutable container. Each registration returns a new instance.

---

### 8. NDJSON Streaming

`--stream` mode uses NDJSON (newline-delimited JSON) for line-by-line output:

```json
{"type":"item","path":"file1.txt",...}
{"type":"item","path":"file2.txt",...}
{"ok":true,...,"stream":true,"count":1000,"truncated":false,"summary":{...}}
```

**Advantage**: Agents can parse line-by-line without holding the entire response in memory. Ideal for large directory traversal.

---

### 9. Local Development Quick Start

```powershell
git clone <repo-url>
cd AIBaseCLI-ABC
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Run tests
$env:PYTHONPATH = "src"
python -m pytest tests/ -v --tb=short

# Quick verify (skip property-based and GNU differential)
python -m pytest tests/ -v --tb=short -k "not (property_based or Hypothesis or Gnu or gnu_differential)"
```

---

### 10. Project Structure (post-refactoring)

```
src/aicoreutils/
├── core/                 # Foundation layer (no business logic)
│   ├── config.py         # AgentConfig immutable config
│   ├── constants.py      # Centralized defaults
│   ├── envelope.py       # JSON envelopes
│   ├── exceptions.py     # AgentError
│   ├── exit_codes.py     # Exit code mapping
│   ├── path_utils.py     # Safe path operations
│   ├── plugin_registry.py # Immutable plugin registry
│   ├── sandbox.py        # Sandbox security
│   └── stream.py         # NDJSON streaming
├── protocol/             # Shared utility functions
│   ├── _io.py, _hashing.py, _text.py, ...
├── parser/               # CLI parsing
│   └── _parser.py        # build_parser() + dispatch
├── commands/             # Command implementations
│   ├── fs/               # File-system commands (ls, cat, cp, rm...)
│   ├── text/             # Text-processing commands (sort, cut, tr...)
│   └── system/           # System commands (date, env, kill...)
├── catalog.py            # Command priority catalog
├── plugins.py            # Plugin discovery & registration
└── async_interface.py    # Async call interface
```