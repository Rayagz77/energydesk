variable "project_id" {
  description = "Identifiant du projet Scaleway (console > Project settings)"
  type        = string
}

variable "region" {
  description = "Region Scaleway"
  type        = string
  default     = "fr-par"
}

variable "zone" {
  description = "Zone Scaleway"
  type        = string
  default     = "fr-par-1"
}

variable "prefix" {
  description = "Prefixe des ressources"
  type        = string
  default     = "energydesk"
}

variable "k8s_version" {
  description = "Version Kubernetes. null = derniere version proposee par Kapsule"
  type        = string
  default     = null
}

variable "node_type" {
  description = "Type d'instance des noeuds (verifier les types compatibles Kapsule dans la console)"
  type        = string
  default     = "DEV1-M"
}

variable "node_count" {
  description = "Nombre de noeuds du pool"
  type        = number
  default     = 2
}

variable "db_node_type" {
  description = "Gabarit de la base PostgreSQL managee"
  type        = string
  default     = "DB-DEV-S"
}

variable "db_volume_size_gb" {
  description = "Taille du volume de la base (Go)"
  type        = number
  default     = 10
}

variable "db_user" {
  description = "Utilisateur applicatif de la base"
  type        = string
  default     = "energydesk"
}

variable "db_password" {
  description = "Mot de passe de la base (variable d'environnement TF_VAR_db_password)"
  type        = string
  sensitive   = true
}

variable "backup_retention_days" {
  description = "Duree de conservation des sauvegardes dans le bucket (jours)"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Etiquettes appliquees aux ressources (suivi des couts FinOps)"
  type        = list(string)
  default     = ["energydesk", "bc3", "env:prod"]
}
