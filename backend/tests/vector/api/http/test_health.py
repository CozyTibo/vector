"""HTTP health and readiness routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vector.api.http.main import app
from vector.api.http.routes import health as health_routes


def test_health_liveness_always_200() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.integration
def test_ready_returns_database_ok_when_db_up() -> None:
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] in ("ok", "skipped")


def test_ready_returns_database_failed_when_db_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "failed",
        "redis": "skipped",
    }


def test_ready_redis_failed_when_redis_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _GoodConn:
        def __enter__(self) -> _GoodConn:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, *_args: object, **_kwargs: object) -> None:
            return None

    class _GoodEngine:
        def connect(self) -> _GoodConn:
            return _GoodConn()

    class _BadRedis:
        def ping(self) -> bool:
            raise ConnectionError("redis down")

        def close(self) -> None:
            return None

    monkeypatch.setattr(health_routes, "get_engine", lambda: _GoodEngine())
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr(health_routes.redis, "from_url", lambda _url: _BadRedis())

    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["redis"] == "failed"


class _BadConn:
    def __enter__(self) -> None:
        raise OSError("connection refused")

    def __exit__(self, *_args: object) -> None:
        return None


class _BadEngine:
    def connect(self) -> _BadConn:
        return _BadConn()


class _GoodConn:
    def __enter__(self) -> _GoodConn:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> None:
        return None


class _GoodEngine:
    def connect(self) -> _GoodConn:
        return _GoodConn()


def test_ready_e2e_database_failed_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "get_engine", lambda: _BadEngine())
    monkeypatch.delenv("REDIS_URL", raising=False)

    client = TestClient(app)
    response = client.get("/ready/e2e")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "failed"
    assert body["migrations"] == "skipped"
    assert body["redis"] == "skipped"
    assert body["worker"] == "skipped"


def test_ready_e2e_ok_when_db_and_migrations_ok_redis_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "get_engine", lambda: _GoodEngine())
    monkeypatch.setattr(health_routes, "_migrations_state", lambda _e: ("ok", None))
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(health_routes, "_redis_status", lambda: "skipped")

    client = TestClient(app)
    response = client.get("/ready/e2e")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["migrations"] == "ok"
    assert body["redis"] == "skipped"
    assert body["worker"] == "skipped"


def test_ready_e2e_migrations_behind_returns_503_with_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "get_engine", lambda: _GoodEngine())
    monkeypatch.setattr(
        health_routes,
        "_migrations_state",
        lambda _e: ("behind", "database at 'abc', head is 'def'"),
    )
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(health_routes, "_redis_status", lambda: "skipped")

    client = TestClient(app)
    response = client.get("/ready/e2e")
    assert response.status_code == 503
    body = response.json()
    assert body["migrations"] == "behind"
    assert body["migrations_detail"] == "database at 'abc', head is 'def'"


def test_ready_e2e_worker_ok_when_redis_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "get_engine", lambda: _GoodEngine())
    monkeypatch.setattr(health_routes, "_migrations_state", lambda _e: ("ok", None))
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr(health_routes, "_redis_status", lambda: "ok")
    monkeypatch.setattr(health_routes, "_worker_state", lambda: "ok")

    client = TestClient(app)
    response = client.get("/ready/e2e")
    assert response.status_code == 200
    assert response.json()["worker"] == "ok"


def test_ready_e2e_no_workers_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_routes, "get_engine", lambda: _GoodEngine())
    monkeypatch.setattr(health_routes, "_migrations_state", lambda _e: ("ok", None))
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr(health_routes, "_redis_status", lambda: "ok")
    monkeypatch.setattr(health_routes, "_worker_state", lambda: "no_workers")

    client = TestClient(app)
    response = client.get("/ready/e2e")
    assert response.status_code == 503
    assert response.json()["worker"] == "no_workers"
