"""P08-25 — Synthesis runtime legality matrix (**S‑LEG‑01..07**, **SYN‑FORB‑01..05**, **PROD-SYN-01**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SYNTHESIS_LEGALITY_PREDICATES_V1,
)
from vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix import (
    SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1,
    list_synthesis_legality_predicate_ids_v1,
    GP08_RLM01_GATE_ID_V1,
    PHASE08_SYNTHESIS_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    PROD_SYN01_MATRIX_ROW_ID_V1,
    SYNTHESIS_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
    SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
    assert_synthesis_production_lawful_v1,
    build_synthesis_runtime_legality_matrix_catalog_v1,
    detect_synthesis_forbidden_deployments_v1,
    evaluate_prod_syn01_v1,
    evaluate_synthesis_production_gates_v1,
    synthesis_runtime_legality_allows_v1,
    verify_gp08_rlm01_predicate_catalog_seven_sorted_unique_static,
    verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle,
    verify_gp08_rlm02_s_leg01_anti01_ci_green_static,
    verify_gp08_rlm03_s_leg02_replay01_double_run_static,
    verify_gp08_rlm04_forbidden_deployments_shape_static,
    verify_gp08_rlm05_production_milestones_frozen_static,
    verify_gp08_rlm06_prod_syn01_threshold_static,
    verify_gp08_rlm07_build_catalog_contract_shape_static,
    verify_gp08_rlm08_admin_openapi_path_matrix_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-law-system.md"
        if marker.is_file():
            return root
    msg = "repo root not found"
    raise RuntimeError(msg)


def test_runtime_constants() -> None:
    assert PHASE08_SYNTHESIS_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION >= 1
    assert "phase-08-synthesis-law-system" in SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1
    assert PROD_SYN01_MATRIX_ROW_ID_V1 == "PROD-SYN-01"


def test_predicates_seven_sorted() -> None:
    ids = list_synthesis_legality_predicate_ids_v1()
    assert ids == tuple(f"S-LEG-{i:02d}" for i in range(1, 8))
    assert len(SYNTHESIS_LEGALITY_PREDICATES_V1) == 7


def test_forbidden_deployments_five() -> None:
    assert len(SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1) == 5
    assert SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1[0].forbidden_id == "SYN-FORB-01"


def test_all_rlm_oracles_pass() -> None:
    assert verify_gp08_rlm01_predicate_catalog_seven_sorted_unique_static()["passed"] is True
    assert verify_gp08_rlm02_s_leg01_anti01_ci_green_static()["passed"] is True
    assert verify_gp08_rlm03_s_leg02_replay01_double_run_static()["passed"] is True
    assert verify_gp08_rlm04_forbidden_deployments_shape_static()["passed"] is True
    assert verify_gp08_rlm05_production_milestones_frozen_static()["passed"] is True
    assert verify_gp08_rlm06_prod_syn01_threshold_static()["passed"] is True
    assert verify_gp08_rlm07_build_catalog_contract_shape_static()["passed"] is True
    assert verify_gp08_rlm08_admin_openapi_path_matrix_static()["passed"] is True
    bundle = verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle()
    assert bundle["passed"] is True
    assert bundle["id"] == GP08_RLM01_GATE_ID_V1


def test_build_runtime_catalog_with_production_gates() -> None:
    tid = uuid.uuid4()
    doc = build_synthesis_runtime_legality_matrix_catalog_v1(None, tenant_id=tid)
    assert doc["tenant_id"] == str(tid)
    assert doc["synthesis_runtime_legality_matrix_contract"] == SYNTHESIS_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    assert doc["gate_id"] == GP08_RLM01_GATE_ID_V1
    assert len(doc["predicates"]) == 7
    assert len(doc["forbidden_deployments"]) == 5
    assert "production_milestones" in doc
    assert doc["production_milestones"]["dev"]["passed"] is True
    gates = evaluate_synthesis_production_gates_v1(None, tenant_id=tid)
    assert gates["S-LEG-01"]["passed"] is True
    assert gates["S-LEG-02"]["passed"] is True
    detector = detect_synthesis_forbidden_deployments_v1(None, tenant_id=tid)
    assert len(detector) == 5
    assert doc["forbidden_deployments_clear"] is True
    assert "prod_syn01" in doc


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-synthesis-law-system.md").read_text(
        encoding="utf-8"
    )
    assert "S-LEG-01" in text and "PROD-SYN-01" in text
    assert "build_synthesis_legality_matrix_catalog_v1" in text


def test_prod_syn01_empty_tenant_passes(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8rlm25-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 RLM25")
    tenant = Tenant(
        company_name="P8RLM25",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8rlm25-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    out = evaluate_prod_syn01_v1(db_session, tenant_id=tenant.id)
    assert out["passed"] is True
    assert out["matrix_row_id"] == "PROD-SYN-01"
    assert_synthesis_production_lawful_v1(db_session, tenant_id=tenant.id, milestone="production")
    assert synthesis_runtime_legality_allows_v1(db_session, tenant_id=tenant.id) is True
