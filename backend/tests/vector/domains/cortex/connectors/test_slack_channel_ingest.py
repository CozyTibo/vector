"""Tests for Slack admin ingest channel selection helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.connectors.slack.channel_ingest import (
    _catalog_is_fresh,
    _channel_catalog_cached_only,
    _parse_saved_channels,
    _resolve_channel_catalog,
    get_saved_ingest_channel_ids,
)
from vector.domains.cortex.connectors.slack.errors import SlackWebApiError


def test_parse_saved_channels() -> None:
    raw = {
        "channels": [
            {"channel_id": "C1", "name": "general"},
            {"id": "C2", "name": "random"},
        ]
    }
    assert _parse_saved_channels(raw) == [
        {"channel_id": "C1", "name": "general"},
        {"channel_id": "C2", "name": "random"},
    ]


def test_get_saved_ingest_channel_ids() -> None:
    detail = SimpleNamespace(
        ingest_channels_json={"channels": [{"channel_id": "C99", "name": "eng"}]}
    )
    assert get_saved_ingest_channel_ids(detail) == ["C99"]


def test_catalog_is_fresh() -> None:
    now = datetime.now(UTC)
    detail = SimpleNamespace(
        channel_catalog_fetched_at=now - timedelta(seconds=30),
        channel_catalog_json={"channels": [{"channel_id": "C1", "name": "a"}]},
    )
    assert _catalog_is_fresh(detail, now=now, ttl_seconds=900) is True


def test_resolve_channel_catalog_uses_cache_without_live_call(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(UTC)
    detail = SimpleNamespace(
        bot_access_token="xoxb-test",
        channel_catalog_fetched_at=now - timedelta(seconds=10),
        channel_catalog_json={
            "channels": [
                {
                    "channel_id": "C1",
                    "name": "general",
                    "is_private": False,
                    "is_member": True,
                    "selected_for_ingest": False,
                    "can_bot_join": True,
                }
            ]
        },
        ingest_channels_json={"channels": []},
        team_id="T1",
        team_name="Test",
    )
    connection = SimpleNamespace(id=uuid.uuid4())
    link = SimpleNamespace(detail=detail, connection=connection, tenant_id=uuid.uuid4())
    db = MagicMock()
    settings = SimpleNamespace(
        cortex_slack_admin_channel_catalog_ttl_seconds=900,
        cortex_slack_admin_channel_catalog_max_pages=15,
        cortex_slack_conversation_types="public_channel",
        vector_use_mock_connectors=False,
    )

    def _boom(*_a: object, **_k: object) -> dict[str, dict[str, object]]:
        raise SlackWebApiError("should_not_call")

    monkeypatch.setattr(
        "vector.domains.cortex.connectors.slack.channel_ingest._fetch_slack_channel_catalog_live",
        _boom,
    )

    by_id, stale, _fetched = _resolve_channel_catalog(db, link, settings=settings, force_refresh=False)
    assert stale is False
    assert "C1" in by_id
    assert by_id["C1"]["name"] == "general"


def test_channel_catalog_cached_only_never_calls_live(monkeypatch: pytest.MonkeyPatch) -> None:
    detail = SimpleNamespace(
        channel_catalog_json={
            "channels": [
                {
                    "channel_id": "C1",
                    "name": "general",
                    "is_private": False,
                    "is_member": True,
                    "selected_for_ingest": False,
                    "can_bot_join": True,
                }
            ]
        },
        ingest_channels_json={"channels": []},
    )
    link = SimpleNamespace(
        detail=detail,
        connection=SimpleNamespace(id=uuid.uuid4()),
        tenant_id=uuid.uuid4(),
    )
    db = MagicMock()

    def _boom(*_a: object, **_k: object) -> dict[str, dict[str, object]]:
        raise SlackWebApiError("should_not_call")

    monkeypatch.setattr(
        "vector.domains.cortex.connectors.slack.channel_ingest._fetch_slack_channel_catalog_live",
        _boom,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.connectors.slack.channel_ingest._channel_catalog_from_raw_ingest",
        _boom,
    )

    by_id = _channel_catalog_cached_only(db, link)
    assert "C1" in by_id
