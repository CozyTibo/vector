"""Scheduler clears orphan cortex_live pending reservations."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.ingestion.scheduler import (
    RoutedSyncJob,
    reconcile_orphan_live_queue_pending,
    select_sync_jobs_to_enqueue,
)


def test_reconcile_orphan_live_queue_pending_clears_when_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = uuid.uuid4()
    cid = uuid.uuid4()
    job = RoutedSyncJob(tenant_id=tid, connection_id=cid, connector_id="slack")
    settings = MagicMock()
    session = MagicMock()
    cleared: list[tuple[uuid.UUID, uuid.UUID]] = []

    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.is_live_queue_pending",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler._has_running_ingestion_run",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.clear_live_queue_pending",
        lambda _settings, *, tenant_id, connection_id: cleared.append((tenant_id, connection_id)),
    )

    n = reconcile_orphan_live_queue_pending(session, settings, [job])
    assert n == 1
    assert cleared == [(tid, cid)]


def test_reconcile_orphan_live_queue_pending_keeps_active_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = RoutedSyncJob(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector_id="github",
    )
    settings = MagicMock()
    session = MagicMock()

    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.is_live_queue_pending",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler._has_running_ingestion_run",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.clear_live_queue_pending",
        lambda *_a, **_k: pytest.fail("should not clear while run is active"),
    )

    assert reconcile_orphan_live_queue_pending(session, settings, [job]) == 0


def test_select_sync_jobs_reconciles_before_broker_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = MagicMock()
    session = MagicMock()
    job = RoutedSyncJob(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector_id="linear",
    )
    order: list[str] = []

    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.iter_routed_live_sync_jobs",
        lambda *_a, **_k: order.append("candidates") or [job],
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.reconcile_orphan_live_queue_pending",
        lambda *_a, **_k: order.append("reconcile") or 1,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.filter_jobs_without_broker_pending",
        lambda jobs, _settings: order.append("filter") or jobs,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.apply_per_tenant_fair_enqueue_cap",
        lambda jobs, _settings: order.append("cap") or jobs,
    )

    select_sync_jobs_to_enqueue(session, settings)
    assert order == ["candidates", "reconcile", "filter", "cap"]
