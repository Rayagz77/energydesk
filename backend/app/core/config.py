"""Configuration lue exclusivement depuis les variables d'environnement.

Aucun secret n'a de valeur par defaut utilisable : l'application refuse de demarrer
si la cle JWT est absente ou trop courte (voir app.main).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    app_env: str = "local"
    log_level: str = "INFO"

    # PostgreSQL
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "energydesk"
    db_user: str = "energydesk"
    db_password: str = Field(default="", repr=False)
    db_sslmode: str = "prefer"  # "require" pour une base managee dans le cloud

    # Authentification
    jwt_secret_key: str = Field(default="", repr=False)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # Stockage objet compatible S3 (MinIO en local, stockage objet cloud ensuite)
    s3_endpoint_url: str | None = None
    s3_region: str = "fr-par"
    s3_access_key: str = Field(default="", repr=False)
    s3_secret_key: str = Field(default="", repr=False)
    s3_bucket_attachments: str = "energydesk-attachments"
    s3_create_bucket: bool = False  # True uniquement en local (MinIO)
    max_upload_mb: int = 5

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = Field(default="", repr=False)
    rabbitmq_vhost: str = "/"
    rabbitmq_exchange: str = "energydesk.events"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
