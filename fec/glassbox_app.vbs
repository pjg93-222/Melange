' Hidden launch shim for the GLASS BOX app. Runs open_glassbox_app.ps1 with no
' console window so the desktop shortcut behaves like an application launcher.
Option Explicit
Dim shell, fso, base, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
base = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & base & "\open_glassbox_app.ps1"" -NoShortcut"
shell.Run cmd, 0, False
