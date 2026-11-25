<#
.SYNOPSIS
  Remplace le texte "OWNER" par votre nom de compte GitHub (en minuscules) dans les manifests.
  A lancer UNE fois apres avoir cree le depot GitHub.
  Usage : .\scripts\set-owner.ps1 -Owner mon-compte
#>
param([Parameter(Mandatory = $true)][string]$Owner)
$Owner = $Owner.ToLower()
$files = Get-ChildItem -Recurse -File -Path deploy, backend, worker, frontend -Include *.yaml, Dockerfile |
  Where-Object { (Get-Content $_.FullName -Raw) -cmatch "OWNER" }
foreach ($f in $files) {
  $content = (Get-Content $f.FullName -Raw) -creplace "OWNER", $Owner
  [IO.File]::WriteAllText($f.FullName, $content, (New-Object System.Text.UTF8Encoding $false))
  Write-Host "Mis a jour : $($f.FullName)"
}
