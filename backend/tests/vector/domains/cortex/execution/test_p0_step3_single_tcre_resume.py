"""P0 step 3 — single TCRE resume path via execution lease (no continuation enqueue)."""

from __future__ import annotations

import inspect
import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import (
    get_tenant_execution_lease_v1,
    mark_tenant_waiting_v1,
)
from vector.domains.cortex.execution.scheduling import verify_p0_step3_single_tcre_resume_path_v1
from vector.domains.cortex.execution.tenant_constants import FSM_AWAITING_TCRE, LEASE_STATUS_DIRTY
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.domains.cortex.substrate_pipeline.orchestrator import on_tcre_job_completed_for_pipeline_v1
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p0s3-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P0 Step 3 TCRE Resume",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_verify_p0_step3_single_tcre_resume_path() -> None:
    assert verify_p0_step3_single_tcre_resume_path_v1() == []


def test_tcre_resume_module_has_no_continuation_coupling() -> None:
    from vector.domains.cortex.execution import tcre_resume as mod

    src = inspect.getsource(mod.on_tcre_job_terminal_for_execution_v1)
    assert "resume_pipeline_after_tcre_completion_v1" not in src
    assert "resume_convergence_from_waiting_v1" in src
    assert "enqueue_tenant_convergence_v1" in src


@pytest.mark.integration
def test_on_tcre_pipeline_resumes_via_execution_lease_only(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p0s3-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    mark_tenant_waiting_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_cursor=PHASE_07_RETRIEVAL,
        waiting_reason="tcre_async",
    )

    enqueue_calls: list[dict[str, object]] = []

    def _capture_enqueue(**kwargs: object) -> dict[str, str]:
        enqueue_calls.append(kwargs)
        return {"phase_id": PHASE_07_RETRIEVAL}

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.enqueue_next_pipeline_phase_v1",
        _capture_enqueue,
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
    assert enqueue_calls == []

    lease = get_tenant_execution_lease_v1(db_session, tenant_id=tenant.id)
    assert lease is not None
    assert lease.status == LEASE_STATUS_DIRTY
    assert lease.fsm_state != FSM_AWAITING_TCRE
    assert str(lease.pipeline_run_id) == str(run.id)
    assert lease.phase_cursor == PHASE_07_RETRIEVAL
