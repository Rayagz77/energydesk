# Cahier des charges fonctionnel et technique — EnergyDesk

## 1. Contexte et objectif

EnergyDesk permet de signaler et de suivre des incidents techniques liés aux compteurs électriques et aux données de comptage. Le projet valide le bloc BC3 : l'accent est mis sur la chaîne d'ingénierie et d'exploitation cloud-native, pas sur la richesse fonctionnelle.

Toutes les données sont **fictives**. L'application ne communique avec aucun compteur réel, aucun système d'exploitation de réseau et aucune base d'entreprise.

## 2. Acteurs

| Acteur | Description |
|---|---|
| Utilisateur | Signale des incidents et suit uniquement ses propres tickets |
| Agent support | Consulte tous les tickets, les attribue, change leur statut, commente |
| Administrateur technique | Crée les comptes agents (commande d'administration), exploite la plateforme |

## 3. Exigences fonctionnelles

| ID | Exigence | Règle de gestion |
|---|---|---|
| F1 | Inscription | Email unique, nom de 2 à 100 caractères, mot de passe de 12 caractères minimum. Rôle « utilisateur » imposé |
| F2 | Connexion | Email et mot de passe. Jeton valable 30 minutes |
| F3 | Créer un ticket | Titre (5 à 120 caractères), description, type d'incident, identifiant d'équipement au format `CPT-FICTIF-000000`, priorité |
| F4 | Lister les tickets | Filtres par statut et par priorité, pagination. Un utilisateur ne voit que ses tickets |
| F5 | Consulter un ticket | Détail, commentaires, pièces jointes, état de la notification |
| F6 | Changer le statut | Agent uniquement. Transitions : Nouveau → En cours → Résolu → Fermé, et Résolu → En cours (réouverture) |
| F7 | Attribuer | Agent uniquement, vers un agent actif |
| F8 | Commenter | Auteur du ticket ou agent. 2 000 caractères maximum |
| F9 | Pièce jointe | PDF, PNG ou JPEG, 5 Mo maximum, type vérifié sur le contenu réel |
| F10 | Tableau de bord | Ouverts (Nouveau), En cours, Résolus, Critiques non fermés. Périmètre selon le rôle |
| F11 | Notification asynchrone | À chaque création de ticket. Destinataires : support et demandeur. Sans doublon |

Valeurs de référence :
- Statuts : Nouveau, En cours, Résolu, Fermé.
- Priorités : Basse, Moyenne, Haute, Critique.
- Types : compteur ne transmettant plus, anomalie de relevé ou d'index, dysfonctionnement d'équipement, demande de vérification ou d'intervention.

Hors périmètre : gestion avancée des interventions, géolocalisation, IA, messagerie temps réel, connexion à un système de comptage réel.

## 4. Modèle de données (4 entités)

- **User** : id, email, full_name, password_hash, role (user|agent), is_active, created_at.
- **Ticket** : id, title, description, category, equipment_id, priority, status, created_by, assigned_to, notified_at, created_at, updated_at.
- **Comment** : id, ticket_id, author_id, content, created_at.
- **Attachment** : id, ticket_id, uploaded_by, original_filename, object_key, content_type, size_bytes, sha256, created_at. Le fichier est dans le stockage objet. Seules ses métadonnées sont en base.

## 5. Exigences techniques

| Domaine | Exigence |
|---|---|
| Architecture | Front-end (Nginx), API REST stateless (FastAPI), PostgreSQL, stockage objet S3, RabbitMQ, worker Python : services distincts |
| API | Documentation OpenAPI (`/api/docs`), validation des entrées, endpoints `/health/live` et `/health/ready`, métriques `/metrics` |
| Données | Migrations Alembic versionnées, données persistantes, aucun mot de passe dans le code |
| Conteneurs | Images multi-stage, non root, sans secret, versionnées (`<version>-<sha>`), publiées sur GHCR, healthchecks |
| Orchestration | Kubernetes (chart Helm), namespaces dev/test/prod, Ingress, ConfigMaps et Secrets, requests et limits, probes, PVC, HPA |
| CI/CD | GitHub Actions sur push : lint, tests, scans, build, publication, mise à jour GitOps |
| IaC | Terraform local (plateforme) et cloud (réseau, cluster, base, stockage, IAM) |
| GitOps | Argo CD synchronise le chart depuis Git |
| Observabilité | Logs JSON (Loki), métriques (Prometheus), dashboard Grafana, alertes, 2 SLI/SLO |
| Sécurité | Contrôles ISO/IEC 27001:2022 listés dans `docs/securite-iso27001.md` |
| FinOps | Coût estimé et deux optimisations mesurées (`docs/finops.md`) |

## 6. Exigences non fonctionnelles

| Critère | Objectif |
|---|---|
| Disponibilité de l'API | SLO 99 % (requêtes sans erreur 5xx) |
| Latence | SLO 95 % des requêtes en moins de 300 ms |
| Déploiement | Sans interruption (rolling update, `maxUnavailable: 0`) |
| Résilience | Recréation automatique des pods ; pas de perte de notification si RabbitMQ est indisponible (balayage de rattrapage) |
| Sauvegarde | Quotidienne, restauration testée |

## 7. Critères d'acceptation

1. Le scénario `scripts/demo-compose.ps1` réussit entièrement dans Docker.
2. Le pipeline CI est vert sur `main` et publie des images versionnées.
3. Argo CD affiche dev et test `Synced` et `Healthy`.
4. Le HPA augmente le nombre de pods sous la charge mesurée par k6.
5. Une alerte est déclenchée puis résolue.
6. Une sauvegarde est restaurée avec succès.
7. `terraform apply` crée l'infrastructure cloud depuis un projet vide.
