# AICoreUtils 协议说明 / Protocol

## 中文说明

`aicoreutils` 是受 GNU Coreutils 启发的 Agent 优先 CLI 层。它保留 Unix
“小工具、可组合”的模型，但把接口契约调整为更适合机器调用：

- 成功结果默认写入 stdout，格式为 JSON
- 错误默认写入 stderr，格式为 JSON
- 退出码稳定且语义化
- 修改文件的命令提供 `--dry-run`
- 危险操作需要显式参数确认
- 输出确定、有界，并避免颜色、进度条和欢迎语等噪音
- 需要管道组合时显式使用 `--raw`

### 优先级模型

当前实现按照以下优先级组织 GNU Coreutils 风格命令：

1. P0 `read_observe_and_decide`：观察、读取和判断。已覆盖 `ls`、`stat`、
   `dir`、`vdir`、`cat`、`head`、`tail`、`wc`、`pwd`、`basename`、`dirname`、
   `realpath`、`readlink`、`test`、`[`、`md5sum`、`sha256sum`。
2. P1 `mutate_files_safely`：安全修改文件系统。已覆盖 `cp`、`mv`、`rm`、
   `mkdir`、`touch`、`ln`、`link`、`chmod`、`chown`、`chgrp`、`truncate`、
   `mktemp`、`mkfifo`、`mknod`、`install`、`ginstall`、`tee`、`rmdir`、
   `unlink`、`shred`。
3. P2 `transform_and_compose_text`：文本处理、编码和校验。已覆盖 `sort`、
   `comm`、`join`、`paste`、`shuf`、`tac`、`nl`、`fold`、`fmt`、`csplit`、
   `split`、`od`、`pr`、`ptx`、`numfmt`、`tsort`、`uniq`、`cut`、`tr`、`expand`、`unexpand`、
   `base64`、`base32`、`basenc`、`seq`、`cksum`、`sum`、`b2sum`、`sha1sum`、
   `sha224sum`、`sha384sum`、`sha512sum`。
4. P3 `system_context_and_execution`：系统上下文和有界执行。已覆盖 `date`、
   `env`、`printenv`、`whoami`、`groups`、`id`、`uname`、`arch`、`hostname`、
   `hostid`、`logname`、`uptime`、`tty`、`users`、`who`、`nproc`、`df`、`du`、
   `dd`、`sync`、`dircolors`、`printf`、`echo`、`pathchk`、`factor`、`expr`、
   `true`、`false`、`sleep`、`yes`、`timeout`、`nice`、`nohup`、`kill`。

查看完整分类：

```powershell
python -m agentutils catalog --pretty
```

### JSON 协议

成功时写入 stdout：

```json
{"ok":true,"tool":"aicoreutils","version":"0.2.0","command":"ls","result":{},"warnings":[]}
```

失败时写入 stderr：

```json
{"ok":false,"tool":"aicoreutils","version":"0.2.0","command":"cat","error":{"code":"not_found","message":"Path does not exist.","path":"missing.txt"}}
```

退出码：

- `0`：成功
- `1`：谓词为假或 `false` 命令
- `2`：参数或用法错误
- `3`：路径不存在
- `4`：权限不足
- `5`：输入无效
- `6`：目标冲突
- `7`：部分失败
- `8`：被安全策略阻止
- `10`：I/O 错误

### 示例

