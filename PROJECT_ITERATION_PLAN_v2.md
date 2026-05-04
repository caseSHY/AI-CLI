# AICoreUtils 项目迭代计划 v2.0

> 版本：2.0 | 日期：2026-05-04 | 负责人：全权项目负责人
>
> 当前状态：TDQS **A** (3.2/5) | 114 工具 | PyPI v0.3.9 | Glama 75%

---

## 一、项目定位与核心竞争力

### 1.1 愿景

成为 AI Agent 时代的 **标准系统接口层** —— AI 与操作系统之间的唯一桥梁。

### 1.2 竞争壁垒（不可替代性）

| 壁垒 | 说明 | 对手差距 |
|------|------|---------|
| **114 工具** | 最全的 MCP 命令集，覆盖文件、文本、系统、进程 | 第二名仅 ~20 个 |
| **零依赖** | 纯 stdlib，pip install 即用 | 所有对手依赖 Node.js/DB 驱动 |
| **安全架构** | dry-run + allow-* 门禁 + cwd 沙箱 | 对手无安全机制 |
| **JSON-first** | 每个输出可解析，错误也是结构化的 | 对手多为纯文本 |
| **多格式导出** | MCP + OpenAI + Anthropic 自动生成 | 对手需手动维护 |

### 1.3 一句话定位

> "AI 的 GNU Coreutils：114 个 JSON-first 系统命令，零依赖，安全第一。"

---

## 二、阶段规划

### Phase A：修复技术债（1-2 天）——稳定基础

#### A1. 统一版本号
- [ ] `pyproject.toml`、`__version__`、`_TOOL_VERSION`、`server.json` 全部统一为 `0.3.9`
- [ ] 添加 CI 检查：`assert __version__ == server.json.version == pyproject.toml.version`

#### A2. 合并重复代码路径
- [ ] 移除 `parser/__init__.py` 中跨包的脆弱导入
- [ ] 统一 `os.path` / `pathlib` 使用为 `pathlib` 优先

#### A3. 完成插件 CLI 集成
- [ ] `build_parser()` 从 `PluginRegistry` 动态注册插件子命令
- [ ] 添加插件发现测试

---

### Phase B：补齐核心工具（3-5 天）——扩大覆盖面

#### B1. 最优先（Agent 刚需）
| 工具 | 用途 | 优先级 | 预计工时 |
|------|------|--------|---------|
| `grep` | 文件内容搜索，支持 regex | P0 | 4h |
| `find` | 按名称/类型/时间查找文件 | P0 | 4h |
| `diff` | 比较两个文件差异 | P0 | 3h |
| `curl` | HTTP GET/POST，返回 JSON | P0 | 4h |
| `git` | git status/log/diff/branch 只读操作 | P0 | 6h |

#### B2. 次优先
| 工具 | 用途 | 优先级 |
|------|------|--------|
| `sed` | 正则替换 | P1 |
| `ps` | 进程列表 | P1 |
| `jq` | JSON 查询/过滤 | P1 |
| `tar`/`gzip` | 压缩解压（只读查看） | P1 |
| `pip` | 包信息查询（只读） | P2 |

---

### Phase C：提升测试覆盖（2 天）——质量保障

- [ ] CI 覆盖率从 25% → 60%+
- [ ] 新增 MCP 服务器集成测试
- [ ] 新增插件系统集成测试
- [ ] 新增 sandbox 逃逸测试

---

### Phase D：发布与推广（持续）——获取用户

#### D1. Docker 镜像
- [ ] 发布 `caseSHY/aicoreutils:latest` 到 Docker Hub
- [ ] Glama 页面的 Docker build 直接用发布镜像加速

#### D2. 多平台分发包
- [ ] Homebrew formula：`brew install aicoreutils`
- [ ] 一键安装脚本：`curl -fsSL https://get.aicoreutils.dev | sh`

#### D3. 集成文档
- [ ] Claude Desktop 集成指南（已有，完善）
- [ ] Cursor / Windsurf / Continue.dev 集成指南
- [ ] OpenAI Agents SDK 插件
- [ ] LangChain 工具包装器

#### D4. 社区推广
- [ ] MCP Registry 修复发布
- [ ] Reddit r/mcp r/ClaudeAI 发帖
- [ ] Hacker News Show HN
- [ ] Model Context Protocol Discord 介绍

#### D5. 数据驱动推广
- [ ] 添加 Glama badge 到 README（已有 Score badge）
- [ ] 发布 v1.0 里程碑（114 工具达 A 级 + 5 新工具）
- [ ] 添加 "Used by" 案例收集

---

### Phase E：持续优化 TDQS（持续）

- [ ] 目标：114 工具全部 A 级（3.5+），均值 4.0+
- [ ] 当前进展：从 C→A，均值 3.2，28 个 A 级
- [ ] 策略：每个新版本提交后 Sync Glama，追踪趋势

---

## 三、里程碑与发布时间表

| 版本 | 内容 | 目标日期 |
|------|------|---------|
| v0.4.0 | Phase A 完成（版本统一 + 插件集成） | Week 1 |
| v0.5.0 | Phase B P0 工具（grep/find/diff/curl/git） | Week 2 |
| v0.6.0 | Phase B P1 工具 + Phase C 测试 | Week 3 |
| v1.0.0 | Phase D 发布（Docker + 文档 + 推广） | Week 4 |

---

## 四、成功指标

| 指标 | 当前 | 目标 v1.0 |
|------|------|----------|
| TDQS 均值 | 3.2 | ≥4.0 |
| TDQS 最低分 | 2.5 | ≥3.5 |
| A 级工具数 | 28/114 | ≥114/114 |
| Glama 总评分 | 75% | ≥90% |
| 工具总数 | 114 | ≥120 |
| 测试覆盖率 | 25% | ≥60% |
| PyPI 下载量 | — | ≥1000/月 |
| Glama usage | 0 | ≥10/30天 |
| GitHub stars | ~10 | ≥100 |
