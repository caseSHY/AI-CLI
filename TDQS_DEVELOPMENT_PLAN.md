# AI-CLI TDQS 修复与升级开发计划

> 目标：114 个工具全部达到 **A 级 (≥3.5)**，理想目标 **≥4.0**

## 中文说明

本文档是 TDQS 改进计划，目标为 114 个工具全部 A 级 (≥3.5)。

## English

This document is a TDQS improvement plan. Summary: target all 114 tools at A-grade (≥3.5).

> 当前状态：Glama 均值 4.3/5，最低 3.1，~100 个 A 级

---

## 一、当前 TDQS 状态

| 指标 | 计划初始 | 当前 | 目标 |
|------|---------|------|------|
| 平均 TDQS | 3.1/5 | **4.3/5** | ≥4.5/5 |
| 最低 TDQS | 2.2/5 | **3.1/5** | ≥3.5/5 |
| A 级工具数 | 23/114 (20%) | **~100/114** | 114/114 |
| B 级工具数 | 49 | **~3** | 0 |
| C 级工具数 | 42 | **0** | 0 |
| 总体评分 | 75% | **92%** | ≥95% |

### TDQS 评分公式

```
TDQS = Purpose×25% + Usage×20% + Behavior×20% + Parameters×15% + Conciseness×10% + Completeness×10%
Server-Level = mean(TDQS)×60% + min(TDQS)×40%
Tiers: A≥3.5, B≥3.0, C≥2.0
```

---

## 二、剩余工作

### B 级工具（本地已修，待 Glama rebuild 生效）

| 工具 | 当前分 | 修复 commit | 预计 |
|------|--------|------------|------|
| nice | 3.1 | `6061c63` | ≥3.5 |
| ginstall | 3.2 | `42ee918` | ≥3.5 |
| stdbuf | 3.2 | `6ff55b8` | ≥3.5 |
| dir | 3.2 | `634c273` | ≥3.5 |
| basenc | 3.4 | `fdd6e10` | ≥3.5 |

### 低分 A 级工具微调（3.5-3.7）

约 10-15 个工具可通过补充 Usage Guidelines 或 Behavior 1-2 行提升 0.3-0.5 分。

---

## 三、描述模板（五段式结构）

```
[Purpose]  [Verb] [Resource] [Distinguisher].
[Behavior] Read-only / Destructive. [Side effects]. [Safety notes].
[Parameters] [Key param interactions beyond schema].
[Output] Returns JSON by default. Use --raw for plain output.
[Usage] Use [tool] when [scenario]. Not for [exclusion]. See also [alternatives].
```

### Usage Guidelines 模板（最大提升杠杆，权重 20%）

```
Use [tool] when [concrete scenario].
Not for [specific exclusion].
See also [sibling] for [alternative approach].
```

### Behavioral Transparency 模板（权重 20%）

只读工具：
```
Read-only operation. Returns data without modifying filesystem state.
```

破坏性工具：
```
Destructive: [specific effect]. Use --dry-run to preview.
Requires explicit allow_[action] confirmation for execution.
```

---

## 四、实施检查清单

- [x] ginstall 描述优化（commit `42ee918`）
- [x] nice 描述优化（commit `6061c63`）
- [x] stdbuf 描述优化（commit `6ff55b8`）
- [x] dir 描述优化（commit `634c273`）
- [x] basenc 描述优化（commit `fdd6e10`）
- [ ] Glama rebuild 验证上述 5 个工具升 A
- [ ] 批量微调 3.5-3.7 分段工具的 Usage + Behavior
- [ ] Glama 最终验证：114 工具全部 A 级
- [ ] 最低分 ≥3.5，均值 ≥4.5
