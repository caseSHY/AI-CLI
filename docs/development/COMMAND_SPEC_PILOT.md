# 命令规格注册表 / Command Spec Registry

## 中文说明

本文件记录 P4 架构治理的命令规格注册表。当前 parser 仍是运行时权威来源；`src/aicoreutils/command_specs.py` 已能为全部 parser 注册命令生成过渡 spec，并保留 `pwd`、`basename`、`seq` 三个手写 spec 作为未来 schema-first 迁移样板。

### 目标

- 证明命令名、稳定等级、风险等级、参数、handler、GNU 兼容说明可以由单一 spec 表达。
- 为后续生成 argparse、MCP schema、tool-list 和文档片段建立类型化数据结构。
- 在迁移前用审计脚本阻断全量过渡 spec、手写试点 spec 与当前 parser 的漂移。

### 检查命令

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_specs.py
```

### 当前范围

| 层级 | 范围 | 用途 |
|---|---|---|
| 全命令过渡 spec | 所有 parser 注册命令 | 审计全命令风险等级、handler、参数 dest 和基础说明。 |
| 手写试点 spec | `pwd`, `basename`, `seq` | 作为未来 schema-first 生成 argparse/MCP schema 的模板。 |

### 手写试点范围

| 命令 | 原因 | 当前状态 |
|---|---|---|
| `pwd` | 无参数，最小 spec 形状。 | spec 与 parser 一致性检查。 |
| `basename` | 有 positional、option、raw 输出。 | spec 与 parser 参数 dest 检查。 |
| `seq` | 有多参数和输出上限。 | spec 与风险等级检查。 |

### 下一步迁移门槛

只有满足以下条件，才能把 command spec 从 parser-derived 审计原型提升为生成源：

1. 试点命令的 CLI golden 输出不变。
2. MCP tools/list 输出不变，除非 release notes 明确说明。
3. `scripts/audit_command_specs.py`、`scripts/audit_command_matrix.py`、MCP server 测试全部通过。
4. 新 spec 字段能覆盖稳定等级、风险等级、参数说明、handler 和 GNU 兼容说明。

---

## English

This document records the command spec registry for P4 architecture governance. The current parser remains the runtime authority; `src/aicoreutils/command_specs.py` can now derive transitional specs for every parser-registered command and keeps three hand-written specs, `pwd`, `basename`, and `seq`, as the future schema-first migration template.

### Goals

- Prove that command name, stability level, risk level, arguments, handler, and GNU compatibility notes can be represented by one spec.
- Establish typed data structures for later generation of argparse, MCP schema, tool-list, and documentation snippets.
- Block drift between full transitional specs, hand-written pilot specs, and the current parser before migration.

### Check Command

```powershell
$env:PYTHONPATH = "src"
python scripts/audit_command_specs.py
```

### Current Scope

| Layer | Scope | Purpose |
|---|---|---|
| Full transitional specs | Every parser-registered command | Audit command risk level, handler, argument dests, and basic summary across the full surface. |
| Hand-written pilot specs | `pwd`, `basename`, `seq` | Template for future schema-first argparse/MCP schema generation. |

### Hand-Written Pilot Scope

| Command | Reason | Current State |
|---|---|---|
| `pwd` | No arguments; smallest spec shape. | Spec/parser consistency check. |
| `basename` | Has positional, option, and raw output. | Spec/parser argument dest check. |
| `seq` | Has multiple arguments and output bound. | Spec/risk-level check. |

### Next Promotion Gates

Promote command spec from parser-derived audit prototype to generation source only when:

1. Pilot commands keep their CLI golden output.
2. MCP tools/list output stays unchanged unless release notes explicitly say otherwise.
3. `scripts/audit_command_specs.py`, `scripts/audit_command_matrix.py`, and MCP server tests pass.
4. New spec fields cover stability level, risk level, argument docs, handler, and GNU compatibility notes.
