"""Configuration du worker, lue depuis les variables d'environnement."""

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    db_host: str = field(default_factory=lambda: _env("DB_HOST", "localhost"))
    db_port: int = field(default_factory=lambda: int(_env("DB_PORT", "5432")))
    db_name: str = field(default_factory=lambda: _env("DB_NAME", "energydesk"))
    db_user: str = field(default_factory=lambda: _env("DB_USER", "energydesk"))
    db_password: str = field(default_factory=lambda: _env("DB_PASSWORD"), repr=False)
    db_sslmode: str = field(default_factory=lambda: _env("DB_SSLMODE", "prefer"))

    s3_endpoint_url: str | None = field(default_factory=lambda: _env("S3_ENDPOINT_URL") or None)
    s3_region: str = field(default_factory=lambda: _env("S3_REGION", "fr-par"))
    s3_access_key: str = field(default_factory=lambda: _env("S3_ACCESS_KEY"), repr=False)
    s3_secret_key: str = field(default_factory=lambda: _env("S3_SECRET_KEY"), repr=False)
    s3_bucket: str = field(default_factory=lambda: _env("S3_BUCKET_ATTACHMENTS", "energydesk-attachments"))

    rabbitmq_host: str = field(default_factory=lambda: _env("RABBITMQ_HOST", "localhost"))
    rabbitmq_port: int = field(default_factory=lambda: int(_env("RABBITMQ_PORT", "5672")))
    rabbitmq_user: str = field(default_factory=lambda: _env("RABBITMQ_USER", "guest"))
    rabbitmq_password: str = field(default_factory=lambda: _env("RABBITMQ_PASSWORD"), repr=False)
    rabbitmq_vhost: str = field(default_factory=lambda: _env("RABBITMQ_VHOST", "/"))
    exchange: str = field(default_factory=lambda: _env("RABBITMQ_EXCHANGE", "energydesk.events"))
    queue: str = field(default_factory=lambda: _env("RABBITMQ_QUEUE_TICKET_CREATED", "ticket.created"))

    metrics_port: int = field(default_factory=lambda: int(_env("WORKER_METRICS_PORT", "9100")))
    sweep_interval_seconds: int = field(default_factory=lambda: int(_env("WORKER_SWEEP_INTERVAL", "60")))
    sweep_min_age_seconds: int = field(default_factory=lambda: int(_env("WORKER_SWEEP_MIN_AGE", "60")))
    notification_recipient: str = field(
        default_factory=lambda: _env("NOTIFICATION_RECIPIENT", "support@energydesk.local")
    )

    @property
    def db_conninfo(self) -> str:
        from psycopg.conninfo import make_conninfo

        return make_conninfo(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password,
            sslmode=self.db_sslmode,
            connect_timeout=5,
        )
