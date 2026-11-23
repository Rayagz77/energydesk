# Chaîne de déploiement et stratégie de mise en production

## 1. Qui fait quoi

| Outil | Rôle | Ce qu'il ne fait pas | Fichiers |
|---|---|---|---|
| **GitHub Actions** | Valide (lint, tests, scans), **construit** les images, les **publie** sur GHCR, puis écrit le nouveau tag dans Git | Ne touche jamais au cluster | `.github/workflows/ci.yml`, `promote.yml` |
| **Terraform** | **Crée l'infrastructure** : réseau, cluster, base managée, stockage objet, IAM (cloud) ; namespaces, quotas et outils de plateforme (local) | Ne déploie pas l'application | `infra/terraform/cloud`, `infra/terraform/local` |
| **Argo CD** | **Synchronise** le cluster avec Git : il compare l'état voulu (chart Helm dans Git) à l'état réel et applique la différence | Ne construit rien | `deploy/argocd/` |
| **Kubernetes** | **Orchestre** les conteneurs : démarrage, redémarrage, mise à l'échelle, réseau, volumes | Ne sait pas d'où vient la version | `deploy/helm/energydesk/` |

Exemple concret. Un développeur pousse un commit. GitHub Actions teste et construit l'image `energydesk-api:0.1.1-a1b2c3d`, puis écrit ce tag dans `values-dev.yaml`. Argo CD voit le commit et applique le chart. Kubernetes remplace les pods un par un. Terraform n'intervient pas : l'infrastructure existe déjà.

## 2. GitOps : la source de vérité est Git

| Élément | Valeur |
|---|---|
| Source Git | `https://github.com/<compte>/energydesk.git` |
| Révision suivie | branche `main` |
| Chemin | `deploy/helm/energydesk` (chart Helm) |
| Fichiers de valeurs | `values.yaml` + `values-<env>.yaml` |
| Namespaces cibles | `energydesk-dev`, `energydesk-test`, `energydesk-prod` |
| Politique dev et test | synchronisation automatique, `prune` et `selfHeal` |
| Politique prod | synchronisation **manuelle** (validation humaine) |
| Mise à jour des images | la CI commite le tag (`<version>-<sha court>`) dans `values-dev.yaml` ; le workflow `promote` copie un tag validé vers test, prod ou cloud |

Avantages : chaque déploiement correspond à un commit (traçabilité). Un retour arrière se fait par `git revert`. Une modification manuelle dans le cluster est annulée par `selfHeal` en dev et test.

## 3. Versionnement des images

- Version applicative dans le fichier `VERSION` (SemVer, ex. `0.1.0`).
- Tag d'image immuable : `<version>-<sha court du commit>` (ex. `0.1.0-a1b2c3d`). C'est celui que l'on déploie.
- Tag `<version>` en complément. On n'utilise jamais `latest` pour déployer.

## 4. Stratégie de déploiement : rolling update sans interruption

Paramètres (`values.yaml`) : `maxSurge: 1`, `maxUnavailable: 0`, et une `readinessProbe` sur `/health/ready` (qui vérifie la base).

Déroulé :
1. Kubernetes crée **un** pod de la nouvelle version (surge = 1).
2. Il attend que ce pod soit **prêt** (readiness OK).
3. Il arrête alors **un** ancien pod. Il ne descend jamais sous le nombre voulu (`maxUnavailable: 0`).
4. Il recommence jusqu'au remplacement complet.

Si le nouveau pod n'est jamais prêt, le déploiement s'arrête et les anciens pods continuent de servir. Retour arrière : `git revert` (GitOps) ou `kubectl rollout undo`.

Les migrations de base s'exécutent dans un `initContainer`, protégées par un verrou PostgreSQL. Contrainte assumée : chaque migration doit rester compatible avec la version précédente du code, puisque les deux versions tournent ensemble pendant le rolling update.

### Pourquoi pas canary ou blue/green

Le sujet les cite comme « idéal ». Un canary propre demande un outil de répartition du trafic par pourcentage (Argo Rollouts, ou des poids Traefik) et une analyse automatique des métriques. Avec le délai du projet, nous avons choisi un rolling update maîtrisé et démontré, plus une promotion par environnement (dev → test → prod) qui joue déjà un rôle de déploiement progressif. Le canary est une évolution documentée, pas une fonctionnalité livrée.

## 5. Environnements

| | dev | test | prod (local) | cloud |
|---|---|---|---|---|
| Namespace | energydesk-dev | energydesk-test | energydesk-prod | energydesk-prod (cluster Scaleway) |
| Synchronisation | auto | auto | manuelle | manuelle |
| Origine du tag | CI à chaque push | promotion | promotion | promotion |
| API (HPA) | 1 → 4 | 1 → 3 | 2 → 5 | 2 → 5 |
| Base | StatefulSet + PVC | StatefulSet + PVC | StatefulSet + PVC | PostgreSQL managé |
| Stockage objet | MinIO | MinIO | MinIO | Object Storage Scaleway |
| TLS | non | non | oui (auto-signé) | à ajouter (cert-manager) |
| Sauvegarde | non | non | CronJob quotidienne | sauvegardes du service managé |
