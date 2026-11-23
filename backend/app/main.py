"""Point d'entree de l'API EnergyDesk."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.routes import attachments, auth, health, stats, tickets, users
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.observability import ObservabilityMiddleware, metrics_endpoint
from app.services.storage import S3Storage, get_storage

logger = logging.getLogger(__name__)


def _check_settings() -> None:
    settings = get_settings()
    if len(settings.jwt_secret_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY absente ou trop courte (32 caracteres minimum).")
    if not settings.db_password and settings.app_env not in {"test"}:
        raise RuntimeError("DB_PASSWORD absente.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    _check_settings()
    if settings.s3_create_bucket:
        storage = get_storage()
        if isinstance(storage, S3Storage):
            try:
                storage.ensure_bucket()
            except Exception:  # noqa: BLE001 - MinIO peut demarrer apres l'API
                logger.warning("bucket non verifie au demarrage", extra={"event": "bucket_check_failed"})
    logger.info(
        "demarrage de l'API", extra={"event": "startup", "version": __version__, "env": settings.app_env}
    )
    yield


app = FastAPI(
    title="EnergyDesk API",
    description=("Gestion des incidents techniques de comptage electrique. Donnees exclusivement fictives."),
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(ObservabilityMiddleware)

API_PREFIX = "/api/v1"
for module in (auth, users, tickets, attachments, stats):
    app.include_router(module.router, prefix=API_PREFIX)
app.include_router(health.router)
app.add_route("/metrics", metrics_endpoint, include_in_schema=False)
