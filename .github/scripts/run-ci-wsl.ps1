param(
    [string]$Distro = "",
    [string]$Python = "python3",
    [switch]$InstallSystemDeps,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$scriptPath = "./.github/scripts/wsl-ci.sh"

function Quote-BashArg([string]$Value) {
    return "'" + ($Value -replace "'", "'\''") + "'"
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$wslList = & wsl.exe -l -q 2>$null
$wslExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($wslExitCode -ne 0 -or -not $wslList) {
    Write-Host @"
WSL is not installed or no Linux distribution is registered.

Run this from an elevated PowerShell window:
  wsl --install -d Ubuntu

Then restart if Windows asks, open Ubuntu once to create the user, and rerun:
  .\.github\scripts\run-ci-wsl.ps1 -InstallSystemDeps
"@
    exit 2
}

$scriptArgs = @("--python", $Python)
if ($InstallSystemDeps) { $scriptArgs += "--install-system-deps" }
if ($SkipInstall) { $scriptArgs += "--skip-install" }

$bashCommand = "bash " + (Quote-BashArg $scriptPath) + " " + (($scriptArgs | ForEach-Object { Quote-BashArg $_ }) -join " ")

$wslArgs = @()
if ($Distro) {
    $wslArgs += @("-d", $Distro)
}
$wslArgs += @("--cd", $repoRoot, "bash", "-lc", $bashCommand)

& wsl.exe @wslArgs
exit $LASTEXITCODE
