"""P085-30 — Admin operational cockpit (**G-P085-CP-01**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_operational_cockpit_gate import (
    verify_gp085_operational_cockpit_gate_static,
)
from vector.domains.cortex.operational_runtime.operational_cockpit import (
    GP085_CP01_GATE_ID_V1,
    OPERATIONAL_COCKPIT_SURFACES_V1,
    build_density_trend_rollups_7d_v1,
    build_operational_cockpit_catalog_v1,
    build_operational_cockpit_surface_checklist_v1,
    build_operational_cockpit_v1,
    build_operational_command_center_v1,
    build_operational_rbac_matrix_v1,
    build_pipeline_progression_timeline_v1,
    build_substrate_operational_heatmap_v1,
    verify_gp085_cp01_static,
    verify_operational_cockpit_surface_registry_static,
)
from vector.domains.cortex.substrate_pipeline.constants import SUBSTRATE_PIPELINE_PHASE_ORDER


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_surface_registry_has_nineteen_surfaces() -> None:
    assert len(OPERATIONAL_COCKPIT_SURFACES_V1) == 19
    assert {int(s["surface_number"]) for s in OPERATIONAL_COCKPIT_SURFACES_V1} == set(range(1, 20))


def test_gp085_cp01_static_gate() -> None:
    reg = verify_operational_cockpit_surface_registry_static()
    assert reg["passed"] is True
    out = verify_gp085_cp01_static()
    assert out["passed"] is True
    assert out["id"] == GP085_CP01_GATE_ID_V1
    assert verify_gp085_operational_cockpit_gate_static()["passed"] is True


def test_cockpit_catalog_wired_count() -> None:
    cat = build_operational_cockpit_catalog_v1()
    assert cat["primary_gate_id"] == GP085_CP01_GATE_ID_V1
    assert int(cat["surfaces_wired_count"]) >= 12
    assert int(cat["surfaces_total"]) == 19


def test_surface_checklist_all_wired_at_step_30() -> None:
    checklist = build_operational_cockpit_surface_checklist_v1()
    assert len(checklist) == 19
    assert all(s.get("wired_at_closure") for s in checklist)


def test_rbac_matrix_has_dangerous_permission() -> None:
    rb = build_operational_rbac_matrix_v1()
    assert "cortex.operational.dangerous" in rb["permissions"]


def test_doctrine_file_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md").is_file()


@pytest.mark.integration
def test_command_center_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085cp-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 CP",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    cc = build_operational_command_center_v1(db_session, tenant_id=tenant.id)
    assert cc["gate_id"] == GP085_CP01_GATE_ID_V1
    assert "maturity_class" in cc
    assert "health_dimensions" in cc
    assert "overview_badges" in cc
    assert "next_required_step" in cc


@pytest.mark.integration
def test_timeline_without_pipeline(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085cptl-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 CP TL",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    tl = build_pipeline_progression_timeline_v1(db_session, tenant_id=tenant.id)
    assert tl["gate_id"] == "G-P085-CP-03"
    assert tl["pipeline_run_id"] is None
    assert tl["phases"] == []
    assert "ascii_timeline_line" in tl


@pytest.mark.integration
def test_heatmap_and_density_trends(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085cphm-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 CP HM",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    hm = build_substrate_operational_heatmap_v1(db_session, tenant_id=tenant.id)
    assert len(hm["grid"]) == 5

    trends = build_density_trend_rollups_7d_v1(db_session, tenant_id=tenant.id)
    assert trends["window_days"] == 7
    assert "retrieval_materialization_by_day" in trends


@pytest.mark.integration
def test_full_cockpit_aggregate(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085cpagg-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 CP AGG",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    cockpit = build_operational_cockpit_v1(db_session, tenant_id=tenant.id)
    assert cockpit["surfaces_wired_count"] == 19
    assert cockpit["command_center"]["gate_id"] == GP085_CP01_GATE_ID_V1
    assert len(cockpit["surface_checklist"]) == 19
    assert cockpit["explorers_index"]["explorers_total"] == 10
    assert cockpit["overview_integration"]["gate_id"] == "G-P085-CP-03"
    assert set(SUBSTRATE_PIPELINE_PHASE_ORDER)  # import sanity
