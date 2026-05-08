"""BDD steps for match_state_machine.feature."""

from fastapi.testclient import TestClient
from pytest_bdd import given, scenario, then, when

from app.auth.dependencies import AdminPrincipal, require_admin
from app.db import get_db
from app.main import create_app


def _make_client(db_session):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[require_admin] = lambda: AdminPrincipal(
        role="admin", user_id="00000000-0000-0000-0000-000000000001", email="admin@test.com"
    )
    return TestClient(app, raise_server_exceptions=False)


def _setup_division_with_submitted_match(client, db_session):
    """Helper: create tournament, division, 2 participants, generate RR, force match to submitted."""
    t = client.post(
        "/api/v1/tournaments",
        json={
            "name": "T",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
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
    matches = client.get(f"/api/v1/divisions/{d['id']}/matches").json()
    match_id = matches[0]["id"]

    # Force match state to 'submitted' directly via DB (bypassing judge flow)
    from sqlalchemy import text

    db_session.execute(
        text("UPDATE matches SET state = 'submitted', winner_id = :winner WHERE id = :id"),
        {"winner": pa["id"], "id": match_id},
    )
    db_session.execute(
        text(
            "INSERT INTO match_rounds (id, match_id, round_number, competitor_a_score, competitor_b_score, state) "
            "VALUES (gen_random_uuid(), :mid, 1, 5, 3, 'completed')"
        ),
        {"mid": match_id},
    )
    db_session.commit()
    return t, d, match_id, pa, pb


@scenario(
    "match_state_machine.feature", "Edit result allowed on submitted match in round_robin division"
)
def test_edit_allowed(): ...


@scenario("match_state_machine.feature", "Edit result blocked when division is not round_robin")
def test_edit_blocked_state(): ...


@scenario("match_state_machine.feature", "Edit result blocked on a non-submitted match")
def test_edit_blocked_not_submitted(): ...


@given("a submitted match in a round_robin division", target_fixture="ctx")
def submitted_match(db_session):
    c = _make_client(db_session)
    t, d, match_id, pa, pb = _setup_division_with_submitted_match(c, db_session)
    return {"client": c, "tournament": t, "division": d, "match_id": match_id, "pa": pa, "pb": pb}


@given("a submitted match in a division with state play_ins", target_fixture="ctx")
def submitted_match_play_ins(db_session):
    c = _make_client(db_session)
    t, d, match_id, pa, pb = _setup_division_with_submitted_match(c, db_session)
    c.patch(f"/api/v1/divisions/{d['id']}", json={"state": "play_ins"})
    return {"client": c, "tournament": t, "division": d, "match_id": match_id, "pa": pa, "pb": pb}


@given("a scheduled match in a round_robin division", target_fixture="ctx")
def scheduled_match(db_session):
    c = _make_client(db_session)
    t = c.post(
        "/api/v1/tournaments",
        json={
            "name": "T",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
        },
    ).json()
    d = c.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "Open"}).json()
    pa = c.post(
        f"/api/v1/tournaments/{t['id']}/participants", json={"name": "A", "custom_fields": {}}
    ).json()
    pb = c.post(
        f"/api/v1/tournaments/{t['id']}/participants", json={"name": "B", "custom_fields": {}}
    ).json()
    c.post(f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": pa["id"]})
    c.post(f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": pb["id"]})
    c.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    matches = c.get(f"/api/v1/divisions/{d['id']}/matches").json()
    return {"client": c, "tournament": t, "division": d, "match_id": matches[0]["id"]}


@when("admin edits the result with new scores")
def edit_result(ctx):
    ctx["response"] = ctx["client"].post(
        f"/api/v1/matches/{ctx['match_id']}/edit-result",
        json={
            "round_scores": [{"round_number": 1, "competitor_a_score": 4, "competitor_b_score": 6}]
        },
    )


@when("admin attempts to edit the result")
def attempt_edit(ctx):
    ctx["response"] = ctx["client"].post(
        f"/api/v1/matches/{ctx['match_id']}/edit-result",
        json={
            "round_scores": [{"round_number": 1, "competitor_a_score": 3, "competitor_b_score": 2}]
        },
    )


@then("the match result is updated")
def result_updated(ctx):
    assert ctx["response"].status_code == 200


@then("an activity log entry with action match.result_edited exists")
def activity_log_entry(ctx):
    # Verify winner recomputed: new scores a=4, b=6 → competitor B wins
    updated = ctx["response"].json()
    assert updated["winner_id"] == ctx["pb"]["id"]
    # Verify activity log entry was written
    tournament_id = ctx["tournament"]["id"]
    log_r = ctx["client"].get(f"/api/v1/tournaments/{tournament_id}/activity?limit=50")
    assert log_r.status_code == 200
    items = log_r.json()
    actions = [entry["action"] for entry in items]
    assert "match.result_edited" in actions, (
        f"Expected match.result_edited in activity log, got: {actions}"
    )


@then("a 409 error is returned")
def assert_409(ctx):
    assert ctx["response"].status_code == 409
