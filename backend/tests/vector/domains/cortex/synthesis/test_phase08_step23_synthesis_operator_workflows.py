"""Phase 08 Step 23 — synthesis operator workflows + debugger SPA routes."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from vector.domains.cortex.synthesis.synthesis_bounded_caps import SYNTHESIS_SD_CODES_REGISTRY_V1
from vector.domains.cortex.synthesis.synthesis_control_plane import SYNTHESIS_CONTROL_PLANE_SURFACES_V1
from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
    GP08_WF01_GATE_ID_V1,
    PHASE08_SYNTHESIS_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_OPERATOR_ANSWERABILITY_V1,
    SYNTHESIS_OPERATOR_WORKFLOWS_V1,
    SYNTHESIS_SD_REMEDIATION_LINKS_V1,
    SYNTHESIS_SURFACE_SPA_ROUTES_V1,
    SynthesisOperatorWorkflowsError,
    assert_synthesis_resynthesize_confirmation_v1,
    build_synthesis_operator_workflows_catalog_v1,
    build_synthesis_resynthesize_confirmation_phrase_v1,
    build_synthesis_spa_route_registry_v1,
    list_remediation_links_for_sd_omissions_v1,
    verify_gp08_wf01_synthesis_spa_routes_complete_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-admin-control-plane-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION >= 1


def test_gp08_wf01_static_gate() -> None:
    out = verify_gp08_wf01_synthesis_spa_routes_complete_static()
    assert out["passed"] is True
    assert out["id"] == GP08_WF01_GATE_ID_V1


def test_sixteen_surfaces_have_spa_routes() -> None:
    registry = build_synthesis_spa_route_registry_v1()
    surface_rows = [
        r
        for r in registry
        if r.get("surface_id")
        not in ("operator_workflows_hub", "resynthesize_dangerous", "sd_omission_explorer")
    ]
    assert len(surface_rows) == 16
    for surface in SYNTHESIS_CONTROL_PLANE_SURFACES_V1:
        assert str(surface["surface_id"]) in SYNTHESIS_SURFACE_SPA_ROUTES_V1


def test_workflows_catalog_shape() -> None:
    tid = str(uuid.uuid4())
    cat = build_synthesis_operator_workflows_catalog_v1(tenant_id=tid, tenant_slug="acme")
    assert cat["gate_id"] == GP08_WF01_GATE_ID_V1
    assert cat["tenant_id"] == tid
    assert len(cat["workflows"]) == len(SYNTHESIS_OPERATOR_WORKFLOWS_V1) == 4
    assert len(cat["answerability_table"]) == len(SYNTHESIS_OPERATOR_ANSWERABILITY_V1) == 6
    assert len(cat["remediation_links"]) == len(SYNTHESIS_SD_CODES_REGISTRY_V1)
    for code in SYNTHESIS_SD_CODES_REGISTRY_V1:
        assert code in SYNTHESIS_SD_REMEDIATION_LINKS_V1


def test_resynthesize_confirmation_gate() -> None:
    phrase = build_synthesis_resynthesize_confirmation_phrase_v1("acme")
    assert phrase == "RE-SYNTHESIZE acme"
    assert_synthesis_resynthesize_confirmation_v1(phrase, tenant_slug="acme")
    with pytest.raises(SynthesisOperatorWorkflowsError) as exc:
        assert_synthesis_resynthesize_confirmation_v1("wrong", tenant_slug="acme")
    assert exc.value.code == "confirmation_phrase_invalid"


def test_remediation_links_for_omissions_dedupes() -> None:
    links = list_remediation_links_for_sd_omissions_v1(
        [
            {"sd_code": "SD-CITE-GAP"},
            {"sd_code": "SD-CITE-GAP"},
            {"sd_code": "SD-SCOPE-EMPTY"},
        ]
    )
    assert len(links) == 2
    assert links[0]["spa_route"] == "citations"


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-admin-control-plane-spec.md").read_text(
        encoding="utf-8",
    )
    assert "W1" in text and "W4" in text
    assert "§Workflows" in text or "## §Workflows" in text


def test_workflow_spa_steps_present() -> None:
    cat = build_synthesis_operator_workflows_catalog_v1()
    for wf in cat["workflows"]:
        assert wf.get("spa_steps")
        if wf["workflow_id"] == "W3":
            assert wf.get("dangerous") is True
