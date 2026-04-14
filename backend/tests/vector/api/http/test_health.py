"""HTTP health routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vector.api.http.main import app
from vector.api.http.routes import health as health_routes


@pytest.mark.integration
def test_health_returns_ok_when_db_up() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_200_when_db_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BadConn:
        def __enter__(self) -> None:
            raise OSError("connection refused")

        def __exit__(self, *_args: object) -> None:
            return None

    class _BadEngine:
        def connect(self) -> _BadConn:
            return _BadConn()

    monkeypatch.setattr(health_routes, "get_engine", lambda: _BadEngine())

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "failed"}
