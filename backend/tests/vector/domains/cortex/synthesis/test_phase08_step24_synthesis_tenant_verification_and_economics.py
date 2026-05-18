"""Phase 08 Step 24 — synthesis tenant verification slice + readiness economics."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.normative import PHASE08_PROGRAM_FREEZE_VERSION
from vector.domains.cortex.synthesis.synthesis_readiness_economics import (
    GP08_ECO01_GATE_ID_V1,
    GP08_ECO02_GATE_ID_V1,
    GP08_ECO03_GATE_ID_V1,
    SYNTHESIS_READINESS_ECONOMICS_CONTRACT_V1,
    SYNTHESIS_READINESS_ECONOMICS_SCHEMA_VERSION,
    build_synthesis_readiness_economics_receipt_v1,
    compute_synthesis_economics_receipt_hash_v1,
    verify_gp08_eco01_readiness_economics_clean_profile_static,
    verify_gp08_eco02_readiness_economics_hostile_profile_static,
    verify_gp08_eco03_admin_openapi_path_matrix_static,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
    synthesis_golden_vectors_v1_root,
)
from vector.domains.cortex.synthesis.synthesis_tenant_verification import (
    GP08_TVER01_GATE_ID_V1,
    ORG_GRAPH_SYNTHESIS_VERIFICATION_SLICE_SCHEMA_VERSION,
    build_org_graph_synthesis_verification_slice_v1,
    compute_synthesis_verification_slice_hash_v1,
    publication_epoch_code_v1,
    validate_org_graph_synthesis_verification_slice_v1,
    verify_gp08_tver01_org_graph_synthesis_slice_golden_static,
    verify_gp08_tver02_admin_openapi_path_matrix_static,
    verify_tenant_synthesis_slice_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-evaluation-quality-governance.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_constants() -> None:
    assert ORG_GRAPH_SYNTHESIS_VERIFICATION_SLICE_SCHEMA_VERSION >= 1
    assert SYNTHESIS_READINESS_ECONOMICS_SCHEMA_VERSION >= 1
    assert SYNTHESIS_READINESS_ECONOMICS_CONTRACT_V1 == "synthesis_readiness_economics_v1"


def test_all_step24_oracles_pass() -> None:
    assert verify_gp08_tver01_org_graph_synthesis_slice_golden_static()["passed"] is True
    assert verify_gp08_tver01_org_graph_synthesis_slice_golden_static()["id"] == GP08_TVER01_GATE_ID_V1
    assert verify_gp08_tver02_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp08_eco01_readiness_economics_clean_profile_static()["passed"] is True
    assert verify_gp08_eco01_readiness_economics_clean_profile_static()["id"] == GP08_ECO01_GATE_ID_V1
    assert verify_gp08_eco02_readiness_economics_hostile_profile_static()["passed"] is True
    assert verify_gp08_eco02_readiness_economics_hostile_profile_static()["id"] == GP08_ECO02_GATE_ID_V1
    assert verify_gp08_eco03_admin_openapi_path_matrix_static()["passed"] is True
    assert verify_gp08_eco03_admin_openapi_path_matrix_static()["id"] == GP08_ECO03_GATE_ID_V1


def test_build_org_graph_synthesis_slice() -> None:
    tid = uuid.uuid4()
    body = build_org_graph_synthesis_verification_slice_v1(
        None,
        tenant_id=tid,
        verification_run_id="run-1",
    )
    assert validate_org_graph_synthesis_verification_slice_v1(body) == []
    assert body["tenant_id"] == str(tid)
    assert body["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    h = compute_synthesis_verification_slice_hash_v1(body)
    assert len(h) == 64


def test_publication_epoch_code_stable() -> None:
    assert publication_epoch_code_v1(None) == 0
    a = publication_epoch_code_v1("epoch-a")
    assert a == publication_epoch_code_v1("epoch-a")


def test_readiness_economics_receipts() -> None:
    tid = uuid.uuid4()
    clean = build_synthesis_readiness_economics_receipt_v1(None, tenant_id=tid, profile="clean")
    assert clean["economics_violations"] == []
    assert clean["surface_kind"] == "derived_aggregate"
    assert clean["estimated_monthly_cost_band"] in ("low", "medium", "high")
    hostile = build_synthesis_readiness_economics_receipt_v1(None, tenant_id=tid, profile="hostile")
    assert hostile["economics_violations"] == ["SYNTHESIS_ECO_GOLDEN_CASE_BUDGET"]
    h1 = compute_synthesis_economics_receipt_hash_v1(hostile["economics_stats"])
    assert len(h1) == 64


def test_golden_slice_file_present() -> None:
    path = (
        synthesis_golden_vectors_v1_root()
        / "tenant_verification"
        / "org_graph_synthesis_slice_good_v1.json"
    )
    assert path.is_file()


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-evaluation-quality-governance.md").read_text(
        encoding="utf-8",
    )
    assert "G-P08-TVER-01" in text
    assert "avg_job_duration_ms" in text


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8tver-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 TVER")
    tenant = Tenant(
        company_name="P8TVER",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8tver-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_verify_tenant_synthesis_slice_idle_tenant(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    db_session.commit()
    out = verify_tenant_synthesis_slice_v1(db_session, tenant_id=tenant_id)
    assert out["gate_id"] == GP08_TVER01_GATE_ID_V1
    assert "synthesis_substrate" in out
    assert out["passed"] is True
    assert out["failure_codes"] == []
