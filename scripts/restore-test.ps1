<#
.SYNOPSIS
  Sauvegarde puis test de restauration PostgreSQL (ISO 27001 A.8.13), dans Codespaces.
  1) declenche une sauvegarde immediate a partir de la CronJob ;
  2) lance le Job de restauration dans une base vide ;
  3) affiche les logs (preuve) et les enregistre dans docs/preuves/.
  Usage : pwsh ./scripts/restore-test.ps1 -Namespace energydesk-prod
#>
param([string]$Namespace = "energydesk-prod")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "docs/preuves" | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$proof = "docs/preuves/restore-test-$stamp.txt"

$backupJob = "backup-manuel-$stamp"
kubectl create job --from=cronjob/energydesk-backup $backupJob -n $Namespace
kubectl wait --for=condition=complete "job/$backupJob" -n $Namespace --timeout=180s
"=== Sauvegarde ===" | Tee-Object -FilePath $proof
kubectl logs "job/$backupJob" -n $Namespace --all-containers | Tee-Object -FilePath $proof -Append

$image = kubectl get deploy energydesk-api -n $Namespace -o jsonpath="{.spec.template.spec.containers[0].image}"
kubectl delete job energydesk-restore-test -n $Namespace --ignore-not-found | Out-Null
(Get-Content deploy/k8s/restore-test-job.yaml -Raw) -replace "__NAMESPACE__", $Namespace -replace "__API_IMAGE__", $image |
  kubectl apply -f -
kubectl wait --for=condition=complete job/energydesk-restore-test -n $Namespace --timeout=180s
"=== Restauration ===" | Tee-Object -FilePath $proof -Append
kubectl logs job/energydesk-restore-test -n $Namespace --all-containers | Tee-Object -FilePath $proof -Append
Write-Host "Preuve enregistree : $proof" -ForegroundColor Cyan
