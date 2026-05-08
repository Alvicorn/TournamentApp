"""Full happy-path integration test for Phase 2.

Covers the complete admin flow:
  tournament → judge → participants → division → assign →
  generate-round-robin → reorder → edit-result → activity log present
"""

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_full_happy_path(client: TestClient, db_session: Session) -> None:
    # ------------------------------------------------------------------
    # 1. Create tournament
    # ------------------------------------------------------------------
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "Grand Prix",
            "competition_date": "2026-08-01",
            "time_zone": "America/Vancouver",
            "rounds_per_match": 2,
            "round_length_seconds": 90,
            "slideshow_slide_seconds": 8,
        },
    ).json()
    assert t["lifecycle_state"] == "setup"
    tid = t["id"]

    # ------------------------------------------------------------------
    # 2. Add a judge
    # ------------------------------------------------------------------
    judge = client.post(f"/api/v1/tournaments/{tid}/judges", json={"name": "Judge Ana"}).json()
    assert len(judge["code"]) == 8

    # ------------------------------------------------------------------
    # 3. Create 4 participants (produces 6 round-robin matches)
    # ------------------------------------------------------------------
    participants = []
    for name in ["Alice", "Bob", "Carol", "Dave"]:
        p = client.post(
            f"/api/v1/tournaments/{tid}/participants",
            json={"name": name, "custom_fields": {}},
        ).json()
        assert p["name"] == name
        participants.append(p)

    # ------------------------------------------------------------------
    # 4. Create a division and assign all 4 participants
    # ------------------------------------------------------------------
    div = client.post(f"/api/v1/tournaments/{tid}/divisions", json={"name": "Open"}).json()
    assert div["state"] == "setup"
    for p in participants:
        r = client.post(
            f"/api/v1/divisions/{div['id']}/assign-participant",
            json={"participant_id": p["id"]},
        )
        assert r.status_code == 200

    # ------------------------------------------------------------------
    # 5. Generate round-robin — 4 participants → 6 matches
    # ------------------------------------------------------------------
    rr_r = client.post(f"/api/v1/divisions/{div['id']}/generate-round-robin")
    assert rr_r.status_code == 200
    assert rr_r.json()["state"] == "round_robin"

    matches = client.get(f"/api/v1/divisions/{div['id']}/matches").json()
    assert len(matches) == 6  # 4*(4-1)//2

    # ------------------------------------------------------------------
    # 6. Reorder matches (reverse)
    # ------------------------------------------------------------------
    reversed_ids = [m["id"] for m in reversed(matches)]
    reorder_r = client.post(
        f"/api/v1/divisions/{div['id']}/reorder-matches",
        json={"ordered_match_ids": reversed_ids},
    )
    assert reorder_r.status_code == 200
    reordered = client.get(f"/api/v1/divisions/{div['id']}/matches").json()
    assert [m["id"] for m in reordered] == reversed_ids

    # ------------------------------------------------------------------
    # 7. Force first match to 'submitted' state via raw SQL
    #    (judge scoring is Phase 3; Phase 2 uses admin edit-result)
    # ------------------------------------------------------------------
    match_id = reordered[0]["id"]
    winner_id = reordered[0]["competitor_a_id"]
    db_session.execute(
        text("UPDATE matches SET state = 'submitted', winner_id = :w WHERE id = :id"),
        {"w": winner_id, "id": match_id},
    )
    db_session.execute(
        text(
            "INSERT INTO match_rounds (id, match_id, round_number, competitor_a_score, "
            "competitor_b_score, state) "
            "VALUES (gen_random_uuid(), :mid, 1, 5, 3, 'completed')"
        ),
        {"mid": match_id},
    )
    db_session.commit()

    # ------------------------------------------------------------------
    # 8. Edit result — new scores flip the winner
    # ------------------------------------------------------------------
    loser_id = reordered[0]["competitor_b_id"]
    edit_r = client.post(
        f"/api/v1/matches/{match_id}/edit-result",
        json={
            "round_scores": [{"round_number": 1, "competitor_a_score": 2, "competitor_b_score": 9}]
        },
    )
    assert edit_r.status_code == 200
    assert edit_r.json()["winner_id"] == loser_id  # b scored higher → b wins

    # ------------------------------------------------------------------
    # 9. Verify activity log contains all key actions
    # ------------------------------------------------------------------
    log = client.get(f"/api/v1/tournaments/{tid}/activity?limit=200").json()
    actions = {entry["action"] for entry in log}
    expected_actions = {
        "tournament.created",
        "judge.added",
        "participant.added",
        "division.created",
        "division.round_robin_generated",
        "match.reordered",
        "match.result_edited",
    }
    missing = expected_actions - actions
    assert not missing, f"Activity log missing actions: {missing}. Found: {actions}"
