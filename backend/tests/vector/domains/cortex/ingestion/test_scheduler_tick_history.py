"""Ingestion Beat history helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

from vector.domains.cortex.ingestion.scheduler_tick_history import (
    _connector_debrief_row,
    _tenant_jobs_from_tick,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.ingestion_scheduler_tick import IngestionSchedulerTick


def test_tenant_jobs_from_tick_filters_by_tenant() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    tick = IngestionSchedulerTick(
        id=uuid.uuid4(),
        started_at=datetime.now(tz=UTC),
        outcome="enqueued",
        beat_interval_seconds=120,
        enqueued_jobs=[
            {"tenant_id": str(tenant_a), "connector_id": "slack"},
            {"tenant_id": str(tenant_b), "connector_id": "github"},
        ],
    )
    jobs = _tenant_jobs_from_tick(tick, tenant_a)
    assert len(jobs) == 1
    assert jobs[0]["connector_id"] == "slack"


def test_connector_debrief_row_queued_without_run() -> None:
    session = MagicMock()
    row = _connector_debrief_row(session, connector="linear", run=None, enqueued=True)
    assert row["status"] == "queued"
    assert row["records_written"] is None
    assert row["enqueued"] is True


def test_connector_debrief_row_with_run_and_breakdown() -> None:
    run_id = uuid.uuid4()
    run = IngestionRun(
        id=run_id,
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="notion",
        source_trigger="scheduled_lane",
        status="completed",
        started_at=datetime.now(tz=UTC),
        stats={"records_written": 5},
    )
    session = MagicMock()
    session.execute.return_value.all.return_value = [("page", 5)]
    row = _connector_debrief_row(session, connector="notion", run=run, enqueued=True)
    assert row["records_written"] == 5
    assert row["resource_breakdown"] == [{"resource_type": "page", "count": 5}]
