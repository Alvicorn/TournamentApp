"""BDD steps for late_participant_addition.feature."""

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


@scenario(
    "late_participant_addition.feature",
    "Participant added to round_robin division gets matches against all existing participants",
)
def test_late_add(): ...


@scenario(
    "late_participant_addition.feature",
    "Participant cannot be added after division advances past round_robin",
)
def test_blocked(): ...


@given(
    "a division in round_robin state with 3 existing participants and 3 matches",
    target_fixture="ctx",
)
def division_with_3(db_session):
    c = _make_client(db_session)
    t = c.post(
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
    d = c.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "Open"}).json()
    participants = []
    for name in ["A", "B", "C"]:
        p = c.post(
            f"/api/v1/tournaments/{t['id']}/participants",
            json={"name": name, "custom_fields": {}},
        ).json()
        c.post(f"/api/v1/divisions/{d['id']}/assign-participant", json={"participant_id": p["id"]})
        participants.append(p)
    c.post(f"/api/v1/divisions/{d['id']}/generate-round-robin")
    return {"client": c, "tournament": t, "division": d, "participants": participants}


@given(
    "a division whose state has been manually advanced to play_ins",
    target_fixture="ctx",
)
def advanced_division(db_session):
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
    d = c.post(f"/api/v1/tournaments/{t['id']}/divisions", json={"name": "D"}).json()
    c.patch(f"/api/v1/divisions/{d['id']}", json={"state": "play_ins"})
    return {"client": c, "tournament": t, "division": d}


@when("admin assigns a 4th participant to the division")
def assign_4th(ctx):
    c = ctx["client"]
    p4 = c.post(
        f"/api/v1/tournaments/{ctx['tournament']['id']}/participants",
        json={"name": "D", "custom_fields": {}},
    ).json()
    ctx["response"] = c.post(
        f"/api/v1/divisions/{ctx['division']['id']}/assign-participant",
        json={"participant_id": p4["id"]},
    )
    ctx["new_participant"] = p4


@when("admin attempts to assign a participant")
def attempt_assign(ctx):
    c = ctx["client"]
    p = c.post(
        f"/api/v1/tournaments/{ctx['tournament']['id']}/participants",
        json={"name": "X", "custom_fields": {}},
    ).json()
    ctx["response"] = c.post(
        f"/api/v1/divisions/{ctx['division']['id']}/assign-participant",
        json={"participant_id": p["id"]},
    )


@then("3 new matches are appended to the division")
def three_new_matches(ctx):
    assert ctx["response"].status_code == 200
    r = ctx["client"].get(f"/api/v1/divisions/{ctx['division']['id']}/matches")
    assert len(r.json()) == 6  # 3 original + 3 new


@then("the new participant faces each of the 3 existing participants")
def faces_each(ctx):
    r = ctx["client"].get(f"/api/v1/divisions/{ctx['division']['id']}/matches")
    matches = r.json()
    new_pid = ctx["new_participant"]["id"]
    new_matches = [
        m for m in matches if m["competitor_a_id"] == new_pid or m["competitor_b_id"] == new_pid
    ]
    assert len(new_matches) == 3


@then("a 409 DIVISION_ADVANCED error is returned")
def division_advanced_error(ctx):
    assert ctx["response"].status_code == 409
    assert "DIVISION_ADVANCED" in ctx["response"].json()["detail"]
