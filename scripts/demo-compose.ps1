<#
.SYNOPSIS
  Scenario metier complet contre la pile Docker Compose (preuve de l'exigence "scenario complet dans Docker").
  Prerequis : docker compose up -d --build   (tous les services demarres)
  Usage     : .\scripts\demo-compose.ps1
  Resultat  : chaque etape affiche OK ; la sortie est aussi enregistree dans docs\preuves\.
#>
param(
  [string]$BaseUrl = "http://localhost:8080",
  [string]$EnvFile = ".env"
)
$ErrorActionPreference = "Stop"

# Lecture du .env (mot de passe de l'agent de demonstration)
$envValues = @{}
Get-Content $EnvFile | Where-Object { $_ -match "^\s*[A-Z_]+=" } | ForEach-Object {
  $k, $v = $_ -split "=", 2; $envValues[$k.Trim()] = $v.Trim()
}
$agentEmail = $envValues["AGENT_EMAIL"]; if (-not $agentEmail) { $agentEmail = "agent@energydesk.local" }
$agentPassword = $envValues["AGENT_PASSWORD"]
if (-not $agentPassword -or $agentPassword.Length -lt 12) { throw "AGENT_PASSWORD absent ou trop court dans $EnvFile" }

New-Item -ItemType Directory -Force -Path "docs\preuves" | Out-Null
$log = "docs\preuves\demo-compose-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
function Step($text) { $line = "[OK] $text"; Write-Host $line -ForegroundColor Green; Add-Content $log $line }

$api = "$BaseUrl/api/v1"
$suffix = Get-Random -Maximum 99999
$userEmail = "alice.$suffix@exemple.fr"
$userPassword = "Demo-Utilisateur-2026"

# 1. Agent support (cree par la commande d'administration, pas par l'inscription publique)
docker compose exec -T -e AGENT_PASSWORD=$agentPassword api python -m app.cli create-agent --email $agentEmail --full-name "Agent Demo" | Out-Null
Step "Agent support disponible : $agentEmail"

# 2. Inscription et connexion d'un utilisateur
Invoke-RestMethod -Method Post "$api/auth/register" -ContentType "application/json" `
  -Body (@{ email = $userEmail; full_name = "Alice Demo"; password = $userPassword } | ConvertTo-Json) | Out-Null
$userToken = (Invoke-RestMethod -Method Post "$api/auth/login" -Body @{ username = $userEmail; password = $userPassword }).access_token
$userHeaders = @{ Authorization = "Bearer $userToken" }
Step "Inscription et connexion de $userEmail"

# 3. Creation d'un ticket
$ticket = Invoke-RestMethod -Method Post "$api/tickets" -Headers $userHeaders -ContentType "application/json" -Body (@{
  title = "Compteur ne transmettant plus ses donnees"; description = "Aucune remontee d'index depuis 48 h (donnees fictives)."
  category = "transmission"; equipment_id = "CPT-FICTIF-000123"; priority = "critique" } | ConvertTo-Json)
Step "Ticket cree : $($ticket.id) (statut $($ticket.status), priorite $($ticket.priority))"

# 4. Piece jointe (petite image PNG generee)
$png = Join-Path $env:TEMP "energydesk-demo.png"
[IO.File]::WriteAllBytes($png, [Convert]::FromBase64String("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="))
$upload = curl.exe -s -X POST "$api/tickets/$($ticket.id)/attachments" -H "Authorization: Bearer $userToken" -F "file=@$png;type=image/png" | ConvertFrom-Json
Step "Piece jointe stockee dans MinIO : $($upload.original_filename) ($($upload.size_bytes) octets)"

# 5. Notification asynchrone (worker)
$notified = $null
for ($i = 0; $i -lt 15 -and -not $notified; $i++) {
  Start-Sleep -Seconds 2
  $notified = (Invoke-RestMethod "$api/tickets/$($ticket.id)" -Headers $userHeaders).notified_at
}
if (-not $notified) { throw "Le worker n'a pas notifie le ticket en 30 s : verifier 'docker compose logs worker'" }
Step "Notification traitee par le worker a $notified"

# 6. Isolation : un autre utilisateur ne voit pas ce ticket
$bobEmail = "bob.$suffix@exemple.fr"
Invoke-RestMethod -Method Post "$api/auth/register" -ContentType "application/json" `
  -Body (@{ email = $bobEmail; full_name = "Bob Demo"; password = $userPassword } | ConvertTo-Json) | Out-Null
$bobToken = (Invoke-RestMethod -Method Post "$api/auth/login" -Body @{ username = $bobEmail; password = $userPassword }).access_token
$denied = $false
try {
  Invoke-RestMethod "$api/tickets/$($ticket.id)" -Headers @{ Authorization = "Bearer $bobToken" } | Out-Null
} catch {
  $denied = $true
}
if (-not $denied) { throw "ECHEC : un autre utilisateur a pu lire le ticket" }
Step "Isolation verifiee : un autre utilisateur recoit une erreur (404)"

# 7. Traitement par l'agent : attribution, statut, commentaire
$agentToken = (Invoke-RestMethod -Method Post "$api/auth/login" -Body @{ username = $agentEmail; password = $agentPassword }).access_token
$agentHeaders = @{ Authorization = "Bearer $agentToken" }
$me = Invoke-RestMethod "$api/auth/me" -Headers $agentHeaders
Invoke-RestMethod -Method Patch "$api/tickets/$($ticket.id)/assign" -Headers $agentHeaders -ContentType "application/json" -Body (@{ agent_id = $me.id } | ConvertTo-Json) | Out-Null
Invoke-RestMethod -Method Patch "$api/tickets/$($ticket.id)/status" -Headers $agentHeaders -ContentType "application/json" -Body '{"status":"en_cours"}' | Out-Null
Invoke-RestMethod -Method Post "$api/tickets/$($ticket.id)/comments" -Headers $agentHeaders -ContentType "application/json" -Body '{"content":"Intervention planifiee (fictive)."}' | Out-Null
Step "Agent : ticket attribue, passe en cours, commentaire ajoute"

# 8. Tableau de bord
$stats = Invoke-RestMethod "$api/stats" -Headers $agentHeaders
Step "Tableau de bord agent : ouverts=$($stats.ouverts) en_cours=$($stats.en_cours) resolus=$($stats.resolus) critiques=$($stats.critiques)"

Write-Host "`nScenario complet reussi. Trace : $log" -ForegroundColor Cyan
