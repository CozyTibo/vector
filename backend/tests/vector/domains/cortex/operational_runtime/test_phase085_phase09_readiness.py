"""P085-35 — Phase 09 readiness gates (**G-P085-READY-01**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_phase09_readiness_gate import (
    verify_gp085_phase09_readiness_gate_static,
)
from vector.domains.cortex.operational_runtime.phase_boundaries import CespPhaseBoundaryError
from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
    GP085_READY01_GATE_ID_V1,
    PHASE09_READINESS_CRITERION_IDS_V1,
    assert_phase09_blocked_until_readiness_v1,
    build_phase09_readiness_catalog_v1,
    build_phase09_readiness_checklist_v1,
    evaluate_golden_tenant_profile_v1,
    evaluate_phase09_readiness_v1,
    record_phase09_soak_signoff_v1,
    verify_gp085_ready01_static,
)


def test_gp085_ready01_static_gate() -> None:
    out = verify_gp085_ready01_static()
    assert out["passed"] is True
    assert out["id"] == GP085_READY01_GATE_ID_V1
    assert verify_gp085_phase09_readiness_gate_static()["passed"] is True


def test_readiness_catalog() -> None:
    cat = build_phase09_readiness_catalog_v1()
    assert cat["primary_gate_id"] == GP085_READY01_GATE_ID_V1
    assert len(cat["criterion_ids"]) == 15


def test_static_checklist_r1_r14_pass() -> None:
    checklist = build_phase09_readiness_checklist_v1(session=None)
    assert [c["criterion_id"] for c in checklist] == list(PHASE09_READINESS_CRITERION_IDS_V1)
    pre_r15 = [c for c in checklist if c["criterion_id"] != "R15"]
    assert all(c["passed"] for c in pre_r15)
    r15 = next(c for c in checklist if c["criterion_id"] == "R15")
    assert r15["passed"] is False


def test_phase09_blocked_until_readiness() -> None:
    with pytest.raises(CespPhaseBoundaryError) as exc:
        assert_phase09_blocked_until_readiness_v1(
            readiness_passed=False,
            phase09_ship_flags={"phase09_enabled": True},
            cesp_close_gate_passed=True,
        )
    assert exc.value.code == "phase09_before_readiness"


@pytest.mark.integration
def test_soak_signoff_enables_r15(db_session: Session) -> None:
    record_phase09_soak_signoff_v1(db_session, note="pytest soak")
    db_session.flush()
    out = evaluate_phase09_readiness_v1(db_session)
    r15 = next(c for c in out["checklist"] if c["criterion_id"] == "R15")
    assert r15["passed"] is True
    assert out["readiness_passed"] is True


@pytest.mark.integration
def test_golden_tenant_profile_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085p9-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 P9",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    profile = evaluate_golden_tenant_profile_v1(db_session, tenant_id=tenant.id)
    assert profile["profile_passed"] is False
    assert profile["checks"]["non_zero_published_retrieval_rows"] is False
