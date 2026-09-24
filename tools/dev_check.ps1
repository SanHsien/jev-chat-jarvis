[CmdletBinding()]
param(
    # Skip the Android build (no JDK / SDK needed).
    [switch]$Quick,
    # Skip the upstream check (offline, or CI where upstream movement must not fail the build).
    [switch]$SkipUpstream
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Machine-specific JAVA_HOME / ANDROID_HOME / GRADLE_USER_HOME (gitignored).
$envScript = Join-Path $repoRoot "env.ps1"
if (Test-Path -LiteralPath $envScript) {
    . $envScript
}

if ($repoRoot -match '[^\x00-\x7F]') {
    throw "Repository path must be ASCII-only for the Android toolchain: $repoRoot"
}

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (Get-Command python -ErrorAction Stop).Source
}

function Invoke-Step {
    param(
        [Parameter(Mandatory)]
        [string]$Label,
        [Parameter(Mandatory)]
        [string]$Exe,
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    Write-Host "==> $Label"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

Write-Host "==> Secret scan (sk-or- keys must never be committed)"
$hits = git grep -n -I -E "sk-or-[A-Za-z0-9-]{8,}" -- . ":!tools/dev_check.ps1"
if ($LASTEXITCODE -eq 0) {
    $hits | ForEach-Object { Write-Host $_ }
    throw "Found OpenRouter key-like strings in tracked files"
}

Invoke-Step -Label "Ruff check" -Exe $pythonExe -Arguments @("-m", "ruff", "check", ".")
Invoke-Step -Label "Ruff format --check" -Exe $pythonExe -Arguments @("-m", "ruff", "format", "--check", ".")
Invoke-Step -Label "Pytest" -Exe $pythonExe -Arguments @("-m", "pytest", "-q")
Invoke-Step -Label "Python syntax (tools/)" -Exe $pythonExe -Arguments @("-m", "compileall", "-q", "tools")
Invoke-Step -Label "Markdown links" -Exe $pythonExe -Arguments @("tools\check_links.py")
Invoke-Step -Label "Divergence registry" -Exe $pythonExe -Arguments @("tools\check_divergence.py")

if (-not $Quick) {
    Invoke-Step -Label "Android build (gradlew :app:assembleDebug)" -Exe ".\gradlew.bat" -Arguments @("--no-daemon", ":app:assembleDebug")
}

if (-not $SkipUpstream) {
    Invoke-Step -Label "Upstream check" -Exe $pythonExe -Arguments @("tools\check_upstream_updates.py", "--strict")
}

Write-Host "WINDOWS DEV CHECK GREEN"
