"""Boucle principale du worker : consomme RabbitMQ et rattrape les tickets oublies.

Gestion des erreurs :
- message illisible            -> rejete vers la file "ticket.created.dlq" (dead-letter)
- erreur base ou stockage       -> rejete vers la DLQ ; le balayage periodique retraitera le ticket
- RabbitMQ indisponible         -> reconnexion avec attente croissante (1 s, 2 s, 4 s... 30 s max)
- arret (SIGTERM de Kubernetes) -> fin propre de la boucle
Le balayage retraite les tickets sans notified_at crees depuis plus de WORKER_SWEEP_MIN_AGE secondes :
aucun ticket n'est perdu meme si l'API n'a pas pu publier son message.
"""

import logging
import signal
import threading
import time

import pika

from worker.adapters import PostgresRepository, S3NotificationStore
from worker.config import Settings
from worker.handler import InvalidMessage, parse_message, process_ticket
from worker.health import CONNECTED, MESSAGES, PROCESSING, SWEEP, beat, start_server
from worker.logging_setup import configure_logging

logger = logging.getLogger("energydesk.worker")
DEAD_LETTER_EXCHANGE = "energydesk.dlx"
ROUTING_KEY = "ticket.created"


def declare_topology(channel, settings: Settings) -> None:
    dlq = f"{settings.queue}.dlq"
    channel.exchange_declare(exchange=settings.exchange, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="fanout", durable=True)
    channel.queue_declare(queue=dlq, durable=True)
    channel.queue_bind(queue=dlq, exchange=DEAD_LETTER_EXCHANGE)
    channel.queue_declare(
        queue=settings.queue, durable=True, arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE}
    )
    channel.queue_bind(queue=settings.queue, exchange=settings.exchange, routing_key=ROUTING_KEY)


def handle_delivery(channel, delivery_tag, body: bytes, repo, store, settings: Settings) -> str:
    try:
        ticket_id = parse_message(body)
    except InvalidMessage as exc:
        logger.error("message invalide envoye en DLQ", extra={"event": "message_invalid", "reason": str(exc)})
        channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
        MESSAGES.labels("invalid").inc()
        return "invalid"
    try:
        with PROCESSING.time():
            result = process_ticket(ticket_id, repo, store, settings.notification_recipient)
    except Exception:
        logger.exception(
            "echec du traitement, message envoye en DLQ",
            extra={"event": "message_failed", "ticket_id": str(ticket_id)},
        )
        channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
        MESSAGES.labels("error").inc()
        return "error"
    channel.basic_ack(delivery_tag=delivery_tag)
    MESSAGES.labels(result).inc()
    return result


def sweep(repo: PostgresRepository, store, settings: Settings) -> None:
    try:
        pending = repo.pending_ticket_ids(settings.sweep_min_age_seconds)
    except Exception:
        logger.exception("balayage impossible", extra={"event": "sweep_failed"})
        return
    for ticket_id in pending:
        try:
            result = process_ticket(ticket_id, repo, store, settings.notification_recipient)
        except Exception:
            logger.exception(
                "rattrapage en echec", extra={"event": "sweep_failed", "ticket_id": str(ticket_id)}
            )
            SWEEP.labels("error").inc()
            continue
        SWEEP.labels(result).inc()
        if result == "sent":
            logger.info("ticket rattrape", extra={"event": "sweep_recovered", "ticket_id": str(ticket_id)})


def run_consumer(settings: Settings, repo, store, stop: threading.Event) -> None:
    params = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_vhost,
        credentials=pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password),
        heartbeat=30,
        blocked_connection_timeout=30,
    )
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    declare_topology(channel, settings)
    channel.basic_qos(prefetch_count=10)
    CONNECTED.set(1)
    logger.info("connecte a RabbitMQ", extra={"event": "rabbitmq_connected", "queue": settings.queue})
    last_sweep = 0.0
    try:
        for method, _props, body in channel.consume(settings.queue, inactivity_timeout=5):
            beat()
            if stop.is_set():
                break
            if method is not None:
                handle_delivery(channel, method.delivery_tag, body, repo, store, settings)
            if time.monotonic() - last_sweep >= settings.sweep_interval_seconds:
                sweep(repo, store, settings)
                last_sweep = time.monotonic()
    finally:
        CONNECTED.set(0)
        try:
            channel.cancel()
            connection.close()
        except Exception:  # noqa: BLE001, S110 - fermeture au mieux
            pass


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    start_server(settings.metrics_port)
    repo = PostgresRepository(settings.db_conninfo)
    store = S3NotificationStore(
        settings.s3_bucket,
        settings.s3_endpoint_url,
        settings.s3_region,
        settings.s3_access_key,
        settings.s3_secret_key,
    )
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())

    logger.info("demarrage du worker", extra={"event": "startup"})
    backoff = 1
    while not stop.is_set():
        beat()
        try:
            run_consumer(settings, repo, store, stop)
            backoff = 1
        except Exception as exc:  # noqa: BLE001 - on retente toujours
            logger.warning(
                "connexion RabbitMQ perdue, nouvelle tentative",
                extra={"event": "rabbitmq_retry", "retry_in_s": backoff, "error": str(exc)},
            )
            stop.wait(backoff)
            backoff = min(backoff * 2, 30)
    repo.close()
    logger.info("arret du worker", extra={"event": "shutdown"})


if __name__ == "__main__":
    main()
