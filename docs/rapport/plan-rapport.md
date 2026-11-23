# Plan du rapport (10 à 15 pages)

Conseil : rédige chaque section juste après l'étape correspondante du guide, pendant que tout est frais. Le barème du rapport (10 points) évalue la clarté et la **justification des choix et des arbitrages**. Écris donc toujours « pourquoi », pas seulement « quoi ». N'écris que des résultats que tu as réellement obtenus.

| § | Titre | Pages | Contenu | Preuves à insérer | Barème |
|---|---|---|---|---|---|
| 1 | Introduction et contexte | 0,5 | Objectif BC3, domaine choisi, données fictives, périmètre volontairement simple | — | Rapport |
| 2 | Architecture | 1,5 | Schéma des services et des flux (création d'un ticket de bout en bout), rôle de chaque brique, choix d'une origine unique `/api` | Schéma (README) | Conteneurisation |
| 3 | Choix techniques justifiés | 1,5 | FastAPI, PostgreSQL, S3/MinIO (et arrêt de MinIO communautaire), RabbitMQ (exchange + DLQ), worker idempotent et balayage, Traefik (retrait d'ingress-nginx), Scaleway (comparatif), GHCR | Tableau comparatif cloud | Tous |
| 4 | Conteneurisation | 1 | Multi-stage, non root, `.dockerignore`, healthchecks, réseaux Compose séparés, tags versionnés | `docker compose ps`, trace de `demo-compose`, tailles d'images | Conteneurisation (20) |
| 5 | Kubernetes | 2 | Chart Helm, namespaces, probes, requests et limits, PVC, Ingress et TLS, HPA, rolling update, résilience | Sorties `kubectl` (E1 à E4), résumé k6, HPA dans Grafana | Kubernetes (20) |
| 6 | CI/CD, IaC et GitOps | 2 | Étapes du pipeline, tags, scans, GitOps (commit du tag), promotion, Terraform local et cloud, différences GitHub Actions / Terraform / Argo CD / Kubernetes | Run vert, commit GitOps, Argo CD, `terraform plan/apply` | CI/CD et IaC (20) |
| 7 | Observabilité | 1,5 | Métriques, logs JSON, Loki, dashboard, SLI/SLO (valeurs mesurées et limites), alerte testée | Dashboard, requête Loki, alerte Firing puis résolue | Observabilité (10) |
| 8 | Sécurité et ISO 27001 | 1,5 | Tableau de correspondance (version courte), compromis, chaîne d'approvisionnement (MinIO, Trivy) | `can-i`, restauration, Trivy, protection de branche | Sécurité (10) |
| 9 | FinOps | 1 | Coût estimé sourcé, coût observé, deux optimisations (avant, après, gain, limites) | Tableaux de `docs/finops.md` remplis | FinOps (10) |
| 10 | Difficultés, corrections et arbitrages | 1 | Problèmes réellement rencontrés et leur correction. Exemple vécu à la génération : étiquettes de métriques sans préfixe `/api/v1` et région S3 pour MinIO, détectés par un test de fumée et corrigés avec des tests de non-régression. Ajoute les tiens | Logs d'erreur, commits de correction | Rapport |
| 11 | Bilan et perspectives | 0,5 | Ce qui est atteint, ce qui reste (canary, Sealed Secrets, cert-manager, traces), apprentissages | Matrice de conformité | Rapport |
| Annexes | Matrice de conformité, commandes de vérification | — | `docs/matrice-conformite.md` | — | — |

## Règles de rédaction

- Une capture = une légende qui dit ce qu'elle prouve.
- Pour chaque chiffre : d'où il vient (commande, outil, date).
- Distinguer « estimé » et « mesuré ».
- Si une exigence n'est pas atteinte, l'écrire, avec la cause et ce qui aurait été fait.
- Si tu as utilisé l'IA pour produire le code, respecte les règles de ton école sur la déclaration de son usage.
