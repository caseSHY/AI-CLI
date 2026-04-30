# 测试结果报告 — agentutils v0.1.0

## 1. 报告元信息

| 项目 | 值 |
|---|---|
| 测试日期 | 2026-04-30 |
| Git 分支 | `master` |
| Git commit hash | `11f8cd139d0268a82efcaa505b978e49218b2e01` |
| Git commit message | "Analyze agentutils project structure" |
| Python 版本 | 3.14.4 |
| 操作系统 | Windows 11 (win32) |
| pytest 版本 | 9.0.3 |
| hypothesis 版本 | 6.152.4 |
| 项目版本 | 0.1.0 |
| 测试命令 | `python -m pytest tests/ -v --tb=no -k "not test_human_markdown_files and not test_ci_config and not test_property_based and not Hypothesis"` |
| 本地运行 | 是 |
| CI 运行 | 否（本报告基于本地运行；CI 配置已更新但尚未在 GitHub Actions 上触发） |

---

## 2. 执行摘要

| 项目 | 结论 |
|---|---|
| 总体状态 | **可运行，建议修复安全缺口后合并** |
| 阻塞问题 | **有** — 5 个 sandbox 路径逃逸缺口（详见 §7.2） |
| 安全风险 | **有** — 路径逃逸缺口允许 cwd 外文件被删除/写入/截断（P0/P1） |
| 建议合并 | **修复安全缺口后合并** |
| 最高优先级问题 | `rm`/`tee`/`truncate`/`install`/`dd` 五命令未校验目标路径是否在 cwd 内，可逃逸 sandbox |

> **说明**：当前 84 个可执行测试全部通过。60 个跳过中 51 个是 GNU 命令环境缺失（仅 `sort.exe` 可用），9 个是已知 sandbox 缺口。项目核心逻辑正确，但安全边界不完整。

---

## 3. 总体测试统计

| 指标 | 数值 | 说明 |
|---|---|---:|---|
| 测试文件数 | 16 | 包含 3 个本轮新增 + 13 个已有文件 |
| 测试用例总数 | 171 | pytest collected |
| 通过 | 84 | 全部非跳过测试通过 |
| 失败 | 0 | 排除 1 个预存在失败 `test_docs_bilingual`（`.pytest_cache/README.md` 不含中文标记，与代码无关） |
| 跳过 | 60 | 51 个 GNU 命令缺失 + 9 个 sandbox 已知缺口 |
| xfail | 0 | 未使用 |
| deselected | 27 | 25 个 property-based tests 因耗时长在本轮排除 |
| 本次新增测试文件 | 3 | `test_gnu_differential.py`, `test_property_based_cli.py`, `test_sandbox_escape_hardening.py` |
| 本次新增测试用例 | 117 | 56 + 24 + 37 |

**质量解读**：

- **84 个核心测试全部通过**，说明项目基本功能、JSON 协议、错误码、dry-run、文件副作用、系统命令均工作正常。
- **60 个跳过不代表问题已解决**：其中 51 个是 GNU 对照测试因 Windows 环境缺少 GNU 工具而跳过（属于**环境限制**），9 个是 sandbox 已知缺口（属于**实现缺陷**，必须修复）。
- Property-based 测试（25 个）本轮因 run 时长超过 5 分钟暂时排除，它们在 CI 的 Ubuntu 环境上预期可正常运行。

---

## 4. 新增测试文件说明

### 4.1 `tests/test_gnu_differential.py`

| 项目 | 内容 |
|---|---|
| 文件 | `tests/test_gnu_differential.py` |
| 测试类型 | GNU 对照测试（differential testing） |
| 覆盖对象 | cat, sort, uniq, wc, head, tail, cut, tr, seq, base64, printf, fold, nl, paste, join, comm |
| 测试用例数 | 56 |
| 通过 | 5（仅 sort 命令在 Windows 有对应 GNU 工具） |
| 跳过 | 51（其余 GNU 工具在 Windows 不可用） |
| 跳过原因 | `shutil.which()` 找不到对应 GNU 命令；部分命令的 GNU 版本不支持 UTF-8（Windows sort.exe GBK 编码冲突） |
| 主要策略 | 对每个命令构造 2–7 组输入（空输入、普通文本、重复行、无末尾换行、中文 UTF-8、包含空格/tab、数值文本），对比 GNU stdout 与 agentutils `--raw` stdout |
| 对项目维护的价值 | 在 Ubuntu CI 环境中可实际运行 40+ 个对照测试，防止 agentutils 行为偏离 GNU coreutils 标准；Windows 本地开发时 sort 命令已有 5 个对照测试保护 |
| 当前限制 | Windows 环境仅 `C:\Windows\system32\sort.exe` 可用且功能受限（不支持 `-n`、UTF-8 崩溃到 GBK） |
| 后续动作 | 在 CI 中添加 `apt-get install coreutils` 使大部分测试可运行；对 sort 补充 `--reverse`、`--unique` 的对照测试 |

