"""Integration tests for judge endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


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


def test_create_judge(client: TestClient) -> None:
    t = _tournament(client)
    r = client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "Maria"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Maria"
    # Code: 8 uppercase alphanumeric chars (no 0/O/1/I/L)
    assert len(data["code"]) == 8
    assert data["code"] == data["code"].upper()
    assert not any(c in data["code"] for c in "01ILO")


def test_list_judges(client: TestClient) -> None:
    t = _tournament(client)
    client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "A"})
    client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "B"})
    r = client.get(f"/api/v1/tournaments/{t['id']}/judges")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_delete_judge(client: TestClient) -> None:
    t = _tournament(client)
    j = client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "X"}).json()
    r = client.delete(f"/api/v1/judges/{j['id']}")
    assert r.status_code == 204
    r = client.get(f"/api/v1/tournaments/{t['id']}/judges")
    assert r.json() == []


def test_500_codes_all_unique_and_valid(client: TestClient) -> None:
    """Generate 500 codes and verify no collisions and all pass checksum."""
    from app.codes import is_valid_judge_code

    t = _tournament(client)
    codes = set()
    for i in range(500):
        r = client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": f"Judge {i}"})
        assert r.status_code == 201
        code = r.json()["code"]
        assert is_valid_judge_code(code), f"Invalid checksum on code: {code}"
        codes.add(code)
    assert len(codes) == 500, "Duplicate codes generated"


def test_delete_judge_with_active_match(client: TestClient, db_session: Session) -> None:
    """Deleting a judge with an in_progress match pauses the match and logs judge.removed_active."""
    t = _tournament(client)
    j_r = client.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "Ref"})
    assert j_r.status_code == 201
    j = j_r.json()

    # Set up a division with 2 participants and generate round-robin (1 match)
    d_r = client.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "Open"})
    assert d_r.status_code == 201
    d = d_r.json()
    for name in ["A", "B"]:
        p_r = client.post(
            f"/api/v1/tournaments/{t['id']}/participants",
            json={"name": name, "custom_fields": {}},
        )
        assert p_r.status_code == 201
        client.post(
            f"/api/v1/divisions/{d['id']}/assign-participant",
            json={"participant_id": p_r.json()["id"]},
        )
    client.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")

    # Force the match to in_progress and assign the judge via raw SQL
    matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    match_id = matches[0]["id"]
    db_session.execute(
        text("UPDATE matches SET state = 'in_progress', assigned_judge_id = :jid WHERE id = :mid"),
        {"jid": j["id"], "mid": match_id},
    )
    db_session.commit()

    # Delete the judge — should pause the match and null assigned_judge_id
    r = client.delete(f"/api/v1/judges/{j['id']}")
    assert r.status_code == 204

    # Verify judge is gone
    judges = client.get(f"/api/v1/tournaments/{t['id']}/judges").json()
    assert judges == []

    # Verify match is paused and judge is unassigned
    updated_matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    m = updated_matches[0]
    assert m["state"] == "paused", f"Expected paused, got {m['state']}"
    assert m["assigned_judge_id"] is None

    # Verify activity log has judge.removed_active
    log = client.get(f"/api/v1/tournaments/{t['id']}/activity?limit=50").json()
    actions = [entry["action"] for entry in log]
    assert "judge.removed_active" in actions, f"Expected judge.removed_active in {actions}"
