"""Phase 08 Step 34 — E2E operational certification (G-P08-E2E-01)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_program_closure import _eval_c10_e2e_scenario_a_slice
from vector.domains.cortex.synthesis.testing import (
    GP08_E2E01_GATE_ID_V1,
    build_synthesis_e2e_operational_catalog_v1,
    run_synthesis_e2e_scenario_b_v1,
    run_synthesis_e2e_scenario_c_v1,
    run_synthesis_e2e_scenario_d_v1,
    verify_gp08_e2e01_operational_certification_static,
)
from vector.domains.cortex.synthesis.testing.e2e_operational_certification import (
    SYNTHESIS_E2E_SCENARIOS_V1,
    SYNTHESIS_E2E_TEST_MODULES_V1,
    _synthesis_e2e_tests_dir_v1,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_e2e_gate_and_catalog() -> None:
    static = verify_gp08_e2e01_operational_certification_static()
    assert static["passed"] is True, static
    assert static["id"] == GP08_E2E01_GATE_ID_V1
    catalog = build_synthesis_e2e_operational_catalog_v1()
    assert catalog["gate_id"] == GP08_E2E01_GATE_ID_V1
    assert len(catalog["scenarios"]) == 4
    assert len(catalog["test_modules"]) == 4


def test_e2e_scenario_constants_match_spec_modules() -> None:
    assert len(SYNTHESIS_E2E_SCENARIOS_V1) == 4
    assert len(SYNTHESIS_E2E_TEST_MODULES_V1) == 4
    tests_dir = _synthesis_e2e_tests_dir_v1()
    for mod in SYNTHESIS_E2E_TEST_MODULES_V1:
        assert (tests_dir / mod).is_file(), mod


def test_program_closure_c10_wires_e2e_static() -> None:
    row = _eval_c10_e2e_scenario_a_slice()
    assert row["criterion_id"] == "C10"
    assert row["passed"] is True, row


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8s34-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 S34")
    tenant = Tenant(
        company_name="P8S34",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8s34-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_scenarios_b_c_d_job_path(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    b = run_synthesis_e2e_scenario_b_v1(db_session, tenant_id=tenant_id)
    c = run_synthesis_e2e_scenario_c_v1(db_session, tenant_id=tenant_id)
    d = run_synthesis_e2e_scenario_d_v1(db_session, tenant_id=tenant_id)
    assert b["passed"] is True, b
    assert c["passed"] is True, c
    assert d["passed"] is True, d