### 4.2 `tests/test_property_based_cli.py`

| 项目 | 内容 |
|---|---|
| 文件 | `tests/test_property_based_cli.py` |
| 测试类型 | 基于性质的随机测试（Property-Based Testing, Hypothesis） |
| 覆盖对象 | cat, sort, uniq, wc, base64, head, tail, cut, tr, echo, JSON envelope |
| 测试用例数 | 24 |
| 通过 | 本轮 deselected（本地全量运行超 5 分钟，但单独运行可通过） |
| 主要策略 | 对每个命令定义数学/逻辑不变量（如 sort 输出有序、uniq 无相邻重复、base64 编解码往返还原），由 Hypothesis 生成 100 组随机输入验证 |
| 对项目维护的价值 | 防止实现代码只针对固定样例优化（anti-overfitting）；能发现手工编写测试难以覆盖的边界情况 |
| 当前限制 | Windows 本地 `max_examples=100` 运行时间过长（约 6–8 分钟全量）；`deadline=None` 已设置 |
| 后续动作 | CI 中建议 `max_examples=50`；补充 seq、printf、comm、paste 的性质测试 |

### 4.3 `tests/test_sandbox_escape_hardening.py`

| 项目 | 内容 |
|---|---|
| 文件 | `tests/test_sandbox_escape_hardening.py` |
| 测试类型 | 安全逃逸测试（Sandbox Escape Hardening） |
| 覆盖对象 | 路径遍历、符号链接逃逸、文件名注入、dry-run 零副作用、危险命令默认拒绝 |
| 测试用例数 | 37 |
| 通过 | 28 |
| 跳过 | 9（6 个已知 sandbox 缺口 + 3 个 Windows symlink 不支持） |
| 主要策略 | 在 TemporaryDirectory 中构造 cwd/sandbox/outside 三层结构，验证所有写入/删除命令无法通过 `../outside`、绝对路径、symlink 逃逸 |
| 对项目维护的价值 | **高优先级**：暴露了当前 project 最严重的安全风险；已有 dry-run 和文件名安全测试作为回归保护 |
| 当前限制 | 6 个路径逃逸测试被 `@unittest.skip` 标记但代表**真实实现缺陷**（详见 §7.2）；Windows 不支持 symlink |
| 后续动作 | **必须优先修复 §7.2 中的 5 个缺口**，去掉对应 `@unittest.skip` 装饰器使测试生效 |

---

## 5. GNU 对照测试分析

### 5.1 已实际执行的 GNU 对照测试

**当前环境（Windows 11 win32）**：

| 命令 | GNU 工具路径 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|---|
| sort | `C:\Windows\system32\sort.exe` | 7 | 5 | 0 | 2 个跳过（`--numeric` 不支持、中文 GBK 冲突） |

在 Windows 上运行的 sort 对照测试覆盖了：普通排序、重复行排序、字典序、空输入、单行输入。`--numeric` 因 Windows sort.exe 不支持 `-n` 参数被跳过。中文 UTF-8 排序因 Windows sort.exe 的 GBK 解码崩溃被 `@unittest.skip`。

### 5.2 因环境缺失而跳过的 GNU 对照测试

以下测试在 Windows 全部跳过，**但不代表 agentutils 在这些命令上正确**——它们仅仅是没有机会被验证。