```powershell
python -m agentutils schema --pretty
python -m agentutils ls . --recursive --max-depth 1
python -m agentutils dir .
python -m agentutils vdir .
python -m agentutils basename src/aicoreutils/cli.py --suffix .py
python -m agentutils dirname src/aicoreutils/cli.py
python -m agentutils stat docs/reference/AGENTUTILS.md
python -m agentutils cat docs/reference/AGENTUTILS.md --max-bytes 4096
python -m agentutils test docs/reference/AGENTUTILS.md --file --non-empty
python -m agentutils [ -f docs/reference/AGENTUTILS.md ]
python -m agentutils sha256sum docs/reference/AGENTUTILS.md
python -m agentutils sort data.txt --numeric
python -m agentutils comm left.txt right.txt
python -m agentutils join people.txt roles.txt --raw
python -m agentutils nl data.txt --raw
python -m agentutils fold data.txt --width 80
python -m agentutils fmt notes.txt --width 72
python -m agentutils csplit data.txt --pattern "^---$" --prefix part- --dry-run
python -m agentutils split data.txt --lines 100 --prefix part- --dry-run
python -m agentutils od payload.bin --format hex --max-bytes 64
python -m agentutils pr notes.txt --page-length 60 --header Report --raw
python -m agentutils ptx notes.txt --ignore-case --only agent
python -m agentutils numfmt 1536 --to-unit iec
python -m agentutils tsort deps.txt
python -m agentutils cut data.tsv --fields 1,3
python -m agentutils expand data.txt --tabs 4
python -m agentutils base64 payload.bin
python -m agentutils basenc --base base64url payload.bin
python -m agentutils cksum payload.bin
python -m agentutils date --utc
python -m agentutils hostname
python -m agentutils uptime
python -m agentutils who
python -m agentutils dd --input payload.bin --output copy.bin --count 1 --dry-run
python -m agentutils dircolors --raw
python -m agentutils printf "row:%s:%03d\n" alpha 7 --raw
python -m agentutils factor 84
python -m agentutils expr 3 ">" 2
python -m agentutils pathchk "safe/path.txt" --portable
python -m agentutils env PYTHONPATH
python -m agentutils df .
python -m agentutils du . --max-depth 2
python -m agentutils timeout 5 -- python -c "print('ok')"
python -m agentutils nice --dry-run -- python -c "print('ok')"
python -m agentutils nohup --output agent.log --dry-run -- python -c "print('ok')"
python -m agentutils kill 12345 --signal TERM --dry-run
python -m agentutils seq 1 2 9
python -m agentutils mkdir scratch --dry-run
python -m agentutils chown 0:0 target.txt --dry-run
python -m agentutils install source.txt bin/tool --parents --dry-run
python -m agentutils shred secret.txt --dry-run
python -m agentutils rm scratch --recursive --dry-run
```

管道类命令默认输出 JSON；如果需要原始 stdout 流，使用 `--raw`：

```powershell
Get-Content data.txt | python -m agentutils sort --raw
```

### 说明

本项目不会修改解压后的 GNU Coreutils 上游源码。长期生产化方向可以是把这些
协议决策移植到 C 实现中，或在原始 GNU 工具旁生成 wrapper。当前目标是先提供
一组 Agent 今天就能稳定调用的 JSON 优先工具。

---

## English

`aicoreutils` is an agent-first CLI layer inspired by GNU Coreutils. It keeps the
Unix model of small composable commands, but changes the interface contract for
machine callers:

- Successful results are written to stdout as JSON
- Errors are written to stderr as JSON
- Exit codes are stable and semantic
- Mutation commands expose `--dry-run`
- Dangerous operations require explicit confirmation flags
- Outputs are deterministic, bounded, and free of color/progress/welcome noise
- Raw pipeline output requires explicit `--raw`

### Priority Model

The current implementation groups GNU Coreutils-style commands by priority:

1. P0 `read_observe_and_decide`: observation, reading, and predicates. Covered:
   `ls`, `dir`, `vdir`, `stat`, `cat`, `head`, `tail`, `wc`, `pwd`,
   `basename`, `dirname`, `realpath`, `readlink`, `test`, `[`, `md5sum`,
   `sha256sum`.
2. P1 `mutate_files_safely`: safe filesystem mutation. Covered: `cp`, `mv`,
   `rm`, `mkdir`, `touch`, `ln`, `link`, `chmod`, `chown`, `chgrp`,
   `truncate`, `mktemp`, `mkfifo`, `mknod`, `install`, `ginstall`, `tee`,
   `rmdir`, `unlink`, `shred`.
3. P2 `transform_and_compose_text`: text transforms, encoders, and checksums.
   Covered: `sort`, `comm`, `join`, `paste`, `shuf`, `tac`, `nl`, `fold`,
   `fmt`, `csplit`, `split`, `od`, `pr`, `ptx`, `numfmt`, `tsort`, `uniq`, `cut`, `tr`, `expand`,
   `unexpand`, `base64`, `base32`, `basenc`, `seq`, `cksum`, `sum`, `b2sum`,
   `sha1sum`, `sha224sum`, `sha384sum`, `sha512sum`.
