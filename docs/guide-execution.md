# Guide d'exécution pas à pas — EnergyDesk

Ce guide te dit quoi lancer, dans quel ordre, ce que tu dois voir et quelle preuve garder.
Le code est déjà écrit. Ton travail consiste à l'exécuter, à vérifier et à documenter.

Règle d'or : une exigence passe à « Testé » dans `docs/matrice-conformite.md` seulement quand tu as exécuté la commande et rangé la preuve dans `docs/preuves/`.

Si une commande échoue, copie-moi le message d'erreur complet. Ne contourne pas l'erreur.

---

## Vue d'ensemble

| Étape | Où | Durée estimée | Résultat |
|---|---|---|---|
| A. Dépôt Git et GitHub | PC (PowerShell) | 30 min | Code sur GitHub |
| B. Docker Compose et scénario complet | PC (PowerShell) | 1 h 30 | Axe conteneurisation prouvé |
| C. Pipeline CI/CD | GitHub | 1 h | Images publiées, tag GitOps |
| D. Cluster Kubernetes et Argo CD | Codespaces | 2 h | Déploiement GitOps dev/test/prod |
| E. Résilience, rolling update, HPA | Codespaces | 1 h 30 | Axe Kubernetes prouvé |
| F. Observabilité et alerte | Codespaces | 1 h 30 | Grafana, Loki, alerte, SLO |
| G. Sécurité, sauvegarde, restauration | Codespaces | 1 h | Preuves ISO 27001 |
| H. Cloud avec Terraform | Codespaces + Scaleway | 2 h | Infrastructure cible créée puis détruite |
| I. FinOps | PC + Codespaces | 1 h | Deux optimisations mesurées |
| J. Rapport | PC | 4 à 6 h | Rapport de 10 à 15 pages |

Total estimé : environ 17 à 20 heures. Ce sont des estimations, pas des mesures.

---

## Étape A — Dépôt Git et GitHub (PC)

### A1. Décompresser l'archive

Décompresse `energydesk.zip` dans `C:\Users\<toi>\projets\energydesk`. Évite tout dossier synchronisé par OneDrive.

```powershell
Set-Location "$HOME\projets\energydesk"
Get-ChildItem
```

Résultat attendu : les dossiers `backend`, `worker`, `frontend`, `deploy`, `infra`, `observability`, `scripts`, `docs` et le fichier `docker-compose.yml`.

### A2. Créer le dépôt GitHub

Sur github.com, crée un dépôt vide nommé `energydesk`. Rends-le **public**. Le code ne contient aucun secret, et Argo CD pourra lire le dépôt sans identifiants. Ne coche ni README ni `.gitignore`.

### A3. Remplacer « OWNER » par ton compte GitHub

Les manifests contiennent le mot `OWNER` à la place de ton nom de compte. Ce script le remplace partout :

```powershell
.\scripts\set-owner.ps1 -Owner <ton-compte-github>
```

Si PowerShell refuse d'exécuter le script : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis relance.

### A4. Premier commit et envoi

```powershell
git init -b main
git add .
git status          # verifier qu'aucun fichier .env n'apparait
git commit -m "feat: EnergyDesk - application, conteneurs, Kubernetes, CI/CD, IaC"
git remote add origin https://github.com/<ton-compte>/energydesk.git
git push -u origin main
```

Ce push déclenche déjà le pipeline (étape C). Laisse-le tourner pendant l'étape B.

---

## Étape B — Docker Compose et scénario complet (PC)

