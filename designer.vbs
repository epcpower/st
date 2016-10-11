REM http://superuser.com/a/140077/22310

Set oShell = CreateObject ("Wscript.Shell") 
Dim strArgs
strArgs = "cmd /c designer.bat"
oShell.Run strArgs, 0, false