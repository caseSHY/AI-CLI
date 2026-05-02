# GNU Coreutils 上游缓存 / Upstream Cache

## 中文说明

这个目录用于保存本地 GNU Coreutils 源码缓存，作为开发 Agentutils 时的参考。

下载得到的 `coreutils-9.10` 源码目录和 `coreutils-9.10.tar.xz` 压缩包默认被
Git 忽略，以保持仓库体积较小，并让仓库重点放在 Agentutils 自身实现上。

当前本地缓存预期路径：

```text
vendor/gnu-coreutils/coreutils-9.10/
vendor/gnu-coreutils/coreutils-9.10.tar.xz
vendor/gnu-coreutils/coreutils-9.10.tar.xz.sig
```

如需恢复缓存，请从 GNU 官方目录下载 Coreutils：

```text
https://ftp.gnu.org/gnu/coreutils/
```

---

## English

This directory stores the local GNU Coreutils source cache used as a reference
while developing Agentutils.

The downloaded `coreutils-9.10` source tree and `coreutils-9.10.tar.xz` archive
are ignored by Git by default to keep the repository small and focused on the
Agentutils implementation.

Current local cache paths:

```text
vendor/gnu-coreutils/coreutils-9.10/
vendor/gnu-coreutils/coreutils-9.10.tar.xz
vendor/gnu-coreutils/coreutils-9.10.tar.xz.sig
```

To restore the cache, download GNU Coreutils from:

```text
https://ftp.gnu.org/gnu/coreutils/
```
