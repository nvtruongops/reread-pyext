Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
rootDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = rootDir
WshShell.Run "pythonw.exe -m reread_pyext.app", 1, False
