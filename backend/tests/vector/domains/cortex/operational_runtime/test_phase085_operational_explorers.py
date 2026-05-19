"""P085-31 — Dedicated operational explorer surfaces (**G-P085-CP-02**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_operational_explorers_gate import (
    verify_gp085_operational_explorers_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_operational_explorers import (
    GP085_CP02_GATE_ID_V1,
    OPERATIONAL_EXPLORER_IDS_V1,
    OPERATIONAL_EXPLORER_SURFACES_V1,
    build_operational_explorer_v1,
    build_operational_explorers_index_v1,
    build_substrate_operational_explorers_catalog_v1,
    verify_gp085_cp02_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_explorer_registry_has_ten_surfaces() -> None:
    assert len(OPERATIONAL_EXPLORER_SURFACES_V1) == 10
    assert len(OPERATIONAL_EXPLORER_IDS_V1) == 10
    assert all(s.get("wired") for s in OPERATIONAL_EXPLORER_SURFACES_V1)


def test_gp085_cp02_static_gate() -> None:
    out = verify_gp085_cp02_static()
    assert out["passed"] is True
    assert out["id"] == GP085_CP02_GATE_ID_V1
    assert verify_gp085_operational_explorers_gate_static()["passed"] is True


def test_explorers_catalog() -> None:
    cat = build_substrate_operational_explorers_catalog_v1()
    assert cat["primary_gate_id"] == GP085_CP02_GATE_ID_V1
    assert int(cat["explorers_total"]) == 10
    assert int(cat["explorers_wired_count"]) == 10


def test_doctrine_file_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md").is_file()


@pytest.mark.integration
def test_explorers_index_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085ex-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 EX",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    idx = build_operational_explorers_index_v1(db_session, tenant_id=tenant.id)
    assert idx["gate_id"] == GP085_CP02_GATE_ID_V1
    assert idx["explorers_total"] == 10
    assert len(idx["explorers"]) == 10


@pytest.mark.integration
def test_each_explorer_tables_first_shell(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085exd-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 EX D",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    for explorer_id in OPERATIONAL_EXPLORER_IDS_V1:
        built = build_operational_explorer_v1(
            db_session,
            tenant_id=tenant.id,
            explorer_id=explorer_id,
        )
        assert built.get("surface_kind") == "operational_explorer"
        assert built.get("explorer_id") == explorer_id
        assert "columns" in built
        assert "rows" in built
        assert "summary" in built


def test_unknown_explorer_returns_error_dict() -> None:
    from unittest.mock import MagicMock

    out = build_operational_explorer_v1(
        MagicMock(),
        tenant_id=uuid.uuid4(),
        explorer_id="not_an_explorer",
    )
    assert out.get("error") == "explorer_not_found"
