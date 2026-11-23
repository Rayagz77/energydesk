"""Logique metier du worker, independante de RabbitMQ (donc testable facilement).

Traitement d'un ticket :
1. On relit le ticket en base. S'il n'existe pas ou s'il est deja notifie, on s'arrete.
2. On ecrit la notification dans le stockage objet sous une cle FIXE par ticket
   (notifications/<ticket_id>.json). Rejouer le traitement ecrase le meme objet : pas de doublon.
3. On marque le ticket notifie avec un UPDATE conditionnel (WHERE notified_at IS NULL).
   Si deux workers traitent le meme ticket en meme temps, un seul "gagne" l'UPDATE.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

logger = logging.getLogger("energydesk.worker")


class InvalidMessage(ValueError):
    """Message illisible : il part dans la file des messages en erreur (dead-letter)."""


@dataclass(frozen=True)
class TicketInfo:
    id: uuid.UUID
    title: str
    priority: str
    status: str
    category: str
    equipment_id: str
    created_by_email: str
    created_at: datetime
    notified_at: datetime | None


class TicketRepository(Protocol):
    def get_ticket(self, ticket_id: uuid.UUID) -> TicketInfo | None: ...

    def mark_notified(self, ticket_id: uuid.UUID) -> bool: ...


class NotificationStore(Protocol):
    def put_json(self, key: str, document: dict) -> None: ...


def parse_message(body: bytes) -> uuid.UUID:
    try:
        payload = json.loads(body)
        if payload.get("event") != "ticket.created":
            raise InvalidMessage(f"evenement inattendu : {payload.get('event')!r}")
        return uuid.UUID(payload["ticket_id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, InvalidMessage):
            raise
        raise InvalidMessage(str(exc)) from exc


def build_notification(ticket: TicketInfo, recipient: str, now: datetime) -> dict:
    return {
        "type": "ticket_created",
        "ticket_id": str(ticket.id),
        "title": ticket.title,
        "priority": ticket.priority,
        "category": ticket.category,
        "equipment_id": ticket.equipment_id,
        "recipients": [recipient, ticket.created_by_email],
        "subject": f"[EnergyDesk] Nouveau ticket ({ticket.priority}) : {ticket.title}",
        "ticket_created_at": ticket.created_at.isoformat(),
        "notified_at": now.isoformat(),
    }


def process_ticket(
    ticket_id: uuid.UUID,
    repo: TicketRepository,
    store: NotificationStore,
    recipient: str,
    now: datetime | None = None,
) -> str:
    """Renvoie 'sent', 'duplicate' ou 'missing'."""
    ticket = repo.get_ticket(ticket_id)
    if ticket is None:
        logger.warning("ticket introuvable", extra={"event": "ticket_missing", "ticket_id": str(ticket_id)})
        return "missing"
    if ticket.notified_at is not None:
        logger.info(
            "notification deja envoyee, message ignore",
            extra={"event": "notification_duplicate", "ticket_id": str(ticket_id)},
        )
        return "duplicate"

    now = now or datetime.now(UTC)
    notification = build_notification(ticket, recipient, now)
    store.put_json(f"notifications/{ticket_id}.json", notification)

    if not repo.mark_notified(ticket_id):
        logger.info(
            "ticket notifie entre-temps par un autre worker",
            extra={"event": "notification_duplicate", "ticket_id": str(ticket_id)},
        )
        return "duplicate"

    logger.info(
        "notification envoyee",
        extra={
            "event": "notification_sent",
            "ticket_id": str(ticket_id),
            "priority": ticket.priority,
            "recipients": notification["recipients"],
        },
    )
    return "sent"
