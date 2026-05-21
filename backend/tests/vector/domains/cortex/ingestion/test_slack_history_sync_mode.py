"""Slack channel history sync-mode and time-bound helpers."""

from __future__ import annotations

from vector.domains.cortex.ingestion.sync_executor import (
    _slack_channel_history_sync_mode,
    _slack_history_pages_done,
    _slack_history_time_bounds,
)


def test_admin_selected_channel_stays_in_backfill_until_complete() -> None:
    ingest_ids = {"C1"}
    assert (
        _slack_channel_history_sync_mode(
            ctx_sync_mode="incremental",
            channel_id="C1",
            ingest_channel_ids=ingest_ids,
            existing_history={"last_message_ts": "100.0001", "next_cursor": "cur"},
        )
        == "backfill"
    )
    assert (
        _slack_channel_history_sync_mode(
            ctx_sync_mode="incremental",
            channel_id="C1",
            ingest_channel_ids=ingest_ids,
            existing_history={
                "backfill_complete": True,
                "cumulative_history_pages": 5,
                "last_message_ts": "100.0001",
            },
        )
        == "incremental"
    )


def test_backfill_resume_uses_latest_when_cursor_absent() -> None:
    oldest, latest = _slack_history_time_bounds(
        sync_mode="backfill",
        existing_history={"last_message_ts": "200.5"},
        history_cursor=None,
        backfill_oldest_ts="",
    )
    assert oldest is None
    assert latest == "200.5"


def test_shallow_backfill_complete_reopens_for_deeper_history() -> None:
    ingest_ids = {"C1"}
    assert (
        _slack_channel_history_sync_mode(
            ctx_sync_mode="incremental",
            channel_id="C1",
            ingest_channel_ids=ingest_ids,
            existing_history={
                "backfill_complete": True,
                "history_pages_at_complete": 1,
                "last_message_ts": "100.1",
            },
        )
        == "backfill"
    )
    assert (
        _slack_channel_history_sync_mode(
            ctx_sync_mode="incremental",
            channel_id="C1",
            ingest_channel_ids=ingest_ids,
            existing_history={
                "backfill_complete": True,
                "cumulative_history_pages": 12,
                "last_message_ts": "100.1",
            },
        )
        == "incremental"
    )


def test_backfill_exhausted_stays_incremental() -> None:
    assert (
        _slack_channel_history_sync_mode(
            ctx_sync_mode="incremental",
            channel_id="C1",
            ingest_channel_ids={"C1"},
            existing_history={"backfill_complete": True, "backfill_exhausted": True},
        )
        == "incremental"
    )


def test_history_pages_done_prefers_cumulative() -> None:
    assert _slack_history_pages_done({"cumulative_history_pages": 9}) == 9


def test_incremental_uses_oldest_for_new_messages() -> None:
    oldest, latest = _slack_history_time_bounds(
        sync_mode="incremental",
        existing_history={"last_message_ts": "300.1"},
        history_cursor=None,
        backfill_oldest_ts="",
    )
    assert oldest == "300.1"
    assert latest is None


def test_incremental_ignores_backfill_cursor_in_time_bounds() -> None:
    """With a cursor, backfill paging omits oldest/latest; incremental must not use that path."""
    oldest, latest = _slack_history_time_bounds(
        sync_mode="incremental",
        existing_history={"last_message_ts": "300.1", "next_cursor": "cursor-backfill"},
        history_cursor="cursor-backfill",
        backfill_oldest_ts="",
    )
    assert oldest == "300.1"
    assert latest is None
