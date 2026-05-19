"""P085-07 — Dead-letter queue (**G-P085-DLQ-01**)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_dlq_gate import verify_gp085_dlq_gate_static
from vector.domains.cortex.operational_runtime.recovery_continuity import (
    GP085_DLQ01_GATE_ID_V1,
    build_recovery_continuity_catalog_v1,
    verify_gp085_dlq01_static,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_06_TCRE
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    DLQ_STATUS_OPEN,
    DLQ_STATUS_RECOVERED,
    FAILURE_CLASS_CONTINUATION_MISSING,
    FAILURE_CLASS_TCRE_FAILED,
    PipelineDeadLetterError,
    assert_dlq_auto_retry_budget_v1,
    assert_failure_class_closed_v1,
    count_dlq_auto_retries_for_receipt_v1,
    default_recovery_actions_for_failure_class_v1,
    record_pipeline_dead_letter_v1,
    resolve_dead_letter_v1,
    resolve_open_dlq_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1


def test_recovery_continuity_catalog_lists_failure_classes() -> None:
    cat = build_recovery_continuity_catalog_v1()
    assert cat["primary_gate_id"] == GP085_DLQ01_GATE_ID_V1
    assert len(cat["failure_class_ids"]) == 6
    assert "walk_poison" in cat["failure_class_ids"]
    assert "retry_continuation" in cat["recovery_action_ids"]
    assert cat["n_max_auto_retries_per_receipt"] >= 1


def test_verify_gp085_dlq01_static_passes() -> None:
    assert verify_gp085_dlq01_static()["passed"] is True
    assert verify_gp085_dlq_gate_static()["passed"] is True


def test_failure_class_must_be_closed() -> None:
    with pytest.raises(PipelineDeadLetterError):
        assert_failure_class_closed_v1("not_a_real_class")
    actions = default_recovery_actions_for_failure_class_v1(FAILURE_CLASS_TCRE_FAILED)
    assert "rebind_tcre" in actions


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085dlq-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 DLQ Tenant",
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
def test_record_and_resolve_dead_letter(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085dlq-{uuid.uuid4().hex[:12]}",
    )
    receipt = "sha256:" + "a" * 64
    row = record_pipeline_dead_letter_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_id=PHASE_06_TCRE,
        failure_class=FAILURE_CLASS_CONTINUATION_MISSING,
        async_job_id=uuid.uuid4(),
        resume_receipt_hash=receipt,
        failure_detail="test_missing_continuation",
    )
    assert row.dlq_status == DLQ_STATUS_OPEN
    assert row.replay_safe is True
    assert "retry_continuation" in list(row.recovery_actions or [])

    resolved = resolve_dead_letter_v1(
        db_session,
        dead_letter_id=row.id,
        outcome=DLQ_STATUS_RECOVERED,
    )
    assert resolved is not None
    assert resolved.dlq_status == DLQ_STATUS_RECOVERED


@pytest.mark.integration
def test_dlq_auto_retry_budget_enforced(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_SUBSTRATE_DLQ_MAX_AUTO_RETRIES_PER_RECEIPT", "2")
    from vector.settings import get_settings

    get_settings.cache_clear()
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085budget-{uuid.uuid4().hex[:12]}",
    )
    receipt = "sha256:" + "b" * 64
    for _ in range(2):
        record_pipeline_dead_letter_v1(
            db_session,
            tenant_id=tenant.id,
            pipeline_run_id=run.id,
            phase_id=PHASE_06_TCRE,
            failure_class=FAILURE_CLASS_TCRE_FAILED,
            resume_receipt_hash=receipt,
            auto_retry_increment=1,
        )
    assert count_dlq_auto_retries_for_receipt_v1(db_session, resume_receipt_hash=receipt) == 2
    with pytest.raises(PipelineDeadLetterError) as exc:
        assert_dlq_auto_retry_budget_v1(db_session, resume_receipt_hash=receipt)
    assert exc.value.code == "dlq_auto_retry_budget_exhausted"
    get_settings.cache_clear()


@pytest.mark.integration
def test_resolve_open_dlq_for_pipeline(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085resolve-{uuid.uuid4().hex[:12]}",
    )
    record_pipeline_dead_letter_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_id=PHASE_06_TCRE,
        failure_class=FAILURE_CLASS_TCRE_FAILED,
    )
    count = resolve_open_dlq_for_pipeline_v1(db_session, pipeline_run_id=run.id)
    assert count == 1
