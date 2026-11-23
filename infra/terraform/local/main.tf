# Plateforme locale EnergyDesk : namespaces separes, quotas, Ingress, observabilite et Argo CD.
# L'application elle-meme n'est PAS installee ici : c'est le role d'Argo CD (GitOps).

# --- Namespaces applicatifs (separation dev / test / prod, ISO 27001 A.8.31) ---
resource "kubernetes_namespace_v1" "app" {
  for_each = toset(var.environments)

  metadata {
    name = "energydesk-${each.key}"
    labels = {
      "app.kubernetes.io/part-of"          = "energydesk"
      "energydesk/environment"             = each.key
      "pod-security.kubernetes.io/enforce" = "baseline"
      "pod-security.kubernetes.io/warn"    = "restricted"
    }
  }
}

# Quota : un environnement ne peut pas consommer toutes les ressources du cluster.
resource "kubernetes_resource_quota_v1" "app" {
  for_each = kubernetes_namespace_v1.app

  metadata {
    name      = "energydesk-quota"
    namespace = each.value.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"           = var.quota.requests_cpu
      "requests.memory"        = var.quota.requests_memory
      "limits.cpu"             = var.quota.limits_cpu
      "limits.memory"          = var.quota.limits_memory
      "pods"                   = var.quota.pods
      "persistentvolumeclaims" = var.quota.pvcs
    }
  }
}

# Valeurs par defaut pour les conteneurs qui ne declarent pas leurs ressources (Jobs ponctuels).
resource "kubernetes_limit_range_v1" "app" {
  for_each = kubernetes_namespace_v1.app

  metadata {
    name      = "energydesk-defaults"
    namespace = each.value.metadata[0].name
  }
  spec {
    limit {
      type            = "Container"
      default         = { cpu = "500m", memory = "512Mi" }
      default_request = { cpu = "50m", memory = "64Mi" }
    }
  }
}

# --- Namespaces de la plateforme ---
resource "kubernetes_namespace_v1" "platform" {
  for_each = toset(concat(
    var.install_traefik ? ["traefik"] : [],
    var.install_observability ? ["monitoring"] : [],
    var.install_argocd ? ["argocd"] : [],
  ))

  metadata {
    name   = each.key
    labels = { "app.kubernetes.io/part-of" = "energydesk-platform" }
  }
}

# --- Ingress controller ---
resource "helm_release" "traefik" {
  count = var.install_traefik ? 1 : 0

  name       = "traefik"
  namespace  = kubernetes_namespace_v1.platform["traefik"].metadata[0].name
  repository = "https://traefik.github.io/charts"
  chart      = "traefik"
  version    = var.chart_versions.traefik
  values     = [file("${path.module}/values/traefik.yaml")]
}

# --- Observabilite : Prometheus, Alertmanager, Grafana, Loki, Alloy ---
resource "helm_release" "kube_prometheus_stack" {
  count = var.install_observability ? 1 : 0

  name       = "kube-prometheus-stack"
  namespace  = kubernetes_namespace_v1.platform["monitoring"].metadata[0].name
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.chart_versions.kube_prometheus_stack
  values     = [file("${path.module}/../../../observability/values/kube-prometheus-stack.yaml")]
  timeout    = 900
}

resource "helm_release" "loki" {
  count = var.install_observability ? 1 : 0

  name       = "loki"
  namespace  = kubernetes_namespace_v1.platform["monitoring"].metadata[0].name
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  version    = var.chart_versions.loki
  values     = [file("${path.module}/../../../observability/values/loki.yaml")]
  timeout    = 600
}

resource "helm_release" "alloy" {
  count = var.install_observability ? 1 : 0

  name       = "alloy"
  namespace  = kubernetes_namespace_v1.platform["monitoring"].metadata[0].name
  repository = "https://grafana.github.io/helm-charts"
  chart      = "alloy"
  version    = var.chart_versions.alloy
  values     = [file("${path.module}/../../../observability/values/alloy.yaml")]
  depends_on = [helm_release.loki]
}

# --- GitOps ---
resource "helm_release" "argocd" {
  count = var.install_argocd ? 1 : 0

  name       = "argocd"
  namespace  = kubernetes_namespace_v1.platform["argocd"].metadata[0].name
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.chart_versions.argocd
  values     = [file("${path.module}/values/argocd.yaml")]
  timeout    = 600
}