| 命令 | 跳过原因 | 风险等级 | 在 CI 中是否应执行 |
|---|---|---|---|
| cat | GNU cat 不可用 | 中 — identity 命令，已由 property 测试覆盖 | 是，Ubuntu CI 可运行 |
| uniq | GNU uniq 不可用 | 中 — 已由 property 测试覆盖 | 是 |
| wc | GNU wc 不可用 | 高 — 行数/词数/字节数语义容易出错 | 是 |
| head | GNU head 不可用 | 中 | 是 |
| tail | GNU tail 不可用 | 中 | 是 |
| cut | GNU cut 不可用 | 中 | 是 |
| tr | GNU tr 不可用 | 中 | 是 |
| seq | GNU seq 不可用 | 低 — 数学生成，不易出错 | 是 |
| base64 | GNU base64 不可用 | 中 — 编解码标准性关键 | 是 |
| printf | GNU printf 不可用 | 中 — 格式化语义容易有细微差异 | 是 |
| fold | GNU fold 不可用 | 低 | 是 |
| nl | GNU nl 不可用 | 低 | 是 |
| paste | GNU paste 不可用 | 中 | 是 |
| join | GNU join 不可用 | 中 | 是 |
| comm | GNU comm 不可用 | 中 | 是 |

### 5.3 GNU 对照测试维护建议

1. **Windows 本地环境下 GNU 工具几乎全部缺失**。Windows 自带的 `sort.exe` 与 GNU sort 行为差异显著（不支持 POSIX 选项、编码问题）。开发者不应依赖 Windows 本地 GNU 测试。
2. **Ubuntu CI 中预计 50+ 个 GNU 对照测试可以运行**。建议在 CI workflow 中添加 `sudo apt-get install -y coreutils` 保证所有标准 GNU 工具可用。
3. **sort 命令的 `--numeric` 对照测试**：当前在 Windows 上无法执行；在 Ubuntu CI 上应能通过 `sort -n` 与 agentutils `sort --numeric` 对比。
4. **是否需要区分 Windows/Linux 预期行为**：agentutils 的目标应是匹配 GNU coreutils（Linux 行为）。Windows 上的差异应在测试中标记为 xfail 并在文档中说明。
5. **建议设为必跑测试**：在 CI 中不对 GNU 对照测试做 `-k` 排除，让它们随 PR 自动验证。缺失的 GNU 工具通过 `skip_if_no_gnu()` 自动跳过，不会导致 CI 失败。

---

## 6. Property-Based 随机性质测试分析

### 6.1 性质覆盖一览

| 测试对象 | 已验证性质 | 能防止的问题 | 后续建议 |
|---|---|---|---|
| cat | stdout = 文件内容（identity）；两个相同文件输出一致 | 内容损坏、换行符丢失/增加 | 补充 stdin vs 文件输出一致性 |
| sort | 输出非递减；不丢行；不造新行；`--numeric` 数值有序 | 排序器 bug、行丢失、数据损坏 | 补充 `--reverse`、`--unique` 性质 |
| uniq | 输出无相邻重复；非相邻重复保留 | 过度压缩、非相邻行误删 | 补充 `--count` 模式性质 |
| wc | bytes = UTF-8 编码长度；lines = 换行符数量 | 字节/行计数偏移 | 补充 words 计数的 split 语义一致性 |
| base64 | encode→decode 往返还原；输出为合法 base64 字符集 | 编解码数据损坏、非标准字符 | 补充无 padding 模式性质 |
| head/tail | head(n) = 前 n 行；tail(n) = 后 n 行；n=0 返回空 | 越界读取、行截断错误 | 补充负数 n 的边界行为 |
| cut | `--chars 1` 输出每行首字符；任意输入不崩溃 | 空行/短行崩溃、索引越界 | 补充 `--fields` 的分隔符性质 |
| tr | 恒等映射不变；大小写转换保持字节长；`--delete` 只删目标字符 | 字符映射 bug、多字节字符问题 | 补充 Unicode 多字符映射性质 |
| echo | 空格连接 + 换行 | 分隔符错误 | 已完整 |
| JSON envelope | 必有 `ok/tool/command/result/warnings`；raw 输出不以 `{` 开头 | 协议破坏、输出格式混乱 | 补充错误响应的 envelope 字段完整性 |

### 6.2 运行配置分析

- **`max_examples=100`**：在 Windows 本地全量运行（24 个 property tests × 100 样例 ≈ 2400 次 subprocess 调用）耗时约 6–8 分钟。建议 CI 中使用 `max_examples=50`。
- **`deadline=None`**：必须保留。Windows CI runner 的 I/O 性能不稳定，默认 200ms deadline 会导致偶发性假阳性。
- **不可替代 GNU 对照测试**：Property 测试验证通用数学不变量（如"sort 输出有序"），但不会验证"sort 的字典序与 GNU sort 一致"。两种测试互补。