### B1. Préparer le fichier `.env`

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
notepad .env
```

Remplace chaque `change-me` par une valeur générée par la commande Python. Lance la commande plusieurs fois pour avoir des valeurs différentes. `JWT_SECRET_KEY` doit faire au moins 32 caractères. `MINIO_ROOT_PASSWORD` doit en faire au moins 8. `AGENT_PASSWORD` doit en faire au moins 12.

Vérifie que le fichier est bien ignoré par Git :

```powershell
git check-ignore -v .env
```

Résultat attendu : une ligne qui cite `.gitignore` et `.env`.

### B2. Démarrer la pile

Ferme les applications lourdes (navigateur avec beaucoup d'onglets, Teams). Ton PC a 8 Go.

```powershell
docker compose up -d --build
docker compose ps
```

- `--build` construit les trois images (API, worker, front). La première fois, compte 5 à 10 minutes.
- `docker compose ps` affiche l'état. Attendu : `postgres`, `rabbitmq`, `api`, `frontend` et `worker` en `healthy`, `minio` en `running`, et `migrate` en `exited (0)`. Le service `migrate` applique les migrations puis s'arrête : c'est normal.

Preuve : capture de `docker compose ps` dans `docs/preuves/`.

### B3. Scénario métier complet

```powershell
.\scripts\demo-compose.ps1
```

Ce script joue tout le parcours : création de l'agent, inscription, connexion, ticket critique, pièce jointe, notification par le worker, isolation entre utilisateurs, traitement par l'agent, tableau de bord. Chaque étape affiche `[OK]`. La trace est enregistrée dans `docs/preuves/demo-compose-<date>.txt`.

Ensuite, fais le parcours dans le navigateur et prends des captures :
- http://localhost:8080 : connexion, tableau de bord, liste des tickets, détail d'un ticket.
- http://localhost:8080/api/docs : documentation OpenAPI.
- http://localhost:15672 : console RabbitMQ, file `ticket.created` (identifiants `RABBITMQ_*` du `.env`).
- http://localhost:9001 : console MinIO, objets `tickets/...` et `notifications/...`.

Pour voir les logs JSON du worker :

```powershell
docker compose logs worker --tail 20
```

Tu dois voir une ligne avec `"event": "notification_sent"`.

### B4. Mesure FinOps n° 1 : taille des images

```powershell
.\scripts\measure-images.ps1
```

Le script construit une image API « naïve » (`Dockerfile.naive` : image Python complète, une seule étape, outils de test inclus) et l'image optimisée (multi-stage, `python:3.12-slim`). Il affiche les deux tailles et le gain en pourcentage. Le résultat est enregistré dans `docs/preuves/`. Ce sont tes chiffres réels pour le rapport.

### B5. Arrêter la pile

```powershell
docker compose down        # les donnees restent dans les volumes
```

Ajoute `-v` seulement si tu veux tout effacer.

### Erreurs fréquentes (étape B)

| Symptôme | Cause | Correction |
|---|---|---|
| `api` redémarre en boucle | Clé JWT trop courte ou `.env` incomplet | `docker compose logs api`, puis corriger `.env` |
| `migrate` en erreur | Mot de passe de base modifié après le premier démarrage | `docker compose down -v` puis relancer (efface les données) |
| `error during connect` | Docker Desktop arrêté | Démarrer Docker Desktop |
| Le worker ne notifie pas | RabbitMQ pas encore prêt | Attendre 30 s. Le balayage de rattrapage passe toutes les 30 s. |
| Port 8080 déjà utilisé | Autre application | Changer `127.0.0.1:8080:8080` en `127.0.0.1:8088:8080` dans `docker-compose.yml` |

---

## Étape C — Pipeline CI/CD (GitHub)

### C1. Suivre l'exécution

Sur GitHub, onglet **Actions**, workflow `ci`. Les jobs s'enchaînent ainsi :

1. `lint` : qualité du code avec ruff, y compris des règles de sécurité.
2. `test-backend` et `test-worker` : tests automatisés sur un vrai PostgreSQL.
3. `security-scan` : Trivy sur les dépendances, les secrets et la configuration.
4. `validate-infra` : `helm lint`, `helm template` avec kubeconform, `terraform validate`.
5. `build` : construction des trois images, scan Trivy de chaque image, publication sur GHCR (branche `main` uniquement).
6. `gitops-update-dev` : écriture du nouveau tag dans `values-dev.yaml`, puis commit automatique.

Si un job est rouge : ouvre-le, copie le log de l'étape en échec et envoie-le-moi. Je n'invente pas les résultats. Je corrige à partir du vrai log.

Preuves : capture du run complet en vert, capture des images sur GHCR (onglet **Packages** de ton profil), et le commit `deploy(dev): energydesk 0.1.0-xxxxxxx` dans l'historique.

### C2. Rendre les images publiques

Pour chacune des trois images (`energydesk-api`, `energydesk-worker`, `energydesk-frontend`) : **Packages** → image → **Package settings** → **Change visibility** → **Public**. Le cluster pourra télécharger les images sans secret.

### C3. Protéger la branche `main` (ISO 27001 A.8.4)

**Settings** → **Branches** → **Add branch ruleset** (ou *protection rule*) sur `main`. Active « Require status checks to pass » avec les jobs `lint` et `test-backend`. Active aussi « Block force pushes ». Capture d'écran pour le rapport.

Remarque : le bot GitHub Actions doit pouvoir pousser le commit GitOps. Si la règle bloque ce push, ajoute `github-actions` dans les exceptions (*bypass list*).

### C4. Secrets GitHub nécessaires

Aucun. Le pipeline utilise uniquement le jeton automatique `GITHUB_TOKEN`, avec des permissions limitées job par job : `packages: write` pour publier, `contents: write` pour le commit GitOps. C'est un argument de sécurité à mettre dans le rapport.

---

## Étape D — Cluster Kubernetes et Argo CD (Codespaces)

### D1. Créer le codespace

Sur la page du dépôt : **Code** → **Codespaces** → **…** → **New with options** → type de machine **4-core**. Le fichier `.devcontainer/devcontainer.json` installe tout : Minikube, kubectl, Helm, Terraform, k9s, k3d et PowerShell. Attends la fin de l'installation (environ 5 minutes).

Important pour ton quota : arrête le codespace quand tu ne t'en sers pas (**Codespaces** → **…** → **Stop codespace**).

Dans le terminal du codespace (PowerShell) :

```powershell
./scripts/check-env.ps1
```

### D2. Créer le cluster et la plateforme

```powershell
pwsh ./scripts/cluster-up.ps1
```

Si ton cours utilise k3s : `pwsh ./scripts/cluster-up.ps1 -Distro k3d`.

Ce script :
1. crée le cluster (Minikube, 4 CPU, 10 Go) et active `metrics-server` (indispensable au HPA) ;
2. lance `terraform apply` sur `infra/terraform/local`, qui crée les namespaces `energydesk-dev`, `energydesk-test` et `energydesk-prod` avec quotas, puis installe Traefik, Prometheus, Grafana, Alertmanager, Loki, Alloy et Argo CD.

Compte 10 à 15 minutes. Vérification :

```powershell
kubectl get ns
kubectl get pods -A
helm list -A
```

Preuve : la sortie de `kubectl get ns` et de `helm list -A`. Note les versions affichées par `helm list -A` : tu pourras les épingler dans `infra/terraform/local/terraform.tfvars`.

### D3. Créer les secrets (hors Git)

Copie ton `.env` du PC dans le codespace : crée le fichier `.env` dans l'explorateur de VS Code et colle son contenu. Il reste ignoré par Git. Ensuite :

```powershell
pwsh ./scripts/create-k8s-secrets.ps1
pwsh ./scripts/create-tls-secret.ps1 -Namespace energydesk-prod -HostName energydesk.local
```

### D4. Déclarer les applications dans Argo CD

```powershell
kubectl apply -f deploy/argocd/project.yaml
kubectl apply -f deploy/argocd/applications/energydesk-dev.yaml
kubectl apply -f deploy/argocd/applications/energydesk-test.yaml
kubectl apply -f deploy/argocd/applications/energydesk-prod.yaml
kubectl get applications -n argocd
```

Résultat attendu : `energydesk-dev` et `energydesk-test` passent à `Synced` et `Healthy` en quelques minutes. `energydesk-prod` reste `OutOfSync` : c'est voulu, la production se synchronise à la main.

Interface Argo CD :

```powershell
kubectl get secret -n argocd argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
kubectl port-forward -n argocd svc/argocd-server 8081:80
```

Ouvre le port 8081 depuis l'onglet **Ports** du codespace. Connecte-toi avec `admin` et le mot de passe affiché. Clique sur `energydesk-prod` → **SYNC**.

Preuves : capture des trois applications, et capture de l'arbre des ressources d'une application.

### D5. Accéder à l'application

```powershell
kubectl port-forward -n energydesk-dev svc/energydesk-frontend 8080:80
```

Ouvre le port 8080 depuis l'onglet **Ports**. Le front relaie `/api` vers l'API : toute l'application fonctionne.

Créer l'agent dans le cluster :

```powershell
kubectl exec -n energydesk-dev deploy/energydesk-api -- sh -c 'AGENT_PASSWORD="<mot-de-passe>" python -m app.cli create-agent --email agent@energydesk.local --full-name "Agent Demo"'
```

Tester l'Ingress Traefik (routage par nom d'hôte) :

```powershell
kubectl port-forward -n traefik svc/traefik 8000:80
curl -s -H "Host: dev.energydesk.local" http://localhost:8000/api/v1/auth/me
```

Résultat attendu : `{"detail":"Not authenticated"}` ou un message équivalent. La requête est bien passée par l'Ingress jusqu'à l'API.

Tester le HTTPS en prod :

```powershell
kubectl port-forward -n traefik svc/traefik 8443:443
curl -sk -H "Host: energydesk.local" https://localhost:8443/ -o /dev/null -w "%{http_code}\n"
```

Résultat attendu : `200`.

---

## Étape E — Résilience, rolling update, HPA (Codespaces)

Garde k9s ouvert dans un second terminal pour suivre en direct : `k9s -n energydesk-dev`. Pour le rapport, garde aussi les sorties `kubectl`.

### E1. Recréation d'un pod supprimé

```powershell
kubectl get pods -n energydesk-dev -l app.kubernetes.io/component=api
kubectl delete pod -n energydesk-dev -l app.kubernetes.io/component=api --wait=false
kubectl get pods -n energydesk-dev -l app.kubernetes.io/component=api -w
```

Attendu : un nouveau pod apparaît avec un autre nom, puis passe `Running` et `1/1`. Le Deployment maintient le nombre de réplicas.

### E2. Persistance PostgreSQL

```powershell
kubectl delete pod -n energydesk-dev energydesk-postgres-0
kubectl wait --for=condition=ready pod/energydesk-postgres-0 -n energydesk-dev --timeout=120s
kubectl exec -n energydesk-dev energydesk-postgres-0 -- psql -U energydesk -d energydesk -c "SELECT count(*) FROM tickets;"
```

Attendu : le même nombre de tickets qu'avant la suppression. Les données sont sur le PersistentVolume (`kubectl get pvc -n energydesk-dev`).

### E3. Rolling update par GitOps

Sur ton PC, change la version, puis pousse :

```powershell
Set-Content VERSION "0.1.1"
git commit -am "chore: version 0.1.1"
git push
```

La CI construit `0.1.1-xxxxxxx` et écrit le tag dans `values-dev.yaml`. Argo CD détecte le commit et déploie. Dans le codespace, fais d'abord `git pull`, puis observe :

```powershell
kubectl rollout status deploy/energydesk-api -n energydesk-dev
kubectl rollout history deploy/energydesk-api -n energydesk-dev
kubectl get rs -n energydesk-dev -l app.kubernetes.io/component=api
```

Attendu : les nouveaux pods démarrent un par un. Un ancien pod n'est arrêté qu'une fois le nouveau prêt (`maxUnavailable: 0`). Il n'y a donc aucune interruption de service. Le ReplicaSet précédent reste disponible pour un retour arrière (`kubectl rollout undo` ou revert Git).

Promotion vers test ou prod : onglet **Actions** → `promote` → **Run workflow** → environnement et tag.

### E4. Autoscaling (HPA) sous charge mesurée

La charge est générée dans le cluster par k6. On évite ainsi la limite de débit d'un `port-forward`.

```powershell
kubectl create configmap k6-script -n energydesk-dev --from-file=scripts/load/k6-hpa.js --dry-run=client -o yaml | kubectl apply -f -
kubectl get hpa -n energydesk-dev -w
```

Dans un second terminal :

```powershell
kubectl delete job k6-load -n energydesk-dev --ignore-not-found
kubectl apply -f deploy/k8s/k6-load-job.yaml
kubectl logs -f job/k6-load -n energydesk-dev
```

Le test dure environ 7 minutes. Le Job `k6-load` utilise l'image `grafana/k6:latest` : pour la traçabilité, note la version affichée en tête des logs.

Attendu dans le premier terminal : la colonne `TARGETS` monte au-dessus de 60 %, puis `REPLICAS` passe de 1 à 2, 3 ou 4. Après la fin du test, les réplicas redescendent au bout d'environ une minute.

Preuves :
- la sortie de `kubectl get hpa -w` ;
- le résumé final de k6 (requêtes par seconde, latence p95, taux d'erreur) : c'est ta **charge mesurée** ;
- le panneau « Pods API (HPA) » de Grafana pendant le test.

Si `TARGETS` affiche `<unknown>` : metrics-server n'est pas prêt. Vérifie avec `kubectl top pods -n energydesk-dev`.

---

## Étape F — Observabilité et alerte (Codespaces)

### F1. Grafana

```powershell
kubectl get secret -n monitoring kube-prometheus-stack-grafana -o jsonpath="{.data.admin-password}" | base64 -d
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```

Connexion `admin` avec ce mot de passe. Dashboards → **EnergyDesk - état technique (energydesk-dev)**. Panneaux : SLI disponibilité, SLI latence, taux d'erreur, requêtes par seconde, latence p50/p95/p99, CPU et mémoire par pod, réplicas, redémarrages, activité du worker.

Garde bien la distinction :
- le **dashboard métier** est dans l'application (page « Tableau de bord ») : tickets ouverts, en cours, résolus, critiques ;
- le **dashboard technique** est dans Grafana : santé de la plateforme.

### F2. Logs centralisés (Loki)

Grafana → **Explore** → source **Loki** :

```
{namespace="energydesk-dev", component="api"} | json | event="login_failed"
{namespace="energydesk-dev", component="worker"} | json | event="notification_sent"
```

Provoque un échec de connexion dans l'application, puis relance la première requête : la ligne apparaît. C'est la preuve de la journalisation des événements de sécurité (ISO 27001 A.8.15).

### F3. Tester une alerte

On utilise la prod, car Argo CD n'y corrige pas automatiquement les modifications manuelles.

```powershell
kubectl scale deploy/energydesk-api -n energydesk-prod --replicas=0
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
```

Ouvre le port 9090 → **Alerts**. Après environ 1 minute, `EnergyDeskApiDown` passe de `Pending` à `Firing`. Vérifie aussi dans Alertmanager (`kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093`).

Rétablir le service :

```powershell
kubectl scale deploy/energydesk-api -n energydesk-prod --replicas=2
```

L'alerte repasse ensuite à l'état résolu. Preuves : captures `Pending`, `Firing` et résolue, avec l'heure visible.

### F4. Mesurer les SLO

Après le test de charge, dans Prometheus :

```
energydesk:api_availability:ratio_rate5m
energydesk:api_latency_under_300ms:ratio_rate5m
```

Note les valeurs mesurées et compare-les aux objectifs (99 % et 95 %). Voir `docs/observabilite.md`.

---

## Étape G — Sécurité, sauvegarde, restauration (Codespaces)

### G1. RBAC Kubernetes (moindre privilège)

```powershell
kubectl auth can-i list pods   -n energydesk-prod --as=lea --as-group=energydesk-viewers
kubectl auth can-i delete pods -n energydesk-prod --as=lea --as-group=energydesk-viewers
kubectl auth can-i get secrets -n energydesk-prod --as=lea --as-group=energydesk-viewers
kubectl auth can-i list pods   -n energydesk-prod --as=system:serviceaccount:energydesk-prod:energydesk-app
```

Attendu : `yes`, `no`, `no`, `no`. Le dernier montre que le compte de service de l'application n'a aucun droit sur l'API Kubernetes.

### G2. Sauvegarde et test de restauration

```powershell
pwsh ./scripts/restore-test.ps1 -Namespace energydesk-prod
```

Le script lance une sauvegarde immédiate vers le bucket `energydesk-backups`, puis la restaure dans une base vide et compte les lignes par table. La preuve est enregistrée dans `docs/preuves/restore-test-<date>.txt`.

### G3. Contrôles complémentaires

- `kubectl get pods -n energydesk-prod -o jsonpath="{..securityContext}"` : utilisateurs non root, privilèges retirés.
- Les rapports Trivy dans les logs du pipeline (étape C).
- Un téléversement refusé : essaie de joindre un `.exe` renommé en `.png`. Attendu : erreur 415, et un événement `upload_rejected` dans Loki.

---

## Étape H — Infrastructure cloud avec Terraform (Codespaces + Scaleway)

Coût réel : cette étape crée des ressources payantes. Fais-la d'une traite, prends les preuves, puis détruis tout.

### H1. Identifiants (jamais dans Git)

Dans la console Scaleway : **IAM** → **API keys** → génère une clé pour ton utilisateur. Dans le terminal du codespace :

```powershell
$env:SCW_ACCESS_KEY = "<access key>"
$env:SCW_SECRET_KEY = "<secret key>"
$env:SCW_DEFAULT_PROJECT_ID = "<project id>"
$env:SCW_DEFAULT_ORGANIZATION_ID = "<organization id>"
$env:TF_VAR_db_password = "<mot de passe fort>"
Copy-Item infra/terraform/cloud/terraform.tfvars.example infra/terraform/cloud/terraform.tfvars
code infra/terraform/cloud/terraform.tfvars      # renseigner project_id
```

Vérifie dans la console que le type de nœud `DEV1-M` est proposé pour Kubernetes Kapsule. Sinon, choisis le moins cher qui est proposé et mets-le dans `terraform.tfvars`.

### H2. Créer l'infrastructure

```powershell
terraform -chdir=infra/terraform/cloud init
terraform -chdir=infra/terraform/cloud plan -out tfplan
terraform -chdir=infra/terraform/cloud apply tfplan
```

Le `plan` liste ce qui va être créé : VPC, réseau privé, cluster Kapsule, pool de nœuds, PostgreSQL managé, base, droits, deux buckets, identité IAM, politique et clé de l'application. Garde sa sortie comme preuve. L'`apply` prend 10 à 20 minutes.

### H3. Déployer EnergyDesk sur le cluster cloud

```powershell
terraform -chdir=infra/terraform/cloud output -raw kubeconfig > kubeconfig-cloud.yaml
$env:KUBECONFIG = "$PWD/kubeconfig-cloud.yaml"
kubectl get nodes
terraform -chdir=infra/terraform/cloud output
```

1. Reporte `db_private_host` et `attachments_bucket` dans `deploy/helm/energydesk/values-cloud.yaml`, puis commit et push.
2. Installe Traefik et Argo CD sur le cluster cloud :
   ```powershell
   helm repo add traefik https://traefik.github.io/charts
   helm repo add argo https://argoproj.github.io/argo-helm
   helm install traefik traefik/traefik -n traefik --create-namespace --set service.type=LoadBalancer
   helm install argocd argo/argo-cd -n argocd --create-namespace -f infra/terraform/local/values/argocd.yaml
   ```
3. Crée le secret avec les clés IAM de l'application :
   ```powershell
   pwsh ./scripts/create-k8s-secrets.ps1 -Cloud -Namespaces energydesk-prod
   ```
4. Récupère l'IP publique de Traefik avec `kubectl get svc -n traefik`. Mets `ingress.host: <IP>.nip.io` dans `values-cloud.yaml`, puis commit et push.
5. Déploie avec Argo CD :
   ```powershell
   kubectl apply -f deploy/argocd/project.yaml -f deploy/argocd/applications/energydesk-cloud.yaml
   ```
   Synchronise ensuite `energydesk-cloud` dans l'interface.
6. Ouvre `http://<IP>.nip.io`, crée un ticket avec une pièce jointe, puis vérifie l'objet dans le bucket depuis la console Scaleway.

