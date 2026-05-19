"""Phase 01 Step 2 — scheduler tick (disabled path needs no DB)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


def test_scheduler_tick_noops_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "false")

    from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

    out = tick_cortex_ingestion_scheduler()
    assert out.get("skipped") is True
    assert out.get("enqueued") == 0


def test_scheduler_tick_skips_when_operator_pause_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "true")

    import app.tasks.cortex_ingestion_scheduler as sched_mod
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(sched_mod, "read_scheduler_paused_flag", lambda _settings: True)
        from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

        out = tick_cortex_ingestion_scheduler()
        assert out == {
            "enqueued": 0,
            "skipped": True,
            "reason": "scheduler_paused_operator_redis",
        }
    finally:
        get_settings.cache_clear()


def test_scheduler_tick_passes_connection_scope_to_sync_task(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "true")

    import app.tasks.cortex_ingestion_scheduler as sched_mod
    from vector.domains.cortex.ingestion.scheduler import RoutedSyncJob
    from vector.settings import get_settings

    calls: list[tuple[list[str], str]] = []

    class _DummyTask:
        def apply_async(self, *, args: list[str], queue: str) -> None:
            calls.append((args, queue))

    @contextmanager
    def _fake_session_scope():
        yield object()

    tid = uuid.uuid4()
    cid = uuid.uuid4()
    monkeypatch.setattr(sched_mod, "read_scheduler_paused_flag", lambda _settings: False)
    monkeypatch.setattr(
        sched_mod,
        "iter_routed_live_sync_jobs",
        lambda _session, _settings: [RoutedSyncJob(tenant_id=tid, connection_id=cid, connector_id="slack")],
    )
    monkeypatch.setattr(sched_mod, "session_scope", _fake_session_scope)
    monkeypatch.setattr("app.tasks.cortex_ingestion_sync.run_cortex_connector_sync_task", _DummyTask())

    schedule_mock = MagicMock()
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.schedule_post_ingestion_substrate_refresh",
        schedule_mock,
    )

    get_settings.cache_clear()
    try:
        out = sched_mod.tick_cortex_ingestion_scheduler()
        assert out["enqueued"] == 1
        assert out.get("substrate_refresh_note") == "scheduled_on_incremental_sync_complete_only"
        assert len(calls) == 1
        args, queue = calls[0]
        assert queue == "cortex_live"
        assert args == [str(tid), "slack", "scheduled_lane", "incremental", str(cid)]
        schedule_mock.assert_not_called()
    finally:
        get_settings.cache_clear()
