# WSL 本地 CI / WSL Local CI

## 中文说明

### 目标

Windows 本地开发时，普通 PowerShell 环境无法完整验证 GNU Coreutils 对照测试：

- Windows 缺少大多数 GNU 命令，`tests/test_gnu_differential.py` 会大量 skip。
- GitHub Actions 的 Ubuntu job 会安装 `coreutils`，行为更接近真实 CI。
- WSL/Ubuntu 是本地复现 Ubuntu CI 的首选环境。

### 安装 WSL

当前 Codex 进程没有管理员权限时，不能直接启用 WSL。请在**管理员 PowerShell** 中执行：

```powershell
wsl --install -d Ubuntu
```

如果 Windows 要求重启，重启后打开一次 Ubuntu，按提示创建 Linux 用户。

验证：

```powershell
wsl --status
wsl -l -v
```

### 安装网络故障处理

如果 `wsl --install`、Microsoft Store 或 WSL 在线安装包下载报
`WININET_E_CANNOT_CONNECT`，先确认浏览器能访问 Microsoft 下载域名，再检查当前
网络适配器的 IPv4 DNS。必要时可在**管理员 PowerShell** 中临时切换为稳定公共 DNS，例如：

```powershell
Get-NetAdapter | Where-Object Status -eq Up
Set-DnsClientServerAddress -InterfaceAlias "WLAN" -ServerAddresses 1.1.1.1,8.8.8.8
Clear-DnsClientCache
```

完成安装后，如需恢复路由器 DNS，可执行：

```powershell
Set-DnsClientServerAddress -InterfaceAlias "WLAN" -ResetServerAddresses
Clear-DnsClientCache
```

### 本地运行 Ubuntu CI 等价检查

在仓库根目录的 Windows PowerShell 中运行：

```powershell
.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps
```

该命令会进入 WSL 并执行 `.github/scripts/wsl-ci.sh`，内容与 GitHub Actions Ubuntu job 对齐：

1. 可选安装 `coreutils`、`python3-venv`、`python3-pip`。
2. 创建并使用 `.venv-wsl`，避免污染 Windows `.venv`。
3. 安装 `.[test,dev]`。
4. 运行 `ruff check src/ tests/`。
5. 运行 `ruff format --check src/ tests/`。
6. 运行 `mypy src/agentutils/ --strict`。
7. 运行 `PYTHONPATH=src python -m pytest tests/ -v --tb=short --cov=src/agentutils --cov-report=term-missing`。

复用已安装环境：

```powershell
.\.github\scripts\run-ci-wsl.ps1 -SkipInstall
```

指定发行版或 Python：

```powershell
.\.github\scripts\run-ci-wsl.ps1 -Distro Ubuntu -Python python3.13 -InstallSystemDeps
```

### 结果判定

- 本地 PowerShell 测试通过只能证明 Windows 侧路径、编码、sandbox 测试通过。
- WSL 测试通过才能本地证明 Ubuntu/coreutils 对照测试大部分实际运行。
- WSL 测试通过仍不等于远程 GitHub Actions 已通过；最终状态以远程 CI run 为准。

---

## English

### Goal

Plain Windows PowerShell cannot fully validate GNU Coreutils differential tests:

- Windows does not provide most GNU commands, so `tests/test_gnu_differential.py` skips many cases.
- GitHub Actions installs `coreutils` in the Ubuntu job.
- WSL/Ubuntu is the preferred local environment for reproducing the Ubuntu CI job.

### Install WSL

If the current Codex process is not elevated, it cannot enable WSL directly. Run this in an **elevated PowerShell** window:

```powershell
wsl --install -d Ubuntu
```

Restart if Windows asks, then open Ubuntu once and create the Linux user.

Verify:

```powershell
wsl --status
wsl -l -v
```

### Install Network Troubleshooting

If `wsl --install`, Microsoft Store, or the WSL online installer fails with
`WININET_E_CANNOT_CONNECT`, first verify that Microsoft download domains are
reachable in a browser, then check the active adapter's IPv4 DNS. If needed,
temporarily switch to stable public DNS from an **elevated PowerShell**:

```powershell
Get-NetAdapter | Where-Object Status -eq Up
Set-DnsClientServerAddress -InterfaceAlias "WLAN" -ServerAddresses 1.1.1.1,8.8.8.8
Clear-DnsClientCache
```

After installation, reset to router/DHCP-provided DNS if desired:

```powershell
Set-DnsClientServerAddress -InterfaceAlias "WLAN" -ResetServerAddresses
Clear-DnsClientCache
```

### Run the Ubuntu CI Equivalent Locally

From the repository root in Windows PowerShell:

```powershell
.\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps
```

This enters WSL and runs `.github/scripts/wsl-ci.sh`, mirroring the GitHub Actions Ubuntu job:

1. Optionally install `coreutils`, `python3-venv`, and `python3-pip`.
2. Create and use `.venv-wsl` so the Windows `.venv` is not reused.
3. Install `.[test,dev]`.
4. Run `ruff check src/ tests/`.
5. Run `ruff format --check src/ tests/`.
6. Run `mypy src/agentutils/ --strict`.
7. Run `PYTHONPATH=src python -m pytest tests/ -v --tb=short --cov=src/agentutils --cov-report=term-missing`.

Reuse an existing environment:

```powershell
.\.github\scripts\run-ci-wsl.ps1 -SkipInstall
```

Specify a different distro or Python version:

```powershell
.\.github\scripts\run-ci-wsl.ps1 -Distro Ubuntu -Python python3.13 -InstallSystemDeps
```

### Result Semantics

- Passing in Windows PowerShell proves Windows path, encoding, and sandbox coverage.
- Passing in WSL proves most Ubuntu/coreutils differential tests actually ran locally.
- Passing in WSL is still not the same as passing remote GitHub Actions; remote CI remains the final release gate.
