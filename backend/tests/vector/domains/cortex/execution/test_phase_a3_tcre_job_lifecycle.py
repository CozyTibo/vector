"""Phase A step A3 — TCRE queued job drain."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tcre_job_lifecycle import (
    ORPHAN_RUNNING_CODE_V1,
    drain_stale_queued_tcre_jobs_v1,
    snapshot_tcre_job_status_histogram_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    execute_tcre_reconstruction_job_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"a3-{uuid.uuid4().hex[:10]}@example.com", full_name="A3 User")
    tenant = Tenant(
        company_name="A3TCRE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"a3tcre-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _queued_job(
    db_session: Session,
    tenant_id: uuid.UUID,
    *,
    age_seconds: int = 7200,
    pipeline_run_id: uuid.UUID | None = None,
) -> CortexTcreReconstructionJob:
    prid = pipeline_run_id or uuid.uuid4()
    job = CortexTcreReconstructionJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_kind="reconstruct",
        status="queued",
        dry_run=True,
        scope_json={"substrate_pipeline_run_id": str(prid)},
        summary_json={},
        tcre_policy_bundle_digest="sha256:test",
        reasoning_rule_pack_id="pack-test",
        engine_build_ref="test",
        created_at=datetime.now(UTC) - timedelta(seconds=age_seconds),
    )
    db_session.add(job)
    db_session.flush()
    return job


def test_drain_stale_queued_job_inline(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    pipeline_run_id = uuid.uuid4()
    _queued_job(db_session, tenant_id, pipeline_run_id=pipeline_run_id)

    def _complete_job(_session: Session, job: CortexTcreReconstructionJob) -> dict[str, object]:
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        return {"materialization_count": 0}

    with patch(
        "vector.domains.cortex.execution.tcre_job_lifecycle.execute_tcre_reconstruction_job_v1",
        side_effect=_complete_job,
    ) as mock_exec:
        with patch(
            "vector.domains.cortex.execution.tcre_job_lifecycle.on_tcre_job_terminal_for_execution_v1",
            return_value={"resumed": True, "path": "convergence_lease"},
        ) as mock_resume:
            out = drain_stale_queued_tcre_jobs_v1(
                db_session,
                tenant_id=tenant_id,
                stale_after_seconds=60,
                dry_run=False,
            )

    assert out["stale_queued_before"] == 1
    assert out["stale_queued_after"] == 0
    assert out["jobs_drained"] == 1
    mock_exec.assert_called_once()
    mock_resume.assert_called_once()


def test_orchestrator_finally_terminalizes_orphan_running(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    job = _queued_job(db_session, tenant_id, age_seconds=10)

    with patch(
        "vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator._run_reconstruction_pipeline_in_memory_v1",
        side_effect=KeyboardInterrupt,
    ):
        with pytest.raises(KeyboardInterrupt):
            execute_tcre_reconstruction_job_v1(db_session, job)

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_detail == ORPHAN_RUNNING_CODE_V1


def test_snapshot_histogram(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    _queued_job(db_session, tenant_id, age_seconds=100)
    hist = snapshot_tcre_job_status_histogram_v1(db_session, tenant_id=tenant_id)
    assert hist["queued"] >= 1
