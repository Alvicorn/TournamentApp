from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    with patch("app.routes.health._ping_supabase", return_value=True):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_supabase_unreachable(client: TestClient) -> None:
    with patch("app.routes.health._ping_supabase", return_value=False):
        response = client.get("/health")
    assert response.status_code == 503


def test_health_redis_ok(client: TestClient) -> None:
    with patch("app.routes.health.ping_redis", return_value=True):
        response = client.get("/health/redis")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_redis_unhealthy(client: TestClient) -> None:
    with patch("app.routes.health.ping_redis", return_value=False):
        response = client.get("/health/redis")
    assert response.status_code == 503
