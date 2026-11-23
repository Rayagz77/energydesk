# Matrice de conformité — EnergyDesk (BC3)

Statuts : **Non commencé** · **En cours** · **Testé** · **Bloqué**.

Règle : une ligne passe à « Testé » uniquement quand la commande de vérification a été exécutée sur TON environnement et que la preuve est rangée dans `docs/preuves/`.

« Code prêt » signifie que le code existe et a été vérifié au moment de la génération : tests automatisés verts sur PostgreSQL réel, rendu du chart contrôlé, test de fumée de l'API. Il reste à l'exécuter chez toi.

Mise à jour : 23/11/2026, livraison du code. Étapes A à J : voir `docs/guide-execution.md`.

## M — Périmètre métier

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| M01 | Inscription et connexion sécurisées | Code prêt, tests verts | `backend/app/api/routes/auth.py` | `pytest tests/test_auth.py` ; étape B3 | Trace `demo-compose` | En cours |
| M02 | Création de ticket | Code prêt, tests verts | `routes/tickets.py` | B3 | Trace, capture | En cours |
| M03 | Liste et détail | Code prêt, tests verts | `routes/tickets.py`, `frontend/src/tickets.html`, `ticket.html` | B3 + navigateur | Captures | En cours |
| M04 | Statut modifiable par un agent seulement | Code prêt, tests verts (403, 409) | `routes/tickets.py`, `models` | `pytest -k status` | Sortie pytest | En cours |
| M05 | Attribution à un agent | Code prêt, tests verts | `routes/tickets.py` | B3 | Trace | En cours |
| M06 | Commentaires | Code prêt, tests verts | `routes/tickets.py` | B3 | Trace | En cours |
| M07 | Pièce jointe | Code prêt, tests verts + test de fumée S3 | `routes/attachments.py`, `services/storage.py` | B3 + console MinIO | Capture bucket | En cours |
| M08 | Tableau de bord métier | Code prêt, tests verts | `routes/stats.py`, `frontend/src/dashboard.html` | Navigateur | Capture | En cours |
| M09 | Notification asynchrone | Code prêt, tests verts, rattrapage vérifié | `worker/` | B3 + `docker compose logs worker` | Log `notification_sent` | En cours |
| M10 | Isolation entre utilisateurs | Code prêt, tests verts (404) | `api/deps.py` | B3 étape 6 | Trace | En cours |

## A — Conteneurisation et architecture (20 pts · C6.2, C7.1)

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| A01 | Front servi séparément par Nginx | Code prêt | `frontend/Dockerfile`, `nginx/` | `docker compose ps` | Capture | En cours |
| A02 | API REST stateless + OpenAPI | Code prêt | `backend/app/main.py` | `/api/docs` | Capture | En cours |
| A03 | PostgreSQL + migrations versionnées | Code prêt ; migrations testées | `backend/alembic/` | Service `migrate` exited (0) | Capture | En cours |
| A04 | Stockage objet hors PostgreSQL | Code prêt | `services/storage.py` | Console MinIO | Capture | En cours |
| A05 | File de messages + worker | Code prêt | `services/messaging.py`, `worker/` | Console RabbitMQ | Capture | En cours |
| A06 | Dockerfiles multi-stage, légers, non root | Code prêt | `*/Dockerfile` | `docker images`, `docker inspect` | Tailles | En cours |
| A07 | Aucun secret dans les images | Code prêt | `.dockerignore`, CI Trivy | Job `security-scan` | Log CI | En cours |
| A08 | Images versionnées publiées | Code prêt | `ci.yml` (job build) | GHCR | Capture | En cours |
| A09 | Compose complet avec healthchecks | Code prêt ; `docker compose config` valide | `docker-compose.yml` | B2 | Capture | En cours |
| A10 | Scénario complet dans Docker | Script prêt | `scripts/demo-compose.ps1` | B3 | Trace | En cours |

