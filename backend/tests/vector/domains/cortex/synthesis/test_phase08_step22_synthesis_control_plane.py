"""Phase 08 Step 22 — synthesis admin control plane catalog."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_control_plane import (
    GP08_CP01_GATE_ID_V1,
    PHASE08_SYNTHESIS_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_CONTROL_PLANE_CONTRACT_V1,
    SYNTHESIS_CONTROL_PLANE_SURFACES_V1,
    build_synthesis_control_plane_surface_checklist_v1,
    build_synthesis_control_plane_v1,
    build_synthesis_rbac_matrix_v1,
    verify_gp08_cp01_synthesis_control_plane_rbac_static,
    verify_synthesis_control_plane_surface_registry_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-admin-control-plane-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION >= 1


def test_surface_registry_has_sixteen_surfaces() -> None:
    assert len(SYNTHESIS_CONTROL_PLANE_SURFACES_V1) == 16
    assert {int(s["surface_number"]) for s in SYNTHESIS_CONTROL_PLANE_SURFACES_V1} == set(range(1, 17))


def test_gp08_cp01_static_gate() -> None:
    reg = verify_synthesis_control_plane_surface_registry_static()
    assert reg["passed"] is True
    out = verify_gp08_cp01_synthesis_control_plane_rbac_static()
    assert out["passed"] is True
    assert out["id"] == GP08_CP01_GATE_ID_V1


def test_surface_checklist_openapi_paths() -> None:
    checklist = build_synthesis_control_plane_surface_checklist_v1()
    assert len(checklist) == 16
    aggregate = [s for s in checklist if s["surface_id"] == "control_plane_aggregate"]
    assert aggregate and aggregate[0]["wired_at_closure"] is True
    assert "/control-plane" in "".join(aggregate[0].get("openapi_paths") or [])


def test_rbac_matrix_has_job_run_permission() -> None:
    rb = build_synthesis_rbac_matrix_v1()
    assert "cortex.synthesis.job.run" in rb["permissions"]


def test_doctrine_files_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "synthesis" / "phase-08-admin-control-plane-spec.md").is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8cp22-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 CP22")
    tenant = Tenant(
        company_name="P8CP22",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8cp22-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_build_control_plane_idle_tenant(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    db_session.commit()
    doc = build_synthesis_control_plane_v1(db_session, tenant_id=tenant_id)
    assert doc["synthesis_control_plane_contract"] == SYNTHESIS_CONTROL_PLANE_CONTRACT_V1
    assert doc["gate_id"] == GP08_CP01_GATE_ID_V1
    assert doc["surfaces_total"] == 16
    assert len(doc["surface_checklist"]) == 16
    assert doc["tenant_id"] == str(tenant_id)
    assert "health_strip" in doc
    assert "coverage_summary" in doc
    assert "degradation_posture_summary" in doc
    assert "workload_histogram" in doc
    assert "operator_workflows" in doc
