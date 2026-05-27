"""Ingestion sync split into per-connector modules; live | replay modes."""

from __future__ import annotations

import uuid
from pathlib import Path

from vector.domains.cortex.ingestion import sync_context as sc_mod
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.domains.cortex.ingestion.sync_router import execute_connector_sync as router_execute


def test_sync_executor_shim_delegates_to_router() -> None:
    assert execute_connector_sync is router_execute


def test_sync_context_live_and_replay_only() -> None:
    live = sc_mod.IngestionSyncContext.live_incremental()
    live.validate()
    assert live.sync_mode == "live"
    assert live.checkpoint_sync_mode == "incremental"
    replay = sc_mod.IngestionSyncContext.replay(replay_job_id=uuid.uuid4())
    replay.validate()
    assert replay.sync_mode == "replay"
    backfill = sc_mod.IngestionSyncContext.backfill()
    backfill.validate()
    assert backfill.sync_mode == "live"
    assert backfill.backfill_lane is True
    assert backfill.checkpoint_sync_mode == "backfill"


def test_connector_sync_modules_exist() -> None:
    root = Path(__file__).resolve().parents[5] / "src/vector/domains/cortex/ingestion/connectors"
    for name in ("github", "linear", "slack", "notion", "calls"):
        assert (root / name / "sync.py").is_file()
