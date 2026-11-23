<#
.SYNOPSIS
  Cree le cluster Kubernetes local DANS CODESPACES puis installe la plateforme avec Terraform.
  Usage : pwsh ./scripts/cluster-up.ps1                 (Minikube, par defaut)
          pwsh ./scripts/cluster-up.ps1 -Distro k3d     (k3s via k3d, si c'est l'outil du cours)
#>
param(
  [ValidateSet("minikube", "k3d")][string]$Distro = "minikube",
  [int]$Cpus = 4,
  [string]$Memory = "10g"
)
$ErrorActionPreference = "Stop"

if ($Distro -eq "minikube") {
  minikube start --driver=docker --cpus=$Cpus --memory=$Memory --kubernetes-version=stable
  minikube addons enable metrics-server     # indispensable au HPA
  $context = "minikube"; $installTraefik = "true"
} else {
  # k3s embarque deja Traefik (Ingress), metrics-server et un stockage local (local-path)
  k3d cluster create energydesk --servers 1 --agents 1 --wait
  $context = "k3d-energydesk"; $installTraefik = "false"
}

kubectl config use-context $context
kubectl get nodes -o wide

terraform -chdir=infra/terraform/local init
terraform -chdir=infra/terraform/local apply -auto-approve `
  -var "kube_context=$context" -var "install_traefik=$installTraefik"
terraform -chdir=infra/terraform/local output next_steps
