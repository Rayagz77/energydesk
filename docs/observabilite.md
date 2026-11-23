# Observabilité : métriques, logs, alertes, SLI/SLO

## 1. Ce qui est instrumenté

| Source | Données | Où les voir |
|---|---|---|
| API `/metrics` | `http_requests_total{method,path,status}`, `http_request_duration_seconds` (histogramme) | Prometheus, Grafana |
| Worker `:9100/metrics` | `worker_messages_total{result}`, `worker_sweep_total{result}`, `worker_processing_seconds`, `worker_rabbitmq_connected` | Prometheus, Grafana |
| Kubernetes | CPU et mémoire par pod (cAdvisor), réplicas, redémarrages, HPA (kube-state-metrics) | Grafana |
| Logs API et worker | JSON, une ligne par événement : `http_request`, `ticket_created`, `notification_sent`, `login_failed`… | Loki (Grafana → Explore) |

Le label `path` vaut le modèle de route (`/api/v1/tickets/{ticket_id}`) et non l'URL réelle. Le nombre de séries reste ainsi borné. Les URL inconnues sont regroupées sous `unmatched`.

`/metrics` et `/health` ne sont pas exposés par l'Ingress. Seul Prometheus, dans le cluster, les lit.

## 2. Deux tableaux de bord, deux publics

- **Dashboard métier** (dans l'application, page « Tableau de bord ») : tickets ouverts, en cours, résolus, critiques. Il s'adresse aux utilisateurs et aux agents.
- **Dashboard technique** (Grafana, « EnergyDesk - état technique ») : SLI, trafic, latence, erreurs, CPU, mémoire, pods, worker. Il s'adresse à l'équipe d'exploitation.

## 3. SLI et SLO

| | SLI 1 : disponibilité | SLI 2 : latence |
|---|---|---|
| Définition | Part des requêtes `/api/*` qui ne renvoient pas d'erreur 5xx | Part des requêtes `/api/*` servies en moins de 300 ms |
| Règle Prometheus | `energydesk:api_availability:ratio_rate5m` | `energydesk:api_latency_under_300ms:ratio_rate5m` |
| SLO | **99 %** sur 30 jours | **95 %** sur 30 jours |
| Budget d'erreur | 1 % des requêtes | 5 % des requêtes |

Mesure sur une période plus longue que 5 minutes (par exemple 1 heure) :

```
1 - sum(increase(http_requests_total{namespace="energydesk-dev",path=~"/api/.*",status=~"5.."}[1h]))
  / sum(increase(http_requests_total{namespace="energydesk-dev",path=~"/api/.*"}[1h]))
```

Limite à écrire dans le rapport : la démonstration dure quelques heures, pas 30 jours. On mesure donc le SLI sur la fenêtre observée et on le compare à l'objectif. On ne peut pas affirmer que le SLO mensuel est tenu.

## 4. Alertes

| Alerte | Condition | Gravité | Test |
|---|---|---|---|
| `EnergyDeskApiDown` | Aucune instance de l'API joignable pendant 1 min | critique | `kubectl scale deploy/energydesk-api --replicas=0 -n energydesk-prod` |
| `EnergyDeskHighErrorRate` | Plus de 5 % de 5xx pendant 5 min | avertissement | Arrêter PostgreSQL pendant le test de charge |
| `EnergyDeskSlowApi` | Moins de 95 % des requêtes en moins de 300 ms pendant 10 min | avertissement | Test de charge intense |
| `EnergyDeskWorkerDisconnected` | Worker déconnecté de RabbitMQ pendant 2 min | avertissement | `kubectl scale statefulset/energydesk-rabbitmq --replicas=0` |

## 5. Requêtes Loki utiles

```
{namespace="energydesk-dev", component="api"} | json | event="login_failed"
{namespace="energydesk-dev", component="api"} | json | event="access_denied"
{namespace="energydesk-dev", component="api"} | json | event="http_request" | status >= 500
{namespace="energydesk-dev", component="worker"} | json | event=~"notification_sent|sweep_recovered"
```
