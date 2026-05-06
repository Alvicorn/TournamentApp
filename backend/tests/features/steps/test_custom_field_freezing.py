"""BDD steps for custom_field_freezing.feature."""

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


@scenario("custom_field_freezing.feature", "Custom fields locked while tournament is active")
def test_locked(): ...


@scenario("custom_field_freezing.feature", "Custom fields editable during setup")
def test_editable(): ...


@given("an active tournament with custom fields", target_fixture="ctx")
def active_with_fields(db_session):
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
            "custom_participant_fields": [
                {"key": "age", "label": "Age", "type": "number", "required": True}
            ],
        },
    )
    t = r.json()
    c.post(f"/api/v1/tournaments/{t['id']}/lifecycle", json={"state": "active"})
    return {"client": c, "tournament": t}


@given("a tournament in setup state", target_fixture="ctx")
def setup_state(db_session):
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
    return {"client": c, "tournament": r.json()}


@when("admin PATCHes custom_participant_fields")
def patch_frozen(ctx):
    ctx["response"] = ctx["client"].patch(
        f"/api/v1/tournaments/{ctx['tournament']['id']}",
        json={
            "custom_participant_fields": [
                {"key": "x", "label": "X", "type": "text", "required": False}
            ]
        },
    )


@when("admin PATCHes custom_participant_fields with a new field")
def patch_editable(ctx):
    ctx["response"] = ctx["client"].patch(
        f"/api/v1/tournaments/{ctx['tournament']['id']}",
        json={
            "custom_participant_fields": [
                {"key": "belt", "label": "Belt", "type": "text", "required": False}
            ]
        },
    )


@then("the response status is 409")
def assert_409(ctx):
    assert ctx["response"].status_code == 409


@then("the response status is 200")
def assert_200(ctx):
    assert ctx["response"].status_code == 200


@then('the error detail contains "CUSTOM_FIELDS_FROZEN"')
def assert_frozen_msg(ctx):
    assert "CUSTOM_FIELDS_FROZEN" in ctx["response"].json()["detail"]


@then("the returned custom_participant_fields contains the new field")
def assert_new_field(ctx):
    fields = ctx["response"].json()["custom_participant_fields"]
    assert any(f["key"] == "belt" for f in fields)
