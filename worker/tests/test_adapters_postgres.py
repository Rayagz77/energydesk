"""Test d'integration du depot PostgreSQL du worker (ignore si aucune base n'est joignable).

Il cree un schema temporaire avec les colonnes utilisees par le worker, puis verifie
que l'UPDATE conditionnel ne marque un ticket qu'une seule fois.
"""

import os
import uuid

import psycopg
import pytest

from worker.adapters import PostgresRepository

CONNINFO = psycopg.conninfo.make_conninfo(
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432"),
    dbname=os.environ.get("TEST_DB_NAME", "energydesk_test"),
    user=os.environ.get("DB_USER", "energydesk"),
    password=os.environ.get("DB_PASSWORD", "test"),
    connect_timeout=3,
    options="-c search_path=worker_it",
)


@pytest.fixture
def repo():
    try:
        conn = psycopg.connect(CONNINFO, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL de test non disponible")
    conn.execute("DROP SCHEMA IF EXISTS worker_it CASCADE")
    conn.execute("CREATE SCHEMA worker_it")
    conn.execute("CREATE TABLE users (id uuid PRIMARY KEY, email text NOT NULL)")
    conn.execute(
        """CREATE TABLE tickets (
            id uuid PRIMARY KEY, title text, priority text, status text, category text,
            equipment_id text, created_by_id uuid REFERENCES users(id),
            created_at timestamptz NOT NULL, notified_at timestamptz)"""
    )
    repository = PostgresRepository(CONNINFO)
    yield conn, repository
    repository.close()
    conn.execute("DROP SCHEMA worker_it CASCADE")
    conn.close()


def insert_ticket(conn, age_seconds: int) -> uuid.UUID:
    user_id, ticket_id = uuid.uuid4(), uuid.uuid4()
    conn.execute("INSERT INTO users VALUES (%s, %s)", (user_id, "alice@exemple.fr"))
    conn.execute(
        "INSERT INTO tickets VALUES (%s, 'Titre', 'haute', 'nouveau', 'index', 'CPT-FICTIF-000001', %s,"
        " now() - make_interval(secs => %s), NULL)",
        (ticket_id, user_id, age_seconds),
    )
    return ticket_id


def test_mark_notified_only_once(repo):
    conn, repository = repo
    ticket_id = insert_ticket(conn, age_seconds=0)
    info = repository.get_ticket(ticket_id)
    assert info.created_by_email == "alice@exemple.fr" and info.notified_at is None
    assert repository.mark_notified(ticket_id) is True
    assert repository.mark_notified(ticket_id) is False
    assert repository.get_ticket(ticket_id).notified_at is not None


def test_pending_tickets_respect_minimum_age(repo):
    conn, repository = repo
    old = insert_ticket(conn, age_seconds=300)
    insert_ticket(conn, age_seconds=0)
    assert repository.pending_ticket_ids(min_age_seconds=60) == [old]
