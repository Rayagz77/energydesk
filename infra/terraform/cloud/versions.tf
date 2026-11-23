terraform {
  required_version = ">= 1.6.0"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = ">= 2.40, < 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Etat Terraform local par defaut (fichier ignore par Git, il contient des secrets).
  # Pour un travail en equipe : backend "s3" vers un bucket Object Storage chiffre et prive.
}