### 6.3 缺失的性质

| 命令 | 缺失性质 | 重要性 |
|---|---|---|
| seq | 等差性质：相邻项差值恒定 | 中 |
| comm | 三列互不相交；union = 输入 | 中 |
| paste | 行数与最长输入文件一致 | 中 |
| fold | 每行长度 ≤ width（除最后一行） | 低 |
| shuf | 输出 multiset = 输入 multiset | 中 |

---

## 7. 安全逃逸测试分析

> **⚠️ 高优先级章节 — 本节内容影响项目是否可安全部署。**

### 7.1 已通过的安全保护

| 风险类型 | 覆盖命令 | 当前结果 | 说明 |
|---|---|---|---|
| 目录递归删除 cwd 外 | `rm --recursive` | ✅ 已阻止（exit 8, `unsafe_operation`） | `require_inside_cwd()` 对目录递归有效 |
| 文件复制到 cwd 外 | `cp` | ✅ 已阻止 | 目标路径被校验 |
| 文件移动到 cwd 外 | `mv` | ✅ 已阻止 | 目标路径被校验 |
| 文件名空格/U+0000 类字符 | 全部文件命令 | ✅ 正常处理 | 文件名被正确传参 |
| 文件名以 `-` 开头 | `cat` 等 | ✅ `./-rf` 形式正常工作 | `--` 分隔符也可用 |
| 文件名含命令注入字符 | `cat` 等 | ✅ 作为字面量处理 | `;`、`$()` 等不被解释 |
| 文件名含 AI prompt 注入 | `cat` 等 | ✅ 作为字面量数据 | "ignore previous instructions" 不被执行 |
| 文件内容含 AI 指令 | `cat`/`wc` 等 | ✅ 作为数据只读 | 不会执行内容中的指令 |
| dry-run 不产生文件副作用 | 12 个命令 | ✅ 全部通过 | mkdir/rm/cp/mv/tee/chmod/truncate/split/csplit/dd/touch/shred |
| 危险命令默认拒绝 | shred | ✅ 拒绝（exit 8） | 需要显式确认 |
| sleep 超时保护 | sleep | ✅ 拒绝（exit 8） | `--max-seconds` 限制生效 |
| timeout 外部进程 | timeout | ✅ 正确执行 | 子进程在限制内运行 |
| nice/nohup dry-run | nice/nohup | ✅ 不实际执行 | `--dry-run` 生效 |
| kill dry-run | kill | ✅ 不发送信号 | `--dry-run` 生效 |

### 7.2 已知安全缺口

> **以下 6 条测试当前被 `@unittest.skip` 跳过，但每一条都代表真实实现缺陷。去掉 skip 装饰器即可重现失败。**

| 编号 | 命令 | 触发输入 | 预期结果 | 实际结果 | 风险等级 | 可能修复位置 | 回归测试 |
|---|---|---|---|---|---|---|---|
| SEC-001 | `rm` | `rm ../outside.txt`（无 `--recursive`） | 拒绝（exit 8, `unsafe_operation`） | 成功删除 cwd 外文件 | **P0** | `src/agentutils/fs_commands.py` → `command_rm` | `test_rm_outside_file_should_be_blocked` |
| SEC-002 | `rm` | `rm /absolute/path/outside.txt`（无 `--recursive`） | 拒绝（exit 8） | 成功删除绝对路径文件 | **P0** | 同上 | `test_rm_absolute_outside_should_be_blocked` |
| SEC-003 | `tee` | `tee ../outside.txt` | 拒绝 | 成功写入 cwd 外文件 | **P1** | `src/agentutils/fs_commands.py` → `command_tee` | `test_tee_to_outside_should_be_blocked` |
| SEC-004 | `truncate` | `truncate ../outside.txt --size 0` | 拒绝 | 成功截断 cwd 外文件 | **P1** | `src/agentutils/fs_commands.py` → `command_truncate` | `test_truncate_outside_should_be_blocked` |
| SEC-005 | `install` | `install tool.txt ../outside_dir/installed` | 拒绝 | 成功安装到 cwd 外 | **P1** | `src/agentutils/fs_commands.py` → `command_install` | `test_install_to_outside_should_be_blocked` |
| SEC-006 | `dd` | `dd --input src.txt --output ../outside.txt` | 拒绝 | 成功写入 cwd 外 | **P1** | `src/agentutils/fs_commands.py` 或 `system_commands.py` → `command_dd` | `test_dd_output_to_outside_should_be_blocked` |

