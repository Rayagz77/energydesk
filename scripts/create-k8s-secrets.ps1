<#
.SYNOPSIS
  Cree (ou met a jour) le Secret "energydesk-secrets" dans chaque namespace, a partir du fichier .env.
  Les secrets ne passent jamais par Git (ISO 27001 A.5.17, A.8.12).

  Local (Minikube/k3s) :  pwsh ./scripts/create-k8s-secrets.ps1
  Cloud (Scaleway)     :  pwsh ./scripts/create-k8s-secrets.ps1 -Cloud -Namespaces energydesk-prod
                          (cles S3 de l'identite IAM de l'application lues dans "terraform output")
#>
param(
  [string]$EnvFile = ".env",
  [string[]]$Namespaces = @("energydesk-dev", "energydesk-test", "energydesk-prod"),
  [switch]$Cloud
)
$ErrorActionPreference = "Stop"
$values = @{}
Get-Content $EnvFile | Where-Object { $_ -match "^\s*[A-Z_]+=" } | ForEach-Object {
  $k, $v = $_ -split "=", 2; $values[$k.Trim()] = $v.Trim()
}
foreach ($key in "DB_PASSWORD", "JWT_SECRET_KEY", "RABBITMQ_PASSWORD", "MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD") {
  if (-not $values[$key] -or $values[$key] -like "change-me*") { throw "$key absent ou non modifie dans $EnvFile" }
}

$s3Access = $values["MINIO_ROOT_USER"]; $s3Secret = $values["MINIO_ROOT_PASSWORD"]
if ($Cloud) {
  $s3Access = terraform -chdir=infra/terraform/cloud output -raw app_access_key
  $s3Secret = terraform -chdir=infra/terraform/cloud output -raw app_secret_key
}

foreach ($ns in $Namespaces) {
  kubectl create namespace $ns --dry-run=client -o yaml | kubectl apply -f - | Out-Null
  kubectl create secret generic energydesk-secrets -n $ns `
    --from-literal=DB_PASSWORD=$($values["DB_PASSWORD"]) `
    --from-literal=JWT_SECRET_KEY=$($values["JWT_SECRET_KEY"]) `
    --from-literal=RABBITMQ_PASSWORD=$($values["RABBITMQ_PASSWORD"]) `
    --from-literal=MINIO_ROOT_USER=$($values["MINIO_ROOT_USER"]) `
    --from-literal=MINIO_ROOT_PASSWORD=$($values["MINIO_ROOT_PASSWORD"]) `
    --from-literal=S3_ACCESS_KEY=$s3Access `
    --from-literal=S3_SECRET_KEY=$s3Secret `
    --dry-run=client -o yaml | kubectl apply -f -
  Write-Host "Secret energydesk-secrets pret dans $ns"
}
