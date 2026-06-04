"""Phase 01 Step 2 — ingestion-only Beat scheduler tick."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


def _patch_scheduler_sessions(monkeypatch: pytest.MonkeyPatch, sched_mod: object) -> uuid.UUID:
    tick_id = uuid.uuid4()

    @contextmanager
    def _fake_session_scope():
        session = MagicMock()

        def _add(obj: object) -> None:
            if hasattr(obj, "id"):
                setattr(obj, "id", tick_id)

        session.add = _add
        session.flush = MagicMock()
        session.get = MagicMock(return_value=MagicMock(id=tick_id))
        yield session

    monkeypatch.setattr(sched_mod, "session_scope", _fake_session_scope)
    monkeypatch.setattr(sched_mod, "complete_scheduler_tick_v1", lambda *_a, **_k: None)
    return tick_id


def test_scheduler_tick_noops_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "false")

    import app.tasks.cortex_ingestion_scheduler as sched_mod
    from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

    tick_id = _patch_scheduler_sessions(monkeypatch, sched_mod)

    out = tick_cortex_ingestion_scheduler()
    assert out.get("skipped") is True
    assert out.get("enqueued") == 0
    assert out.get("tick_id") == str(tick_id)


def test_scheduler_tick_skips_when_operator_pause_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "true")

    import app.tasks.cortex_ingestion_scheduler as sched_mod
    from vector.settings import get_settings

    tick_id = _patch_scheduler_sessions(monkeypatch, sched_mod)
    get_settings.cache_clear()
    try:
        monkeypatch.setattr(sched_mod, "read_scheduler_paused_flag", lambda _settings: True)
        from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

        out = tick_cortex_ingestion_scheduler()
        assert out["enqueued"] == 0
        assert out["skipped"] is True
        assert out["reason"] == "scheduler_paused_operator_redis"
        assert out["tick_id"] == str(tick_id)
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

    calls: list[tuple[list[str], dict[str, str], str]] = []

    class _DummyTask:
        def apply_async(
            self,
            *,
            args: list[str],
            kwargs: dict[str, str] | None = None,
            queue: str,
        ) -> None:
            calls.append((args, kwargs or {}, queue))

    tid = uuid.uuid4()
    cid = uuid.uuid4()
    tick_id = _patch_scheduler_sessions(monkeypatch, sched_mod)
    monkeypatch.setattr(sched_mod, "read_scheduler_paused_flag", lambda _settings: False)
    monkeypatch.setattr(
        sched_mod,
        "select_sync_jobs_to_enqueue",
        lambda _session, _settings: (
            [RoutedSyncJob(tenant_id=tid, connection_id=cid, connector_id="slack")],
            [RoutedSyncJob(tenant_id=tid, connection_id=cid, connector_id="slack")],
        ),
    )
    monkeypatch.setattr(sched_mod, "reserve_live_queue_pending", lambda *_a, **_k: True)
    monkeypatch.setattr("app.tasks.cortex_ingestion_sync.run_cortex_connector_sync_task", _DummyTask())

    get_settings.cache_clear()
    try:
        out = sched_mod.tick_cortex_ingestion_scheduler()
        assert out["enqueued"] == 1
        assert out["tick_id"] == str(tick_id)
        assert len(calls) == 1
        args, kwargs, queue = calls[0]
        assert queue == "cortex_live"
        assert args == [str(tid), "slack", "scheduled_lane", "incremental", str(cid)]
        assert kwargs["scheduler_tick_id"] == str(tick_id)
    finally:
        get_settings.cache_clear()
