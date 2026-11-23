"""Acces reels a PostgreSQL et au stockage objet."""

import json
import uuid
from datetime import timedelta

import boto3
import psycopg
from botocore.config import Config

from worker.handler import TicketInfo

_SELECT_TICKET = """
SELECT t.id, t.title, t.priority, t.status, t.category, t.equipment_id,
       u.email, t.created_at, t.notified_at
FROM tickets t JOIN users u ON u.id = t.created_by_id
WHERE t.id = %s
"""

_MARK_NOTIFIED = "UPDATE tickets SET notified_at = now() WHERE id = %s AND notified_at IS NULL RETURNING id"

_PENDING = """
SELECT id FROM tickets
WHERE notified_at IS NULL AND created_at < now() - %s
ORDER BY created_at
LIMIT %s
"""


class PostgresRepository:
    def __init__(self, conninfo: str) -> None:
        self.conninfo = conninfo
        self._conn: psycopg.Connection | None = None

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self.conninfo, autocommit=True)
        return self._conn

    def _execute(self, query: str, params: tuple) -> psycopg.Cursor:
        try:
            return self._connection().execute(query, params)
        except psycopg.OperationalError:
            # Connexion perdue (redemarrage de la base) : on la jette, la suivante sera neuve.
            self.close()
            self._conn = None
            raise

    def get_ticket(self, ticket_id: uuid.UUID) -> TicketInfo | None:
        row = self._execute(_SELECT_TICKET, (ticket_id,)).fetchone()
        return TicketInfo(*row) if row else None

    def mark_notified(self, ticket_id: uuid.UUID) -> bool:
        return self._execute(_MARK_NOTIFIED, (ticket_id,)).fetchone() is not None

    def pending_ticket_ids(self, min_age_seconds: int, limit: int = 50) -> list[uuid.UUID]:
        rows = self._execute(_PENDING, (timedelta(seconds=min_age_seconds), limit)).fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()


class S3NotificationStore:
    def __init__(
        self, bucket: str, endpoint_url: str | None, region: str, access_key: str, secret_key: str
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def put_json(self, key: str, document: dict) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )
