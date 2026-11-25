# FinOps : coût de l'infrastructure cible et optimisations

Règle : on distingue toujours les **estimations** (tarifs publics × durée) des **mesures** (valeurs relevées ou facturées). Toute case « à compléter » se remplit avec une source datée.

## 1. Choix du fournisseur (comparaison rapide)

| Fournisseur | Plan de contrôle Kubernetes | Stockage objet compatible S3 | Remarques |
|---|---|---|---|
| **Scaleway Kapsule (retenu)** | Gratuit (offre mutualisée) | Oui, natif | Région Paris, PostgreSQL managé, provider Terraform officiel |
| Google GKE | Un cluster zonal ou Autopilot couvert par le crédit gratuit mensuel | Via clés HMAC (interopérabilité) | IAM plus complexe |
| Azure AKS | Gratuit (niveau Free) | Non (Blob Storage) | Code de stockage à adapter |
| AWS EKS | Environ 0,10 $/h par cluster | Oui | Coût fixe élevé pour un projet court |

Sources : pages de prix des fournisseurs, consultées le 23/11/2026. À revérifier le jour du rendu.

## 2. Estimation du coût cible (Scaleway, hors TVA)

| Ressource | Quantité | Tarif unitaire (source, date) | Coût horaire | Coût mensuel (× 730 h) |
|---|---|---|---|---|
| Plan de contrôle Kapsule mutualisé | 1 | Gratuit (scaleway.com/fr/tarifs/containers) | 0 € | 0 € |
| Nœuds (type `DEV1-M` ou équivalent) | 2 | à compléter (page Instances) | à compléter | à compléter |
| PostgreSQL managé `DB-DEV-S` | 1 | 0,0156 €/h (page Managed Databases, 23/11/2026) | 0,0156 € | ≈ 11,39 € |
| Volume de la base (10 Go) | 10 Go | à compléter | — | à compléter |
| Load Balancer (créé par Traefik) | 1 | à compléter | à compléter | à compléter |
| Object Storage (pièces jointes et sauvegardes) | < 1 Go | à compléter | — | à compléter |
| Volumes des nœuds et PVC RabbitMQ | à compléter | à compléter | — | à compléter |
| **Total estimé** | | | | **à compléter** |

**Coût observé** (facture ou console de facturation après la démonstration) : à compléter, avec la durée réelle d'utilisation.

## 3. Optimisations appliquées

### Optimisation 1 : taille des images Docker

| | Avant (`Dockerfile.naive`) | Après (`Dockerfile`) |
|---|---|---|
| Image de base | `python:3.12` complète | `python:3.12-slim` |
| Étapes | une seule | multi-stage (builder puis runtime) |
| Contenu | code, tests, outils de dev, cache pip | environnement virtuel et code uniquement |
| Utilisateur | root | `app` (uid 10001) |
| Taille mesurée (25/11/2026, Codespaces) | 2,1 Go (≈ 2 000 Mio) | 382 Mo (≈ 365 Mio) |
| Gain | | **− 81,8 %** (mesuré, `scripts/measure-images.ps1`) |

Impact : téléchargements plus rapides lors des déploiements et du scaling, moins de stockage dans le registre, moins de paquets donc moins de vulnérabilités.
Limite : l'économie directe en euros est faible à cette échelle. Le gain principal porte sur la vitesse et la sécurité.

### Optimisation 2 : requests CPU/RAM ajustées après mesure

| Composant | Request avant | Consommation mesurée (`kubectl top`, au repos puis sous charge) | Request après (mesure + ~30 %) | Gain |
|---|---|---|---|---|
| api | 100m / 160Mi | à compléter | à compléter | à compléter |
| worker | 50m / 96Mi | à compléter | à compléter | à compléter |
| frontend | 20m / 32Mi | à compléter | à compléter | à compléter |

Impact : les requests déterminent combien de pods tiennent sur un nœud, donc le nombre de nœuds facturés.
Limite : des requests trop basses dégradent le HPA (qui calcule en % de la request) et augmentent le risque d'éviction. On garde une marge.

### Optimisation 3 (facultative) : durée de vie de l'infrastructure

L'infrastructure cloud est créée pour la démonstration puis détruite (`terraform destroy`). Coût évité = coût horaire total × heures non consommées. C'est possible parce que l'infrastructure est reproductible par Terraform.

Autres leviers déjà en place : plan de contrôle gratuit, base managée au plus petit gabarit, pas de haute disponibilité de la base en démonstration, expiration des sauvegardes à 30 jours, HPA qui réduit le nombre de pods hors charge, étiquettes (`tags`) sur les ressources pour ventiler les coûts.
