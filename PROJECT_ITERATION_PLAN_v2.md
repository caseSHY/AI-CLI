# AICoreUtils 项目迭代计划 v3.0

> 版本：3.0 | 日期：2026-05-04 | 负责人：全权项目负责人
>
> 本版本放弃新工具扩展（grep/find/diff/curl/git 将作为独立新项目），聚焦现有 114 工具的完善与发布。

## 中文说明

当前状态：TDQS **A** (均值 4.3/5) | 114 工具 | PyPI v0.4.7 | Glama 92% | CI 12/12 通过

## English

Project iteration plan v3.0. Scope: polish existing 114 tools, zero new tool additions. New utilities will be separate projects.

---

## 一、当前基线

| 指标 | 值 |
|------|-----|
| 工具数 | 114 |
| TDQS 均值 | 4.3/5 (A) |
| TDQS 最低 | 3.1/5 (B) |
| Glama 总评分 | 92% |
| PyPI 版本 | v0.4.7 |
| CI 矩阵 | Ubuntu 3.11/3.12/3.13 + macOS 3.11/3.12/3.13 + Windows 3.11/3.12/3.13 + lint + typecheck = 12 jobs |
| 测试数 | 369 passed, 60 skipped (Windows), ~400 (CI) |
| 覆盖率 | 39.78% |
| mcp_server.py 覆盖 | 90% |
| 文档 | CHANGELOG.md ✅ CONTRIBUTING.md ✅ CURRENT_STATUS.md ✅ |
| 中文双语文档 | 已治理 |

---

## 二、阶段规划

### Phase 1：TDQS 零 B 级（1 天）—— 全部 A 级

**目标**：114 工具全部 ≥3.5，消除最低分瓶颈（当前最低 3.1）

#### 已修复（待 Glama rebuild 生效）
- `stdbuf` (3.2) — 已修描述，commit `6ff55b8`
- `dir` (3.2) — 已修描述，commit `634c273`
- `basenc` (3.4) — 已修描述，commit `fdd6e10`

#### 待修复（B 级剩余）
- [ ] `nice` (3.1 → 3.5+) — 已修描述 commit `6061c63`，待 Glama 确认
- [ ] `ginstall` (3.2 → 3.5+) — 已修描述 commit `42ee918`，待 Glama 确认
- [ ] 批量检查剩余 ~14 个未评分工具（schema/catalog/coreutils/tool-list 等 meta 工具）
- [ ] 对 TDQS < 3.8 的工具微调 Usage Guidelines + Behavior 维度

**交付物**：
1. Glama 上无 B 级工具
2. 最低分 ≥3.5
3. 服务器 TDQS 等级保持 A

---

### Phase 2：测试与覆盖率提升（2 天）

#### 2.1 覆盖率提升
- [ ] 覆盖率从 39.78% → 50%（目标：当前 CI 门禁 35% 已通过）
- [ ] `async_interface.py` (23% → 50%+) — 补充异步路径测试
- [ ] `core/path_utils.py` (30% → 50%+) — 安全校验路径测试
- [ ] `core/sandbox.py` (15% → 40%+) — 沙箱边界测试
- [ ] `core/plugin_registry.py` (44% → 70%+) — 插件系统测试

#### 2.2 CI 门禁提高
- [ ] 覆盖率门槛 35% → 45%

#### 2.3 测试补充
- [ ] `mcp_server.py` 补充 _call_tool 边缘情况（无 handler、SystemExit、异常 dispatch）
- [ ] `tool_schema.py` 补充 schema 生成测试
- [ ] `core/config.py` 补充环境变量覆盖测试

---

### Phase 3：技术债清理（1 天）

#### 3.1 代码路径统一
- [ ] `os.path` 用法迁移到 `pathlib`（一致性）
- [ ] `parser/__init__.py` 中跨包导入审查

#### 3.2 CI/DevOps 优化
- [ ] GitHub Actions Node.js 24 迁移（2026-06-02 强制升级前完成）
- [ ] `actions/checkout@v5` + `actions/setup-python@v6`（等官方发布）
- [ ] pre-commit ruff rev 更新到最新

#### 3.3 仓库清理
- [ ] `.venv/` `.venv-wsl/` 确认已 gitignore
- [ ] `dist/` 已 commit 的旧文件清理（`git rm --cached`）
- [ ] `.cache/` `.benchmarks/` 确认已 gitignore

---

### Phase 4：发布与推广（持续）

#### 4.1 Docker 镜像
- [ ] 发布到 Docker Hub：`caseSHY/aicoreutils:latest`
- [ ] CI 自动构建推送（tag 触发）

#### 4.2 多平台分发
- [ ] Homebrew formula：`brew install aicoreutils`
- [ ] 一键安装脚本：`curl -fsSL https://get.aicoreutils.dev | sh`

#### 4.3 集成文档
- [ ] Claude Desktop 集成指南（已有，完善）
- [ ] Cursor / Windsurf / Continue.dev 集成指南
- [ ] OpenAI Agents SDK 插件示例
- [ ] LangChain 工具包装器示例

#### 4.4 社区推广
- [ ] MCP Registry 完善 profile
- [ ] Reddit r/mcp r/ClaudeAI 发帖
- [ ] Hacker News Show HN
- [ ] Model Context Protocol Discord 介绍

---

### Phase 5：长期工程治理（持续）

- [ ] `CURRENT_STATUS.md` 随每次 CI 变更同步更新
- [ ] 每版本 release 后更新 CHANGELOG.md
- [ ] 文档治理测试保持通过
- [ ] 监控 Glama TDQS 趋势，每次 rebuild 后检查退化
- [ ] 探索 CI 自动化 TDQS 监控（如有 API）

---

## 三、里程碑

| 版本 | 内容 | 状态 |
|------|------|-----|
| v0.4.7 | P1 mcp_server 测试 + P2 CI 增强 + P3 文档 | ✅ 已完成 |
| v0.4.8 | Phase 1 完成：TDQS 零 B 级 | 🎯 下一版本 |
| v0.5.0 | Phase 2 完成：覆盖率 50% + 门禁 45% | |
| v0.6.0 | Phase 3 完成：技术债清零 + Node.js 24 | |
| v1.0.0 | Phase 4 完成：Docker + Homebrew + 社区 | |

---

## 四、成功指标

| 指标 | 当前 | 目标 v1.0 |
|------|------|----------|
| TDQS 均值 | 4.3 | ≥4.5 |
| TDQS 最低分 | 3.1 | ≥3.5 |
| A 级工具数 | ~100/114 | 114/114 |
| Glama 总评分 | 92% | ≥95% |
| 测试覆盖率 | 39.78% | ≥50% |
| CI 矩阵 job 数 | 12 | 12 |
| mcp_server 覆盖 | 90% | ≥95% |
| Docker 镜像 | ❌ | ✅ |
| Homebrew | ❌ | ✅ |
| PyPI 下载量 | — | ≥1000/月 |
| GitHub stars | ~10 | ≥100 |
| Glama usage | 9/30天 | ≥30/30天 |
