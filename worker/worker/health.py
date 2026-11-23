"""Serveur HTTP du worker : /metrics (Prometheus) et /healthz (sonde liveness Kubernetes).

/healthz repond 503 si la boucle principale n'a pas tourne depuis 60 secondes
(processus bloque) : Kubernetes redemarre alors le conteneur.
"""

import threading
import time
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from prometheus_client import Counter, Gauge, Histogram, make_wsgi_app

MESSAGES = Counter("worker_messages_total", "Messages RabbitMQ traites par resultat", ["result"])
SWEEP = Counter("worker_sweep_total", "Tickets rattrapes par le balayage periodique", ["result"])
PROCESSING = Histogram("worker_processing_seconds", "Duree de traitement d'un ticket")
CONNECTED = Gauge("worker_rabbitmq_connected", "1 si le worker est connecte a RabbitMQ")
LAST_LOOP = Gauge("worker_last_loop_timestamp_seconds", "Dernier passage dans la boucle principale")

STALE_AFTER_SECONDS = 60
_heartbeat = {"value": time.time()}


def beat() -> None:
    now = time.time()
    _heartbeat["value"] = now
    LAST_LOOP.set(now)


def is_alive(now: float | None = None) -> bool:
    return ((now or time.time()) - _heartbeat["value"]) < STALE_AFTER_SECONDS


_metrics_app = make_wsgi_app()


def app(environ, start_response):
    if environ.get("PATH_INFO") == "/healthz":
        ok = is_alive()
        start_response("200 OK" if ok else "503 Service Unavailable", [("Content-Type", "text/plain")])
        return [b"ok\n" if ok else b"stale\n"]
    return _metrics_app(environ, start_response)


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, *args) -> None:  # pas de log a chaque sonde
        pass


def start_server(port: int) -> WSGIServer:
    server = make_server("0.0.0.0", port, app, handler_class=_QuietHandler)  # noqa: S104
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