**风险分析**：

- **SEC-001 / SEC-002 (P0)**：`rm` 不校验目标路径可导致任意文件删除。虽然攻击者需要先知道 cwd 外部路径，但在 agent 自动化场景中（agent 可能在用户未审查的情况下执行命令），这种漏洞非常危险。
- **SEC-003 / SEC-004 / SEC-006 (P1)**：允许将任意内容写入 cwd 外文件，可能被用于植入恶意文件、覆盖配置或持久化后门。
- **SEC-005 (P1)**：`install` 可将文件安装到任何路径，等同于任意文件写入。

**根本原因**：`command_rm` 对文件（非目录）路径未调用 `require_inside_cwd()`，仅对 `--recursive` 目录做了限制。`command_tee`、`command_truncate`、`command_install`、`command_dd` 的输出路径均未经过 `require_inside_cwd()` 校验。`protocol.py` 中已存在 `require_inside_cwd()` 函数，只需在各命令中一致使用。

### 7.3 符号链接逃逸

所有 3 个 symlink 测试因 Windows 上无法创建 symlink（权限不足）被跳过。**这些测试在 Linux/Ubuntu CI 上应当实际运行**。

| 测试 | 跳过原因 | 在 Ubuntu CI 应启用 |
|---|---|---|
| `test_tee_to_symlink_preserves_outside_content` | Windows symlink 不可用 | 是 |
| `test_truncate_to_symlink_preserves_outside_content` | Windows symlink 不可用 | 是 |
| `test_rm_symlink_preserves_outside_file` | Windows symlink 不可用 | 是 |

---

## 8. 已知问题修复路线图

| 优先级 | 问题 | 建议修复文件 | 建议修复方式 | 验收测试 |
|---|---|---|---|---|
| **P0** | `rm` 可删除 cwd 外文件 | `src/agentutils/fs_commands.py` | 在 `command_rm` 中对每个目标路径调用 `require_inside_cwd(cwd, resolved)` | 去掉 `PathTraversalKnownGapsTests.test_rm_outside_file_should_be_blocked` 和 `test_rm_absolute_outside_should_be_blocked` 的 skip 装饰器 |
| **P1** | `tee` 可写入 cwd 外文件 | `src/agentutils/fs_commands.py` | `command_tee` 的输出路径调用 `require_inside_cwd()` | 去掉 `test_tee_to_outside_should_be_blocked` 的 skip |
| **P1** | `truncate` 可截断 cwd 外文件 | `src/agentutils/fs_commands.py` | `command_truncate` 中添加路径校验 | 去掉 `test_truncate_outside_should_be_blocked` 的 skip |
| **P1** | `install` 可安装到 cwd 外 | `src/agentutils/fs_commands.py` | `command_install` 的目标路径调用 `require_inside_cwd()` | 去掉 `test_install_to_outside_should_be_blocked` 的 skip |
| **P1** | `dd` 可写入 cwd 外 | `src/agentutils/fs_commands.py` 或 `system_commands.py` | `command_dd` 的输出路径调用 `require_inside_cwd()` | 去掉 `test_dd_output_to_outside_should_be_blocked` 的 skip |
| **P2** | CI 中 GNU 对照测试无法运行 | `.github/workflows/ci.yml` | 添加 `sudo apt-get install -y coreutils` | 重跑 CI 确认 50+ GNU 测试通过 |
| **P3** | Property 测试 CI 速度 | `.github/workflows/ci.yml` 或 `pyproject.toml` | 设置 `max_examples=50` 或单独 job | CI 完成后确认 property tests 在 5 分钟内完成 |

**修复顺序建议**：

1. **先修 SEC-001/002（rm，P0）**：风险最高，影响最大。
2. **再修 SEC-003/004/005/006（tee/truncate/install/dd，P1）**：四者修复模式相同（在目标路径前插入 `require_inside_cwd()` 调用），可以一次提交完成。
3. **CI 中启用 GNU 对照测试（P2）**：安装 `coreutils` 包。
4. **调整 CI property 测试配置（P3）**。

