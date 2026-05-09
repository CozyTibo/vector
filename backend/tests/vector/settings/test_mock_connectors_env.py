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


def test_mock_mode_swaps_data_plane_connector_urls() -> None:
    """OAuth hosts remain real; connector data-plane endpoints switch to local mock."""
    old_env = os.environ.get("ENV")
    old_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    old_base = os.environ.get("VECTOR_MOCK_CONNECTOR_BASE_URL")
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "true"
        os.environ["VECTOR_MOCK_CONNECTOR_BASE_URL"] = "http://127.0.0.1:9183"
        s = Settings()
        assert s.github_rest_api_base_url() == "http://127.0.0.1:9183"
        assert s.github_rest_api_app_install_base_url() == "https://api.github.com"
        assert s.linear_graphql_url() == "http://127.0.0.1:9183/linear/graphql"
        assert s.linear_graphql_oauth_profile_url() == "https://api.linear.app/graphql"
        assert s.linear_oauth_token_url() == "https://api.linear.app/oauth/token"
        assert s.notion_api_base_url() == "http://127.0.0.1:9183/notion/v1"
        assert s.calls_google_calendar_events_base_url() == "http://127.0.0.1:9183/google-calendar/v3"
    finally:
        get_settings.cache_clear()
        _restore("ENV", old_env)
        _restore("VECTOR_USE_MOCK_CONNECTORS", old_mock)
        _restore("VECTOR_MOCK_CONNECTOR_BASE_URL", old_base)


def test_github_rest_defaults_to_real_api() -> None:
    old_env = os.environ.get("ENV")
    old_mock = os.environ.get("VECTOR_USE_MOCK_CONNECTORS")
    get_settings.cache_clear()
    try:
        os.environ["ENV"] = "development"
        os.environ["VECTOR_USE_MOCK_CONNECTORS"] = "false"
        s = Settings()
        assert s.github_rest_api_base_url() == "https://api.github.com"
        assert s.github_rest_api_app_install_base_url() == "https://api.github.com"
        assert s.linear_graphql_url() == "https://api.linear.app/graphql"
        assert s.linear_oauth_token_url() == "https://api.linear.app/oauth/token"
        assert s.notion_api_base_url() == "https://api.notion.com/v1"
        assert s.calls_google_calendar_events_base_url() == "https://www.googleapis.com/calendar/v3"
    finally:
        get_settings.cache_clear()
        _restore("ENV", old_env)
        _restore("VECTOR_USE_MOCK_CONNECTORS", old_mock)


def _restore(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
