"""Endpoints de sante utilises par Docker et Kubernetes.

- /health/live  : le processus repond (liveness). Ne depend d'aucun service externe.
- /health/ready : l'API peut servir des requetes, la base repond (readiness).
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["sante"])


@router.get("/live")
def live() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return JSONResponse(content={"status": "ok", "database": "up"})
