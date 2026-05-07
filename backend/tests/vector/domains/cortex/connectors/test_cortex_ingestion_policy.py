"""Cortex connector migration routing flags."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.connectors import cortex_ingestion_policy as policy
from vector.settings import get_settings

_DB_URL = "postgresql+psycopg://test:test@localhost:5432/vector_test"


@pytest.fixture(autouse=True)
def _database_url_for_policy_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """``Settings()`` requires ``DATABASE_URL`` from env when constructed inside tests."""
    monkeypatch.setenv("DATABASE_URL", _DB_URL)


def _clear_cortex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "CORTEX_CONNECTOR_MIGRATION_ENABLED",
        "CORTEX_CONNECTOR_MIGRATION_CALLS",
        "CORTEX_CONNECTOR_MIGRATION_GITHUB",
        "CORTEX_CONNECTOR_MIGRATION_LINEAR",
        "CORTEX_CONNECTOR_MIGRATION_NOTION",
        "CORTEX_CONNECTOR_MIGRATION_SLACK",
        "CORTEX_CONNECTOR_MIGRATION_CALLS_TENANTS",
        "CORTEX_CONNECTOR_MIGRATION_GITHUB_TENANTS",
        "CORTEX_CONNECTOR_MIGRATION_LINEAR_TENANTS",
        "CORTEX_CONNECTOR_MIGRATION_NOTION_TENANTS",
        "CORTEX_CONNECTOR_MIGRATION_SLACK_TENANTS",
    ):
        monkeypatch.delenv(key, raising=False)


def test_route_inactive_when_master_off(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    _clear_cortex_env(monkeypatch)
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "false")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_GITHUB", "true")
    get_settings.cache_clear()
    st = get_settings()
    try:
        assert not policy.should_route_ingestion_to_cortex(st, "github", tid)
    finally:
        get_settings.cache_clear()


def test_route_inactive_when_connector_off(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    _clear_cortex_env(monkeypatch)
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_GITHUB", "false")
    get_settings.cache_clear()
    st = get_settings()
    try:
        assert not policy.should_route_ingestion_to_cortex(st, "github", tid)
    finally:
        get_settings.cache_clear()


def test_route_active_when_all_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    _clear_cortex_env(monkeypatch)
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_LINEAR", "true")
    get_settings.cache_clear()
    st = get_settings()
    try:
        assert policy.should_route_ingestion_to_cortex(st, "linear", tid)
    finally:
        get_settings.cache_clear()


def test_allowlist_restricts_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    inside = uuid.uuid4()
    outside = uuid.uuid4()
    _clear_cortex_env(monkeypatch)
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_SLACK", "true")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_SLACK_TENANTS", str(inside))
    get_settings.cache_clear()
    st = get_settings()
    try:
        assert policy.should_route_ingestion_to_cortex(st, "slack", inside)
        assert not policy.should_route_ingestion_to_cortex(st, "slack", outside)
    finally:
        get_settings.cache_clear()


def test_unknown_connector_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_cortex_env(monkeypatch)
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "true")
    get_settings.cache_clear()
    st = get_settings()
    try:
        assert not policy.should_route_ingestion_to_cortex(st, "unknown", uuid.uuid4())
    finally:
        get_settings.cache_clear()


def test_extract_tenant_kw() -> None:
    tid = uuid.uuid4()
    assert policy.extract_tenant_id_from_enqueue_args((), {"tenant_id": tid}) == tid


def test_extract_tenant_positional() -> None:
    tid = uuid.uuid4()
    assert policy.extract_tenant_id_from_enqueue_args((tid,), {}) == tid


def test_admin_github_enqueue_raises_runtime_when_no_migration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")
    monkeypatch.delenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", raising=False)
    monkeypatch.delenv("CORTEX_CONNECTOR_MIGRATION_GITHUB", raising=False)

    from vector.api.http.routes.admin import connector_sync
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="poll ingestion is unavailable"):
            connector_sync.enqueue_github_poll_sync()
    finally:
        get_settings.cache_clear()


def test_admin_github_enqueue_raises_notimplemented_when_cortex_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = uuid.uuid4()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("CORTEX_CONNECTOR_MIGRATION_GITHUB", "true")

    from vector.api.http.routes.admin import connector_sync
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(NotImplementedError, match="Cortex ingestion executor"):
            connector_sync.enqueue_github_poll_sync(tenant_id=tid)
    finally:
        get_settings.cache_clear()
