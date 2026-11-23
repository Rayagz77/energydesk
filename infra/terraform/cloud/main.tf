# Infrastructure cible EnergyDesk sur Scaleway (region Paris) :
#   reseau prive (VPC) -> cluster Kubernetes Kapsule -> PostgreSQL manage -> stockage objet -> IAM.
#
#   terraform init
#   terraform plan  -out tfplan
#   terraform apply tfplan
#   terraform destroy            (a faire des que les preuves sont prises : FinOps)

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

data "scaleway_k8s_version" "latest" {
  name = "latest"
}

# ---------- Reseau ----------
resource "scaleway_vpc" "main" {
  name = "${var.prefix}-vpc"
  tags = var.tags
}

resource "scaleway_vpc_private_network" "main" {
  name   = "${var.prefix}-pn"
  vpc_id = scaleway_vpc.main.id
  ipv4_subnet {
    subnet = "172.16.0.0/22"
  }
  tags = var.tags
}

# ---------- Cluster Kubernetes ----------
resource "scaleway_k8s_cluster" "main" {
  name                        = "${var.prefix}-kapsule"
  type                        = "kapsule" # plan de controle mutualise : gratuit
  version                     = coalesce(var.k8s_version, data.scaleway_k8s_version.latest.name)
  cni                         = "cilium"
  private_network_id          = scaleway_vpc_private_network.main.id
  delete_additional_resources = true # supprime aussi Load Balancers et volumes au destroy
  tags                        = var.tags

  auto_upgrade {
    enable                        = false
    maintenance_window_start_hour = 3
    maintenance_window_day        = "sunday"
  }
}

resource "scaleway_k8s_pool" "default" {
  cluster_id  = scaleway_k8s_cluster.main.id
  name        = "default"
  node_type   = var.node_type
  size        = var.node_count
  autoscaling = false
  autohealing = true
  tags        = var.tags
}

# ---------- Base de donnees PostgreSQL managee ----------
resource "scaleway_rdb_instance" "main" {
  name               = "${var.prefix}-pg"
  node_type          = var.db_node_type
  engine             = "PostgreSQL-16"
  is_ha_cluster      = false
  user_name          = var.db_user
  password           = var.db_password
  volume_type        = "sbs_5k"
  volume_size_in_gb  = var.db_volume_size_gb
  encryption_at_rest = true # chiffrement des donnees stockees (ISO 27001 A.8.24)

  # Sauvegardes automatiques du fournisseur (ISO 27001 A.8.13)
  disable_backup            = false
  backup_schedule_frequency = 24
  backup_schedule_retention = 7

  # Uniquement sur le reseau prive : pas d'adresse publique pour la base.
  private_network {
    pn_id       = scaleway_vpc_private_network.main.id
    enable_ipam = true
  }

  tags = var.tags
}

resource "scaleway_rdb_database" "app" {
  instance_id = scaleway_rdb_instance.main.id
  name        = "energydesk"
}

resource "scaleway_rdb_privilege" "app" {
  instance_id   = scaleway_rdb_instance.main.id
  user_name     = var.db_user
  database_name = scaleway_rdb_database.app.name
  permission    = "all"
}

# ---------- Stockage objet ----------
resource "scaleway_object_bucket" "attachments" {
  name = "${var.prefix}-attachments-${random_string.suffix.result}"
  versioning {
    enabled = true # protege contre l'ecrasement ou la suppression accidentelle
  }
  tags = { project = "energydesk", usage = "attachments" }
}

resource "scaleway_object_bucket_acl" "attachments" {
  bucket = scaleway_object_bucket.attachments.id
  acl    = "private"
}

resource "scaleway_object_bucket" "backups" {
  name = "${var.prefix}-backups-${random_string.suffix.result}"
  lifecycle_rule {
    id      = "expire-old-backups"
    enabled = true
    expiration {
      days = var.backup_retention_days # FinOps : pas d'accumulation de sauvegardes inutiles
    }
  }
  tags = { project = "energydesk", usage = "backups" }
}

resource "scaleway_object_bucket_acl" "backups" {
  bucket = scaleway_object_bucket.backups.id
  acl    = "private"
}

# ---------- IAM : identite dediee a l'application, droits minimaux ----------
# L'application n'utilise PAS les cles de l'administrateur : elle a sa propre identite,
# limitee aux objets du stockage, dans ce seul projet.
resource "scaleway_iam_application" "app" {
  name        = "${var.prefix}-app"
  description = "Identite de l'application EnergyDesk (acces au stockage objet uniquement)"
}

resource "scaleway_iam_policy" "app_storage" {
  name           = "${var.prefix}-app-object-storage"
  description    = "Lecture/ecriture des objets, sans gestion des buckets ni des autres services"
  application_id = scaleway_iam_application.app.id
  rule {
    project_ids          = [var.project_id]
    permission_set_names = ["ObjectStorageObjectsRead", "ObjectStorageObjectsWrite", "ObjectStorageObjectsDelete"]
  }
}

resource "scaleway_iam_api_key" "app" {
  application_id     = scaleway_iam_application.app.id
  description        = "Cle de l'application EnergyDesk (stockee dans un Secret Kubernetes)"
  default_project_id = var.project_id
}
