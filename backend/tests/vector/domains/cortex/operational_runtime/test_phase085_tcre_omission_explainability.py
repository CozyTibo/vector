"""P085-20 — TCRE omission explainability (**G-P085-TCRE-03**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.tcre_completeness_projection import (
    project_tcre_completeness_v1,
)
from vector.domains.cortex.operational_runtime.cesp_tcre_omission_explainability_gate import (
    verify_gp085_tcre_omission_explainability_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability import (
    GP085_TCRE03_GATE_ID_V1,
    OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1,
    OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1,
    OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1,
    OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1,
    UPSTREAM_UNMATERIALIZED_RAW_V1,
    build_substrate_tcre_omission_explainability_catalog_v1,
    build_tcre_omission_explainability_panel_v1,
    explain_tcre_reconstruction_job_omissions_v1,
    verify_gp085_tcre03_static,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)


def test_tcre_omission_catalog() -> None:
    cat = build_substrate_tcre_omission_explainability_catalog_v1()
    assert cat["primary_gate_id"] == GP085_TCRE03_GATE_ID_V1
    assert OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1 in cat["omission_field_ids"]


def test_verify_gp085_tcre03_static_passes() -> None:
    assert verify_gp085_tcre03_static()["passed"] is True
    assert verify_gp085_tcre_omission_explainability_gate_static()["passed"] is True


def test_explain_job_omissions_from_summary() -> None:
    job = CortexTcreReconstructionJob(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_kind="reconstruct",
        status="completed",
        dry_run=False,
        scope_json={"materialization_limit": 100},
        summary_json={
            "materialization_count": 100,
            "chronology_degraded_count": 3,
            "edge_non_replay_equivalent_count": 1,
        },
        tcre_policy_bundle_digest="d" * 64,
        reasoning_rule_pack_id="pack",
        engine_build_ref="test",
    )
    exp = explain_tcre_reconstruction_job_omissions_v1(job)
    assert exp[OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1] == 3
    assert exp[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1] == 1
    assert exp[OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1] == 1


def test_explain_failed_job_causal_unverified() -> None:
    job = CortexTcreReconstructionJob(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_kind="reconstruct",
        status="failed",
        dry_run=False,
        scope_json={},
        summary_json={},
        tcre_policy_bundle_digest="d" * 64,
        reasoning_rule_pack_id="pack",
        engine_build_ref="test",
    )
    exp = explain_tcre_reconstruction_job_omissions_v1(job)
    assert exp[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1] == 1


@pytest.mark.integration
def test_build_tcre_omission_panel_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085tcreom-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 TCRE Om",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    panel = build_tcre_omission_explainability_panel_v1(db_session, tenant_id=row.id)
    assert panel["gate_id"] == GP085_TCRE03_GATE_ID_V1
    assert panel["completeness_law_satisfied"] is True
    assert UPSTREAM_UNMATERIALIZED_RAW_V1 in panel["omission_counts"]
    assert panel["per_job_explanations"] == []


def test_tcre_completeness_never_run_degraded(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.tcre_completeness_projection.compute_tcre_density_metrics_v1",
        lambda *_a, **_k: {
            "tcre_maturity_class": "R0",
            "substrate_state": "degraded",
            "metrics": {
                "tcre_materialization_total": 10,
                "tcre_reconstructed_count": 0,
                "tcre_pending_count": 10,
                "tcre_saturation_percent": 0.0,
                "tcre_density_score": 0,
                "reconstruction_never_run": True,
                "degraded_chronology_count": 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.tcre_completeness_projection.build_tcre_omission_classes_for_completeness_v1",
        lambda *_a, **_k: {OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1: 10},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.completeness.tcre_completeness_projection.build_reasoning_runtime_health_v1",
        lambda *_a, **_k: {
            "failed_job_count": 0,
            "degraded_chronology_percent": 0.0,
            "last_replay_result": True,
        },
    )

    stage = project_tcre_completeness_v1(db_session, tenant_id=tid)
    assert stage["substrate_state"] == "degraded"
    assert stage["omission_classes"].get(OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1) == 10
