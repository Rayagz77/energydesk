from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext

from app.db.session import Base, engine


def test_liveness(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_checks_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_metrics_are_exposed(client):
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert 'path="/health/live"' in response.text
    assert "http_request_duration_seconds_bucket" in response.text


def test_metrics_use_full_route_template(client, user_headers):
    client.get("/api/v1/tickets/00000000-0000-0000-0000-000000000000", headers=user_headers)
    client.get("/route-inexistante-123")
    text = client.get("/metrics").text
    assert 'path="/api/v1/tickets/{ticket_id}",status="404"' in text
    assert 'path="/api/v1/auth/login"' in text
    assert 'path="unmatched"' in text
    assert "route-inexistante" not in text


def test_openapi_documentation_available(client):
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "EnergyDesk API"


def test_migrations_match_models():
    """Le schema cree par les migrations Alembic correspond exactement aux modeles."""
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
