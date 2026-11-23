<#
.SYNOPSIS
  Verifie que les outils necessaires sont installes et affiche leurs versions.
  Usage : .\scripts\check-env.ps1
#>
$tools = @(
  @{ Name = "git";       Args = @("--version") },
  @{ Name = "python";    Args = @("--version") },
  @{ Name = "docker";    Args = @("version", "--format", "Client {{.Client.Version}} / Serveur {{.Server.Version}}") },
  @{ Name = "kubectl";   Args = @("version", "--client") },
  @{ Name = "helm";      Args = @("version", "--short") },
  @{ Name = "terraform"; Args = @("-version") },
  @{ Name = "minikube";  Args = @("version", "--short") },
  @{ Name = "k9s";       Args = @("version", "--short") }
)
$missing = @()
foreach ($t in $tools) {
  if (Get-Command $t.Name -ErrorAction SilentlyContinue) {
    $out = (& $t.Name @($t.Args) 2>&1 | Select-Object -First 1)
    Write-Host ("[OK]      {0,-10} {1}" -f $t.Name, $out)
  } else {
    Write-Host ("[ABSENT]  {0}" -f $t.Name) -ForegroundColor Yellow
    $missing += $t.Name
  }
}
if ($missing.Count -gt 0) {
  Write-Host "`nOutils absents : $($missing -join ', '). Normal sur le PC si ces outils sont utilises dans Codespaces." -ForegroundColor Yellow
}
