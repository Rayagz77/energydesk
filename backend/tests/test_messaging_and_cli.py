import uuid

from app.cli import main as cli_main
from app.services.messaging import RabbitPublisher
from tests.conftest import PASSWORD, login


def test_publisher_never_raises_when_broker_is_down():
    """Si RabbitMQ est indisponible, la publication echoue proprement (pas d'exception)."""
    publisher = RabbitPublisher("127.0.0.1", 1, "guest", "guest", "/", "energydesk.events")
    assert publisher.publish_ticket_created(uuid.uuid4()) is False


def test_cli_creates_agent(client, monkeypatch, capsys):
    monkeypatch.setenv("AGENT_PASSWORD", PASSWORD)
    code = cli_main(["create-agent", "--email", "Agent2@EnergyDesk.local", "--full-name", "Agent 2"])
    assert code == 0
    assert "agent2@energydesk.local" in capsys.readouterr().out
    headers = login(client, "agent2@energydesk.local")
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "agent"
