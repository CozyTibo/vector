"""P08-28 — Synthesis evaluation harness (**G-P08-EVAL-01/02**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_evaluation import (
    GP08_EVAL01_GATE_ID_V1,
    GP08_EVAL02_GATE_ID_V1,
    PHASE08_SYNTHESIS_EVALUATION_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_EVALUATION_CONTRACT_V1,
    SYNTHESIS_EVALUATION_SPEC_REF_V1,
    build_sample_artifact_from_golden_replay_case_v1,
    build_synthesis_evaluation_catalog_v1,
    compute_citation_coverage_metrics_v1,
    evaluate_gp08_eval01_citation_coverage_v1,
    evaluate_gp08_eval02_wording_drift_v1,
    list_synthesis_evaluation_run_ledger_v1,
    min_citation_coverage_threshold_v1,
    record_synthesis_evaluation_run_v1,
    run_golden_corpus_evaluation_v1,
    run_synthesis_evaluation_suite_v1,
    verify_gp08_eval01_citation_coverage_static,
    verify_gp08_eval01_synthesis_evaluation_static_bundle,
    verify_gp08_eval02_wording_drift_non_blocking_static,
    verify_gp08_eval03_golden_corpus_suite_static,
    verify_gp08_eval04_evaluation_suite_sample_static,
    verify_gp08_eval05_admin_openapi_path_matrix_static,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8eval-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Eval User")
    tenant = Tenant(
        company_name="P8EVAL",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8eval-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_runtime_constants() -> None:
    assert PHASE08_SYNTHESIS_EVALUATION_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-08-evaluation-quality-governance" in SYNTHESIS_EVALUATION_SPEC_REF_V1
    assert SYNTHESIS_EVALUATION_CONTRACT_V1 == "synthesis_evaluation_receipt_v1"


def test_citation_coverage_eval01_on_golden_sample() -> None:
    artifact = build_sample_artifact_from_golden_replay_case_v1()
    metrics = compute_citation_coverage_metrics_v1(artifact)
    assert metrics["total_claims"] == 1
    assert metrics["cited_claims"] == 1
    assert metrics["coverage_ratio"] == 1.0
    out = evaluate_gp08_eval01_citation_coverage_v1(artifact)
    assert out["id"] == GP08_EVAL01_GATE_ID_V1
    assert out["passed"] is True
    assert out["severity"] == "hard_fail"
    assert float(out["detail"]["min_citation_coverage_threshold"]) == min_citation_coverage_threshold_v1()


def test_eval02_wording_drift_non_blocking() -> None:
    out = evaluate_gp08_eval02_wording_drift_v1(wording_diff_detected=True)
    assert out["id"] == GP08_EVAL02_GATE_ID_V1
    assert out["passed"] is True
    assert out["severity"] == "warn"
    assert out["detail"]["blocking"] is False


def test_golden_corpus_evaluation() -> None:
    golden = run_golden_corpus_evaluation_v1()
    assert golden["golden_corpus_passed"] is True
    assert golden["case_count"] == 4


def test_evaluation_suite_static() -> None:
    receipt = run_synthesis_evaluation_suite_v1(None, tenant_id=None, record_ledger=False)
    assert receipt["evaluation_passed"] is True
    assert receipt["surface_kind"] == "verification_probe"
    assert GP08_EVAL01_GATE_ID_V1 in receipt["gate_results"]
    assert GP08_EVAL02_GATE_ID_V1 in receipt["gate_results"]


def test_evaluation_suite_with_tenant(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    receipt = run_synthesis_evaluation_suite_v1(db_session, tenant_id=tenant_id, record_ledger=False)
    assert receipt["evaluation_passed"] is True
    assert receipt["tenant"]["tenant_id"] == str(tenant_id)


def test_run_ledger() -> None:
    before = len(list_synthesis_evaluation_run_ledger_v1())
    record_synthesis_evaluation_run_v1({"evaluation_passed": True, "probe": "test"})
    assert len(list_synthesis_evaluation_run_ledger_v1()) == before + 1


def test_static_oracles() -> None:
    assert verify_gp08_eval01_citation_coverage_static()["passed"] is True
    assert verify_gp08_eval02_wording_drift_non_blocking_static()["passed"] is True
    assert verify_gp08_eval03_golden_corpus_suite_static()["passed"] is True
    assert verify_gp08_eval04_evaluation_suite_sample_static()["passed"] is True
    assert verify_gp08_eval05_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp08_eval01_synthesis_evaluation_static_bundle()["passed"] is True


def test_catalog_builder() -> None:
    cat = build_synthesis_evaluation_catalog_v1()
    assert cat["surface_kind"] == "verification_probe"
    assert GP08_EVAL01_GATE_ID_V1 in cat["gate_ids"]
    assert cat["static_gate_samples"][GP08_EVAL01_GATE_ID_V1]["passed"] is True
