"""Tableau de bord metier (statistiques des tickets)."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Role, Ticket, TicketPriority, TicketStatus, User
from app.schemas import Stats

router = APIRouter(prefix="/stats", tags=["tableau de bord"])


def _count_if(condition):
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


@router.get("", response_model=Stats)
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Stats:
    stmt = select(
        _count_if(Ticket.status == TicketStatus.NOUVEAU),
        _count_if(Ticket.status == TicketStatus.EN_COURS),
        _count_if(Ticket.status == TicketStatus.RESOLU),
        _count_if(Ticket.status == TicketStatus.FERME),
        _count_if((Ticket.priority == TicketPriority.CRITIQUE) & (Ticket.status != TicketStatus.FERME)),
        func.count(Ticket.id),
    )
    if user.role != Role.AGENT:
        stmt = stmt.where(Ticket.created_by_id == user.id)
    ouverts, en_cours, resolus, fermes, critiques, total = db.execute(stmt).one()
    return Stats(
        ouverts=ouverts,
        en_cours=en_cours,
        resolus=resolus,
        fermes=fermes,
        critiques=critiques,
        total=total,
    )
