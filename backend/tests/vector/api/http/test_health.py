"""HTTP health routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vector.api.http.main import app


def test_health_live_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
