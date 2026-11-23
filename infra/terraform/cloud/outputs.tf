output "cluster_name" {
  value = scaleway_k8s_cluster.main.name
}

output "kubeconfig" {
  description = "terraform output -raw kubeconfig > kubeconfig-cloud.yaml (fichier ignore par Git)"
  value       = scaleway_k8s_cluster.main.kubeconfig[0].config_file
  sensitive   = true
}

output "db_private_host" {
  description = "Adresse privee de PostgreSQL (a reporter dans values-cloud.yaml)"
  value       = scaleway_rdb_instance.main.private_network[0].ip
}

output "db_port" {
  value = scaleway_rdb_instance.main.private_network[0].port
}

output "attachments_bucket" {
  value = scaleway_object_bucket.attachments.name
}

output "backups_bucket" {
  value = scaleway_object_bucket.backups.name
}

output "s3_endpoint" {
  value = "https://s3.${var.region}.scw.cloud"
}

output "app_access_key" {
  value     = scaleway_iam_api_key.app.access_key
  sensitive = true
}

output "app_secret_key" {
  value     = scaleway_iam_api_key.app.secret_key
  sensitive = true
}
