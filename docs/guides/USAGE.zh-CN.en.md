# AICoreUtils 使用说明 / User Guide

## 中文说明

`aicoreutils` 是一个面向 LLM Agent 的命令行工具包原型。它参考 GNU Coreutils
的常用工具，但把交互方式改成更适合机器调用的形式：默认输出 JSON，错误写入
stderr，退出码稳定明确，修改文件的命令支持 `--dry-run`。

它不是为了替代人类常用的 `ls`、`cat`、`rm` 等命令，而是为 Agent 提供一套更
容易解析、更少噪音、更安全的标准接口。

### 它解决什么问题

- Agent 不需要彩色表格、进度条或交互菜单，它需要稳定的结构化文本。
- Agent 需要根据退出码和错误对象判断下一步怎么做。
- Agent 调用文件修改命令前，通常需要先模拟执行，确认影响范围。
- Agent 需要按需发现工具能力，而不是一次性把所有工具 schema 塞进上下文。

### 已实现的命令

当前版本优先覆盖文件观察、安全文件修改，以及常用文本管道处理：

- 观察类：`pwd`、`basename`、`dirname`、`realpath`、`readlink`、`test`、`[`、`ls`、`dir`、`vdir`、`stat`、`cat`、`head`、`tail`、`wc`
- 校验类：`md5sum`、`sha1sum`、`sha224sum`、`sha256sum`、`sha384sum`、`sha512sum`、`b2sum`、`cksum`、`sum`
- 文本处理：`sort`、`comm`、`join`、`paste`、`shuf`、`tac`、`nl`、`fold`、`fmt`、`csplit`、`split`、`od`、`pr`、`ptx`、`numfmt`、`tsort`、`uniq`、`cut`、`tr`、`expand`、`unexpand`、`seq`
- 编码处理：`base64`、`base32`、`basenc`
- 系统上下文：`date`、`env`、`printenv`、`whoami`、`groups`、`id`、`uname`、`arch`、`hostname`、`hostid`、`logname`、`uptime`、`tty`、`users`、`who`、`nproc`、`df`、`du`
- 字节复制和同步：`dd`、`sync`、`dircolors`
- 基础输出和轻量计算：`printf`、`echo`、`pathchk`、`factor`、`expr`
- 有界执行和进程控制：`true`、`false`、`sleep`、`yes`、`timeout`、`nice`、`nohup`、`kill`
- 修改类：`mkdir`、`touch`、`cp`、`mv`、`rm`、`ln`、`link`、`chmod`、`chown`、`chgrp`、`truncate`、`mktemp`、`mkfifo`、`mknod`、`install`、`ginstall`、`tee`、`rmdir`、`unlink`、`shred`
- 元信息：`catalog`、`schema`

查看完整分类：

```powershell
aicoreutils catalog --pretty
```

查看 JSON 协议和退出码：

```powershell
aicoreutils schema --pretty
```

### 常用示例

列出当前目录：

```powershell
aicoreutils ls .
aicoreutils dir .
aicoreutils vdir .
```

递归列出目录，但限制深度和数量：

```powershell
aicoreutils ls . --recursive --max-depth 2 --limit 100
```

读取文件前 4096 字节：

```powershell
aicoreutils cat docs/reference/AGENTUTILS.md --max-bytes 4096
```

统计文件行数、词数、字符数和字节数：

```powershell
aicoreutils wc docs/reference/AGENTUTILS.md
```

判断路径是否是非空文件：

```powershell
aicoreutils test docs/reference/AGENTUTILS.md --file --non-empty
aicoreutils [ -f docs/reference/AGENTUTILS.md ]
```

解析路径：

```powershell
aicoreutils readlink --canonicalize docs/reference/AGENTUTILS.md
```

提取路径组件：

```powershell
aicoreutils basename src/aicoreutils/cli.py --suffix .py
aicoreutils dirname src/aicoreutils/cli.py
```

计算 SHA-256：

```powershell
aicoreutils sha256sum docs/reference/AGENTUTILS.md
aicoreutils cksum payload.bin
aicoreutils sum payload.bin
```

排序文本行：

```powershell
aicoreutils sort data.txt --numeric
```

