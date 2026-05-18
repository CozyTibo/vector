"""Operational continuity — pipeline continuation, eligibility explainability, recovery."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import PHASE_06_TCRE
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_RESUMED,
    CONTINUATION_STATUS_WAITING,
    WAITING_ON_TCRE_COMPLETION,
    compute_resume_receipt_hash_v1,
    get_continuation_for_pipeline_v1,
    mark_pipeline_waiting_on_tcre_v1,
    resume_pipeline_after_tcre_completion_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_LEGALITY_FAILED_V1,
    normalize_retrieval_skip_reason_v1,
)


@pytest.fixture
def tenant(db_session: Session):
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"cont-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="Pipeline Continuity Tenant",
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
def test_mark_pipeline_waiting_on_tcre(db_session, tenant) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"cont-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
        celery_task_id="celery-1",
    )
    db_session.flush()
    assert cont.continuation_status == CONTINUATION_STATUS_WAITING
    assert cont.waiting_on == WAITING_ON_TCRE_COMPLETION
    assert cont.current_phase == PHASE_06_TCRE
    assert cont.async_job_id == job_id


@pytest.mark.integration
def test_resume_pipeline_idempotent_receipt(db_session, tenant, monkeypatch) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"cont-resume-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
    )

    enqueued: list[dict] = []

    def _fake_enqueue(**kwargs):  # type: ignore[no-untyped-def]
        enqueued.append(kwargs)
        return {"phase_id": kwargs.get("phase_id"), "celery_task_id": "task-1"}

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.enqueue_next_pipeline_phase_v1",
        _fake_enqueue,
    )

    out1 = resume_pipeline_after_tcre_completion_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
        tcre_job_status="completed",
    )
    assert out1["resumed"] is True
    cont = get_continuation_for_pipeline_v1(db_session, pipeline_run_id=run.id)
    assert cont is not None
    assert cont.continuation_status == CONTINUATION_STATUS_RESUMED
    receipt = str(out1["resume_receipt_hash"])

    out2 = resume_pipeline_after_tcre_completion_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
        tcre_job_status="completed",
    )
    assert out2["resumed"] is False
    assert out2["reason"] == "duplicate_resume_receipt"
    assert len(enqueued) == 1


@pytest.mark.integration
def test_explain_synthesis_eligibility_idle(db_session, tenant) -> None:
    expl = explain_synthesis_eligibility_v1(db_session, tenant_id=tenant.id)
    assert expl["eligible_scopes"] == 0
    assert expl["synthesis_ready"] is False
    assert "no_published_retrieval_epoch" in expl["blocked_by"]


def test_retrieval_skip_registry_normalization() -> None:
    row = normalize_retrieval_skip_reason_v1(
        source="tcre_job",
        code="RETRIEVAL_RD_LEGALITY_V1",
    )
    assert row["ret_skip_code"] == RET_SKIP_LEGALITY_FAILED_V1
    assert row["replay_safe"] is True


def test_resume_receipt_hash_deterministic() -> None:
    h1 = compute_resume_receipt_hash_v1(
        resume_identity_digest="abc",
        continuation_nonce="nonce",
        tcre_job_status="completed",
    )
    h2 = compute_resume_receipt_hash_v1(
        resume_identity_digest="abc",
        continuation_nonce="nonce",
        tcre_job_status="completed",
    )
    assert h1 == h2
