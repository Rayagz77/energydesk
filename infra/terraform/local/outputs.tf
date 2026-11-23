output "app_namespaces" {
  description = "Namespaces applicatifs crees"
  value       = [for ns in kubernetes_namespace_v1.app : ns.metadata[0].name]
}

output "next_steps" {
  description = "Commandes utiles apres l'installation"
  value       = <<-EOT
    Mot de passe Grafana (utilisateur admin) :
      kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d
    Mot de passe Argo CD (utilisateur admin) :
      kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
    Acces :
      kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
      kubectl port-forward -n argocd svc/argocd-server 8081:80
  EOT
}