比较、连接或按列合并文本：

```powershell
aicoreutils comm left.txt right.txt
aicoreutils join people.txt roles.txt --raw
aicoreutils paste a.txt b.txt --delimiter "|"
```

打乱、反转或转换制表符：

```powershell
aicoreutils shuf data.txt --seed 42
aicoreutils tac data.txt --raw
aicoreutils expand data.txt --tabs 4
aicoreutils unexpand data.txt --tabs 4 --all
```

编号、折行、重排段落、查看字节或格式化数字：

```powershell
aicoreutils nl data.txt --raw
aicoreutils fold data.txt --width 80
aicoreutils fmt notes.txt --width 72
aicoreutils csplit data.txt --pattern "^---$" --prefix part- --dry-run
aicoreutils pr notes.txt --page-length 60 --header Report --raw
aicoreutils ptx notes.txt --ignore-case --only agent
aicoreutils od payload.bin --format hex --max-bytes 64
aicoreutils numfmt 1536 --to-unit iec
aicoreutils tsort deps.txt
```

折叠相邻重复行：

```powershell
aicoreutils uniq data.txt --count
```

选择 TSV 的第 1 和第 3 列：

```powershell
aicoreutils cut data.tsv --fields 1,3
```

替换文本中的字面字符（支持 stdin、文件、内联输入）：

```powershell
aicoreutils tr --input "abc" "a-c" "A-C"
aicoreutils tr abc ABC --path data.txt
echo "hello" | aicoreutils tr --delete "aeiou"
```

编码文件内容：

```powershell
aicoreutils base64 payload.bin
aicoreutils basenc --base base64url payload.bin
```

查看时间、环境和系统上下文：

```powershell
aicoreutils date --utc
aicoreutils env PYTHONPATH
aicoreutils whoami
aicoreutils groups
aicoreutils id
aicoreutils uname
aicoreutils arch
aicoreutils hostname
aicoreutils hostid
aicoreutils logname
aicoreutils uptime
aicoreutils tty
aicoreutils users
aicoreutils who
aicoreutils nproc
aicoreutils df .
aicoreutils du . --max-depth 2
```

复制字节、同步文件系统或输出无颜色配置：

```powershell
# dd: GNU 传统风格 key=value operands（也支持 --input/--output 标志）
aicoreutils dd if=source.bin of=copy.bin bs=1024 count=1
aicoreutils dd --input source.bin --output copy.bin --bs 512 --count 2
aicoreutils dd if=source.bin of=copy.bin --dry-run
aicoreutils sync --dry-run
aicoreutils dircolors --raw
```

生成有界序列或重复文本：

```powershell
aicoreutils seq 1 2 9
aicoreutils printf "row:%s:%03d\n" alpha 7 --raw
aicoreutils echo hello agent --raw
aicoreutils factor 84
aicoreutils expr 3 ">" 2
aicoreutils pathchk "safe/path.txt" --portable
aicoreutils yes ok --count 3
aicoreutils sleep 1 --dry-run
aicoreutils timeout 5 -- python -c "print('ok')"
aicoreutils nice --dry-run -- python -c "print('ok')"
aicoreutils nohup --output agent.log --dry-run -- python -c "print('ok')"
aicoreutils kill 12345 --signal TERM --dry-run
```

模拟创建链接：

```powershell
aicoreutils ln source.txt linked.txt --dry-run
aicoreutils link source.txt hard-linked.txt --dry-run
```

模拟创建 FIFO：

```powershell
aicoreutils mkfifo pipe-name --dry-run
```

模拟拆分文件：

```powershell
aicoreutils split data.txt --lines 100 --prefix part- --dry-run
```

模拟修改权限：

```powershell
aicoreutils chmod 600 secret.txt --dry-run
aicoreutils chown 0:0 secret.txt --dry-run
aicoreutils chgrp 0 secret.txt --dry-run
```

截断文件到 0 字节：

```powershell
aicoreutils truncate log.txt --size 0
```

创建临时文件：

```powershell
aicoreutils mktemp --prefix agent. --suffix .tmp
```

模拟创建节点或安装文件：

