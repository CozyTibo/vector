"""Scheduler skips enqueue when a run is already in flight."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.ingestion.scheduler import (
    _has_running_ingestion_run,
    iter_routed_live_sync_jobs,
)


def test_has_running_ingestion_run_true_when_running_row() -> None:
    session = MagicMock()
    session.scalar.return_value = uuid.uuid4()
    assert _has_running_ingestion_run(
        session,
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector_id="slack",
    )


def test_iter_routed_live_sync_jobs_skips_in_flight(monkeypatch) -> None:
    tc = MagicMock()
    tc.tenant_id = uuid.uuid4()
    tc.id = uuid.uuid4()
    tc.provider = "slack"
    tc.status = "active"

    settings = MagicMock()
    settings.cortex_ingestion_scheduler_enabled = True

    session = MagicMock()
    session.scalars.return_value.all.return_value = [tc]

    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.should_route_ingestion_to_cortex",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler._past_min_gap",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler._has_running_ingestion_run",
        lambda *_a, **_k: True,
    )

    assert iter_routed_live_sync_jobs(session, settings) == []
