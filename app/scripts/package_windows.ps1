param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$entryPoint = Join-Path $repoRoot "desktop_main.py"
$specPath = Join-Path $repoRoot "pysidedeploy.spec"
$distRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'dist'))
$bundle = [System.IO.Path]::GetFullPath((Join-Path $distRoot 'reread_pyext.dist'))
$distPrefix = $distRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if (-not $bundle.StartsWith($distPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clear a package path outside dist: $bundle"
}
if (Test-Path -LiteralPath $bundle) {
    $existingBundle = Get-Item -LiteralPath $bundle -Force
    if ($existingBundle.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "Refusing to rebuild through a reparse point: $bundle"
    }
    Remove-Item -LiteralPath $bundle -Recurse -Force
}

$deployCommand = Get-Command pyside6-deploy -ErrorAction SilentlyContinue
if (-not $deployCommand) {
    throw 'pyside6-deploy is missing. Install the build extra with python -m pip install -e .[desktop-build].'
}
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $nodeCommand) {
    throw "Node.js 18 or newer is required to package the Bergamot worker."
}
& python -c "import win32api, win32clipboard, win32con, win32gui"
if ($LASTEXITCODE -ne 0) {
    throw 'pywin32 is missing from the active build environment. Reinstall the project with python -m pip install -e .[desktop-build].'
}
$dumpbinCommand = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
if (-not $dumpbinCommand) {
    $vswhere = Join-Path ([Environment]::GetFolderPath('ProgramFilesX86')) 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $vswhere) {
        $dumpbinPath = & $vswhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -find 'VC\Tools\MSVC\**\bin\Hostx64\x64\dumpbin.exe' | Select-Object -First 1
        if ($dumpbinPath -and (Test-Path -LiteralPath $dumpbinPath)) {
            $env:PATH = "$(Split-Path -Parent $dumpbinPath);$env:PATH"
            $dumpbinCommand = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
        }
    }
}
if (-not $dumpbinCommand) {
    Write-Warning "dumpbin.exe is unavailable; Qt's optional native dependency scan may be skipped. Verify the built app on a clean Windows profile."
}

$nodeVersionFile = Join-Path $repoRoot 'runtime\node-version.txt'
$nodeLicenseFile = Join-Path $repoRoot 'runtime\node-LICENSE.txt'
if (-not (Test-Path -LiteralPath $nodeVersionFile) -or -not (Test-Path -LiteralPath $nodeLicenseFile)) {
    throw 'The pinned Node.js version and its upstream license must be present under app/runtime.'
}
$pinnedNodeVersion = (Get-Content -LiteralPath $nodeVersionFile -Raw).Trim()
$actualNodeVersion = (& $nodeCommand.Source --version).Trim()
if ($actualNodeVersion -ne $pinnedNodeVersion) {
    throw "Node.js runtime mismatch: expected $pinnedNodeVersion from app/runtime/node-version.txt, found $actualNodeVersion. Update the pinned runtime license before packaging."
}

if (-not (Test-Path -LiteralPath $specPath)) {
    $init = Start-Process -FilePath $deployCommand.Source -ArgumentList @($entryPoint, "--init", "--force") -WorkingDirectory $repoRoot -NoNewWindow -Wait -PassThru
    if ($init.ExitCode -ne 0) {
        throw "pyside6-deploy could not create pysidedeploy.spec (exit $($init.ExitCode))."
    }
}

$build = Start-Process -FilePath $deployCommand.Source -ArgumentList @("-c", $specPath, "--force", "--mode", "standalone", "--name", "reread_pyext") -WorkingDirectory $repoRoot -NoNewWindow -Wait -PassThru
if ($build.ExitCode -ne 0) {
    throw "PySide6 desktop build failed (exit $($build.ExitCode))."
}

if (-not (Test-Path -LiteralPath $bundle)) {
    throw "Build completed without the expected bundle directory: $bundle"
}
$generatedExecutable = Join-Path $bundle "desktop_main.exe"
if (-not (Test-Path -LiteralPath $generatedExecutable)) {
    throw "Build completed without the expected executable: $generatedExecutable"
}
Move-Item -LiteralPath $generatedExecutable -Destination (Join-Path $bundle "reread_pyext.exe") -Force

$runtimeDirectory = Join-Path $bundle "runtime"
New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
Copy-Item -LiteralPath $nodeCommand.Source -Destination (Join-Path $runtimeDirectory "node.exe") -Force
Copy-Item -LiteralPath $nodeLicenseFile -Destination (Join-Path $runtimeDirectory "node-LICENSE.txt") -Force

$licenseDirectory = Join-Path $bundle 'licenses'
New-Item -ItemType Directory -Path $licenseDirectory -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $repoRoot 'licenses') -File -Filter '*.txt' | Copy-Item -Destination $licenseDirectory -Force
$licenseCollector = Join-Path $repoRoot 'scripts\copy_runtime_licenses.py'
& python -X utf8 $licenseCollector --output-dir (Join-Path $licenseDirectory 'runtime')
if ($LASTEXITCODE -ne 0) {
    throw "Runtime license collection failed (exit $LASTEXITCODE)."
}

$projectLicense = Join-Path $repoRoot '..\LICENSE'
if (Test-Path -LiteralPath $projectLicense) {
    Copy-Item -LiteralPath $projectLicense -Destination (Join-Path $bundle 'LICENSE') -Force
} else {
    throw "Project license is missing: $projectLicense"
}
$projectNotices = Join-Path $repoRoot '..\THIRD_PARTY_NOTICES.md'
if (Test-Path -LiteralPath $projectNotices) {
    Copy-Item -LiteralPath $projectNotices -Destination (Join-Path $bundle 'THIRD_PARTY_NOTICES.md') -Force
}

$modelData = Join-Path $bundle 'data\models'
if (Test-Path -LiteralPath $modelData) {
    $bundledModelWeights = Get-ChildItem -LiteralPath $modelData -Recurse -File | Where-Object {
        $_.Extension -in @('.bin', '.spm') -or $_.Name.EndsWith('.bin.gz') -or $_.Name.EndsWith('.spm.gz')
    }
    if ($bundledModelWeights.Count -gt 0) {
        throw "Model weights were included in the standalone bundle: $($bundledModelWeights[0].FullName)"
    }
}

Write-Output "Desktop bundle created at $bundle"
