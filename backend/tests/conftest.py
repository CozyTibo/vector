"""Shared fixtures."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vector.api.http.deps import get_db
from vector.api.http.main import app
from vector.settings import get_settings


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("DATABASE_URL"):
        return
    skip = pytest.mark.skip(reason="DATABASE_URL not set (use `make test`)")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def engine() -> Any:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        msg = "DATABASE_URL is required for DB tests"
        raise RuntimeError(msg)
    return create_engine(url, pool_pre_ping=True)


@pytest.fixture
def db_session(engine: Any) -> Generator[Session, None, None]:
    conn = engine.connect()
    trans = conn.begin()
    factory = sessionmaker(autoflush=False, autocommit=False, bind=conn)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def client(db_session: Session) -> Generator[Any, None, None]:
    from starlette.testclient import TestClient

    def override_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as ac:
        yield ac
    app.dependency_overrides.clear()