## K — Kubernetes (20 pts · C7.1, C8.1, C6.1)

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| K01 | Namespaces dev/test/prod | Code prêt | `infra/terraform/local/main.tf` | `kubectl get ns` | Sortie | En cours |
| K02 | Deployments, Services | Chart rendu et contrôlé | `templates/api.yaml`, `worker.yaml`, `frontend.yaml` | `kubectl get deploy,svc -n …` | Sortie | En cours |
| K03 | Ingress | Chart prêt (Traefik) | `templates/ingress.yaml` | D5 (curl Host) | Sortie | En cours |
| K04 | ConfigMaps, Secrets | Chart + script | `configmap.yaml`, `scripts/create-k8s-secrets.ps1` | `kubectl get cm,secret` | Sortie | En cours |
| K05 | Requests et limits | Chart prêt | `values.yaml` | `kubectl describe pod` | Sortie | En cours |
| K06 | Probes startup/readiness/liveness | Chart prêt | `templates/*.yaml` | `kubectl describe pod` | Sortie | En cours |
| K07 | PV pour PostgreSQL | Chart prêt | `templates/postgres.yaml` | E2 | Sortie | En cours |
| K08 | Stockage objet cloud | Terraform + values prêts | `infra/terraform/cloud`, `values-cloud.yaml` | H3 | Capture bucket | En cours |
| K09 | HPA sous charge mesurée | Chart + k6 prêts | `templates/api.yaml`, `deploy/k8s/k6-load-job.yaml` | E4 | Sorties HPA et k6 | En cours |
| K10 | Recréation d'un pod | — | — | E1 | Sortie | Non commencé |
| K11 | Rolling update | Stratégie configurée | `values.yaml` | E3 | Sortie | En cours |
| K12 | Stratégie documentée | Fait | `docs/deploiement.md` | Lecture | Section du rapport | En cours |

## C — CI/CD et IaC (20 pts · C7.2, C7.3, C8.2)

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| C01 | Pipeline sur push | Code prêt | `.github/workflows/ci.yml` | C1 | Capture du run | En cours |
| C02 | Lint | Prêt (ruff vert à la génération) | `pyproject.toml` | Job lint | Capture | En cours |
| C03 | Tests automatisés | 41 + 15 tests verts à la génération | `backend/tests`, `worker/tests` | Jobs de test | Artefacts JUnit | En cours |
| C04 | Sécurité et scan d'images | Code prêt | `ci.yml` | Jobs security-scan et build | Log Trivy | En cours |
| C05 | Build et push versionnés | Code prêt | `ci.yml`, `VERSION` | GHCR | Capture | En cours |
| C06 | Mise à jour de la version déployée | Code prêt | `ci.yml` (gitops-update-dev), `promote.yml` | Commit `deploy(dev)` | Historique Git | En cours |
| C07 | Déploiement GitOps Argo CD | Manifests prêts | `deploy/argocd/` | D4 | Capture Argo CD | En cours |
| C08 | GitHub Secrets documentés | Fait (aucun requis) | `docs/guide-execution.md` C4 | Lecture | Section du rapport | En cours |
| C09 | Terraform réseau | Code prêt (validé en CI) | `infra/terraform/cloud/main.tf` | H2 | Sortie plan/apply | En cours |
| C10 | Terraform cluster | Code prêt | idem | H2 | Sortie | En cours |
| C11 | Terraform base et stockage | Code prêt | idem | H2 | Sortie | En cours |
| C12 | Terraform stockage objet | Code prêt | idem | H2 | Sortie | En cours |
| C13 | Terraform IAM | Code prêt | idem | H2 | Sortie | En cours |
| C14 | Reproductible depuis zéro | — | — | H4 | Sorties destroy/apply | Non commencé |
| C15 | Séparation local / cloud | Fait | `infra/terraform/local`, `cloud` | Lecture | Arborescence | En cours |

## O — Observabilité (10 pts · C8.1)

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| O01 | Logs JSON API et worker | Code prêt, vérifié au test de fumée | `core/logging.py`, `worker/logging_setup.py` | `kubectl logs` | Extrait | En cours |
| O02 | Collecte et consultation des logs | Config prête | `observability/values/loki.yaml`, `alloy.yaml` | F2 | Capture Loki | En cours |
| O03 | Requêtes, latence, erreurs | Code prêt, vérifié | `core/observability.py` | `/metrics`, F1 | Capture | En cours |
| O04 | CPU/RAM, état des pods | Dashboard prêt | `files/grafana-dashboard.json` | F1 | Capture | En cours |
| O05 | Dashboard Grafana | Prêt | idem | F1 | Capture | En cours |
| O06 | Alerte testée | Règles prêtes | `templates/monitoring.yaml` | F3 | Captures Pending, Firing, résolue | En cours |
| O07 | SLI/SLO | Règles prêtes | idem, `docs/observabilite.md` | F4 | Valeurs mesurées | En cours |
| O08 | Dashboard métier distinct | Fait | `frontend/src/dashboard.html` | Navigateur | Capture | En cours |

