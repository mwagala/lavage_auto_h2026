$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Environnement virtuel introuvable: $PythonExe. Cree le .venv puis installe dependences.txt."
}

Set-Location $ProjectRoot
& $PythonExe "app.py"