```powershell
aicoreutils mknod placeholder --type regular --dry-run
aicoreutils install source.txt bin/tool --parents --dry-run
aicoreutils ginstall --directory bin --dry-run
```

管道与 stdin 输入：

```powershell
# 管道输入 — 大多数文本命令支持 stdin
echo "hello world" | aicoreutils wc
echo "abc" | aicoreutils tr a-z A-Z
echo "line1" | aicoreutils base64
printf "b\na\nc\n" | aicoreutils sort
printf "a\na\nb\n" | aicoreutils uniq --count
printf "name\tage\n" | aicoreutils cut --fields 1
echo "key\tval" | aicoreutils paste --delimiter "|" - -
cat file.txt | aicoreutils head --lines 5
tail -f log.txt | aicoreutils tee out.txt
```

把 stdin 写入文件：

```powershell
aicoreutils tee output.txt < input.txt
```

输出原始文本流，用于管道组合：

```powershell
aicoreutils sort data.txt --raw | aicoreutils head --lines 10 --raw
```

模拟删除目录，不实际修改文件系统：

```powershell
aicoreutils shred secret.txt --dry-run
aicoreutils rm coreutils-9.10 --recursive --dry-run
```

### 输出格式

成功时，结果写入 stdout：

```json
{"ok":true,"tool":"aicoreutils","version":"0.1.0","command":"pwd","result":{"path":"C:\\Users\\example\\project"},"warnings":[]}
```

失败时，错误写入 stderr：

```json
{"ok":false,"tool":"aicoreutils","version":"0.1.0","command":"cat","error":{"code":"not_found","message":"Path does not exist.","path":"missing.txt"}}
```

### 退出码

- `0`：成功
- `2`：参数或用法错误
- `3`：路径不存在
- `4`：权限不足
- `5`：输入无效
- `6`：目标冲突，例如目标文件已存在
- `7`：部分失败
- `8`：被安全策略阻止
- `10`：I/O 错误

### 适合谁使用

- 正在开发 LLM Agent、自动化脚本或代码助手的人
- 想把传统 CLI 包装成机器友好接口的人
- 需要低噪音、可解析、可组合命令输出的工具开发者

---

## English Guide

`aicoreutils` is a prototype command-line toolkit designed for LLM agents. It is
inspired by common GNU Coreutils commands, but reshapes the interface for
machine callers: JSON output by default, JSON errors on stderr, stable semantic
exit codes, and `--dry-run` support for file mutation commands.

It is not meant to replace human-friendly commands like `ls`, `cat`, or `rm`.
Instead, it gives agents a quieter, safer, and easier-to-parse command surface.

### What Problem It Solves

- Agents do not need colored tables, progress bars, or interactive menus. They
  need stable structured text.
- Agents need clear exit codes and error objects to decide what to do next.
- Agents often need to preview file mutations before changing the filesystem.
- Agents benefit from on-demand discovery instead of loading every tool schema
  into context up front.

### Implemented Commands

The current version focuses on filesystem observation, safe mutation, and common
text pipeline operations:

- Observation: `pwd`, `basename`, `dirname`, `realpath`, `readlink`, `test`, `[`,
  `ls`, `dir`, `vdir`, `stat`, `cat`, `head`, `tail`, `wc`
- Checksums: `md5sum`, `sha1sum`, `sha224sum`, `sha256sum`, `sha384sum`,
  `sha512sum`, `b2sum`, `cksum`, `sum`
- Text transforms: `sort`, `comm`, `join`, `paste`, `shuf`, `tac`, `nl`,
  `fold`, `fmt`, `csplit`, `split`, `od`, `pr`, `ptx`, `numfmt`, `tsort`, `uniq`, `cut`, `tr`,
  `expand`, `unexpand`, `seq`
- Encoders: `base64`, `base32`, `basenc`
- System context: `date`, `env`, `printenv`, `whoami`, `id`, `uname`,
  `groups`, `arch`, `hostname`, `hostid`, `logname`, `uptime`, `tty`, `users`,
  `who`, `nproc`, `df`, `du`
- Byte copy and sync: `dd`, `sync`, `dircolors`
- Basic output and lightweight calculation: `printf`, `echo`, `pathchk`,
  `factor`, `expr`
