"""Liste des agents (pour l'attribution des tickets)."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_agent
from app.db.session import get_db
from app.models import Role, User
from app.schemas import UserBrief

router = APIRouter(prefix="/users", tags=["utilisateurs"])


@router.get("/agents", response_model=list[UserBrief])
def list_agents(_: User = Depends(require_agent), db: Session = Depends(get_db)) -> list[User]:
    stmt = select(User).where(User.role == Role.AGENT, User.is_active.is_(True)).order_by(User.full_name)
    return list(db.scalars(stmt))
