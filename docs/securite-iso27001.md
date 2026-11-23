# Sécurité et contrôles ISO/IEC 27001:2022

Ce document rattache chaque mesure d'EnergyDesk aux contrôles de l'Annexe A cités dans le sujet. La colonne « Preuve » indique quoi montrer dans le rapport.

## 1. Tableau de correspondance

| Mesure dans EnergyDesk | Mise en œuvre | Contrôle(s) Annexe A | Preuve |
|---|---|---|---|
| Authentification sécurisée | Mots de passe hachés en **Argon2id** (pwdlib). 12 caractères minimum. Jeton JWT signé HS256, valable 30 min, avec `iss` et `exp` obligatoires. Temps de réponse constant si le compte n'existe pas | A.8.5 | `tests/test_auth.py`, requête SQL montrant `$argon2id$` |
| Contrôle d'accès applicatif | Deux rôles. Un utilisateur ne voit que ses tickets (**404** sinon, l'existence n'est pas révélée). Statut et attribution réservés aux agents. Comptes agents créés uniquement par commande d'administration | A.5.15, A.8.3 | `tests/test_tickets.py` (403/404) |
| Moindre privilège Kubernetes | Compte de service sans droit et sans jeton monté. Rôle `viewer` en lecture seule (pas de lecture des Secrets). Quotas par namespace | A.5.15, A.8.2 | `kubectl auth can-i` (guide, G1) |
| Moindre privilège cloud | Identité IAM dédiée à l'application, limitée aux objets du stockage, dans un seul projet. Les clés administrateur ne vont jamais dans le cluster | A.5.15, A.8.2 | `infra/terraform/cloud/main.tf`, console IAM |
| Gestion des secrets | Aucun secret dans Git ni dans les images. `.env` ignoré. Secrets Kubernetes créés hors Git par script. Identifiants cloud en variables d'environnement. État Terraform ignoré par Git. Scan Trivy des secrets en CI | A.5.17, A.8.12 | `git check-ignore -v .env`, job `security-scan` |
| Chiffrement en transit | HTTPS sur l'Ingress (certificat auto-signé en local). Connexion à la base managée en `sslmode=require` en cloud. Endpoint S3 en HTTPS en cloud | A.8.24 | `curl -vk https://...` |
| Chiffrement au repos | `encryption_at_rest = true` sur PostgreSQL managé. Chiffrement côté serveur du stockage objet du fournisseur (à confirmer dans sa documentation) | A.8.24 | `main.tf`, console Scaleway |
| Journalisation de sécurité | Logs JSON : `login_success`, `login_failed`, `token_rejected`, `access_denied`, `upload_rejected`, `ticket_status_changed`, `user_registered`. Collecte par Alloy et consultation dans Loki | A.8.15 | Requête Loki (guide, F2) |
| Supervision et alertes | Prometheus, Grafana, Alertmanager. Alertes API indisponible, taux d'erreur, latence, worker déconnecté | A.8.16 | Alerte `Firing` (guide, F3) |
| Sauvegardes | CronJob quotidienne `pg_dump` vers un bucket. Restauration testée dans une base vide. En cloud : sauvegardes automatiques du service managé et expiration à 30 jours dans le bucket | A.8.13 | `restore-test-<date>.txt` |
| Configuration versionnée | Tout est décrit par du code versionné : Dockerfiles, Compose, Helm, Terraform, Argo CD, CI | A.8.9 | Historique Git |
| Séparation des environnements | Namespaces dev/test/prod, quotas distincts, prod synchronisée manuellement, promotion explicite des versions | A.8.31 | `kubectl get ns`, Argo CD |
| Accès au code source | Dépôt GitHub, protection de la branche `main` (contrôles obligatoires, pas de force-push), permissions minimales du `GITHUB_TOKEN` par job | A.8.4 | Capture des règles de branche |
| Cycle de développement sécurisé | Lint avec règles de sécurité (ruff « S »), tests automatisés, scans Trivy (dépendances, secrets, configuration, images), Dependabot, versions figées | A.8.25, A.8.28 | Run GitHub Actions |
| Protection contre les logiciels malveillants | Pièces jointes : type vérifié sur la **signature binaire** (PDF/PNG/JPEG seulement), 5 Mo maximum, nom nettoyé, clé de stockage aléatoire, téléchargement avec `nosniff`. Images scannées. Action Trivy épinglée sur une version saine | A.8.7 | `tests/test_attachments.py` |
| Durcissement des conteneurs | Utilisateurs non root, système de fichiers en lecture seule, capacités Linux retirées, `seccomp RuntimeDefault`, pas d'élévation de privilèges. En-têtes HTTP de sécurité (CSP stricte, `X-Frame-Options`, `nosniff`) | A.8.9, A.8.28 | `kubectl get pod -o yaml` |

## 2. Compromis assumés

- **MinIO en local** avec le compte principal, par simplicité. En cloud, l'application a sa propre identité IAM.
- **Périmètre IAM au projet** plutôt qu'au bucket. Une *bucket policy* restreindrait l'accès à un seul bucket. Mais elle doit aussi autoriser l'identité qui exécute Terraform, sous peine de bloquer les `apply` et `destroy` suivants. Nous l'avons gardée comme amélioration.
- **Secrets Kubernetes** encodés en base64 dans etcd. Améliorations possibles : Sealed Secrets ou External Secrets avec un coffre-fort, et le chiffrement d'etcd.
- **Jeton en `sessionStorage`** côté navigateur. Le risque XSS est réduit par la CSP stricte et l'affichage systématique par `textContent`.
- **Fournisseurs tiers** : MinIO communautaire archivé en février 2026, image reprise chez Chainguard. Compromission de `trivy-action` en mars 2026, action épinglée sur la seule version non compromise. Ces deux faits justifient le contrôle de la chaîne d'approvisionnement.

## 3. Déclaration d'applicabilité (extrait, facultatif)

| Contrôle | Applicable | Justification |
|---|---|---|
| A.5.15 Contrôle d'accès | Oui | Données de tickets propres à chaque utilisateur |
| A.5.17 Informations d'authentification | Oui | Mots de passe, clés JWT, clés cloud |
| A.8.2 Droits d'accès à privilèges | Oui | Comptes Kubernetes et cloud |
| A.8.3 Restriction de l'accès à l'information | Oui | Isolation entre utilisateurs |
| A.8.4 Accès au code source | Oui | Le dépôt pilote le déploiement (GitOps) |
| A.8.5 Authentification sécurisée | Oui | Application exposée sur le web |
| A.8.7 Protection contre les logiciels malveillants | Oui | Téléversement de fichiers |
| A.8.9 Gestion de la configuration | Oui | Infrastructure as code |
| A.8.12 Prévention de la fuite de données | Oui | Secrets hors Git et hors images |
| A.8.13 Sauvegarde | Oui | Données persistantes |
| A.8.15 Journalisation | Oui | Traçabilité des accès |
| A.8.16 Activités de surveillance | Oui | Disponibilité du service |
| A.8.24 Cryptographie | Oui | Transit et repos |
| A.8.25 / A.8.28 Développement sécurisé | Oui | Code développé en interne |
| A.8.31 Séparation des environnements | Oui | dev, test, prod |
| A.7.x Sécurité physique | Non (délégué) | Centres de données du fournisseur cloud |
