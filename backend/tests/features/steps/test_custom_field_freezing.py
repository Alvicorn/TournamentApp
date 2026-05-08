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


@scenario(
    "custom_field_freezing.feature",
    "Adding a custom field does not break existing participants",
)
def test_add_field_back_fills_null(): ...


@scenario(
    "custom_field_freezing.feature",
    "Removing a custom field updates the tournament spec",
)
def test_remove_field_drops_spec(): ...


@given(
    "a tournament in setup state with an existing participant having no extra fields",
    target_fixture="ctx",
)
def setup_with_participant_no_extras(db_session):
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
    p_r = c.post(
        f"/api/v1/tournaments/{t['id']}/participants",
        json={"name": "Alice", "custom_fields": {}},
    )
    assert p_r.status_code == 201
    return {"client": c, "tournament": t, "participant": p_r.json()}


@given(
    "a tournament in setup state with a participant having a belt field value",
    target_fixture="ctx",
)
def setup_with_belt_participant(db_session):
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
                {"key": "belt", "label": "Belt", "type": "text", "required": False}
            ],
        },
    )
    assert r.status_code == 201
    t = r.json()
    p_r = c.post(
        f"/api/v1/tournaments/{t['id']}/participants",
        json={"name": "Alice", "custom_fields": {"belt": "black"}},
    )
    assert p_r.status_code == 201
    return {"client": c, "tournament": t, "participant": p_r.json()}


@when("admin PATCHes custom_participant_fields to add a belt field")
def patch_add_belt_field(ctx):
    ctx["response"] = ctx["client"].patch(
        f"/api/v1/tournaments/{ctx['tournament']['id']}",
        json={
            "custom_participant_fields": [
                {"key": "belt", "label": "Belt", "type": "text", "required": False}
            ]
        },
    )


@when("admin PATCHes custom_participant_fields to remove all fields")
def patch_remove_all_fields(ctx):
    ctx["response"] = ctx["client"].patch(
        f"/api/v1/tournaments/{ctx['tournament']['id']}",
        json={"custom_participant_fields": []},
    )


@then("the existing participant can still be retrieved successfully")
def participant_still_retrievable(ctx):
    r = ctx["client"].get(f"/api/v1/tournaments/{ctx['tournament']['id']}/participants")
    assert r.status_code == 200
    participants = r.json()
    assert len(participants) == 1
    assert participants[0]["id"] == ctx["participant"]["id"]
    assert participants[0]["name"] == "Alice"


@then("the tournament custom_participant_fields is empty")
def tournament_fields_empty(ctx):
    fields = ctx["response"].json().get("custom_participant_fields", None)
    assert fields == [], f"Expected empty custom_participant_fields, got: {fields}"
