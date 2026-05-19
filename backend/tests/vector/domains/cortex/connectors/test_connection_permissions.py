"""Unit tests for connector permission diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

from vector.domains.cortex.connectors.connection_permissions import (
    slack_permission_snapshot,
)


def _settings_stub() -> MagicMock:
    return MagicMock()


def test_slack_warns_when_history_scopes_missing() -> None:
    snap = slack_permission_snapshot(
        _settings_stub(),
        granted_scope="channels:read,users:read,chat:write",
        connected=True,
        requested_scopes_override="channels:read,users:read,chat:write",
    )
    assert snap.ingest_health == "warn"
    assert "channels:history" in snap.missing_recommended
    assert "groups:history" in snap.missing_recommended


def test_slack_ok_when_ingest_scopes_granted() -> None:
    snap = slack_permission_snapshot(
        _settings_stub(),
        granted_scope="channels:read,channels:history,groups:history,users:read",
        connected=True,
        requested_scopes_override="channels:read,channels:history,groups:history,users:read",
    )
    assert snap.ingest_health == "ok"
    assert snap.missing_recommended == []


def test_slack_warns_when_user_granted_fewer_than_requested() -> None:
    snap = slack_permission_snapshot(
        _settings_stub(),
        granted_scope="channels:read,users:read",
        connected=True,
        requested_scopes_override="channels:read,channels:history,users:read",
    )
    assert snap.ingest_health == "warn"
    assert "channels:history" in snap.missing_requested
