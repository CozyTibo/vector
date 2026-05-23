"""Phase B6 — fresh pipeline run after graph change."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_QUEUED,
    PIPELINE_STATUS_PARTIAL,
    PIPELINE_STATUS_RUNNING,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    mirror_completed_phases_between_runs_v1,
    recover_continuity_p0_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.post_ingestion_fresh_pipeline_run import (
    resolve_pipeline_run_id_after_phase04_v1,
    start_fresh_pipeline_run_after_graph_change_v1,
    supersede_pipeline_run_for_graph_change_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    create_pipeline_run_v1,
    get_phase_run_v1,
)


@pytest.mark.integration
def test_supersede_running_pipeline_marks_partial(db_session, tenant) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"old-{uuid.uuid4()}",
    )
    run.status = PIPELINE_STATUS_RUNNING
    db_session.flush()
    out = supersede_pipeline_run_for_graph_change_v1(
        db_session,
        pipeline_run_id=run.id,
        superseded_by_pipeline_run_id=uuid.uuid4(),
    )
    assert out["superseded"] is True
    db_session.refresh(run)
    assert run.status == PIPELINE_STATUS_PARTIAL
    assert run.summary_json.get("superseded") is True


@pytest.mark.integration
def test_fresh_run_does_not_mirror_phases(db_session, tenant) -> None:
    old = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"old-{uuid.uuid4()}",
    )
    old.status = PIPELINE_STATUS_RUNNING
    for phase_id in (PHASE_03_IDENTITY, PHASE_04_GRAPH):
        phase = get_phase_run_v1(db_session, pipeline_run_id=old.id, phase_id=phase_id)
        assert phase is not None
        phase.status = PHASE_STATUS_COMPLETED
        phase.output_json = {"mirrored": True}
    db_session.flush()

    out = start_fresh_pipeline_run_after_graph_change_v1(
        db_session,
        tenant_id=tenant.id,
        graph_projection_stable_hash="hash-b6-test",
        prior_pipeline_run_id=old.id,
    )
    assert out["started"] is True
    fresh_id = uuid.UUID(str(out["fresh_pipeline_run_id"]))
    assert fresh_id != old.id
    for phase_id in (PHASE_03_IDENTITY, PHASE_04_GRAPH, PHASE_05_TRAVERSAL):
        phase = get_phase_run_v1(db_session, pipeline_run_id=fresh_id, phase_id=phase_id)
        assert phase is not None
        assert phase.status == PHASE_STATUS_QUEUED
        assert phase.output_json == {}

    mirrored = mirror_completed_phases_between_runs_v1(
        db_session,
        source_pipeline_run_id=old.id,
        dest_pipeline_run_id=fresh_id,
    )
    assert mirrored  # explicit mirror still works when opted in
    recover = recover_continuity_p0_pipeline_v1(
        db_session,
        tenant_id=tenant.id,
        strategy="new_run",
        mirror_completed_phases=False,
    )
    assert recover.get("mirrored_phases") == []


def test_resolve_pipeline_run_after_phase04_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    current = uuid.uuid4()
    fresh = uuid.uuid4()
    out = {
        "event_trigger_graph_hash": {
            "fresh_pipeline_run_id": str(fresh),
            "resume_from_phase": PHASE_03_IDENTITY,
        }
    }
    new_id, switch = resolve_pipeline_run_id_after_phase04_v1(out, current_pipeline_run_id=current)
    assert new_id == fresh
    assert switch["switched"] is True


@pytest.fixture
def tenant(db_session):
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"b6-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="B6",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.mark.integration
def test_trigger_starts_fresh_run_on_hash_change(
    db_session,
    tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "schedule_octs_walks_for_tenant_v1",
        lambda **_k: {"scheduled": True},
    )
    from vector.domains.cortex.execution.execution_event_triggers import (
        DETAIL_KEY_LAST_GRAPH_HASH_V1,
        get_tenant_execution_lease_v1,
        trigger_graph_hash_walk_schedule_v1,
    )

    lease = get_tenant_execution_lease_v1(db_session, tenant_id=tenant.id)
    if lease is not None:
        detail = dict(lease.detail_json or {})
        detail[DETAIL_KEY_LAST_GRAPH_HASH_V1] = "stale-for-b6"
        lease.detail_json = detail
        db_session.flush()

    old = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"old-{uuid.uuid4()}",
    )
    old.status = PIPELINE_STATUS_RUNNING
    db_session.flush()

    trigger = trigger_graph_hash_walk_schedule_v1(
        db_session,
        tenant_id=tenant.id,
        graph_projection_stable_hash="new-hash-value-b6",
        pipeline_run_id=old.id,
    )
    assert trigger.get("hash_changed") is True
    assert trigger.get("no_phase_mirror") is True
    assert trigger.get("fresh_pipeline_run_id")
    assert str(trigger["fresh_pipeline_run_id"]) != str(old.id)
