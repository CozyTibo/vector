"""Shared fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# `mock_connectors` lives under `backend/` (sibling to `tests/`); unit tests import it by top-level name.
_backend_dir = Path(__file__).resolve().parents[1]
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Must run before any `vector.*` import: otherwise `Settings` loads repo `.env` and breaks tests that
# `monkeypatch.delenv` / expect connectors to be unconfigured, and GitHub JWT tests (PEM vs path).
os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")

from app.core.logging import setup_logging

setup_logging()

from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy import create_engine, event
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
    prev_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    prev_waitlist_email = os.environ.get("VECTOR_WAITLIST_SIGNUP_EMAIL")
    prev_onboarding_activation = os.environ.get("VECTOR_ONBOARDING_ACTIVATION_EMAIL")
    # CI and automated tests must never use local mock connectors (strategy §17).
    os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "false"
    # Integration tests call /auth/register; do not enqueue real waitlist emails to Mailtrap/SES.
    os.environ["VECTOR_WAITLIST_SIGNUP_EMAIL"] = "false"
    # Admin workspace-access toggles should not enqueue onboarding activation tasks in CI.
    os.environ["VECTOR_ONBOARDING_ACTIVATION_EMAIL"] = "false"
    yield
    get_settings.cache_clear()
    if prev_mock is None:
        os.environ.pop("VECTOR_USE_MOCK_CONNECTORS", None)
    else:
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = prev_mock
    if prev_waitlist_email is None:
        os.environ.pop("VECTOR_WAITLIST_SIGNUP_EMAIL", None)
    else:
        os.environ["VECTOR_WAITLIST_SIGNUP_EMAIL"] = prev_waitlist_email
    if prev_onboarding_activation is None:
        os.environ.pop("VECTOR_ONBOARDING_ACTIVATION_EMAIL", None)
    else:
        os.environ["VECTOR_ONBOARDING_ACTIVATION_EMAIL"] = prev_onboarding_activation


@pytest.fixture(scope="session")
def engine() -> Any:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        msg = "DATABASE_URL is required for DB tests"
        raise RuntimeError(msg)
    return create_engine(url, pool_pre_ping=True)


@pytest.fixture
def db_session(engine: Any) -> Generator[Session, None, None]:
    """Per-test session on a connection rolled back after the test.

    Uses a SAVEPOINT so tests may call ``session.commit()`` without ending the
    outer transaction (avoids SAWarning on teardown rollback).
    """
    conn = engine.connect()
    trans = conn.begin()
    factory = sessionmaker(autoflush=False, autocommit=False, bind=conn)
    session = factory()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, transaction: Any) -> None:
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", _restart_savepoint)
        session.close()
        if trans.is_active:
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
