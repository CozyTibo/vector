"""Tests for Slack admin ingest channel selection helpers."""

from __future__ import annotations

from types import SimpleNamespace

from vector.domains.cortex.connectors.slack.channel_ingest import (
    _parse_saved_channels,
    get_saved_ingest_channel_ids,
)


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
