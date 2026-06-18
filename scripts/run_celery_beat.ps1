$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$CeleryExe = Join-Path $ProjectRoot ".venv\Scripts\celery.exe"
$ScheduleFile = Join-Path $ProjectRoot "celerybeat-schedule"

if (-not (Test-Path $CeleryExe)) {
    Write-Error "Celery introuvable dans le .venv: $CeleryExe. Installe les dependances avec .\.venv\Scripts\pip.exe install -r dependences.txt."
}

Set-Location $ProjectRoot

# Beat ne traite pas les evenements lui-meme. Il publie seulement la tache
# periodique dans Redis; le worker Celery doit tourner dans un autre terminal.
& $CeleryExe -A backend.celery.celery_app:celery_app beat -l INFO --schedule $ScheduleFile
