"""Phase 1 step 1.4 — P1-D TCRE resume integration (CONT-INV-04)."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import (
    get_tenant_execution_lease_v1,
    mark_tenant_waiting_v1,
)
from vector.domains.cortex.execution.scheduling import (
    verify_execution_hot_path_no_continuation_boundary_v1,
    verify_single_tcre_execution_resume_boundary_v1,
    verify_tcre_worker_no_retrieval_materialization_boundary_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_WAITING,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.domains.cortex.substrate_pipeline.continuity_p1_tcre import (
    evaluate_p1_4_tcre_resume_proof_v1,
    verify_p1_d_static_boundaries_v1,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    on_tcre_job_completed_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1


def test_p1_d_static_boundaries_green() -> None:
    assert verify_single_tcre_execution_resume_boundary_v1() == []
    assert verify_execution_hot_path_no_continuation_boundary_v1() == []
    assert verify_tcre_worker_no_retrieval_materialization_boundary_v1() == []
    audit = verify_p1_d_static_boundaries_v1()
    assert audit["static_boundaries_ok"] is True
    assert audit["errors"] == []


def test_p1_d_celery_task_wires_pipeline_resume_on_completed() -> None:
    import app.tasks.cortex_tcre_reconstruction_jobs as tcre_jobs

    src = inspect.getsource(tcre_jobs.run_tcre_reconstruction_job_task)
    assert "on_tcre_job_completed_for_pipeline_v1" in src
    assert "materialize_retrieval" not in src


def test_p1_4_proof_evaluator_pass() -> None:
    proof = evaluate_p1_4_tcre_resume_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        static_boundaries={"static_boundaries_ok": True},
        footprint={
            "pipeline_run_id": "ce7df86d-b229-4467-ad28-1109ed119d34",
            "lease_pipeline_run_id": "ce7df86d-b229-4467-ad28-1109ed119d34",
            "phase_06_status": "completed",
            "phase_06_async": True,
            "phase_06_job_id": "job-1",
            "tcre_jobs_total": 3,
            "lease_status": "dirty",
            "lease_fsm_state": "RETRIEVAL",
            "lease_phase_cursor": PHASE_07_RETRIEVAL,
            "waiting_reason": "tcre_async",
            "resumed_from_waiting_at": "2026-05-22T22:00:00+00:00",
        },
        integration_tests_green=True,
        deploy_recorded_at=datetime(2026, 5, 22, 23, 0, 0, tzinfo=UTC),
    )
    assert proof["p1_4_pass"] is True


def test_p1_4_proof_evaluator_pass_execution_past_tcre() -> None:
    proof = evaluate_p1_4_tcre_resume_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        static_boundaries={"static_boundaries_ok": True},
        footprint={
            "lease_pipeline_run_id": "ce7df86d-b229-4467-ad28-1109ed119d34",
            "phase_06_status": "completed",
            "phase_06_async": True,
            "phase_06_job_id": "job-1",
            "tcre_jobs_total": 3,
            "lease_phase_cursor": "phase_08_synthesis",
            "waiting_reason": "tcre_async",
        },
        integration_tests_green=True,
        trace_only=True,
    )
    assert proof["p1_4_pass"] is True


def test_p1_4_proof_evaluator_fails_without_boundaries() -> None:
    proof = evaluate_p1_4_tcre_resume_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": False}},
        static_boundaries={"static_boundaries_ok": False},
        footprint={"tcre_jobs_total": 0},
        integration_tests_green=False,
    )
    assert proof["p1_4_pass"] is False


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p14-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P1-D TCRE",
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
def test_p1_d_phase06_waiting_tcre_terminal_resumes_phase07(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """phase 06 → mark_tenant_waiting → TCRE terminal → resume at phase 07 (no continuation)."""
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p14-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    mark_tenant_waiting_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_cursor=PHASE_07_RETRIEVAL,
        waiting_reason="tcre_async",
    )
    lease_before = get_tenant_execution_lease_v1(db_session, tenant_id=tenant.id)
    assert lease_before is not None
    assert lease_before.status == LEASE_STATUS_WAITING
    assert lease_before.fsm_state == FSM_AWAITING_TCRE
    assert lease_before.phase_cursor == PHASE_07_RETRIEVAL

    continuation_calls: list[dict[str, object]] = []

    def _capture_continuation(**kwargs: object) -> dict[str, str]:
        continuation_calls.append(kwargs)
        return {"phase_id": PHASE_07_RETRIEVAL}

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.enqueue_next_pipeline_phase_v1",
        _capture_continuation,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.execution.tcre_resume.enqueue_tenant_convergence_v1",
        lambda *_a, **_k: {"enqueued": True, "reason": "tcre_complete"},
    )

    out = on_tcre_job_completed_for_pipeline_v1(
        db_session,
        tenant_id=tenant.id,
        job_scope={"substrate_pipeline_run_id": str(run.id)},
        tcre_job_id=job_id,
        tcre_job_status="completed",
    )
    assert out is not None
    assert out.get("resumed") is True
    assert out.get("path") == "convergence_lease"
    assert continuation_calls == []

    lease_after = get_tenant_execution_lease_v1(db_session, tenant_id=tenant.id)
    assert lease_after is not None
    assert lease_after.status == LEASE_STATUS_DIRTY
    assert lease_after.fsm_state != FSM_AWAITING_TCRE
    assert lease_after.phase_cursor == PHASE_07_RETRIEVAL
    assert str(lease_after.pipeline_run_id) == str(run.id)
    assert (lease_after.detail_json or {}).get("resumed_from_waiting_at")
