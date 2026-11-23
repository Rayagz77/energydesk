import uuid

from tests.conftest import TICKET_PAYLOAD, create_ticket


def test_create_ticket_publishes_event(client, user_headers, publisher):
    ticket = create_ticket(client, user_headers)
    assert ticket["status"] == "nouveau"
    assert ticket["priority"] == "haute"
    assert ticket["created_by"]["full_name"] == "Alice Martin"
    assert publisher.published == [uuid.UUID(ticket["id"])]


def test_create_ticket_validates_input(client, user_headers):
    bad_equipment = {**TICKET_PAYLOAD, "equipment_id": "PRM-12345678901234"}
    bad_priority = {**TICKET_PAYLOAD, "priority": "urgente"}
    short_title = {**TICKET_PAYLOAD, "title": "abc"}
    for payload in (bad_equipment, bad_priority, short_title):
        response = client.post("/api/v1/tickets", json=payload, headers=user_headers)
        assert response.status_code == 422


def test_create_ticket_requires_authentication(client):
    assert client.post("/api/v1/tickets", json=TICKET_PAYLOAD).status_code == 401


def test_user_sees_only_own_tickets(client, user_headers, other_headers):
    mine = create_ticket(client, user_headers)
    create_ticket(client, other_headers, title="Ticket de Bob a ne pas voir")
    response = client.get("/api/v1/tickets", headers=user_headers)
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert [t["id"] for t in page["items"]] == [mine["id"]]


def test_user_cannot_read_other_user_ticket(client, user_headers, other_headers):
    bob_ticket = create_ticket(client, other_headers)
    response = client.get(f"/api/v1/tickets/{bob_ticket['id']}", headers=user_headers)
    assert response.status_code == 404


def test_agent_sees_all_tickets(client, user_headers, other_headers, agent_headers):
    create_ticket(client, user_headers)
    create_ticket(client, other_headers)
    response = client.get("/api/v1/tickets", headers=agent_headers)
    assert response.json()["total"] == 2


def test_filter_by_status_and_priority(client, user_headers):
    create_ticket(client, user_headers, priority="critique")
    create_ticket(client, user_headers, priority="basse")
    response = client.get("/api/v1/tickets?priority=critique", headers=user_headers)
    assert response.json()["total"] == 1
    response = client.get("/api/v1/tickets?status=resolu", headers=user_headers)
    assert response.json()["total"] == 0


def test_user_cannot_change_status(client, user_headers):
    ticket = create_ticket(client, user_headers)
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status", json={"status": "en_cours"}, headers=user_headers
    )
    assert response.status_code == 403


def test_agent_status_workflow(client, user_headers, agent_headers):
    ticket = create_ticket(client, user_headers)
    url = f"/api/v1/tickets/{ticket['id']}/status"
    for target in ("en_cours", "resolu", "ferme"):
        response = client.patch(url, json={"status": target}, headers=agent_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == target


def test_invalid_transition_is_refused(client, user_headers, agent_headers):
    ticket = create_ticket(client, user_headers)
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/status", json={"status": "ferme"}, headers=agent_headers
    )
    assert response.status_code == 409


def test_agent_assigns_ticket_to_agent(client, user_headers, agent, agent_headers):
    ticket = create_ticket(client, user_headers)
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/assign",
        json={"agent_id": str(agent.id)},
        headers=agent_headers,
    )
    assert response.status_code == 200
    assert response.json()["assigned_to"]["id"] == str(agent.id)


def test_cannot_assign_to_regular_user(client, user_headers, agent_headers):
    ticket = create_ticket(client, user_headers)
    me = client.get("/api/v1/auth/me", headers=user_headers).json()
    response = client.patch(
        f"/api/v1/tickets/{ticket['id']}/assign", json={"agent_id": me["id"]}, headers=agent_headers
    )
    assert response.status_code == 400


def test_list_agents_reserved_to_agents(client, user_headers, agent, agent_headers):
    assert client.get("/api/v1/users/agents", headers=user_headers).status_code == 403
    response = client.get("/api/v1/users/agents", headers=agent_headers)
    assert response.status_code == 200
    assert [a["id"] for a in response.json()] == [str(agent.id)]


def test_comments(client, user_headers, other_headers, agent_headers):
    ticket = create_ticket(client, user_headers)
    url = f"/api/v1/tickets/{ticket['id']}/comments"
    assert client.post(url, json={"content": "Precision"}, headers=user_headers).status_code == 201
    assert client.post(url, json={"content": "Prise en charge"}, headers=agent_headers).status_code == 201
    assert client.post(url, json={"content": "Intrus"}, headers=other_headers).status_code == 404
    assert client.post(url, json={"content": ""}, headers=user_headers).status_code == 422

    detail = client.get(f"/api/v1/tickets/{ticket['id']}", headers=user_headers).json()
    assert [c["content"] for c in detail["comments"]] == ["Precision", "Prise en charge"]


def test_stats_by_role(client, user_headers, other_headers, agent_headers):
    t1 = create_ticket(client, user_headers, priority="critique")
    create_ticket(client, user_headers)
    create_ticket(client, other_headers, priority="critique")
    client.patch(f"/api/v1/tickets/{t1['id']}/status", json={"status": "en_cours"}, headers=agent_headers)

    user_stats = client.get("/api/v1/stats", headers=user_headers).json()
    assert user_stats == {"ouverts": 1, "en_cours": 1, "resolus": 0, "fermes": 0, "critiques": 1, "total": 2}
    agent_stats = client.get("/api/v1/stats", headers=agent_headers).json()
    assert agent_stats["total"] == 3
    assert agent_stats["critiques"] == 2
