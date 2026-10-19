$ErrorActionPreference = 'Stop'
$appRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$bundle = Join-Path $appRoot 'dist\reread_pyext.dist'
$outputDir = Join-Path $appRoot 'dist'
$installerScript = Join-Path $appRoot 'installer\reread_pyext.iss'

$projectConfig = Get-Content -LiteralPath (Join-Path $appRoot 'pyproject.toml') -Raw
if ($projectConfig -notmatch '(?m)^version\s*=\s*"([^"]+)"') {
    throw 'Could not read project version from app/pyproject.toml.'
}
$appVersion = $Matches[1]

$nodeCommand = Get-Command node.exe -ErrorAction Stop
$nodeVersion = (& $nodeCommand.Source --version).Trim()
$pinnedNodeVersion = (Get-Content -LiteralPath (Join-Path $appRoot 'runtime\node-version.txt') -Raw).Trim()
if ($nodeVersion -ne $pinnedNodeVersion) {
    throw "Node.js runtime mismatch: expected $pinnedNodeVersion, found $nodeVersion."
}

$compilerCandidates = @(
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    (Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Inno Setup 6\ISCC.exe'),
    (Join-Path ([Environment]::GetFolderPath('ProgramFiles')) 'Inno Setup 6\ISCC.exe')
)
$compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$compilerPath = if ($compilerCommand) { $compilerCommand.Source } else { $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1 }
if (-not $compilerPath) {
    throw 'Inno Setup 6 compiler was not found. Install JRSoftware.InnoSetup or set PATH to ISCC.exe.'
}
if (-not (Test-Path -LiteralPath $installerScript)) {
    throw "Installer script is missing: $installerScript"
}

& (Join-Path $appRoot 'scripts\package_windows.ps1')
if (-not (Test-Path -LiteralPath $bundle)) {
    throw "Standalone bundle is missing: $bundle"
}

$env:REREAD_APP_VERSION = $appVersion
$env:REREAD_BUNDLE_DIR = $bundle
$env:REREAD_OUTPUT_DIR = $outputDir
& $compilerPath $installerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed with exit code $LASTEXITCODE."
}

$installer = Join-Path $outputDir 'reread_pyext_setup.exe'
if (-not (Test-Path -LiteralPath $installer)) {
    throw "Inno Setup did not produce the expected installer: $installer"
}
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "Installer created: $installer"
Write-Output "SHA-256: $hash"
