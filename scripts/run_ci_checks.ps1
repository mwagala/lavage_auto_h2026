$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Environnement virtuel introuvable: $PythonExe. Cree le .venv puis installe requirements-dev.txt."
}

Set-Location $ProjectRoot

& $PythonExe -m pip install -r requirements-dev.txt
& $PythonExe -m ruff check .
& $PythonExe -m compileall app.py backend bd frontend scripts
& $PythonExe -m pytest
& docker compose config --quiet
& docker compose build
& docker compose run --rm --no-deps web sh -c "gunicorn --check-config app:app"
