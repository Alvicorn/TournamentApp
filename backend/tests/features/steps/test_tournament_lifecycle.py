"""BDD steps for tournament_lifecycle.feature."""

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
    return TestClient(app, raise_server_exceptions=True)


@scenario("tournament_lifecycle.feature", "Activating a tournament freezes custom fields")
def test_freeze(): ...


@scenario("tournament_lifecycle.feature", "Demo tournament can be reset")
def test_reset(): ...


@scenario("tournament_lifecycle.feature", "Non-demo tournament cannot be reset")
def test_no_reset(): ...


@given("a tournament in setup state with custom fields defined", target_fixture="ctx")
def setup_with_fields(db_session):
    c = _make_client(db_session)
    r = c.post(
        "/api/v1/tournaments",
        json={
            "name": "T1",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 3,
            "round_length_seconds": 120,
            "slideshow_slide_seconds": 10,
            "custom_participant_fields": [
                {"key": "belt", "label": "Belt", "type": "text", "required": False}
            ],
        },
    )
    return {"client": c, "tournament": r.json()}


@given("a demo tournament in active state with a judge", target_fixture="ctx")
def demo_active_with_judge(db_session):
    c = _make_client(db_session)
    r = c.post(
        "/api/v1/tournaments",
        json={
            "name": "Demo",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
            "is_demo": True,
        },
    )
    t = r.json()
    c.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    judge_r = c.post(f"/api/v1/tournaments/{t['id']}/judges", json={"name": "Judge A"})
    return {"client": c, "tournament": t, "judge": judge_r.json()}


@given("a non-demo tournament in active state", target_fixture="ctx")
def non_demo_active(db_session):
    c = _make_client(db_session)
    r = c.post(
        "/api/v1/tournaments",
        json={
            "name": "Real",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 3,
            "round_length_seconds": 120,
            "slideshow_slide_seconds": 10,
        },
    )
    t = r.json()
    return {"client": c, "tournament": t}


@when("the admin transitions the tournament to active")
def activate(ctx):
    ctx["response"] = ctx["client"].post(
        f"/api/v1/tournaments/{ctx['tournament']['id']}/lifecycle",
        json={"state": "active"},
    )


@when("the admin resets the tournament")
def reset(ctx):
    ctx["response"] = ctx["client"].post(f"/api/v1/tournaments/{ctx['tournament']['id']}/reset")


@when("the admin attempts to reset the tournament")
def attempt_reset(ctx):
    ctx["response"] = ctx["client"].post(f"/api/v1/tournaments/{ctx['tournament']['id']}/reset")


@then("the lifecycle state is active")
def assert_active(ctx):
    assert ctx["response"].status_code == 200
    assert ctx["response"].json()["lifecycle_state"] == "active"


@then("the lifecycle state is setup")
def assert_setup(ctx):
    assert ctx["response"].status_code == 200
    assert ctx["response"].json()["lifecycle_state"] == "setup"


@then("the judge is soft-deleted")
def assert_judge_gone(ctx):
    r = ctx["client"].get(f"/api/v1/tournaments/{ctx['tournament']['id']}/judges")
    assert r.status_code == 200
    assert r.json() == [], f"Expected no judges after reset, got: {r.json()}"


@then("modifying custom_participant_fields returns 409")
def assert_frozen(ctx):
    r = ctx["client"].patch(
        f"/api/v1/tournaments/{ctx['tournament']['id']}",
        json={"custom_participant_fields": []},
    )
    assert r.status_code == 409
    assert "CUSTOM_FIELDS_FROZEN" in r.json()["detail"]


@then('a 409 error is returned with detail containing "demo"')
def assert_409_demo(ctx):
    assert ctx["response"].status_code == 409
    assert "demo" in ctx["response"].json()["detail"].lower()


@scenario(
    "tournament_lifecycle.feature",
    "Completing a tournament blocks participant updates",
)
def test_completed_blocks_updates(): ...


@given("a tournament in active state with a participant", target_fixture="ctx")
def active_with_participant(db_session):
    c = _make_client(db_session)
    r = c.post(
        "/api/v1/tournaments",
        json={
            "name": "T",
            "competition_date": "2026-06-01",
            "time_zone": "UTC",
            "rounds_per_match": 2,
            "round_length_seconds": 60,
            "slideshow_slide_seconds": 8,
        },
    )
    assert r.status_code == 201
    t = r.json()
    c.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    p_r = c.post(
        f"/api/v1/tournaments/{t['id']}/participants",
        json={"name": "Alice", "custom_fields": {}},
    )
    assert p_r.status_code == 201
    return {"client": c, "tournament": t, "participant": p_r.json()}


@when("the admin completes the tournament")
def complete_tournament(ctx):
    r = ctx["client"].post(
        f"/api/v1/tournaments/{ctx['tournament']['id']}/lifecycle",
        json={"state": "completed"},
    )
    assert r.status_code == 200, (
        f"Expected 200 completing tournament, got {r.status_code}: {r.text}"
    )


@when("admin attempts to update the participant")
def attempt_update_participant(ctx):
    ctx["response"] = ctx["client"].patch(
        f"/api/v1/participants/{ctx['participant']['id']}",
        json={"name": "Updated Name"},
    )


@then("a 409 error is returned with TOURNAMENT_COMPLETED detail")
def assert_tournament_completed_409(ctx):
    assert ctx["response"].status_code == 409
    assert "TOURNAMENT_COMPLETED" in ctx["response"].json()["detail"]
