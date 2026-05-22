"""P0-C — continuity pipeline recovery (step 0.3)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_QUEUED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_RUNNING,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    mirror_completed_phases_between_runs_v1,
    recover_continuity_p0_pipeline_v1,
    reopen_failed_pipeline_run_v1,
    requeue_pipeline_phases_from_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    create_pipeline_run_v1,
    fail_phase_v1,
    get_phase_run_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.tenant import Tenant


@pytest.fixture
def tenant(db_session: Session) -> Tenant:
    slug = f"p0c-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P0C",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_reopen_failed_run_requeues_downstream_phases(db_session: Session, tenant: Tenant) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"test-{uuid.uuid4()}",
    )
    for phase_id in (PHASE_02_CANONICAL, PHASE_03_IDENTITY, PHASE_04_GRAPH):
        phase = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=phase_id)
        assert phase is not None
        phase.status = PHASE_STATUS_COMPLETED
    fail_phase_v1(
        db_session,
        pipeline_run_id=run.id,
        phase_id=PHASE_05_TRAVERSAL,
        error="schema missing",
    )
    db_session.refresh(run)
    assert run.status == PIPELINE_STATUS_FAILED

    out = reopen_failed_pipeline_run_v1(
        db_session,
        pipeline_run_id=run.id,
        resume_from_phase=PHASE_05_TRAVERSAL,
    )
    assert out["reopened"] is True
    db_session.refresh(run)
    assert run.status == PIPELINE_STATUS_RUNNING

    p05 = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=PHASE_05_TRAVERSAL)
    p06 = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=PHASE_06_TCRE)
    assert p05 is not None and p05.status == PHASE_STATUS_QUEUED
    assert p06 is not None and p06.status == PHASE_STATUS_QUEUED


def test_mirror_completed_phases(db_session: Session, tenant: Tenant) -> None:
    src = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"src-{uuid.uuid4()}",
    )
    dst = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"dst-{uuid.uuid4()}",
    )
    for phase_id in (PHASE_02_CANONICAL, PHASE_03_IDENTITY):
        phase = get_phase_run_v1(db_session, pipeline_run_id=src.id, phase_id=phase_id)
        assert phase is not None
        phase.status = PHASE_STATUS_COMPLETED
        phase.output_json = {"substrate_phase_receipt": {"phase_id": phase_id, "outcome": "ok", "receipt_hash": "x"}}
    db_session.flush()

    mirrored = mirror_completed_phases_between_runs_v1(
        db_session,
        source_pipeline_run_id=src.id,
        dest_pipeline_run_id=dst.id,
    )
    assert mirrored == [PHASE_02_CANONICAL, PHASE_03_IDENTITY]
    p02 = get_phase_run_v1(db_session, pipeline_run_id=dst.id, phase_id=PHASE_02_CANONICAL)
    assert p02 is not None and p02.status == PHASE_STATUS_COMPLETED


def test_recover_new_run_mirrors_and_enqueues(
    db_session: Session,
    tenant: Tenant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"fail-{uuid.uuid4()}",
    )
    for phase_id in (PHASE_02_CANONICAL, PHASE_03_IDENTITY, PHASE_04_GRAPH):
        phase = get_phase_run_v1(db_session, pipeline_run_id=failed.id, phase_id=phase_id)
        assert phase is not None
        phase.status = PHASE_STATUS_COMPLETED
    fail_phase_v1(db_session, pipeline_run_id=failed.id, phase_id=PHASE_05_TRAVERSAL, error="x")
    db_session.flush()

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.continuity_p0_recovery.enqueue_execution_slice_at_phase_v1",
        lambda **_k: {"scheduled": True, "task_id": "test"},
    )

    out = recover_continuity_p0_pipeline_v1(
        db_session,
        tenant_id=tenant.id,
        strategy="new_run",
        source_pipeline_run_id=failed.id,
    )
    assert out["recovered"] is True
    assert out["pipeline_run_id"] != str(failed.id)
    assert PHASE_04_GRAPH in out["mirrored_phases"]
    assert PHASE_05_TRAVERSAL in out["requeued_phases"]
    new_run = db_session.get(CortexSubstratePipelineRun, uuid.UUID(out["pipeline_run_id"]))
    assert new_run is not None
    assert new_run.status == PIPELINE_STATUS_RUNNING