4. P3 `system_context_and_execution`: system context and bounded execution.
   Covered: `date`, `env`, `printenv`, `whoami`, `groups`, `id`, `uname`,
   `arch`, `hostname`, `hostid`, `logname`, `uptime`, `tty`, `users`, `who`,
   `nproc`, `df`, `du`, `dd`, `sync`, `dircolors`, `printf`, `echo`,
   `pathchk`, `factor`, `expr`, `true`, `false`, `sleep`, `yes`,
   `timeout`, `nice`, `nohup`, `kill`.

Print the complete catalog:

```powershell
python -m agentutils catalog --pretty
```

### JSON Protocol

Success is written to stdout:

```json
{"ok":true,"tool":"aicoreutils","version":"0.2.0","command":"ls","result":{},"warnings":[]}
```

Errors are written to stderr:

```json
{"ok":false,"tool":"aicoreutils","version":"0.2.0","command":"cat","error":{"code":"not_found","message":"Path does not exist.","path":"missing.txt"}}
```

Exit codes:

- `0`: success
- `1`: predicate false or the `false` command
- `2`: usage error
- `3`: path not found
- `4`: permission denied
- `5`: invalid input
- `6`: conflict
- `7`: partial failure
- `8`: blocked by safety policy
- `10`: I/O error

### Examples

```powershell
python -m agentutils schema --pretty
python -m agentutils ls . --recursive --max-depth 1
python -m agentutils dir .
python -m agentutils vdir .
python -m agentutils basename src/aicoreutils/cli.py --suffix .py
python -m agentutils dirname src/aicoreutils/cli.py
python -m agentutils stat docs/reference/AGENTUTILS.md
python -m agentutils cat docs/reference/AGENTUTILS.md --max-bytes 4096
python -m agentutils test docs/reference/AGENTUTILS.md --file --non-empty
python -m agentutils [ -f docs/reference/AGENTUTILS.md ]
python -m agentutils sha256sum docs/reference/AGENTUTILS.md
python -m agentutils sort data.txt --numeric
python -m agentutils comm left.txt right.txt
python -m agentutils join people.txt roles.txt --raw
python -m agentutils nl data.txt --raw
python -m agentutils fold data.txt --width 80
python -m agentutils fmt notes.txt --width 72
python -m agentutils csplit data.txt --pattern "^---$" --prefix part- --dry-run
python -m agentutils split data.txt --lines 100 --prefix part- --dry-run
python -m agentutils od payload.bin --format hex --max-bytes 64
python -m agentutils pr notes.txt --page-length 60 --header Report --raw
python -m agentutils ptx notes.txt --ignore-case --only agent
python -m agentutils numfmt 1536 --to-unit iec
python -m agentutils tsort deps.txt
python -m agentutils cut data.tsv --fields 1,3
python -m agentutils expand data.txt --tabs 4
python -m agentutils base64 payload.bin
python -m agentutils basenc --base base64url payload.bin
python -m agentutils cksum payload.bin
python -m agentutils date --utc
python -m agentutils hostname
python -m agentutils uptime
python -m agentutils who
python -m agentutils dd --input payload.bin --output copy.bin --count 1 --dry-run
python -m agentutils dircolors --raw
python -m agentutils printf "row:%s:%03d\n" alpha 7 --raw
python -m agentutils factor 84
python -m agentutils expr 3 ">" 2
python -m agentutils pathchk "safe/path.txt" --portable
python -m agentutils env PYTHONPATH
python -m agentutils df .
python -m agentutils du . --max-depth 2
python -m agentutils timeout 5 -- python -c "print('ok')"
python -m agentutils nice --dry-run -- python -c "print('ok')"
python -m agentutils nohup --output agent.log --dry-run -- python -c "print('ok')"
python -m agentutils kill 12345 --signal TERM --dry-run
python -m agentutils seq 1 2 9
python -m agentutils mkdir scratch --dry-run
python -m agentutils chown 0:0 target.txt --dry-run
python -m agentutils install source.txt bin/tool --parents --dry-run
python -m agentutils shred secret.txt --dry-run
python -m agentutils rm scratch --recursive --dry-run
```

Pipeline-oriented commands use JSON by default. Use `--raw` when a plain stdout
stream is needed:

```powershell
Get-Content data.txt | python -m agentutils sort --raw
```

### Notes

This project does not modify the extracted GNU Coreutils upstream source. A
long-term production fork can later port these protocol decisions into C or
generate wrappers beside the original utilities. The current milestone is a
small, reliable JSON-first command surface that agents can call today.
