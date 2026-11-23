variable "kubeconfig_path" {
  description = "Chemin du fichier kubeconfig"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Contexte kubectl du cluster local (minikube, ou k3d-energydesk pour k3d)"
  type        = string
  default     = "minikube"
}

variable "environments" {
  description = "Environnements applicatifs : un namespace energydesk-<env> chacun"
  type        = list(string)
  default     = ["dev", "test", "prod"]
}

variable "install_traefik" {
  description = "Installer Traefik (Ingress). Mettre false avec k3s/k3d, qui l'integre deja."
  type        = bool
  default     = true
}

variable "install_observability" {
  description = "Installer Prometheus, Grafana, Alertmanager, Loki et Alloy"
  type        = bool
  default     = true
}

variable "install_argocd" {
  description = "Installer Argo CD"
  type        = bool
  default     = true
}

# Versions des charts. null = derniere version disponible au moment de l'installation.
# Pour une reproductibilite stricte, reporter ici les versions affichees par "helm list -A".
variable "chart_versions" {
  description = "Versions epinglees des charts Helm de la plateforme"
  type = object({
    traefik               = optional(string)
    kube_prometheus_stack = optional(string)
    loki                  = optional(string)
    alloy                 = optional(string)
    argocd                = optional(string)
  })
  default = {}
}

variable "quota" {
  description = "Quota de ressources par namespace applicatif"
  type = object({
    requests_cpu    = string
    requests_memory = string
    limits_cpu      = string
    limits_memory   = string
    pods            = string
    pvcs            = string
  })
  default = {
    requests_cpu    = "2"
    requests_memory = "3Gi"
    limits_cpu      = "6"
    limits_memory   = "8Gi"
    pods            = "25"
    pvcs            = "6"
  }
}
