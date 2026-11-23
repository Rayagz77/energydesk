"""Tickets : creation, liste, detail, statut, attribution, commentaires."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_ticket, get_current_user, require_agent
from app.core.logging import security_logger
from app.db.session import get_db
from app.models import (
    ALLOWED_TRANSITIONS,
    Comment,
    Role,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
)
from app.schemas import (
    CommentCreate,
    CommentOut,
    TicketAssign,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketPage,
    TicketStatusUpdate,
)
from app.services.messaging import Publisher, get_publisher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    publisher: Publisher = Depends(get_publisher),
) -> Ticket:
    ticket = Ticket(**payload.model_dump(), created_by_id=user.id)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info(
        "ticket cree",
        extra={
            "event": "ticket_created",
            "ticket_id": str(ticket.id),
            "priority": ticket.priority.value,
            "user_id": str(user.id),
        },
    )
    # Publication APRES l'enregistrement : le worker trouvera toujours le ticket en base.
    publisher.publish_ticket_created(ticket.id)
    return ticket


@router.get("", response_model=TicketPage)
def list_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketPage:
    conditions = []
    if user.role != Role.AGENT:
        conditions.append(Ticket.created_by_id == user.id)
    if status_filter is not None:
        conditions.append(Ticket.status == status_filter)
    if priority is not None:
        conditions.append(Ticket.priority == priority)

    total = db.scalar(select(func.count()).select_from(Ticket).where(*conditions)) or 0
    items = db.scalars(
        select(Ticket).where(*conditions).order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    ).unique()
    return TicketPage(
        items=[TicketOut.model_validate(t) for t in items], total=total, limit=limit, offset=offset
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket: Ticket = Depends(get_accessible_ticket)) -> Ticket:
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_status(
    payload: TicketStatusUpdate,
    request: Request,
    ticket: Ticket = Depends(get_accessible_ticket),
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> Ticket:
    if payload.status not in ALLOWED_TRANSITIONS[ticket.status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Transition interdite : {ticket.status.value} -> {payload.status.value}.",
        )
    previous = ticket.status
    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    security_logger.info(
        "statut modifie",
        extra={
            "event": "ticket_status_changed",
            "ticket_id": str(ticket.id),
            "from_status": previous.value,
            "to_status": ticket.status.value,
            "user_id": str(agent.id),
        },
    )
    return ticket


@router.patch("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    payload: TicketAssign,
    ticket: Ticket = Depends(get_accessible_ticket),
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
) -> Ticket:
    target = db.get(User, payload.agent_id)
    if target is None or target.role != Role.AGENT or not target.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le destinataire doit etre un agent actif.")
    ticket.assigned_to_id = target.id
    db.commit()
    db.refresh(ticket)
    logger.info(
        "ticket attribue",
        extra={
            "event": "ticket_assigned",
            "ticket_id": str(ticket.id),
            "assigned_to": str(target.id),
            "user_id": str(agent.id),
        },
    )
    return ticket


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    payload: CommentCreate,
    ticket: Ticket = Depends(get_accessible_ticket),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Comment:
    comment = Comment(ticket_id=ticket.id, author_id=user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
