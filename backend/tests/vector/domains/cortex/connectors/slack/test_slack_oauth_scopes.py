"""Slack OAuth authorize URL must request identity-critical scopes."""

from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import pytest

from vector.domains.cortex.connectors.slack.oauth_flow import start_slack_oauth_url
from vector.settings import Settings, get_settings


@pytest.fixture
def slack_oauth_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("VECTOR_SETTINGS_SKIP_DOTENV", "1")
    monkeypatch.setenv("SLACK_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("SLACK_CALLBACK_URL", "https://example.com/slack/callback")
    monkeypatch.delenv("SLACK_BOT_SCOPES", raising=False)
    get_settings.cache_clear()
    return get_settings()


def test_start_slack_oauth_url_requests_users_read_email(slack_oauth_settings: Settings) -> None:
    url = start_slack_oauth_url(
        slack_oauth_settings,
        uuid.uuid4(),
        uuid.uuid4(),
    )
    parsed = urlparse(url)
    assert parsed.netloc == "slack.com"
    assert parsed.path == "/oauth/v2/authorize"
    scopes = parse_qs(parsed.query)["scope"][0].split(",")
    assert "users:read.email" in scopes
    assert "users:read" in scopes
