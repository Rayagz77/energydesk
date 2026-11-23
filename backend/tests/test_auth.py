from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User
from tests.conftest import PASSWORD, register_and_login


def test_register_creates_user_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "Alice@Exemple.fr", "full_name": "Alice", "password": PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@exemple.fr"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body


def test_password_is_hashed_with_argon2(client):
    register_and_login(client, "alice@exemple.fr")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "alice@exemple.fr"))
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_register_duplicate_email_conflict(client):
    register_and_login(client, "alice@exemple.fr")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alice@exemple.fr", "full_name": "Alice", "password": PASSWORD},
    )
    assert response.status_code == 409


def test_register_rejects_weak_password_and_bad_email(client):
    weak = client.post(
        "/api/v1/auth/register",
        json={"email": "x@exemple.fr", "full_name": "X Y", "password": "court"},
    )
    bad_email = client.post(
        "/api/v1/auth/register",
        json={"email": "pas-un-email", "full_name": "X Y", "password": PASSWORD},
    )
    assert weak.status_code == 422
    assert bad_email.status_code == 422


def test_login_wrong_password_is_rejected(client):
    register_and_login(client, "alice@exemple.fr")
    response = client.post(
        "/api/v1/auth/login", data={"username": "alice@exemple.fr", "password": "mauvais-mdp-123"}
    )
    assert response.status_code == 401


def test_login_unknown_user_is_rejected(client):
    response = client.post(
        "/api/v1/auth/login", data={"username": "inconnu@exemple.fr", "password": PASSWORD}
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client, user_headers):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer faux"}).status_code == 401
    response = client.get("/api/v1/auth/me", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "alice@exemple.fr"
