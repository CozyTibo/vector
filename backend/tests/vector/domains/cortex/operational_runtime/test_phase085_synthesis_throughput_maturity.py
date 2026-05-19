"""P085-26 — Synthesis throughput maturity (**G-P085-SYN-03**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_synthesis_throughput_gate import (
    verify_gp085_synthesis_throughput_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_synthesis_throughput_maturity import (
    build_substrate_synthesis_throughput_catalog_v1,
    verify_gp085_syn03_static,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    project_synthesis_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
    GP085_SYN03_GATE_ID_V1,
    METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1,
    METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1,
    METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1,
    apply_synthesis_throughput_maturity_to_stage_v1,
    compute_synthesis_scope_coverage_percent_v1,
    evaluate_synthesis_throughput_targets_v1,
)


def test_synthesis_throughput_catalog() -> None:
    cat = build_substrate_synthesis_throughput_catalog_v1()
    assert cat["primary_gate_id"] == GP085_SYN03_GATE_ID_V1
    assert cat["activation_audit_table"] == "cortex_synthesis_activation_audits"
    assert METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1 in cat["metric_ids"]


def test_verify_gp085_syn03_static_passes() -> None:
    assert verify_gp085_syn03_static()["passed"] is True
    assert verify_gp085_synthesis_throughput_gate_static()["passed"] is True


def test_scope_coverage_percent_formula() -> None:
    assert compute_synthesis_scope_coverage_percent_v1(eligible_scopes=10, synthesized_scopes=9) == 90.0
    assert compute_synthesis_scope_coverage_percent_v1(eligible_scopes=0, synthesized_scopes=0) == 0.0


def test_throughput_targets_all_met() -> None:
    targets = evaluate_synthesis_throughput_targets_v1(
        jobs_completed_per_day=3,
        scope_coverage_percent=95.0,
        activation_audit_empty_rate=2.0,
        eligible_scopes=10,
        policy={
            "jobs_per_day_floor": 1,
            "scope_coverage_target_percent": 90.0,
            "activation_audit_empty_rate_max_percent": 5.0,
        },
    )
    assert targets["all_throughput_targets_met"] is True


def test_throughput_targets_fail_when_empty_rate_high() -> None:
    targets = evaluate_synthesis_throughput_targets_v1(
        jobs_completed_per_day=0,
        scope_coverage_percent=50.0,
        activation_audit_empty_rate=20.0,
        eligible_scopes=5,
        policy={
            "jobs_per_day_floor": 1,
            "scope_coverage_target_percent": 90.0,
            "activation_audit_empty_rate_max_percent": 5.0,
        },
    )
    assert targets["all_throughput_targets_met"] is False
    assert targets["audit_empty_rate_within_limit"] is False


def test_apply_throughput_coerces_healthy_stage() -> None:
    stage = {
        "stage_id": "synthesis",
        "substrate_state": "healthy",
        "metrics": {},
        "omission_classes": {},
        "drift_warnings": [],
    }
    throughput = {
        "substrate_state": "degraded",
        "synthesis_maturity_class": "SYN1",
        "throughput_targets": {"all_throughput_targets_met": False},
        "metrics": {
            METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: 0,
            METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: 40.0,
            METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: 10.0,
            "eligible_scopes": 5,
        },
    }
    out = apply_synthesis_throughput_maturity_to_stage_v1(stage, throughput=throughput)
    assert out["substrate_state"] == "degraded"
    assert out["metrics"][METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1] == 0


@pytest.mark.integration
def test_project_synthesis_completeness_includes_throughput_metrics(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085synthru-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 SYN THRU",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    stage = project_synthesis_completeness_v1(db_session, tenant_id=tenant.id)
    metrics = dict(stage.get("metrics") or {})
    assert METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1 in metrics
    assert METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1 in metrics
    assert METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1 in metrics
    assert "synthesis_classification" in metrics
