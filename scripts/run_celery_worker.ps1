$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CeleryExe = Join-Path $ProjectRoot ".venv\Scripts\celery.exe"

if (-not (Test-Path $CeleryExe)) {
    Write-Error "Celery introuvable dans le .venv: $CeleryExe. Installe les dependances avec .\.venv\Scripts\pip.exe install -r dependences.txt."
}

Set-Location $ProjectRoot
& $CeleryExe -A backend.celery.celery_app:celery_app worker -l INFO --pool=solo
