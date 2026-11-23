"""Dependances communes : utilisateur courant, controle des roles, acces aux tickets."""

import uuid

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.logging import security_logger
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Role, Ticket, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentification requise.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        security_logger.warning(
            "jeton refuse",
            extra={"event": "token_rejected", "path": request.url.path},
        )
        raise _UNAUTHORIZED from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    request.state.user_id = str(user.id)
    return user


def require_agent(request: Request, user: User = Depends(get_current_user)) -> User:
    if user.role != Role.AGENT:
        security_logger.warning(
            "action reservee aux agents refusee",
            extra={"event": "access_denied", "user_id": str(user.id), "path": request.url.path},
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Action reservee aux agents support.")
    return user


def get_accessible_ticket(
    ticket_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Ticket:
    """Renvoie le ticket si l'utilisateur y a droit, sinon 404.

    On repond 404 (et non 403) a un utilisateur qui demande le ticket d'un autre :
    on ne revele meme pas que ce ticket existe.
    """
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket introuvable.")
    if user.role != Role.AGENT and ticket.created_by_id != user.id:
        security_logger.warning(
            "acces a un ticket d'un autre utilisateur refuse",
            extra={
                "event": "access_denied",
                "user_id": str(user.id),
                "ticket_id": str(ticket_id),
                "path": request.url.path,
            },
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket introuvable.")
    return ticket
