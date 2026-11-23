<#
.SYNOPSIS
  Mesure FinOps no 1 : taille de l'image API "naive" (avant) contre l'image multi-stage (apres).
  Usage : .\scripts\measure-images.ps1
  La sortie est enregistree dans docs\preuves\ pour le rapport.
#>
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "docs\preuves" | Out-Null
$out = "docs\preuves\finops-tailles-images-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"

docker build -f backend/Dockerfile.naive -t energydesk-api:naive backend
docker build -t energydesk-api:optimise backend
docker build -t energydesk-worker:optimise worker
docker build -t energydesk-frontend:optimise frontend

$rows = docker image ls --format "{{.Repository}}:{{.Tag}};{{.Size}}" |
  Where-Object { $_ -match "^energydesk-(api|worker|frontend):(naive|optimise);" }
$rows | ForEach-Object { $_ -replace ";", "  " } | Tee-Object -FilePath $out

$naive = [double](docker image inspect energydesk-api:naive --format "{{.Size}}")
$opt = [double](docker image inspect energydesk-api:optimise --format "{{.Size}}")
$gain = [math]::Round((1 - $opt / $naive) * 100, 1)
$line = "API : naive = {0:N0} Mo ; optimisee = {1:N0} Mo ; gain = {2} %" -f ($naive / 1MB), ($opt / 1MB), $gain
$line | Tee-Object -FilePath $out -Append
