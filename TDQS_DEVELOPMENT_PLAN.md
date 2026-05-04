# AI-CLI TDQS 修复与升级开发计划

> 目标：114 个工具全部达到 **A 级 (≥3.5)**，理想目标 **≥4.0**

## 中文说明

本文档是 TDQS 改进计划，目标为 114 个工具全部 A 级 (≥3.5)，理想 ≥4.0。

## English

This document is a TDQS improvement plan. Summary: target all 114 tools at A-grade (≥3.5).
>
> 当前状态：均值 3.1/5，最低 2.2，仅 23 个 A 级

---

## 一、评分问题诊断

### TDQS 评分公式

```text
TDQS = Purpose×25% + Usage×20% + Behavior×20% + Parameters×15% + Conciseness×10% + Completeness×10%
Server-Level = mean(TDQS)×60% + min(TDQS)×40%
Tiers: A≥3.5, B≥3.0, C≥2.0, D≥1.0
```

### 各维度现状与最大可提升分数

| 维度 | 权重 | 当前典型分 | 目标分 | 单维度可提升 | 对总分贡献 |
|------|------|-----------|--------|-------------|-----------|
| Purpose Clarity | 25% | 4/5 | 5/5 | +1 | +0.25 |
| Usage Guidelines | 20% | **2/5** | 4/5 | +2 | **+0.40** |
| Behavioral Transparency | 20% | **2/5** | 4/5 | +2 | **+0.40** |
| Parameter Semantics | 15% | 3/5 | 4/5 | +1 | +0.15 |
| Conciseness | 10% | 4/5 | 5/5 | +1 | +0.10 |
| Completeness | 10% | **2/5** | 4/5 | +2 | **+0.20** |
| **合计** | | | | | **+1.50** |

> 理论最大提升：从 2.2（最低）→ 3.7（A 级），从 3.1（均值）→ 4.6（A 级）

### 按评分段分布

| 分数段 | 工具数 | 级别 | 需要提升幅度 |
|--------|--------|------|------------|
| 2.0-2.4 | 6 | C | +1.6 ~ +1.1 |
| 2.5-2.9 | 36 | C | +1.0 ~ +0.6 |
| 3.0-3.4 | 49 | B | +0.5 ~ +0.1 |
| 3.5-3.9 | 20 | A | 保持/微调 |
| 4.0+ | 3 | A | 标杆 |

---

## 二、核心修复策略

### 修复优先级矩阵

```
高影响 + 低成本 → 优先修复
├── Usage Guidelines (2→4): 每条工具加 1 句 "when to use / when not"
├── Behavioral Transparency (2→4): 声明只读/副作用/幂等
└── Completeness (2→4): 说明返回格式

低影响 + 低成本 → 批量优化
├── Purpose Clarity (4→5): 确保 verb+resource 明确
└── Parameter Semantics (3→4): 描述中补充参数关联关系
```

### 描述模板（五段式结构）

```
[Purpose]  [Verb] [Resource] [Distinguisher].

[Behavior] Read-only. No side effects. [Safety note if destructive].

[Parameters] [key params explained beyond schema, relationships noted].

[Output] Returns [structured JSON format] or raw [format] with
--raw. [error handling].

[Usage] Use [tool] when [scenario]. Not for [exclusion]. See also
[alternatives].
```

---

## 三、分阶段实施计划

### Phase 1：建立标准模板与修复第一批（最差工具） — 预计 3 天

**目标**：修复评分最低的 10 个工具，建立可复用的模板模式

#### 要修复的工具（C 级，2.2-2.4）

| # | 工具 | 当前分 | 主要问题 | 目标分 |
|---|------|--------|---------|--------|
| 1 | false | 2.2 | 描述混乱，无行为说明 | 4.0 |
| 2 | coreutils | 2.4 | 抽象工具无使用指南 | 3.8 |
| 3 | dir | 2.4 | 7个参数无行为说明 | 3.8 |
| 4 | pinky | 2.4 | Behavior 1/5，无安全说明 | 3.8 |
| 5 | ptx | 2.4 | 8个参数无输出说明 | 3.8 |
| 6 | yes | 2.4 | 描述模糊，无使用指南 | 3.8 |

**交付物**：
1. `DESCRIPTION_TEMPLATES.md` — 描述模板规范文档
2. 6 个工具的修复 PR
3. 评分回升验证

---

### Phase 2：批量修复 C 级工具（2.5-2.9） — 预计 5 天

**目标**：修复剩余 36 个 C 级工具

#### 按类分组并行修复

