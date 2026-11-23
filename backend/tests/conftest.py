"""Configuration des tests.

Les tests utilisent une VRAIE base PostgreSQL (TEST_DB_* ou valeurs par defaut ci-dessous).
RabbitMQ et le stockage objet sont remplaces par des doubles en memoire :
on teste la logique de l'API, pas ces services externes.

En local :   docker run -d --name ed-test-db -e POSTGRES_USER=energydesk \
               -e POSTGRES_PASSWORD=test -e POSTGRES_DB=energydesk_test -p 5433:5432 postgres:16-alpine
puis :       $env:DB_PORT="5433"; pytest
"""

import os
import uuid
from collections.abc import Iterator

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "energydesk_test")
os.environ.setdefault("DB_USER", "energydesk")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("JWT_SECRET_KEY", "cle-de-test-uniquement-pour-pytest-0123456789")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402
from app.services.messaging import get_publisher  # noqa: E402
from app.services.storage import get_storage  # noqa: E402

PASSWORD = "MotDePasseTest-2026"
BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


class FakePublisher:
    def __init__(self) -> None:
        self.published: list[uuid.UUID] = []

    def publish_ticket_created(self, ticket_id: uuid.UUID) -> bool:
        self.published.append(ticket_id)
        return True


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    def iter_object(self, key: str):
        yield self.objects[key][0]

    def ping(self) -> bool:
        return True


def alembic_config() -> Config:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    """Repart d'un schema vide puis applique les migrations Alembic (elles sont donc testees)."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE comments, attachments, tickets, users RESTART IDENTITY CASCADE"))


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


@pytest.fixture
def storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def client(publisher: FakePublisher, storage: FakeStorage) -> Iterator[TestClient]:
    app.dependency_overrides[get_publisher] = lambda: publisher
    app.dependency_overrides[get_storage] = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str, name: str = "Utilisateur Test") -> dict:
    response = client.post(
        "/api/v1/auth/register", json={"email": email, "full_name": name, "password": PASSWORD}
    )
    assert response.status_code == 201, response.text
    return login(client, email)


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_agent(email: str = "agent@energydesk.local", name: str = "Agent Support") -> User:
    with SessionLocal() as db:
        agent = User(email=email, full_name=name, password_hash=hash_password(PASSWORD), role=Role.AGENT)
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent


@pytest.fixture
def user_headers(client: TestClient) -> dict:
    return register_and_login(client, "alice@exemple.fr", "Alice Martin")


@pytest.fixture
def other_headers(client: TestClient) -> dict:
    return register_and_login(client, "bob@exemple.fr", "Bob Durand")


@pytest.fixture
def agent(client: TestClient) -> User:
    return create_agent()


@pytest.fixture
def agent_headers(client: TestClient, agent: User) -> dict:
    return login(client, agent.email)


TICKET_PAYLOAD = {
    "title": "Compteur ne transmet plus",
    "description": "Le compteur fictif ne remonte plus d'index depuis 3 jours.",
    "category": "transmission",
    "equipment_id": "CPT-FICTIF-000123",
    "priority": "haute",
}


def create_ticket(client: TestClient, headers: dict, **overrides) -> dict:
    response = client.post("/api/v1/tickets", json={**TICKET_PAYLOAD, **overrides}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
