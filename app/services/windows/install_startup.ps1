# PowerShell Script to register reread-desktop in Windows Startup

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = (Get-Item $scriptDir).Parent.Parent.FullName
$vbsPath = Join-Path $scriptDir "start_desktop_hidden.vbs"

$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "re-read Desktop.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$vbsPath`""
$Shortcut.WorkingDirectory = $rootDir
$Shortcut.Description = "re/read Offline Desktop Translation"
$Shortcut.Save()

Write-Host "[OK] Successfully registered re/read in Windows Startup:" -ForegroundColor Green
Write-Host "     $shortcutPath" -ForegroundColor Cyan
Write-Host "The application will start silently on Windows login without terminal window."
