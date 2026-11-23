"""Inscription, connexion et profil."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import security_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Role, User
from app.schemas import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["authentification"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)) -> User:
    """Cree un compte. L'inscription publique cree toujours un compte de role 'user'."""
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=Role.USER,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe deja avec cet email.") from None
    security_logger.info(
        "compte cree",
        extra={"event": "user_registered", "user_id": str(user.id), "ip": _client_ip(request)},
    )
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Connexion par email (champ 'username') et mot de passe. Renvoie un jeton JWT."""
    email = form.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    password_ok = verify_password(form.password, user.password_hash if user else None)
    if user is None or not password_ok or not user.is_active:
        security_logger.warning(
            "echec de connexion",
            extra={"event": "login_failed", "email": email, "ip": _client_ip(request)},
        )
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.id, user.role.value)
    security_logger.info(
        "connexion reussie",
        extra={"event": "login_success", "user_id": str(user.id), "ip": _client_ip(request)},
    )
    return Token(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
