# Crée sur le Bureau le raccourci "Verrouiller" avec un raccourci clavier custom
# Exemple : .\installer-raccourci.ps1 -Touche "CTRL+SHIFT+F12"
param([string]$Touche = "CTRL+ALT+L")
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyw = Join-Path (Split-Path (Get-Command python).Source) "pythonw.exe"
$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Verrouiller.lnk"))
$lnk.TargetPath = $pyw
$lnk.Arguments = "`"$dir\anticroissantage.py`""
$lnk.WorkingDirectory = $dir
$lnk.Hotkey = $Touche
$lnk.IconLocation = "shell32.dll,48"
$lnk.Save()
Write-Host "Raccourci créé : Verrouiller.lnk ($Touche)"
