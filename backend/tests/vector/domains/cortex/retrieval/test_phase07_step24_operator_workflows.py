"""P07-24 — operator workflows + debugger SPA routes (**G-P07-WF-01**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.retrieval_control_plane import (
    RETRIEVAL_CONTROL_PLANE_SURFACES_V1,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    GP07_WF01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
    RETRIEVAL_OPERATOR_ANSWERABILITY_V1,
    RETRIEVAL_OPERATOR_WORKFLOWS_V1,
    RETRIEVAL_RD_REMEDIATION_LINKS_V1,
    RETRIEVAL_SURFACE_SPA_ROUTES_V1,
    RetrievalOperatorWorkflowsError,
    assert_retrieval_index_rebuild_confirmation_v1,
    build_retrieval_operator_workflows_catalog_v1,
    build_retrieval_spa_route_registry_v1,
    list_remediation_links_for_omissions_v1,
    verify_gp07_wf01_spa_routes_complete_static,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-admin-control-plane-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION >= 1


def test_gp07_wf01_static_gate() -> None:
    out = verify_gp07_wf01_spa_routes_complete_static()
    assert out["passed"] is True
    assert out["id"] == GP07_WF01_GATE_ID_V1


def test_sixteen_surfaces_have_spa_routes() -> None:
    registry = build_retrieval_spa_route_registry_v1()
    surface_rows = [
        r
        for r in registry
        if r.get("surface_id") not in ("operator_workflows_hub", "index_rebuild_dangerous")
    ]
    assert len(surface_rows) == 16
    for surface in RETRIEVAL_CONTROL_PLANE_SURFACES_V1:
        assert str(surface["surface_id"]) in RETRIEVAL_SURFACE_SPA_ROUTES_V1


def test_workflows_catalog_shape() -> None:
    tid = str(uuid.uuid4())
    cat = build_retrieval_operator_workflows_catalog_v1(tenant_id=tid)
    assert cat["gate_id"] == GP07_WF01_GATE_ID_V1
    assert cat["tenant_id"] == tid
    assert len(cat["workflows"]) == len(RETRIEVAL_OPERATOR_WORKFLOWS_V1) == 3
    assert len(cat["answerability_table"]) == len(RETRIEVAL_OPERATOR_ANSWERABILITY_V1) == 6
    assert len(cat["remediation_links"]) == len(RETRIEVAL_RD_CODES_REGISTRY_V1)
    for code in RETRIEVAL_RD_CODES_REGISTRY_V1:
        assert code in RETRIEVAL_RD_REMEDIATION_LINKS_V1


def test_index_rebuild_confirmation_gate() -> None:
    assert_retrieval_index_rebuild_confirmation_v1(RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1)
    with pytest.raises(RetrievalOperatorWorkflowsError) as exc:
        assert_retrieval_index_rebuild_confirmation_v1("wrong phrase")
    assert exc.value.code == "confirmation_phrase_invalid"


def test_remediation_links_for_omissions_dedupes() -> None:
    links = list_remediation_links_for_omissions_v1(
        [
            {"retrieval_omission_class": "RD-CAP-HITS"},
            {"retrieval_omission_class": "RD-CAP-HITS"},
            {"retrieval_omission_class": "RD-TCRE-GAP"},
        ]
    )
    assert len(links) == 2
    assert links[0]["spa_route"] == "policy"
    assert links[1]["spa_route"] == "tcre"


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (
        root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-admin-control-plane-spec.md"
    ).read_text(encoding="utf-8")
    assert "W1" in text and "W2" in text and "W3" in text
    assert "§Workflows" in text or "## §Workflows" in text


def test_workflow_spa_steps_present() -> None:
    cat = build_retrieval_operator_workflows_catalog_v1()
    for wf in cat["workflows"]:
        assert wf.get("spa_steps")
        if wf["workflow_id"] == "W3":
            assert wf.get("dangerous") is True
