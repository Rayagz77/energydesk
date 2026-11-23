import json
import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from worker.config import Settings
from worker.handler import InvalidMessage, TicketInfo, parse_message, process_ticket
from worker.health import app as health_app
from worker.health import beat, is_alive
from worker.main import handle_delivery

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def make_ticket(**overrides) -> TicketInfo:
    base = TicketInfo(
        id=uuid.uuid4(),
        title="Compteur muet",
        priority="haute",
        status="nouveau",
        category="transmission",
        equipment_id="CPT-FICTIF-000123",
        created_by_email="alice@exemple.fr",
        created_at=NOW,
        notified_at=None,
    )
    return replace(base, **overrides)


class FakeRepo:
    def __init__(self, ticket: TicketInfo | None, mark_result: bool = True) -> None:
        self.ticket = ticket
        self.mark_result = mark_result
        self.marked: list[uuid.UUID] = []

    def get_ticket(self, ticket_id):
        return self.ticket if self.ticket and self.ticket.id == ticket_id else None

    def mark_notified(self, ticket_id):
        self.marked.append(ticket_id)
        return self.mark_result


class FakeStore:
    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    def put_json(self, key, document):
        self.docs[key] = document


class FakeChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacked.append((delivery_tag, requeue))


def message(ticket_id) -> bytes:
    return json.dumps({"event": "ticket.created", "ticket_id": str(ticket_id)}).encode()


def test_parse_valid_message():
    tid = uuid.uuid4()
    assert parse_message(message(tid)) == tid


@pytest.mark.parametrize(
    "body",
    [b"pas du json", b"{}", b'{"event": "autre", "ticket_id": "x"}', b'{"event": "ticket.created"}'],
)
def test_parse_invalid_messages(body):
    with pytest.raises(InvalidMessage):
        parse_message(body)


def test_notification_sent_once():
    ticket = make_ticket()
    repo, store = FakeRepo(ticket), FakeStore()
    assert process_ticket(ticket.id, repo, store, "support@energydesk.local", NOW) == "sent"
    doc = store.docs[f"notifications/{ticket.id}.json"]
    assert doc["recipients"] == ["support@energydesk.local", "alice@exemple.fr"]
    assert "haute" in doc["subject"]
    assert repo.marked == [ticket.id]


def test_already_notified_ticket_is_ignored():
    ticket = make_ticket(notified_at=NOW)
    repo, store = FakeRepo(ticket), FakeStore()
    assert process_ticket(ticket.id, repo, store, "x", NOW) == "duplicate"
    assert store.docs == {} and repo.marked == []


def test_concurrent_worker_wins_race():
    ticket = make_ticket()
    repo = FakeRepo(ticket, mark_result=False)
    assert process_ticket(ticket.id, repo, FakeStore(), "x", NOW) == "duplicate"


def test_missing_ticket():
    assert process_ticket(uuid.uuid4(), FakeRepo(None), FakeStore(), "x", NOW) == "missing"


def test_delivery_acked_on_success():
    ticket = make_ticket()
    channel = FakeChannel()
    result = handle_delivery(channel, 7, message(ticket.id), FakeRepo(ticket), FakeStore(), Settings())
    assert result == "sent" and channel.acked == [7]


def test_invalid_delivery_goes_to_dead_letter():
    channel = FakeChannel()
    result = handle_delivery(channel, 8, b"???", FakeRepo(None), FakeStore(), Settings())
    assert result == "invalid" and channel.nacked == [(8, False)]


def test_processing_error_goes_to_dead_letter():
    class BrokenRepo(FakeRepo):
        def get_ticket(self, ticket_id):
            raise ConnectionError("base indisponible")

    channel = FakeChannel()
    result = handle_delivery(channel, 9, message(uuid.uuid4()), BrokenRepo(None), FakeStore(), Settings())
    assert result == "error" and channel.nacked == [(9, False)]


def test_health_endpoint():
    beat()
    assert is_alive()
    statuses = []
    body = health_app({"PATH_INFO": "/healthz"}, lambda status, headers: statuses.append(status))
    assert statuses == ["200 OK"] and body == [b"ok\n"]
    assert not is_alive(now=10**12)
