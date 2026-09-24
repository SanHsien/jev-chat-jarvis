[CmdletBinding()]
param(
    [switch]$Quick
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

Write-Host "==> Secret scan (sk-or- keys must never be committed)"
$hits = git grep -n -I -E "sk-or-[A-Za-z0-9-]{8,}" -- . ":!tools/dev_check.ps1"
if ($LASTEXITCODE -eq 0) {
    $hits | ForEach-Object { Write-Host $_ }
    throw "Found OpenRouter key-like strings in tracked files"
}

Write-Host "==> Python syntax check (tools/)"
python -m compileall -q tools
if ($LASTEXITCODE -ne 0) {
    throw "Python syntax check failed with exit code $LASTEXITCODE"
}

if (-not $Quick) {
    Write-Host "==> Android build (gradlew :app:assembleDebug)"
    & .\gradlew.bat --no-daemon :app:assembleDebug
    if ($LASTEXITCODE -ne 0) {
        throw "Android build failed with exit code $LASTEXITCODE"
    }
}

Write-Host "==> Check upstream updates"
python tools/check_upstream_updates.py --strict
if ($LASTEXITCODE -ne 0) {
    throw "Upstream check failed with exit code $LASTEXITCODE"
}

Write-Host "WINDOWS DEV CHECK GREEN"
