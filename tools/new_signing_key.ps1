[CmdletBinding()]
param(
    # Where the keystore and its properties file go. Must be OUTSIDE the repository.
    [string]$OutDir = (Join-Path $HOME "jev-signing"),
    [string]$Alias = "jev",
    [string]$Repo = "SanHsien/jev-chat-jarvis",
    [int]$ValidityDays = 10000,
    # Regenerate even if a keystore already exists (an app signed with the old key
    # can then no longer be updated in place -- only use this on purpose).
    [switch]$Force
)

# Generates the release signing key locally and stores it as GitHub Actions secrets
# for .github/workflows/release.yml. The private key never leaves this machine except
# as the encrypted repository secret. Needs: JDK 17 (keytool) and an authenticated gh.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outFull = [IO.Path]::GetFullPath($OutDir)
if ($outFull.StartsWith([IO.Path]::GetFullPath($repoRoot), [StringComparison]::OrdinalIgnoreCase)) {
    throw "OutDir must be outside the repository: $outFull"
}

$envScript = Join-Path $repoRoot "env.ps1"
if (Test-Path -LiteralPath $envScript) { . $envScript }

$keytool = if ($env:JAVA_HOME) { Join-Path $env:JAVA_HOME "bin/keytool" } else { "keytool" }
if (-not (Get-Command $keytool -ErrorAction SilentlyContinue)) {
    throw "keytool not found. Set JAVA_HOME to JDK 17 (env.ps1) or put keytool on PATH."
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "gh CLI not found." }
gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) { throw "gh is not logged in. Run: gh auth login" }

New-Item -ItemType Directory -Force -Path $outFull | Out-Null
$keystore = Join-Path $outFull "jev-release.jks"
$props = Join-Path $outFull "jev-release.properties"
if ((Test-Path -LiteralPath $keystore) -and -not $Force) {
    throw "Keystore already exists: $keystore (re-run with -Force only if you really want a new key)"
}
if (Test-Path -LiteralPath $keystore) { Remove-Item -LiteralPath $keystore }

# 32 random URL-safe characters. PKCS12 uses one password for store and key.
$bytes = New-Object byte[] 24
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$password = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_")

& $keytool -genkeypair -noprompt `
    -keystore $keystore -storetype PKCS12 `
    -alias $Alias -keyalg RSA -keysize 4096 -validity $ValidityDays `
    -dname "CN=SanHsien, O=jev-chat-jarvis fork" `
    -storepass $password -keypass $password
if ($LASTEXITCODE -ne 0) { throw "keytool failed with exit code $LASTEXITCODE" }

# For local release builds: $env:JEV_KEYSTORE_PROPS = "<this file>"
# No BOM: java.util.Properties would read it as part of the first key.
[IO.File]::WriteAllLines($props, [string[]]@(
    "storeFile=$($keystore.Replace('\', '/'))"
    "storePassword=$password"
    "keyAlias=$Alias"
    "keyPassword=$password"
), (New-Object Text.UTF8Encoding($false)))

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($keystore))
$secrets = [ordered]@{
    JEV_KEYSTORE_B64      = $b64
    JEV_KEYSTORE_PASSWORD = $password
    JEV_KEY_ALIAS         = $Alias
    JEV_KEY_PASSWORD      = $password
}
foreach ($name in $secrets.Keys) {
    # --body, not a pipe: PowerShell appends a newline to piped strings, which would
    # end up inside the password.
    gh secret set $name --repo $Repo --body $secrets[$name]
    if ($LASTEXITCODE -ne 0) { throw "gh secret set $name failed" }
}

Write-Host ""
Write-Host "Keystore:   $keystore"
Write-Host "Properties: $props"
& $keytool -list -v -keystore $keystore -storepass $password -alias $Alias |
    Select-String "SHA256:" | ForEach-Object { Write-Host "Certificate $($_.Line.Trim())" }
Write-Host ""
Write-Host "Secrets set on ${Repo}: $($secrets.Keys -join ', ')"
Write-Host "BACK UP $outFull (e.g. a password manager). Losing this key means users must"
Write-Host "uninstall before they can install any later release."
