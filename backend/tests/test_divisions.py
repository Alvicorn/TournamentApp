"""Integration tests for division endpoints."""

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
        },
    )
    assert r.status_code == 201
    return r.json()


def _participant(client: TestClient, tournament_id: str, name: str = "Alice") -> dict:
    r = client.post(
        f"/api/v1/tournaments/{tournament_id}/participants",
        json={"name": name, "custom_fields": {}},
    )
    assert r.status_code == 201
    return r.json()


def _division(client: TestClient, tournament_id: str, name: str = "Open") -> dict:
    r = client.post(f"/api/v1/tournaments/{tournament_id}/divisions", json={"name": name})
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


def test_create_division(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    assert d["name"] == "Open"
    assert d["state"] == "setup"


def test_list_divisions(client: TestClient) -> None:
    t = _tournament(client)
    _division(client, t["id"], "A")
    _division(client, t["id"], "B")
    r = client.get(f"/api/v1/tournaments/{t['id']}/divisions")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_rename_division(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    r = client.patch(f"/api/v1/divisions/{d['id']}", json={"name": "Heavyweight"})
    assert r.status_code == 200
    assert r.json()["name"] == "Heavyweight"


def test_pause_and_resume_division(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    r = client.patch(
        f"/api/v1/divisions/{d['id']}", json={"state": "paused", "paused_reason": "ring closed"}
    )
    assert r.status_code == 200
    assert r.json()["state"] == "paused"
    r = client.patch(f"/api/v1/divisions/{d['id']}", json={"state": "setup"})
    assert r.status_code == 200
    assert r.json()["state"] == "setup"


# ---------------------------------------------------------------------------
# Participant assignment
# ---------------------------------------------------------------------------


def test_assign_participant(client: TestClient) -> None:
    t = _tournament(client)
    p = _participant(client, t["id"])
    d = _division(client, t["id"])
    r = client.post(
        f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
    )
    assert r.status_code == 200
    r = client.get(f"/api/v1/tournaments/{t['id']}/participants")
    assert r.json()[0]["division_id"] == d["id"]


def test_assign_participant_already_in_division_rejected(client: TestClient) -> None:
    t = _tournament(client)
    p = _participant(client, t["id"])
    d = _division(client, t["id"])
    d2 = _division(client, t["id"], "B")
    client.post(f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]})
    r = client.post(
        f"/api/v1/divisions/{d2['id']}/assign-participant", json={"participant_id": p["id"]}
    )
    assert r.status_code == 409
    assert "ALREADY_IN_DIVISION" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Round-robin generation
# ---------------------------------------------------------------------------


def test_generate_round_robin_4_participants(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    for name in ["A", "B", "C", "D"]:
        p = _participant(client, t["id"], name)
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
        )
    r = client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    assert r.status_code == 200
    matches_r = client.get(f"/api/v1/divisions/{d['id']}/matches")
    assert len(matches_r.json()) == 6  # 4*(4-1)//2


def test_generate_round_robin_transition_state(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    for name in ["A", "B"]:
        p = _participant(client, t["id"], name)
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
        )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    r = client.get(f"/api/v1/tournaments/{t['id']}/divisions")
    div = next(d for d in r.json() if d["name"] == "Open")
    assert div["state"] == "round_robin"


def test_generate_round_robin_idempotent_blocked(client: TestClient) -> None:
    """Cannot generate a second time after state transitions to round_robin."""
    t = _tournament(client)
    d = _division(client, t["id"])
    for name in ["A", "B"]:
        p = _participant(client, t["id"], name)
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
        )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    r = client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Late participant addition
# ---------------------------------------------------------------------------


def test_late_participant_addition_appends_matches(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    names = ["A", "B", "C"]
    for name in names:
        p = _participant(client, t["id"], name)
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
        )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")

    # Add a 4th participant — should generate 3 new matches
    p4 = _participant(client, t["id"], "D")
    r = client.post(
        f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p4["id"]}
    )
    assert r.status_code == 200

    matches_r = client.get(f"/api/v1/divisions/{d['id']}/matches")
    # 3 original + 3 new = 6
    assert len(matches_r.json()) == 6


def test_late_addition_blocked_after_play_ins(client: TestClient) -> None:
    t = _tournament(client)
    d = _division(client, t["id"])
    p = _participant(client, t["id"])
    # Force division state to play_ins via PATCH (admin override)
    client.patch(f"/api/v1/divisions/{d['id']}", json={"state": "play_ins"})
    r = client.post(
        f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
    )
    assert r.status_code == 409
    assert "DIVISION_ADVANCED" in r.json()["detail"]
