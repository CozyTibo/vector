"""Phase A step A6 — synthesis job terminal transitions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_job_envelope import compute_synthesis_job_envelope_digest_v1
from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    DUPLICATE_INFLIGHT_SUPERSEDED_CODE_V1,
    ORPHAN_RUNNING_CODE_V1,
    prepare_synthesis_job_row_for_execute_v1,
    reconcile_stale_queued_synthesis_jobs_v1,
    supersede_duplicate_inflight_synthesis_jobs_v1,
    terminalize_synthesis_job_completed_v1,
    terminalize_synthesis_job_failed_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_repository import create_synthesis_job_row_v1
from vector.domains.cortex.substrate_pipeline.continuity_p0_synthesis_terminal_transitions import (
    verify_a6_synthesis_terminal_transitions_wiring_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"a6-{uuid.uuid4().hex[:10]}@example.com", full_name="A6 User")
    tenant = Tenant(
        company_name="A6SYN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"a6syn-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _minimal_envelope(tenant_id: uuid.UUID, *, idem: str | None = None) -> dict[str, object]:
    return {
        "schema_version": 1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "idempotency_key": idem or f"test-a6-{uuid.uuid4().hex[:12]}",
    }


def test_a6_wiring_static() -> None:
    wiring = verify_a6_synthesis_terminal_transitions_wiring_v1()
    assert wiring["wiring_ok"] is True


def test_completed_terminalize_is_idempotent(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    envelope = _minimal_envelope(tenant_id)
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    job = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    job.status = "running"
    job.started_at = datetime.now(UTC)
    db_session.flush()
    terminalize_synthesis_job_completed_v1(job, execution_trace=[{"phase": "PUBLISH"}])
    assert job.status == "completed"
    terminalize_synthesis_job_failed_v1(job, error_code="should_not_apply")
    assert job.status == "completed"


def test_supersede_duplicate_inflight_jobs(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    idem = f"dup-{uuid.uuid4().hex[:16]}"
    envelope = _minimal_envelope(tenant_id, idem=idem)
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    older = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    older.status = "queued"
    newer = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    newer.status = "running"
    newer.started_at = datetime.now(UTC)
    db_session.flush()
    count = supersede_duplicate_inflight_synthesis_jobs_v1(
        db_session,
        tenant_id=tenant_id,
        idempotency_key=idem,
        envelope_digest=digest,
        keep_job_id=newer.id,
    )
    db_session.refresh(older)
    assert count == 1
    assert older.status == "failed"
    assert older.error_detail == DUPLICATE_INFLIGHT_SUPERSEDED_CODE_V1


def test_prepare_single_enqueue_path(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    envelope = _minimal_envelope(tenant_id)
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    prepared = prepare_synthesis_job_row_for_execute_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    assert prepared.idempotent_completed_job is None
    assert prepared.job.status == "running"


def test_reconcile_stale_queued(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    envelope = _minimal_envelope(tenant_id)
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    job = create_synthesis_job_row_v1(
        db_session,
        tenant_id=tenant_id,
        envelope=envelope,
        envelope_digest=digest,
    )
    job.status = "queued"
    job.created_at = datetime.now(UTC) - timedelta(hours=3)
    db_session.flush()
    out = reconcile_stale_queued_synthesis_jobs_v1(
        db_session,
        tenant_id=tenant_id,
        stale_after_seconds=3600,
        dry_run=False,
    )
    db_session.refresh(job)
    assert out["stale_queued_count"] == 1
    assert job.status == "failed"


def test_orchestrator_finally_still_terminalizes_orphan_running(
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
