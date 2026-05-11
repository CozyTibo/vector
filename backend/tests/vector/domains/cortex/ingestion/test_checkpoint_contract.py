"""Phase 01 Step 7 — checkpoint schema migration + deep merge + dual cursor lanes."""

from __future__ import annotations

from vector.domains.cortex.ingestion.checkpoint_contract import (
    CHECKPOINT_MODE_BACKFILL,
    CHECKPOINT_MODE_INCREMENTAL,
    CHECKPOINT_SCHEMA_VERSION,
    checkpoint_last_incremental_at,
    merge_monotonic_connector_state,
    migrate_checkpoint_state,
)


def test_last_incremental_at_does_not_regress() -> None:
    merged = merge_monotonic_connector_state(
        {"last_incremental_at": "2026-05-07T12:00:00+00:00", "repos_fetched": 5},
        {"last_incremental_at": "2026-05-07T10:00:00+00:00", "repos_fetched": 99},
    )
    assert merged["last_incremental_at"] == "2026-05-07T12:00:00+00:00"
    assert merged["repos_fetched"] == 99


def test_repos_fetched_uses_max() -> None:
    merged = merge_monotonic_connector_state(
        {"repos_fetched": 10},
        {"repos_fetched": 3},
    )
    assert merged["repos_fetched"] == 10


def test_github_installation_repos_pages_uses_max() -> None:
    merged = merge_monotonic_connector_state(
        {"github_installation_repos_pages": 4},
        {"github_installation_repos_pages": 2},
    )
    assert merged["github_installation_repos_pages"] == 4


def test_github_pull_requests_written_uses_max() -> None:
    merged = merge_monotonic_connector_state(
        {"github_pull_requests_written": 12},
        {"github_pull_requests_written": 3},
    )
    assert merged["github_pull_requests_written"] == 12


def test_legacy_state_is_migrated_to_v2_schema() -> None:
    migrated, changed = migrate_checkpoint_state(
        {"last_incremental_at": "2026-05-08T10:00:00+00:00", "repos_fetched": 4}
    )
    assert changed is True
    assert migrated["checkpoint_schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert migrated["modes"][CHECKPOINT_MODE_INCREMENTAL]["repos_fetched"] == 4
    assert checkpoint_last_incremental_at(migrated) == "2026-05-08T10:00:00+00:00"


def test_merge_tracks_writer_lane_without_clobbering_other_mode() -> None:
    existing = {
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "modes": {
            CHECKPOINT_MODE_INCREMENTAL: {"last_incremental_at": "2026-05-08T09:00:00+00:00"},
            CHECKPOINT_MODE_BACKFILL: {"backfill_oldest_ts": "2026-04-01T00:00:00+00:00"},
        },
        "streams": {},
        "meta": {},
    }
    merged = merge_monotonic_connector_state(
        existing,
        {"last_incremental_at": "2026-05-08T11:00:00+00:00"},
        sync_mode="incremental",
    )
    assert merged["modes"][CHECKPOINT_MODE_INCREMENTAL]["last_incremental_at"] == (
        "2026-05-08T11:00:00+00:00"
    )
    assert merged["modes"][CHECKPOINT_MODE_BACKFILL]["backfill_oldest_ts"] == "2026-04-01T00:00:00+00:00"


def test_backfill_writes_to_backfill_lane() -> None:
    merged = merge_monotonic_connector_state(
        {},
        {"backfill_oldest_ts": "2026-03-01T00:00:00+00:00"},
        sync_mode="backfill",
    )
    assert merged["modes"][CHECKPOINT_MODE_BACKFILL]["backfill_oldest_ts"] == "2026-03-01T00:00:00+00:00"
    assert merged["meta"]["last_writer_mode"] == CHECKPOINT_MODE_BACKFILL


def test_invalid_existing_state_recovers_with_fresh_schema() -> None:
    merged = merge_monotonic_connector_state(
        {"checkpoint_schema_version": 999, "modes": "bad-shape"},
        {"last_incremental_at": "2026-05-08T11:00:00+00:00"},
        sync_mode="incremental",
    )
    assert merged["checkpoint_schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert isinstance(merged["modes"], dict)
    assert merged["meta"].get("migrated_from_legacy") is True
