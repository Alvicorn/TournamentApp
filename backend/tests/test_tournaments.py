"""Integration tests for tournament endpoints."""

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_tournament(client: TestClient, *, is_demo: bool = False) -> dict:
    payload = {
        "name": "Test Tournament",
        "competition_date": "2026-06-01",
        "time_zone": "America/Vancouver",
        "rounds_per_match": 3,
        "round_length_seconds": 120,
        "slideshow_slide_seconds": 10,
        "is_demo": is_demo,
    }
    resp = client.post("/api/v1/tournaments", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_tournament(client: TestClient) -> None:
    t = _create_tournament(client)
    assert t["name"] == "Test Tournament"
    assert t["lifecycle_state"] == "setup"
    assert t["is_demo"] is False


def test_get_active_tournament(client: TestClient) -> None:
    _create_tournament(client)
    resp = client.get("/api/v1/tournaments/active")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Tournament"


def test_get_active_404_when_none(client: TestClient) -> None:
    resp = client.get("/api/v1/tournaments/active")
    assert resp.status_code == 404


def test_patch_tournament(client: TestClient) -> None:
    t = _create_tournament(client)
    resp = client.patch(f"/api/v1/tournaments/{t['id']}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


def test_only_one_active_non_demo_allowed(client: TestClient) -> None:
    _create_tournament(client)
    resp = client.post(
        "/api/v1/tournaments",
        json={
            "name": "Second",
            "competition_date": "2026-07-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
        },
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_activate_tournament(client: TestClient) -> None:
    t = _create_tournament(client)
    resp = client.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "active"


def test_custom_fields_frozen_when_active(client: TestClient) -> None:
    t = _create_tournament(client)
    client.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    resp = client.patch(
        f"/api/v1/tournaments/{t['id']}",
        json={
            "custom_participant_fields": [
                {"key": "belt", "label": "Belt", "type": "text", "required": False}
            ]
        },
    )
    assert resp.status_code == 409
    assert "CUSTOM_FIELDS_FROZEN" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Demo reset
# ---------------------------------------------------------------------------


def test_demo_reset(client: TestClient) -> None:
    t = _create_tournament(client, is_demo=True)
    client.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    resp = client.post(f"/api/v1/tournaments/{t['id']}/reset")
    assert resp.status_code == 200
    assert resp.json()["lifecycle_state"] == "setup"
    assert resp.json()["custom_participant_fields"] == []


def test_non_demo_reset_rejected(client: TestClient) -> None:
    t = _create_tournament(client)
    resp = client.post(f"/api/v1/tournaments/{t['id']}/reset")
    assert resp.status_code == 409