## S — Sécurité ISO/IEC 27001:2022 (10 pts · C6.3)

| ID | Mesure | Contrôles | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| S01 | Authentification, Argon2id | A.8.5 | `core/security.py` | Test `$argon2id$` | Sortie pytest | En cours |
| S02 | Contrôle d'accès applicatif | A.5.15, A.8.3 | `api/deps.py` | Tests 403/404 | Sortie pytest | En cours |
| S03 | Secrets hors Git | A.5.17, A.8.12 | `.gitignore`, scripts | `git check-ignore -v .env` | Sortie | En cours |
| S04 | RBAC Kubernetes | A.5.15, A.8.2 | `templates/rbac.yaml`, `serviceaccount.yaml` | G1 | Sorties `can-i` | En cours |
| S05 | IAM cloud au moindre privilège | A.5.15, A.8.2 | `infra/terraform/cloud/main.tf` | H3 | Console IAM | En cours |
| S06 | TLS en transit | A.8.24 | `ingress.yaml`, `create-tls-secret.ps1` | D5 HTTPS | Sortie curl | En cours |
| S07 | Chiffrement au repos | A.8.24 | `cloud/main.tf` | Console | Capture | En cours |
| S08 | Journalisation sécurité | A.8.15 | `core/logging.py` | F2 | Capture Loki | En cours |
| S09 | Supervision et alertes | A.8.16 | `monitoring.yaml` | F3 | Captures | En cours |
| S10 | Sauvegardes vers stockage objet | A.8.13 | `templates/backup.yaml`, `app/backup.py` | G2 | Trace | En cours |
| S11 | Test de restauration | A.8.13 | `deploy/k8s/restore-test-job.yaml`, `scripts/restore-test.ps1` | G2 | `restore-test-<date>.txt` | En cours |
| S12 | Séparation des environnements | A.8.31 | Terraform local, values | `kubectl get ns` | Sortie | En cours |
| S13 | Configuration versionnée | A.8.9 | tout le dépôt | Historique | Lien | En cours |
| S14 | Accès au code source | A.8.4 | Réglages GitHub | C3 | Capture | Non commencé |
| S15 | Sécurité intégrée au CI | A.8.25, A.8.28, A.8.7 | `ci.yml`, `dependabot.yml` | C1 | Logs | En cours |
| S16 | Uploads dangereux | A.8.7 | `routes/attachments.py`, `services/files.py` | Tests 413/415 | Sortie pytest | En cours |
| S17 | Déclaration d'applicabilité | — | `docs/securite-iso27001.md` §3 | Lecture | Document | En cours |

## F — FinOps (10 pts · C6.4)

| ID | Exigence | Réalisé | Fichiers | Vérification | Preuve | Statut |
|---|---|---|---|---|---|---|
| F01 | Coût chiffré (estimation sourcée) | Gabarit prêt, tarifs à compléter | `docs/finops.md` | Lecture | Tableau | En cours |
| F02 | Optimisation 1 : taille des images | Script prêt | `Dockerfile.naive`, `scripts/measure-images.ps1` | B4 | Trace | En cours |
| F03 | Optimisation 2 : requests après mesure | Méthode prête | `values.yaml` | Étape I | Sorties `kubectl top` | Non commencé |
| F04 | Estimations et coûts observés distingués | Gabarit prêt | `docs/finops.md` | Facture | Capture | Non commencé |

## R — Livrables et rapport (10 pts)

| ID | Livrable | Réalisé | Fichiers | Statut |
|---|---|---|---|---|
| R01 | Dépôt reconstructible par un tiers | README et guide | `README.md`, `docs/guide-execution.md` | En cours |
| R02 | Note de cadrage (modèle fourni) | Modèle non reçu | `docs/cadrage/` | Bloqué |
| R03 | Cahier des charges | Rédigé | `docs/cadrage/cahier-des-charges.md` | En cours |
| R04 | Rapport 10–15 pages | Plan prêt | `docs/rapport/plan-rapport.md` | Non commencé |
| R05 | Preuves archivées | Dossier prêt, scripts qui y écrivent | `docs/preuves/` | Non commencé |
