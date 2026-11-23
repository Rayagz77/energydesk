<#
.SYNOPSIS
  Certificat TLS auto-signe pour l'Ingress local (chiffrement en transit, ISO 27001 A.8.24).
  En cloud, on utiliserait cert-manager et Let's Encrypt.
  Usage (Codespaces) : pwsh ./scripts/create-tls-secret.ps1 -Namespace energydesk-prod -HostName energydesk.local
#>
param(
  [string]$Namespace = "energydesk-prod",
  [string]$HostName = "energydesk.local"
)
$ErrorActionPreference = "Stop"
$dir = New-Item -ItemType Directory -Force -Path (Join-Path ([IO.Path]::GetTempPath()) "energydesk-tls")
$key = Join-Path $dir "tls.key"; $crt = Join-Path $dir "tls.crt"
openssl req -x509 -nodes -newkey rsa:2048 -days 30 -keyout $key -out $crt `
  -subj "/CN=$HostName/O=EnergyDesk (demo)" -addext "subjectAltName=DNS:$HostName"
kubectl create secret tls energydesk-tls -n $Namespace --cert=$crt --key=$key --dry-run=client -o yaml | kubectl apply -f -
Remove-Item -Recurse -Force $dir
Write-Host "Secret TLS energydesk-tls cree dans $Namespace pour $HostName"
