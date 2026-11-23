"""Publication des evenements metier dans RabbitMQ.

L'API publie dans un exchange "topic" durable. C'est le worker qui declare la file,
sa liaison et la file des messages en erreur (dead-letter). L'API ne depend donc pas
de la configuration de la file.

La publication est "best effort" : si RabbitMQ est indisponible, le ticket reste enregistre
et le worker le rattrape lors de son balayage periodique (tickets dont notified_at est vide).
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

import pika

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ROUTING_KEY_TICKET_CREATED = "ticket.created"


class Publisher(Protocol):
    def publish_ticket_created(self, ticket_id: uuid.UUID) -> bool: ...


class RabbitPublisher:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        vhost: str,
        exchange: str,
    ) -> None:
        self.exchange = exchange
        self.parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=pika.PlainCredentials(user, password),
            connection_attempts=1,
            socket_timeout=3,
            blocked_connection_timeout=3,
            heartbeat=0,
        )

    def publish_ticket_created(self, ticket_id: uuid.UUID) -> bool:
        message_id = str(uuid.uuid4())
        body = json.dumps(
            {
                "event": ROUTING_KEY_TICKET_CREATED,
                "ticket_id": str(ticket_id),
                "message_id": message_id,
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )
        connection = None
        try:
            # Une connexion courte par publication : simple et suffisant pour ce volume.
            connection = pika.BlockingConnection(self.parameters)
            channel = connection.channel()
            channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
            channel.confirm_delivery()  # le broker confirme la reception du message
            channel.basic_publish(
                exchange=self.exchange,
                routing_key=ROUTING_KEY_TICKET_CREATED,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=message_id,
                ),
            )
            logger.info(
                "evenement publie",
                extra={"event": "message_published", "ticket_id": str(ticket_id)},
            )
            return True
        except Exception:  # noqa: BLE001 - on ne bloque jamais la creation du ticket
            logger.exception(
                "publication impossible, le worker rattrapera le ticket",
                extra={"event": "message_publish_failed", "ticket_id": str(ticket_id)},
            )
            return False
        finally:
            if connection is not None and connection.is_open:
                connection.close()


@lru_cache
def get_publisher() -> Publisher:
    s = get_settings()
    return RabbitPublisher(
        host=s.rabbitmq_host,
        port=s.rabbitmq_port,
        user=s.rabbitmq_user,
        password=s.rabbitmq_password,
        vhost=s.rabbitmq_vhost,
        exchange=s.rabbitmq_exchange,
    )
