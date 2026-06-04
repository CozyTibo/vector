"""Scheduler broker-pending filter and per-tenant fair enqueue cap."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.ingestion.scheduler import (
    RoutedSyncJob,
    apply_per_tenant_fair_enqueue_cap,
    filter_jobs_without_broker_pending,
)


def test_apply_per_tenant_fair_enqueue_cap_round_robin() -> None:
    tenant_a = uuid.UUID("00000000-0000-4000-8000-000000000001")
    tenant_b = uuid.UUID("00000000-0000-4000-8000-000000000002")
    jobs = [
        RoutedSyncJob(tenant_a, uuid.uuid4(), "github"),
        RoutedSyncJob(tenant_a, uuid.uuid4(), "linear"),
        RoutedSyncJob(tenant_a, uuid.uuid4(), "slack"),
        RoutedSyncJob(tenant_b, uuid.uuid4(), "github"),
        RoutedSyncJob(tenant_b, uuid.uuid4(), "slack"),
    ]
    settings = MagicMock()
    settings.cortex_ingestion_scheduler_max_jobs_per_tenant_per_tick = 1

    out = apply_per_tenant_fair_enqueue_cap(jobs, settings)
    assert len(out) == 2
    assert out[0].tenant_id == tenant_a
    assert out[0].connector_id == "github"
    assert out[1].tenant_id == tenant_b
    assert out[1].connector_id == "github"


def test_apply_per_tenant_fair_enqueue_cap_respects_max_per_tenant() -> None:
    tenant_a = uuid.UUID("00000000-0000-4000-8000-000000000003")
    jobs = [
        RoutedSyncJob(tenant_a, uuid.uuid4(), "github"),
        RoutedSyncJob(tenant_a, uuid.uuid4(), "linear"),
        RoutedSyncJob(tenant_a, uuid.uuid4(), "slack"),
    ]
    settings = MagicMock()
    settings.cortex_ingestion_scheduler_max_jobs_per_tenant_per_tick = 2

    out = apply_per_tenant_fair_enqueue_cap(jobs, settings)
    assert len(out) == 2
    assert all(j.tenant_id == tenant_a for j in out)
    assert [j.connector_id for j in out] == ["github", "linear"]


def test_filter_jobs_without_broker_pending(monkeypatch) -> None:
    pending_tid = uuid.uuid4()
    pending_cid = uuid.uuid4()
    free = RoutedSyncJob(uuid.uuid4(), uuid.uuid4(), "slack")
    blocked = RoutedSyncJob(pending_tid, pending_cid, "github")

    def _is_pending(_settings: object, *, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> bool:
        return tenant_id == pending_tid and connection_id == pending_cid

    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.scheduler.is_live_queue_pending",
        _is_pending,
    )
    out = filter_jobs_without_broker_pending([blocked, free], MagicMock())
    assert out == [free]