| 组名 | 工具数 | 工具列表 |
|------|--------|---------|
| **文本处理** | 8 | cat, echo, fold, fmt, tr, comm, paste, join |
| **文件操作** | 9 | base32, base64, basenc, rm, unlink, truncate, mkdir, install, ginstall |
| **系统信息** | 5 | hostid, printenv, logname, groups, stat |
| **条件/测试** | 4 | [, test, expr, factor |
| **工具/调度** | 5 | seq, nice, stdbuf, stty, timeout |
| **哈希** | 3 | sha224sum, sha512sum, cksum |
| **其他** | 2 | od, dircolors |

**每组批量修复**：工具描述第 3-4 行补充 "Use $TOOL when... Not for..." + 第 4-5 行补充 "Read-only/destructive..."

---

### Phase 3：B 级工具升级（3.0-3.4） — 预计 4 天

**目标**：将 49 个 B 级工具提升至 A 级

这些工具主要缺少 Usage Guidelines (2/5) 和 Behavioral Transparency (2/5)，Purpose 和 Conciseness 已达标。只需补充 2-3 行描述。

#### 快速修复策略

每个工具新增固定模式的 3 行：

```text
[Usage] Use [tool] to [primary use case]. Not for [exclusion].
See also [sibling tools] for related operations.  
Read-only. Returns output on stdout. No destructive side effects.
```

对于破坏性工具（rm, shred, kill, chmod, chown, chgrp, chroot, truncate, dd）：
```text
[Behavior] Potentially destructive. Use --dry-run to preview.
Requires explicit confirmation for actual execution.
```

---

### Phase 4：A 级工具巩固（3.5+） — 预计 2 天

**目标**：将 23 个 A 级工具提升至 4.0+

只需微调 Usage Guidelines 和 Parameter Semantics。

---

### Phase 5：验证与持续维护 — 持续

1. 每次修改后运行 Glama score 检查
2. 设置 CI 自动化检查（如可行）
3. 定期同步 GitHub → Glama 刷新评分

---

## 四、描述修改规范

### 4.1 Usage Guidelines 模板（20% 权重，当前 2→目标 4）

```text
Use [tool] when [concrete scenario].
Not for [specific exclusion].
See also [sibling] for [alternative approach].
```

示例：
```
Use rm to remove files or directories that are no longer needed.
Not for shredding sensitive data — use shred instead.
See also rmdir for removing only empty directories.
```

### 4.2 Behavioral Transparency 模板（20% 权重，当前 2→目标 4）

**只读工具**：
```text
Read-only operation. Returns data without modifying filesystem state.
No authentication required. Safe to call repeatedly.
```

**破坏性工具**：
```text
Destructive: [specific effect]. Use --dry-run to preview.
Requires explicit allow_[action] confirmation for actual execution.
Not reversible—deleted/corrupted data cannot be recovered.
```

**无操作工具**（true/false）：
```text
Does nothing else. No side effects. Idempotent — same result every call.
Always [exits with 0 / exits with 1]. Takes no arguments.
```

### 4.3 Parameter Semantics 模板（15% 权重，当前 3→目标 4）

```text
[param_a] and [param_b] together control [behavior].
Defaults: [key defaults with rationale].
```

### 4.4 Completeness 模板（10% 权重，当前 2→目标 4）

```text
Returns structured JSON by default. Use --raw for plain text output.
On error: returns JSON with exit_code and error fields.
```

---

## 五、各工具优先级修复路线图

### 第一批：最高优先级（C 级 <2.5）

| 工具 | 当前 | 目标 | 关键改动 |
|------|------|------|---------|
| false | 2.2 | 4.0 | 重写描述，参考 true (4.5) 的结构 |
| coreutils | 2.4 | 3.8 | 说明 meta 工具用途，区分其他发现工具 |
| dir | 2.4 | 3.8 | 说明 7 个参数的行为影响，只读声明 |
| pinky | 2.4 | 3.8 | 说明 vs users/who/id，行为透明 |
| ptx | 2.4 | 3.8 | 说明输出格式，stdin 默认行为 |
| yes | 2.4 | 3.8 | 说明 vs echo/seq，bounded 含义 |

### 第二批：高优先级（C 级 2.5-2.9）

36 个工具，按上述分组并行修复。

### 第三批：中优先级（B 级 3.0-3.4）

49 个工具，追加 Usage + Behavior 行即可。

### 第四批：低优先级（A 级 3.5+）

23 个工具，微调。

---

## 六、工作量估算

| 阶段 | 工具数 | 每工具时间 | 总时间 |
|------|--------|-----------|--------|
| Phase 1 | 6 | 30 min | 3 小时 |
| Phase 2 | 36 | 15 min | 9 小时 |
| Phase 3 | 49 | 10 min | 8 小时 |
| Phase 4 | 23 | 5 min | 2 小时 |
| Phase 5 | — | — | 持续 |
| **合计** | **114** | | **~22 小时** |

---

## 七、预期成果

| 指标 | 当前 | 目标 |
|------|------|------|
| 平均 TDQS | 3.1/5 | ≥4.0/5 |
| 最低 TDQS | 2.2/5 | ≥3.5/5 |
| A 级工具数 | 23/114 (20%) | 114/114 (100%) |
| Tool Definition Quality 等级 | C | A |
| 总体评分 | 75% | ≥90% |

---

## 八、实施检查清单

- [ ] 创建 `DESCRIPTION_TEMPLATES.md` 标准模板
- [ ] 修复 false (2.2 → 4.0)
- [ ] 修复 coreutils (2.4 → 3.8)
- [ ] 修复 dir (2.4 → 3.8)
- [ ] 修复 pinky (2.4 → 3.8)
- [ ] 修复 ptx (2.4 → 3.8)
- [ ] 修复 yes (2.4 → 3.8)
- [ ] Phase 2: 批量 C 级修复（36 工具）
- [ ] Phase 3: B 级工具追加 Usage+Behavior（49 工具）
- [ ] Phase 4: A 级工具微调（23 工具）
- [ ] 每次修复后运行验证
- [ ] 同步 Glama 刷新评分
