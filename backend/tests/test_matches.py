"""Integration tests for match endpoints."""

from fastapi.testclient import TestClient


def _setup(client: TestClient) -> tuple[dict, dict, dict, dict]:
    """Returns (tournament, division, participant_a, participant_b)."""
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "T",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 3,
            "round_length_seconds": 120,
            "slideshow_slide_seconds": 10,
        },
    ).json()
    d = client.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "Open"}).json()
    pa = client.post(
        f"/api/v1/tournaments/{t['id']}/participants", json={"name": "A", "custom_fields": {}}
    ).json()
    pb = client.post(
        f"/api/v1/tournaments/{t['id']}/participants", json={"name": "B", "custom_fields": {}}
    ).json()
    client.post(
        f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": pa["id"]}
    )
    client.post(
        f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": pb["id"]}
    )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    return t, d, pa, pb


def test_list_matches(client: TestClient) -> None:
    t, d, pa, pb = _setup(client)
    r = client.get(f"/api/v1/divisions/{d['id']}/matches")
    assert r.status_code == 200
    assert len(r.json()) == 1  # 2 participants = 1 match
    assert r.json()[0]["state"] == "scheduled"


def test_reorder_matches(client: TestClient) -> None:
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "T2",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
        },
    ).json()
    d = client.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "D"}).json()
    names = ["A", "B", "C"]
    for name in names:
        p = client.post(
            f"/api/v1/tournaments/{t['id']}/participants", json={"name": name, "custom_fields": {}}
        ).json()
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]}
        )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")

    matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    assert len(matches) == 3
    reversed_ids = [m["id"] for m in reversed(matches)]

    r = client.post(
        f"/api/v1/divisions/{d['id']}/reorder-matches",
        json={"ordered_match_ids": reversed_ids},
    )
    assert r.status_code == 200

    reordered = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    assert [m["id"] for m in reordered] == reversed_ids


def test_edit_result_round_robin(client: TestClient) -> None:
    t, d, pa, pb = _setup(client)
    matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    match_id = matches[0]["id"]

    # Match is 'scheduled', not 'submitted' → 409
    r = client.post(
        f"/api/v1/matches/{match_id}/edit-result",
        json={
            "round_scores": [{"round_number": 1, "competitor_a_score": 5, "competitor_b_score": 3}]
        },
    )
    assert r.status_code == 409


def test_edit_result_blocked_for_non_round_robin_division(client: TestClient) -> None:
    t, d, pa, pb = _setup(client)
    # Force division to play_ins state
    client.patch(f"/api/v1/divisions/{d['id']}", json={"state": "play_ins"})
    matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    r = client.post(
        f"/api/v1/matches/{matches[0]['id']}/edit-result",
        json={
            "round_scores": [{"round_number": 1, "competitor_a_score": 3, "competitor_b_score": 2}]
        },
    )
    assert r.status_code == 409
