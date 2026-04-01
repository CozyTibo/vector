"""Mock connector settings guards."""

from __future__ import annotations

import os

import pytest

from vector.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def _database_url_for_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/vector_test")


def test_mock_connectors_rejected_when_env_not_development() -> None:
    old_env = os.environ.get("ENV")
    old_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "test"
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "true"
        with pytest.raises(ValueError, match="VECTOR_USE_MOCK_CONNECTORS"):
            Settings()
    finally:
        get_settings.cache_clear()
        _restore("ENV", old_env)
        _restore("VECTOR_USE_MOCK_CONNECTORS", old_mock)


def test_mock_connectors_rejected_in_production() -> None:
    old_env = os.environ.get("ENV")
    old_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "production"
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "true"
        with pytest.raises(ValueError, match="VECTOR_USE_MOCK_CONNECTORS"):
            Settings()
    finally:
        get_settings.cache_clear()
        _restore("ENV", old_env)
        _restore("VECTOR_USE_MOCK_CONNECTORS", old_mock)


def test_github_rest_defaults_to_real_api() -> None:
    old_env = os.environ.get("ENV")
    old_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "false"
        s = Settings()
        assert s.github_rest_api_base_url() == "https://api.github.com"
        assert s.linear_graphql_url() == "https://api.linear.app/graphql"
    finally:
        get_settings.cache_clear()
        _restore("ENV", old_env)
        _restore("VECTOR_USE_MOCK_CONNECTORS", old_mock)


def _restore(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