- Bounded execution and process control: `true`, `false`, `sleep`, `yes`,
  `timeout`, `nice`, `nohup`, `kill`
- Mutation: `mkdir`, `touch`, `cp`, `mv`, `rm`, `ln`, `chmod`, `truncate`,
  `chown`, `chgrp`, `link`, `mktemp`, `mkfifo`, `mknod`, `install`,
  `ginstall`, `tee`, `rmdir`, `unlink`, `shred`
- Metadata: `catalog`, `schema`

Print the prioritized catalog:

```powershell
aicoreutils catalog --pretty
```

Print the JSON protocol and exit codes:

```powershell
aicoreutils schema --pretty
```

### Common Examples

List the current directory:

```powershell
aicoreutils ls .
aicoreutils dir .
aicoreutils vdir .
```

List recursively with bounded depth and output size:

```powershell
aicoreutils ls . --recursive --max-depth 2 --limit 100
```

Read the first 4096 bytes of a file:

```powershell
aicoreutils cat docs/reference/AGENTUTILS.md --max-bytes 4096
```

Count lines, words, characters, and bytes:

```powershell
aicoreutils wc docs/reference/AGENTUTILS.md
```

Test that a path is a non-empty file:

```powershell
aicoreutils test docs/reference/AGENTUTILS.md --file --non-empty
aicoreutils [ -f docs/reference/AGENTUTILS.md ]
```

Resolve a path:

```powershell
aicoreutils readlink --canonicalize docs/reference/AGENTUTILS.md
```

Extract path components:

```powershell
aicoreutils basename src/aicoreutils/cli.py --suffix .py
aicoreutils dirname src/aicoreutils/cli.py
```

Calculate SHA-256:

```powershell
aicoreutils sha256sum docs/reference/AGENTUTILS.md
aicoreutils cksum payload.bin
aicoreutils sum payload.bin
```

Sort text lines:

```powershell
aicoreutils sort data.txt --numeric
```

Compare, join, or merge text columns:

```powershell
aicoreutils comm left.txt right.txt
aicoreutils join people.txt roles.txt --raw
aicoreutils paste a.txt b.txt --delimiter "|"
```

Shuffle, reverse, or convert tabs:

```powershell
aicoreutils shuf data.txt --seed 42
aicoreutils tac data.txt --raw
aicoreutils expand data.txt --tabs 4
aicoreutils unexpand data.txt --tabs 4 --all
```

Number lines, wrap text, reflow paragraphs, dump bytes, or format numbers:

```powershell
aicoreutils nl data.txt --raw
aicoreutils fold data.txt --width 80
aicoreutils fmt notes.txt --width 72
aicoreutils csplit data.txt --pattern "^---$" --prefix part- --dry-run
aicoreutils pr notes.txt --page-length 60 --header Report --raw
aicoreutils ptx notes.txt --ignore-case --only agent
aicoreutils od payload.bin --format hex --max-bytes 64
aicoreutils numfmt 1536 --to-unit iec
aicoreutils tsort deps.txt
```

Collapse adjacent duplicate lines:

```powershell
aicoreutils uniq data.txt --count
```

Select the first and third TSV fields:

```powershell
aicoreutils cut data.tsv --fields 1,3
```

Translate literal characters (supports stdin, file, inline input):

```powershell
aicoreutils tr --input "abc" "a-c" "A-C"
aicoreutils tr abc ABC --path data.txt
echo "hello" | aicoreutils tr --delete "aeiou"
```

Encode file content:

```powershell
aicoreutils base64 payload.bin
aicoreutils basenc --base base64url payload.bin
```

Inspect time, environment, and system context:

```powershell
aicoreutils date --utc
aicoreutils env PYTHONPATH
aicoreutils whoami
aicoreutils groups
aicoreutils id
aicoreutils uname
aicoreutils arch
aicoreutils hostname
aicoreutils hostid
aicoreutils logname
aicoreutils uptime
aicoreutils tty
aicoreutils users
aicoreutils who
aicoreutils nproc
aicoreutils df .
aicoreutils du . --max-depth 2
```

Copy bytes, sync the filesystem, or emit a no-color config:

