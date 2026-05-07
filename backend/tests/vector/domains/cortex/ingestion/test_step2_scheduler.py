"""Phase 01 Step 2 — scheduler tick (disabled path needs no DB)."""

from __future__ import annotations

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
