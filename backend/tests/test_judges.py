"""Integration tests for judge endpoints."""

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