Remarque : `values-cloud.yaml` désactive le monitoring (`monitoring.enabled: false`), car kube-prometheus-stack n'est pas installé sur le cluster cloud, pour limiter le coût. La supervision est démontrée sur le cluster de Codespaces.

Preuves : `kubectl get nodes`, l'application ouverte sur l'IP publique, l'objet dans le bucket, la base dans la console, et la page de facturation avec le coût observé.

### H4. Reproductibilité et destruction

```powershell
kubectl delete -f deploy/argocd/applications/energydesk-cloud.yaml
terraform -chdir=infra/terraform/cloud destroy
```

Le `destroy` puis un nouvel `apply` prouvent que l'infrastructure se reconstruit depuis zéro. Fais-le si le temps le permet. Sinon, la création initiale depuis un projet vide suffit, et tu le dis honnêtement dans le rapport.

Avant le destroy, les buckets doivent être vides. Vide-les depuis la console si Terraform le signale.

---

## Étape I — FinOps

- **Optimisation 1 (taille des images)** : déjà mesurée à l'étape B4.
- **Optimisation 2 (requests CPU/RAM après mesure)** : pendant et après le test de charge, relève la consommation réelle :
  ```powershell
  kubectl top pods -n energydesk-dev
  ```
  Compare-la aux `requests` de `values.yaml`. Ajuste-les à la consommation observée plus une marge d'environ 30 %. Commit, laisse Argo CD redéployer, puis remesure. Calcule la réduction de CPU et de mémoire réservées, et note l'impact sur le nombre de nœuds nécessaires.
- **Optimisation 3 (facultative)** : destruction du cloud hors démonstration. Coût horaire × heures évitées.
- **Coût cible** : complète le tableau de `docs/finops.md` avec les tarifs de la page de prix Scaleway du jour, et le coût observé sur la facture.

---

## Étape J — Rapport

Suis `docs/rapport/plan-rapport.md`. Chaque section indique les preuves à insérer. Mets à jour `docs/matrice-conformite.md` au fur et à mesure.
