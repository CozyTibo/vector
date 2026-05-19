"""P085-32 — Progression timeline + causal chains (**G-P085-CP-03**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_progression_timeline_causal_gate import (
    verify_gp085_progression_timeline_causal_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_progression_timeline_causal import (
    GP085_CP03_GATE_ID_V1,
    OPERATIONAL_STAGE_CARD_IDS_V1,
    build_causal_failure_chain_v1,
    build_operational_stage_cards_v1,
    build_overview_integration_v1,
    build_pipeline_progression_timeline_v1,
    build_progression_timeline_causal_catalog_v1,
    build_timeline_ascii_line_v1,
    verify_gp085_cp03_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_gp085_cp03_static_gate() -> None:
    out = verify_gp085_cp03_static()
    assert out["passed"] is True
    assert out["id"] == GP085_CP03_GATE_ID_V1
    assert verify_gp085_progression_timeline_causal_gate_static()["passed"] is True


def test_progression_timeline_catalog() -> None:
    cat = build_progression_timeline_causal_catalog_v1()
    assert cat["primary_gate_id"] == GP085_CP03_GATE_ID_V1
    assert len(cat["stage_card_ids"]) == 5


def test_ascii_timeline_line_format() -> None:
    phases = [
        {"phase_id": "phase_02_canonical", "glyph": "ok"},
        {"phase_id": "phase_06_tcre", "glyph": "running", "phase_annotation": "TCRE(job=abc)"},
    ]
    line = build_timeline_ascii_line_v1(phases, continuation=None)
    assert "02" in line
    assert "✓" in line
    assert "⏳" in line


def test_doctrine_file_present() -> None:
    root = _repo_root()
    assert (root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-admin-cockpit-spec.md").is_file()


@pytest.mark.integration
def test_timeline_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085tl-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 TL",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    tl = build_pipeline_progression_timeline_v1(db_session, tenant_id=tenant.id)
    assert tl["gate_id"] == GP085_CP03_GATE_ID_V1
    assert tl["pipeline_run_id"] is None
    assert "causal_failure_chain_detail" in tl


@pytest.mark.integration
def test_overview_integration_and_causal_chain(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085ov-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 OV",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    overview = build_overview_integration_v1(db_session, tenant_id=tenant.id)
    assert overview["gate_id"] == GP085_CP03_GATE_ID_V1
    assert len(overview["stage_cards"]) == len(OPERATIONAL_STAGE_CARD_IDS_V1)
    assert overview["anti_fake_green_passed"] is True
    for card in overview["stage_cards"]:
        assert card["classification"] in ("idle", "starved", "progressing")
        assert "next_required_step" in card

    causal = build_causal_failure_chain_v1(db_session, tenant_id=tenant.id)
    assert causal["surface_kind"] == "causal_failure_chain"
    assert "propagation_chain" in causal

    cards = build_operational_stage_cards_v1(db_session, tenant_id=tenant.id)
    assert len(cards) == 5
