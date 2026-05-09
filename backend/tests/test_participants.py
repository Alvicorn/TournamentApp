"""Integration tests for participant endpoints."""

from fastapi.testclient import TestClient


def _tournament(client: TestClient) -> dict:
    r = client.post(
        "/api/v1/tournaments",
        json={
            "name": "T",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 3,
            "round_length_seconds": 120,
            "slideshow_slide_seconds": 10,
            "custom_participant_fields": [
                {"key": "belt", "label": "Belt", "type": "text", "required": True}
            ],
        },
    )
    assert r.status_code == 201
    return r.json()


def _participant(client: TestClient, tournament_id: str, **kwargs) -> dict:
    payload = {"name": "Alice", "custom_fields": {"belt": "black"}, **kwargs}
    r = client.post(f"/api/v1/tournaments/{tournament_id}/participants", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_participant(client: TestClient) -> None:
    t = _tournament(client)
    p = _participant(client, t["id"])
    assert p["name"] == "Alice"
    assert p["custom_fields"]["belt"] == "black"
    assert p["is_withdrawn"] is False
    assert p["division_id"] is None


def test_list_participants(client: TestClient) -> None:
    t = _tournament(client)
    _participant(client, t["id"])
    _participant(client, t["id"], name="Bob")
    r = client.get(f"/api/v1/tournaments/{t['id']}/participants")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_update_participant(client: TestClient) -> None:
    t = _tournament(client)
    p = _participant(client, t["id"])
    r = client.patch(f"/api/v1/participants/{p['id']}", json={"name": "Alicia"})
    assert r.status_code == 200
    assert r.json()["name"] == "Alicia"


def test_delete_participant_no_matches_removes(client: TestClient) -> None:
    t = _tournament(client)
    p = _participant(client, t["id"])
    r = client.delete(f"/api/v1/participants/{p['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/v1/tournaments/{t['id']}/participants")
    assert r.json() == []


def test_delete_participant_with_matches_marks_withdrawn(client: TestClient) -> None:
    """When a participant has matches, DELETE sets is_withdrawn=True instead of deleting."""

    t = _tournament(client)
    # Create a division and two participants, generate round-robin to create matches
    p1 = _participant(client, t["id"])
    p2 = _participant(client, t["id"], name="Bob")
    div_r = client.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "Open"})
    div_id = div_r.json()["id"]
    client.post(f"/api/v1/divisions/{div_id}/assign-participant", json={"participant_id": p1["id"]})
    client.post(f"/api/v1/divisions/{div_id}/assign-participant", json={"participant_id": p2["id"]})
    client.post(f"/api/v1/divisions/{div_id}/generate-round-robin")

    r = client.delete(f"/api/v1/participants/{p1['id']}")
    assert r.status_code == 204

    r = client.get(f"/api/v1/tournaments/{t['id']}/participants")
    participants = r.json()
    alice = next(p for p in participants if p["id"] == p1["id"])
    assert alice["is_withdrawn"] is True
