"""P085-05 — Continuation state machine (**G-P085-CONT-01**)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_continuation_gate import (
    verify_gp085_continuation_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    CONTINUATION_STATUS_COMPLETED,
    CONTINUATION_STATUS_FAILED,
    CONTINUATION_STATUS_RESUMED,
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    SubstrateContinuationError,
    assert_phase06_must_persist_waiting_v1,
    build_substrate_continuity_catalog_v1,
    increment_continuation_metric_v1,
    snapshot_continuation_metrics_v1,
    validate_continuation_status_transition_v1,
    verify_gp085_cont01_state_machine_static,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_RECOVERING,
    mark_continuation_failed_v1,
    mark_pipeline_waiting_on_tcre_v1,
    resume_pipeline_after_tcre_completion_v1,
    transition_continuation_status_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085cont-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Continuation Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_continuity_catalog_lists_states_and_waiting_kinds() -> None:
    cat = build_substrate_continuity_catalog_v1()
    assert cat["primary_gate_id"] == "G-P085-CONT-01"
    assert CONTINUATION_STATUS_WAITING in cat["continuation_status_ids"]
    assert "TCRE_COMPLETION" in cat["waiting_on_kinds"]
    assert cat["stall_threshold_seconds_configured"] >= 300


def test_illegal_transition_completed_to_waiting() -> None:
    with pytest.raises(SubstrateContinuationError) as exc:
        validate_continuation_status_transition_v1(
            from_status=CONTINUATION_STATUS_COMPLETED,
            to_status=CONTINUATION_STATUS_WAITING,
        )
    assert exc.value.code == "terminal_continuation_status"


def test_waiting_to_stalled_to_recovering_path() -> None:
    validate_continuation_status_transition_v1(
        from_status=CONTINUATION_STATUS_WAITING,
        to_status=CONTINUATION_STATUS_STALLED,
    )
    validate_continuation_status_transition_v1(
        from_status=CONTINUATION_STATUS_STALLED,
        to_status=CONTINUATION_STATUS_RECOVERING,
    )
    validate_continuation_status_transition_v1(
        from_status=CONTINUATION_STATUS_RECOVERING,
        to_status=CONTINUATION_STATUS_RESUMED,
    )


def test_verify_gp085_cont01_static_passes() -> None:
    assert verify_gp085_cont01_state_machine_static()["passed"] is True
    assert verify_gp085_continuation_gate_static()["passed"] is True


def test_phase06_must_persist_waiting_law() -> None:
    with pytest.raises(SubstrateContinuationError):
        assert_phase06_must_persist_waiting_v1(continuation_present=False)
    assert_phase06_must_persist_waiting_v1(
        continuation_present=True,
        waiting_on="TCRE_COMPLETION",
    )


@pytest.mark.integration
def test_mark_waiting_and_transition_to_resumed(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
    )
    assert cont.continuation_status == CONTINUATION_STATUS_WAITING

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.enqueue_next_pipeline_phase_v1",
        lambda **_k: {"phase_id": "phase_07_retrieval"},
    )
    out = resume_pipeline_after_tcre_completion_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=job_id,
        tcre_job_status="completed",
    )
    assert out["resumed"] is True
    assert cont.continuation_status == CONTINUATION_STATUS_RESUMED
    metrics = snapshot_continuation_metrics_v1()
    assert metrics["substrate_phase_07_enqueue_total"] >= 1


@pytest.mark.integration
def test_mark_continuation_failed_terminal(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085fail-{uuid.uuid4().hex[:12]}",
    )
    mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    row = mark_continuation_failed_v1(
        db_session,
        pipeline_run_id=run.id,
        failure_reason="operator_marked_unrecoverable",
    )
    assert row is not None
    assert row.continuation_status == CONTINUATION_STATUS_FAILED
    with pytest.raises(SubstrateContinuationError):
        transition_continuation_status_v1(
            db_session,
            continuation=row,
            to_status=CONTINUATION_STATUS_WAITING,
        )
