"""Phase A step A1 — synthesis job lifecycle reconciliation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_job_envelope import compute_synthesis_job_envelope_digest_v1
from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    ORPHAN_RUNNING_CODE_V1,
    reconcile_stale_synthesis_jobs_v1,
    resolve_synthesis_job_before_execute_v1,
    snapshot_synthesis_job_status_histogram_v1,
    terminalize_synthesis_job_failed_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    SynthesisOrchestratorError,
    execute_synthesis_job_envelope_v1,
)
from vector.domains.cortex.synthesis.synthesis_repository import create_synthesis_job_row_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"a1-{uuid.uuid4().hex[:10]}@example.com", full_name="A1 User")
    tenant = Tenant(
        company_name="A1SYN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"a1syn-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "idempotency_key": f"test-a1-{uuid.uuid4().hex[:12]}",
    }


def _stuck_running_job(
    db_session: Session,
    tenant_id: uuid.UUID,
    *,
    idempotency_key: str | None = None,
    age_seconds: int = 7200,
) -> CortexSynthesisJob:
    envelope = _minimal_envelope(tenant_id)
    if idempotency_key:
        envelope["idempotency_key"] = idempotency_key
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    job = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    job.status = "running"
    job.started_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
    db_session.flush()
    return job


def test_reconcile_stale_running_jobs(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    _stuck_running_job(db_session, tenant_id, age_seconds=7200)
    _stuck_running_job(db_session, tenant_id, age_seconds=9000)

    out = reconcile_stale_synthesis_jobs_v1(
        db_session,
        tenant_id=tenant_id,
        stale_after_seconds=3600,
        dry_run=False,
    )
    assert out["reconciled_count"] == 2
    hist = snapshot_synthesis_job_status_histogram_v1(db_session, tenant_id=tenant_id)
    assert hist.get("running", 0) == 0
    assert hist.get("failed", 0) >= 2


def test_resolve_supersedes_stale_inflight_with_same_idempotency(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    idem = f"pipe08-{uuid.uuid4().hex[:16]}"
    stale = _stuck_running_job(db_session, tenant_id, idempotency_key=idem, age_seconds=7200)
    envelope = dict(stale.envelope_json or {})
    digest = stale.envelope_digest

    resolved = resolve_synthesis_job_before_execute_v1(
        db_session,
        tenant_id=tenant_id,
        idempotency_key=idem,
        envelope_digest=digest,
        stale_after_seconds=3600,
    )
    db_session.refresh(stale)
    assert resolved is None
    assert stale.status == "failed"


def test_orchestrator_finally_terminalizes_orphan_running(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VECTOR_SETTINGS_SKIP_DOTENV", "1")
    tenant_id = _tenant_with_owner(db_session)
    body = _minimal_envelope(tenant_id)

    with (
        patch(
            "vector.domains.cortex.synthesis.synthesis_job_lifecycle.synthesis_job_running_stale_seconds_v1",
            return_value=86_400,
        ),
        patch(
            "vector.domains.cortex.synthesis.synthesis_orchestrator.enforce_synthesis_job_envelope_anti_goals_v1",
            side_effect=RuntimeError("uncaught_boom"),
        ),
    ):
        with pytest.raises(RuntimeError, match="uncaught_boom"):
            execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)

    job = db_session.scalar(
        select(CortexSynthesisJob).where(CortexSynthesisJob.tenant_id == tenant_id)
    )
    assert job is not None
    assert job.status == "failed"
    assert job.error_detail == ORPHAN_RUNNING_CODE_V1


def test_terminalize_is_idempotent_for_completed(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    job = _stuck_running_job(db_session, tenant_id, age_seconds=100)
    job.status = "completed"
    job.completed_at = datetime.now(UTC)
    db_session.flush()
    terminalize_synthesis_job_failed_v1(job, error_code="stale")
    assert job.status == "completed"
