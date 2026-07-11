$ErrorActionPreference = "Stop"

$ContainerName = if ($env:REDIS_CONTAINER_NAME) { $env:REDIS_CONTAINER_NAME } else { "lavage-auto-redis" }
$RedisPort = if ($env:REDIS_PORT) { $env:REDIS_PORT } else { "6379" }
$RedisImage = if ($env:REDIS_IMAGE) { $env:REDIS_IMAGE } else { "redis:7-alpine" }

$DockerExe = Get-Command docker -ErrorAction SilentlyContinue
if (-not $DockerExe) {
    Write-Error "Docker est requis pour ce script. Installe Docker ou lance Redis autrement puis configure REDIS_URL."
}

$ExistingContainer = & docker ps -a --filter "name=^/$ContainerName$" --format "{{.Names}}"
$RunningContainer = & docker ps --filter "name=^/$ContainerName$" --format "{{.Names}}"

if ($RunningContainer -contains $ContainerName) {
    Write-Host "Redis est deja lance dans le conteneur $ContainerName sur le port $RedisPort."
    return
}

if ($ExistingContainer -contains $ContainerName) {
    Write-Host "Demarrage du conteneur Redis existant: $ContainerName"
    & docker start $ContainerName | Out-Null
    return
}

Write-Host "Creation et demarrage du conteneur Redis: $ContainerName"
& docker run -d `
    --name $ContainerName `
    -p "${RedisPort}:6379" `
    $RedisImage `
    redis-server --appendonly yes | Out-Null

Write-Host "Redis est disponible sur redis://localhost:$RedisPort/0"
