"""Metriques Prometheus et journal d'acces HTTP.

Metriques exposees sur /metrics (non publie par l'Ingress, lu uniquement par Prometheus) :
- http_requests_total{method, path, status}          -> volume et taux d'erreur
- http_request_duration_seconds{method, path}        -> latence (histogramme, p95)
Le label "path" est le modele de route (/api/v1/tickets/{ticket_id}) et non l'URL reelle,
pour eviter une explosion du nombre de series.
"""

import logging
import time
import uuid

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

access_logger = logging.getLogger("energydesk.access")

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Nombre de requetes HTTP traitees",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Duree de traitement des requetes HTTP",
    ["method", "path"],
    # Le seuil 0.3 s sert au SLO de latence (95 % des requetes en moins de 300 ms).
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0),
)

_SKIP_PATHS = {"/metrics"}


def _route_template(request: Request) -> str:
    """Chemin complet avec ses parametres remplaces par leur nom : /api/v1/tickets/{ticket_id}.

    On part de l'URL reelle (qui contient le prefixe /api/v1) et des parametres reconnus par la route.
    Une URL qui ne correspond a aucune route est regroupee sous "unmatched".
    """
    if request.scope.get("route") is None:
        return "unmatched"
    path = request.url.path
    for name, value in request.path_params.items():
        path = path.replace(str(value), "{" + name + "}")
    return path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - start
            path = _route_template(request)
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            HTTP_LATENCY.labels(request.method, path).observe(duration)
            if not request.url.path.startswith("/health"):
                access_logger.info(
                    "requete http",
                    extra={
                        "event": "http_request",
                        "method": request.method,
                        "path": path,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 1),
                        "request_id": request_id,
                        "user_id": getattr(request.state, "user_id", None),
                    },
                )


def metrics_endpoint(_: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
