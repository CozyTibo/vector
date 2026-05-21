"""Phase 01 Step 3 — ingestion sync context (replay boundaries)."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.ingestion.sync_context import SCOPE_DEFAULT, IngestionSyncContext


def test_live_incremental_uses_default_checkpoint_scope() -> None:
    ctx = IngestionSyncContext.live_incremental()
    assert ctx.replay_mode is False
    assert ctx.checkpoint_scope_key() == SCOPE_DEFAULT


def test_replay_uses_isolated_checkpoint_scope() -> None:
    jid = uuid.uuid4()
    ctx = IngestionSyncContext.replay(replay_job_id=jid, replay_version=2)
    assert ctx.replay_mode is True
    assert ctx.checkpoint_scope_key() == f"replay:{jid}"
    assert ctx.replay_version == 2


def test_replay_requires_job_id() -> None:
    ctx = IngestionSyncContext(sync_mode="replay", replay_job_id=None, replay_version=1)
    with pytest.raises(ValueError, match="replay_job_id"):
        ctx.validate()


def test_replay_version_minimum() -> None:
    ctx = IngestionSyncContext.replay(replay_job_id=uuid.uuid4(), replay_version=0)
    with pytest.raises(ValueError, match="replay_version"):
        ctx.validate()


def test_sync_mode_must_be_allowlisted() -> None:
    ctx = IngestionSyncContext(sync_mode="incremental", replay_job_id=None, replay_version=1)
    with pytest.raises(ValueError, match="sync_mode"):
        ctx.validate()


def test_live_checkpoint_lane_incremental() -> None:
    ctx = IngestionSyncContext.live_incremental()
    assert ctx.checkpoint_sync_mode == "incremental"


def test_backfill_maps_to_live_with_backfill_lane() -> None:
    ctx = IngestionSyncContext.backfill()
    assert ctx.sync_mode == "live"
    assert ctx.checkpoint_sync_mode == "backfill"


def test_backfill_context_flags_backfill_lane() -> None:
    ctx = IngestionSyncContext.backfill()
    ctx.validate()
    assert ctx.replay_mode is False
    assert ctx.writes_backfill_lane is True
    assert ctx.checkpoint_scope_key() == SCOPE_DEFAULT
