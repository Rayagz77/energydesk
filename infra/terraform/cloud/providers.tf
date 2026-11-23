# Identifiants lus dans les variables d'environnement (jamais dans le code) :
#   SCW_ACCESS_KEY, SCW_SECRET_KEY, SCW_DEFAULT_PROJECT_ID, SCW_DEFAULT_ORGANIZATION_ID
provider "scaleway" {
  region = var.region
  zone   = var.zone
}