```powershell
# dd: GNU-style key=value operands (also supports --input/--output flags)
aicoreutils dd if=source.bin of=copy.bin bs=1024 count=1
aicoreutils dd --input source.bin --output copy.bin --bs 512 --count 2
aicoreutils dd if=source.bin of=copy.bin --dry-run
aicoreutils sync --dry-run
aicoreutils dircolors --raw
```

Generate bounded sequences or repeated text:

```powershell
aicoreutils seq 1 2 9
aicoreutils printf "row:%s:%03d\n" alpha 7 --raw
aicoreutils echo hello agent --raw
aicoreutils factor 84
aicoreutils expr 3 ">" 2
aicoreutils pathchk "safe/path.txt" --portable
aicoreutils yes ok --count 3
aicoreutils sleep 1 --dry-run
aicoreutils timeout 5 -- python -c "print('ok')"
aicoreutils nice --dry-run -- python -c "print('ok')"
aicoreutils nohup --output agent.log --dry-run -- python -c "print('ok')"
aicoreutils kill 12345 --signal TERM --dry-run
```

Preview link creation:

```powershell
aicoreutils ln source.txt linked.txt --dry-run
aicoreutils link source.txt hard-linked.txt --dry-run
```

Preview FIFO creation:

```powershell
aicoreutils mkfifo pipe-name --dry-run
```

Preview file splitting:

```powershell
aicoreutils split data.txt --lines 100 --prefix part- --dry-run
```

Preview a mode change:

```powershell
aicoreutils chmod 600 secret.txt --dry-run
aicoreutils chown 0:0 secret.txt --dry-run
aicoreutils chgrp 0 secret.txt --dry-run
```

Truncate a file to 0 bytes:

```powershell
aicoreutils truncate log.txt --size 0
```

Create a temporary file:

```powershell
aicoreutils mktemp --prefix agent. --suffix .tmp
```

Preview node creation or file installation:

```powershell
aicoreutils mknod placeholder --type regular --dry-run
aicoreutils install source.txt bin/tool --parents --dry-run
aicoreutils ginstall --directory bin --dry-run
```

Pipes and stdin input:

```powershell
# Pipe input — most text commands accept stdin
echo "hello world" | aicoreutils wc
echo "abc" | aicoreutils tr a-z A-Z
echo "line1" | aicoreutils base64
printf "b\na\nc\n" | aicoreutils sort
printf "a\na\nb\n" | aicoreutils uniq --count
printf "name\tage\n" | aicoreutils cut --fields 1
cat file.txt | aicoreutils head --lines 5
tail -f log.txt | aicoreutils tee out.txt
# tr --input for inline text input (no pipe needed)
aicoreutils tr --input "abc" "a-c" "A-C"
```

Write stdin to a file:

```powershell
aicoreutils tee output.txt < input.txt
```

Remove an empty directory:

```powershell
aicoreutils rmdir empty-dir --dry-run
```

Use raw text output for pipeline composition:

```powershell
aicoreutils sort data.txt --raw | aicoreutils head --lines 10 --raw
```

Preview a recursive delete without changing the filesystem:

```powershell
aicoreutils shred secret.txt --dry-run
aicoreutils rm coreutils-9.10 --recursive --dry-run
```

### Output Format

On success, the result is written to stdout:

```json
{"ok":true,"tool":"aicoreutils","version":"0.1.0","command":"pwd","result":{"path":"C:\\Users\\example\\project"},"warnings":[]}
```

On failure, the error is written to stderr:

```json
{"ok":false,"tool":"aicoreutils","version":"0.1.0","command":"cat","error":{"code":"not_found","message":"Path does not exist.","path":"missing.txt"}}
```

### Exit Codes

- `0`: success
- `2`: usage error
- `3`: path not found
- `4`: permission denied
- `5`: invalid input
- `6`: conflict, such as an existing destination
- `7`: partial failure
- `8`: blocked by safety policy
- `10`: I/O error

### Who It Is For

- Developers building LLM agents, automation scripts, or coding assistants
- Tool authors wrapping traditional CLIs with machine-friendly interfaces
- Anyone who needs quiet, parseable, composable command output
