"""P085-29 — Autonomous recovery score (**G-P085-HEALTH-02**)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_autonomous_recovery_gate import (
    verify_gp085_autonomous_recovery_gate_static,
)
from vector.domains.cortex.operational_runtime.recovery_receipts import (
    RECOVERY_RECEIPT_OUTCOME_RECOVERED,
    build_recovery_receipt_v1,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score import (
    GP085_HEALTH02_GATE_ID_V1,
    HEALTH_DIM_AUTONOMOUS_RECOVERY_V1,
    METRIC_FAILED_DLQ_V1,
    METRIC_RECOVERED_TOTAL_V1,
    METRIC_RECOVERED_WATCHDOG_V1,
    METRIC_RECOVERY_SCORE_V1,
    build_substrate_autonomous_recovery_catalog_v1,
    collect_recovery_receipt_counts_v1,
    compute_autonomous_recovery_score_v1,
    evaluate_autonomous_recovery_health_v1,
    evaluate_autonomous_recovery_score_v1,
    verify_gp085_health02_static,
)
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    record_pipeline_dead_letter_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_operational_health import (
    evaluate_substrate_operational_health_v1,
)


def test_autonomous_recovery_catalog() -> None:
    cat = build_substrate_autonomous_recovery_catalog_v1()
    assert cat["primary_gate_id"] == GP085_HEALTH02_GATE_ID_V1
    assert cat["formula"] == "recovered_watchdog / (recovered + failed_dlq)"
    assert cat["score_target"] == 0.9
    assert cat["health_dimension_id"] == HEALTH_DIM_AUTONOMOUS_RECOVERY_V1


def test_verify_gp085_health02_static_passes() -> None:
    assert verify_gp085_health02_static()["passed"] is True
    assert verify_gp085_autonomous_recovery_gate_static()["passed"] is True


def test_recovery_score_formula() -> None:
    assert compute_autonomous_recovery_score_v1(
        recovered_watchdog=9,
        recovered_total=10,
        failed_dlq=0,
    ) == 0.9
    assert compute_autonomous_recovery_score_v1(
        recovered_watchdog=0,
        recovered_total=0,
        failed_dlq=0,
    ) == 1.0
    assert compute_autonomous_recovery_score_v1(
        recovered_watchdog=3,
        recovered_total=5,
        failed_dlq=5,
    ) == 0.3


def test_recovery_health_bands() -> None:
    healthy = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.95,
        score_target=0.9,
        degraded_floor=0.7,
    )
    assert healthy["band"] == "healthy"
    assert healthy["meets_target"] is True

    degraded = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.8,
        score_target=0.9,
        degraded_floor=0.7,
    )
    assert degraded["band"] == "degraded"

    critical = evaluate_autonomous_recovery_health_v1(
        recovery_score=0.5,
        score_target=0.9,
        degraded_floor=0.7,
    )
    assert critical["band"] == "critical"


@pytest.mark.integration
def test_evaluate_autonomous_recovery_score_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085recv-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RECV",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = evaluate_autonomous_recovery_score_v1(db_session, tenant_id=tenant.id)
    assert out["gate_id"] == GP085_HEALTH02_GATE_ID_V1
    metrics = dict(out["metrics"])
    assert metrics[METRIC_RECOVERY_SCORE_V1] == 1.0
    assert metrics[METRIC_RECOVERED_WATCHDOG_V1] == 0
    assert metrics[METRIC_RECOVERED_TOTAL_V1] == 0
    assert metrics[METRIC_FAILED_DLQ_V1] == 0
    assert out["autonomous_recovery_health_band"] == "healthy"


@pytest.mark.integration
def test_recovery_receipt_counts_and_dlq(db_session: Session) -> None:
    from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
        mark_pipeline_waiting_on_tcre_v1,
    )
    from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085recv2-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RECV2",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"recv-{uuid.uuid4().hex[:8]}",
    )
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    receipt = build_recovery_receipt_v1(
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        action="retry_continuation",
        continuation_nonce=cont.continuation_nonce,
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        extra={"operator_action": "auto"},
    )
    detail = dict(cont.detail_json or {})
    detail["recovery_receipts"] = [receipt]
    cont.detail_json = detail
    db_session.flush()

    record_pipeline_dead_letter_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_id="06",
        failure_class="phase_enqueue_failed",
        failure_detail="test dlq",
    )
    db_session.commit()

    since = datetime.now(tz=UTC) - timedelta(days=7)
    counts = collect_recovery_receipt_counts_v1(
        db_session,
        tenant_id=tenant.id,
        since=since,
    )
    assert counts[METRIC_RECOVERED_WATCHDOG_V1] >= 1
    assert counts[METRIC_RECOVERED_TOTAL_V1] >= 1

    out = evaluate_autonomous_recovery_score_v1(db_session, tenant_id=tenant.id)
    metrics = dict(out["metrics"])
    assert metrics[METRIC_FAILED_DLQ_V1] >= 1
    assert metrics[METRIC_RECOVERY_SCORE_V1] < 1.0


@pytest.mark.integration
def test_operational_health_includes_autonomous_recovery(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085recv3-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 RECV3",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = evaluate_substrate_operational_health_v1(db_session, tenant_id=tenant.id)
    assert "autonomous_recovery" in out
    assert HEALTH_DIM_AUTONOMOUS_RECOVERY_V1 in out["health_dimensions"]
