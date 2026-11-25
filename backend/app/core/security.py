"""Hachage des mots de passe (Argon2id) et jetons JWT."""

import threading
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()  # Argon2id avec des parametres recommandes

# Chaque calcul Argon2id reserve 64 Mio de memoire (profil RFC 9106 "low memory").
# Sans limite, des connexions simultanees depassent la limite memoire du pod (OOMKilled),
# constate lors du test de charge du 25/11/2026. On borne donc le nombre de calculs
# simultanes par pod ; les requetes suivantes attendent leur tour au lieu de faire tomber le pod.
_HASH_SLOTS = threading.BoundedSemaphore(2)

# Hash factice : il sert a garder un temps de reponse identique quand l'email n'existe pas,
# pour ne pas reveler quels comptes existent (attaque par mesure du temps).
_DUMMY_HASH = _password_hash.hash("energydesk-dummy-password-for-timing")

JWT_ISSUER = "energydesk"


def hash_password(password: str) -> str:
    with _HASH_SLOTS:
        return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    with _HASH_SLOTS:
        if password_hash is None:
            _password_hash.verify(password, _DUMMY_HASH)
            return False
        return _password_hash.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=JWT_ISSUER,
        options={"require": ["exp", "sub", "iss"]},
    )