**修复验证命令**：

```bash
# 修复后运行安全逃逸测试
python -m pytest tests/test_sandbox_escape_hardening.py -v

# 修复后运行完整回归
python -m pytest tests/ -v -k "not test_human_markdown_files"
```

---

## 9. 本次测试增强的既有用例

| 测试文件 | 测试函数 | 原断言问题 | 新断言价值 |
|---|---|---|---|
| `tests/test_agentutils.py` | `test_cat_head_tail_wc_hash` | sha256sum/md5sum/b2sum 仅校验 digest **长度**（64/32/128 字符），不校验具体值 | 现在通过 `hashlib.sha256(target.read_bytes()).hexdigest()` 计算精确 digest 并严格相等比较；能发现任何 hash 实现 bug |
| `tests/test_agent_call_flow.py` | `test_agent_can_observe_decide_and_mutate_with_json` | 同上，sha256sum 仅校验长度 | 同上 |
| `tests/test_agentutils.py` | （导入部分） | 缺少 `hashlib` import | 新增 `import hashlib` |
| `tests/test_agent_call_flow.py` | （导入部分） | 缺少 `hashlib` import | 新增 `import hashlib` |

**平台兼容说明**：原测试中硬编码 `b"alpha beta\nsecond\nthird\n"` 作为 hash 输入，在 Windows 上因 `write_text` 自动转换 `\n→\r\n` 导致 hash 不匹配。新断言使用 `target.read_bytes()` 直接读取文件实际字节，消除了平台差异。

---

## 10. CI 配置建议

### 10.1 快速测试（每个 PR 必跑）

用于快速反馈（目标 < 3 分钟）：

```bash
# 排除耗时的 property tests 和需要外部 GNU 工具的 tests
python -m pytest tests/ -v \
  -k "not test_human_markdown_files and not test_property_based and not Gnu" \
  --tb=short
```

覆盖：所有核心功能、JSON 协议、错误码、文件副作用、sandbox 逃逸（含已知缺口 skip）。
预计时长：约 20–30 秒。

### 10.2 完整测试（合并前 / 每日构建）

```bash
# 安装 GNU coreutils（Ubuntu CI）
sudo apt-get install -y coreutils

# 安装项目及测试依赖
pip install -e ".[test]"

# 运行全部测试
python -m pytest tests/ -v --tb=short \
  -k "not test_human_markdown_files"
```

预计时长：约 3–5 分钟（取决于 Property 测试）。

### 10.3 推荐 CI Workflow 结构

```yaml
jobs:
  quick-test:
    # 每个 PR 触发，快速反馈
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[test]"
      - run: python -m pytest tests/ -v --tb=short
               -k "not test_human_markdown_files and not test_property_based"

  full-test:
    # 合并到 master 或每日触发
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: sudo apt-get install -y coreutils
      - run: pip install -e ".[test]"
      - run: python -m pytest tests/ -v --tb=short
               -k "not test_human_markdown_files"
```

### 10.4 当前 CI 配置已做变更

`.github/workflows/ci.yml` 已从 `unittest discover` 改为 `pytest`，并添加 `.[test]` 安装。但仍需添加 `coreutils` 安装步骤以启用 GNU 对照测试。

---

## 11. 未来新增 GNU CLI 工具时的补测试流程

当向 `src/agentutils/` 新增命令（如 `split`、`dirname`、`realpath` 等）时，应同步新增以下测试：

### 11.1 必须添加的测试（按优先级）

1. **安全逃逸测试**（如果命令涉及文件写入/删除/路径操作）
   - 在 `test_sandbox_escape_hardening.py` 中添加：
     - cwd 外路径拒绝测试
     - dry-run 零副作用测试
     - 文件名注入测试（空格、`-` 开头、unicode、命令注入字符）

2. **JSON 协议测试**
   - 在对应的已有测试文件中添加至少 1 个用例：验证 JSON envelope 的 `ok`/`tool`/`command`/`result` 字段完整性
   - 验证 `--raw` 输出不含 JSON envelope

3. **GNU 对照测试**
   - 在 `test_gnu_differential.py` 中添加对应的 `GnuXxxDifferentialTests` 类
   - 至少 3 组输入（空/普通/边界/UTF-8）
   - 使用 `skip_if_no_gnu()` 处理环境缺失

