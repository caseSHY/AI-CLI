# 架构决策记录 / Architecture Decision Records (ADR)

## 中文说明

---

### ADR-001: JSON 优先而非 GNU 兼容输出

**状态**：已接受 | **日期**：2026-04 | **决策者**：agentutils 团队

#### 背景

agentutils 是为 LLM Agent 设计的 CLI 层，不是给人用的 shell。
人类导向的 CLI 输出（颜色、进度条、交互式提示、可变宽度列）对机器来说是噪音。
GNU Coreutils 以人类用户为目标。

#### 决策

agentutils 的所有输出默认为 JSON。--raw 标志显式绕过 JSON 用于管道组合。

#### 后果

- Agent 在 stdout 上收到确定性的结构化输出。
- 错误始终以 JSON 格式写入 stderr，即使使用 --raw 也是如此。
- GNU 行为兼容性是次要目标。

---

### ADR-002: 安全优先的沙箱而非 POSIX 兼容

**状态**：已接受 | **日期**：2026-04

#### 背景

LLM Agent 可能尝试路径遍历（../etc/passwd）、删除关键路径或覆盖重要文件。
GNU 工具默认允许这些操作（信任用户）。agentutils 不能信任 Agent。

#### 决策

所有 mutating 命令强制执行 cwd 边界。危险目标（文件系统根、家目录、cwd）
永远不可删除。覆盖保护默认为拒绝。

退出码 8（unsafe_operation）为安全阻止保留。

#### 后果

- Agent 必须使用 --allow-outside-cwd、--allow-overwrite 或 --allow-destructive 显式授权。
- 某些 GNU 用例不可行（没有标志的情况下删除 cwd 外的文件）。

---

### ADR-003: 零运行时依赖

**状态**：已接受 | **日期**：2026-04

#### 背景

Python 打包引入了供应链风险。每个依赖都是破坏性变更、CVE 和 LLM 沙箱环境
安装摩擦的潜在来源。

#### 决策

agentutils 没有强制运行时依赖。仅使用标准库。测试/开发依赖（pytest、hypothesis、
ruff、mypy）在 [project.optional-dependencies] 中。

#### 后果

- import agentutils 在任何 Python 3.11+ 安装上都能工作。
- 某些功能（Windows 上用户/组名称查找）优雅降级而非引入第三方包。
- 插件可以有自己的依赖。

---

### ADR-004: 语义化退出码（非 POSIX 标准）

**状态**：已接受 | **日期**：2026-04

#### 背景

POSIX 退出码是 0=成功、1=一般错误、2=误用、>128=信号。
这对于需要根据失败类型做出分支决策的 Agent 来说太粗糙了。

#### 决策

agentutils 定义了 10 个语义退出码（0-8、10）。码 8 为安全阻止保留。
码 9（kill 信号）被跳过，因为 Agent 不应发送信号。

映射在 core/exit_codes.py 中，每个 AgentError 携带一个语义码。

#### 后果

- Agent 可以按退出码分支：3=重试路径、4=请求权限、8=放弃路径。
- 对于码 5-8、10 不兼容 POSIX。

---

## English

# ADR-001: JSON-first over GNU-compatible output

**Status**: accepted | **Date**: 2026-04 | **Deciders**: agentutils team

## Context

agentutils is designed as a CLI layer for LLM agents, not human users.
Human-oriented CLI output (color, progress bars, interactive prompts,
variable-width columns) is noise for machines.  GNU Coreutils targets
humans first.

## Decision

All agentutils output is JSON by default.  `--raw` flag explicitly
bypasses JSON for pipeline composition.

## Consequences

- Agents receive deterministic, structured output on stdout.
- Errors are always JSON on stderr, even when `--raw` is used.
- GNU behavioral compatibility is a secondary goal.

---

# ADR-002: Security-first sandbox over POSIX compatibility

**Status**: accepted | **Date**: 2026-04

## Context

LLM agents may attempt path traversal (`../etc/passwd`), delete
critical paths, or overwrite important files.  GNU tools allow these
operations by design (trust the user).  agentutils cannot trust the
agent.

## Decision

All mutating commands enforce a cwd boundary.  Dangerous targets
(filesystem root, home, cwd) are never deletable.  Overwrite protection
defaults to deny.

Exit code 8 (`unsafe_operation`) is reserved for security blocks.

## Consequences

- Agent must use `--allow-outside-cwd`, `--allow-overwrite`, or
  `--allow-destructive` for explicit authorization.
- Some GNU use-cases are impossible (deleting files outside cwd without
  the flag).

---

# ADR-003: Zero runtime dependencies

**Status**: accepted | **Date**: 2026-04

## Context

Python packaging introduces supply-chain risk.  Every dependency is a
potential vector for breaking changes, CVEs, and install friction for
LLM sandbox environments.

## Decision

agentutils has zero mandatory runtime dependencies.  Only the standard
library is used.  Test/dev dependencies (pytest, hypothesis, ruff, mypy)
are in `[project.optional-dependencies]`.

## Consequences

- `import agentutils` works on any Python 3.11+ installation.
- Some functionality (user/group name lookup on Windows) degrades
  gracefully rather than pulling in third-party packages.
- Plugins may have their own dependencies.

---

# ADR-004: Semantic exit codes (not POSIX standard)

**Status**: accepted | **Date**: 2026-04

## Context

POSIX exit codes are 0=success, 1=general error, 2=misuse, >128=signal.
This is too coarse for an agent that needs to make branching decisions
based on failure types.

## Decision

agentutils defines 10 semantic exit codes (0-8, 10).  Code 8 is
reserved for security blocks.  Code 9 (kill signal) is skipped because
agents should not send signals.

The mapping is in `core/exit_codes.py` and every `AgentError` carries a
semantic code.

## Consequences

- Agents can branch on exit code: 3=retry path, 4=request permission,
  8=abandon path.
- Not POSIX-compatible for codes 5-8, 10.
