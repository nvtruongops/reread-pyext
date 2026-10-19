Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get project root (parent of services/windows)
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
servicesDir = fso.GetParentFolderName(scriptDir)
rootDir = fso.GetParentFolderName(servicesDir)

' Run pythonw.exe completely hidden (window style 0, no wait)
cmd = "pythonw.exe -m reread_pyext.app --background"
WshShell.CurrentDirectory = rootDir
WshShell.Run cmd, 0, False