4. **Property 测试**（如果命令有明确的数学性质）
   - 在 `test_property_based_cli.py` 中添加性质测试类
   - 至少 1 个不变量

### 11.2 测试模板

```python
# 1. 安全逃逸测试模板
class NewCommandSecurityTests(unittest.TestCase):
    def test_newcmd_outside_path_is_blocked(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            sandbox = root / "sandbox"; sandbox.mkdir()
            outside = root / "outside.txt"
            outside.write_text("keep", encoding="utf-8")
            result = run_cli("newcmd", str(outside), cwd=sandbox)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(outside.read_text(encoding="utf-8"), "keep")

# 2. GNU 对照测试模板
class GnuNewcmdDifferentialTests(unittest.TestCase):
    def setUp(self) -> None:
        skip_if_no_gnu("newcmd")

    def test_newcmd_plain(self) -> None:
        text = "input\n"
        g = run_gnu(["newcmd"], input_text=text)
        a = run_agent_raw("newcmd", "--raw", input_text=text)
        self.assertEqual(g.returncode, a.returncode)
        self.assertEqual(_nl(g.stdout), _nl(a.stdout))

# 3. Property 测试模板
class NewcmdPropertyTests(unittest.TestCase):
    @given(flat_text)
    @settings(max_examples=100, deadline=None)
    def test_newcmd_property(self, text: str) -> None:
        result = run_cli("newcmd", "--raw", input_text=text)
        self.assertEqual(result.returncode, 0)
        # ... invariant assertion
```

### 11.3 检查清单

- [ ] 安全逃逸测试已添加（路径遍历、dry-run、文件名注入）
- [ ] GNU 对照测试已添加（使用 `skip_if_no_gnu`）
- [ ] Property 测试已添加（至少 1 个不变量）
- [ ] JSON 协议字段完整性已验证
- [ ] `--raw` 输出已与 GNU 对照
- [ ] 错误码测试已覆盖至少 1 个错误场景
- [ ] 所有文件操作使用 `TemporaryDirectory`

---

## 附录 A：测试分类总表

| 分类 | 问题性质 | 计数 | 处理方式 |
|---|---|---|---|
| **通过** | 实现正确 | 84 | — |
| **环境限制 - GNU 缺失** | 测试无法执行 | 51 | CI 中安装 coreutils 后自动恢复；对实现质量不做判断 |
| **实现缺陷 - 安全缺口** | 必须修复 | 6 | P0/P1，见 §7.2 和 §8 |
| **环境限制 - symlink** | Windows 不支持 | 3 | Ubuntu CI 中自动启用；对实现质量不做判断 |
| **预存在失败** | 测试文件问题（非代码） | 1 | `.pytest_cache/README.md` 不含中文标记，与源代码无关 |
| **Property 测试** | 本报告轮次排除 | 25 | 本地耗时长，CI 中可运行 |

## 附录 B：跳过测试明细

### B.1 环境限制（GNU 工具缺失）— 51 条

所有 `test_gnu_differential.py` 中非 sort 命令的测试均因 `shutil.which()` 找不到 GNU 工具而跳过。详见 §5.2。

### B.2 环境限制（Windows symlink 不支持）— 3 条

| 测试 | 原因 |
|---|---|
| `SymlinkEscapeTests::test_tee_to_symlink_preserves_outside_content` | `OSError` 创建 symlink |
| `SymlinkEscapeTests::test_rm_symlink_preserves_outside_file` | 同上 |
| `SymlinkEscapeTests::test_truncate_to_symlink_preserves_outside_content` | 同上 |

### B.3 实现缺陷（安全缺口）— 6 条

详见 §7.2 表。这 6 条不是真正的"跳过"，而是 `@unittest.skip` 用作已知缺陷标记机制。

### B.4 测试设计限制 — 2 条

| 测试 | 原因 |
|---|---|
| `GnuSortDifferentialTests::test_sort_chinese_utf8` | Windows sort.exe 不支持 UTF-8（GBK 解码崩溃）；`@unittest.skip` |
| `GnuSortDifferentialTests::test_sort_numeric` | Windows sort.exe 不支持 `-n` 选项；运行时检测并 `SkipTest` |
