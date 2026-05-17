"""Phase 07 P07-24 — operator workflows + debugger SPA route law.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-admin-control-plane-spec.md`` §Workflows.
**RET-WF-01** W1–W3 flows + answerability table; **RET-WF-02** dangerous index rebuild gate;
**RET-WF-03** guided ``RD-*`` remediation links to admin surfaces.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
from vector.domains.cortex.retrieval.retrieval_control_plane import (
    RETRIEVAL_CONTROL_PLANE_SPEC_REF_V1,
    RETRIEVAL_CONTROL_PLANE_SURFACES_V1,
    RETRIEVAL_OPERATOR_WORKFLOWS_V1,
    RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1,
)

PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_WF01_GATE_ID_V1: Final[str] = "G-P07-WF-01"

RETRIEVAL_OPERATOR_WORKFLOWS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-admin-control-plane-spec.md"
)

RETRIEVAL_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1: Final[str] = (
    "DOCS/cortex/10-admin/dangerous-action-safety-model.md"
)

RET_WF01_RULE_ID_V1: Final[str] = "RET-WF-01"

RET_WF02_RULE_ID_V1: Final[str] = "RET-WF-02"

RET_WF03_RULE_ID_V1: Final[str] = "RET-WF-03"

RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1: Final[str] = "EXECUTE RETRIEVAL INDEX REBUILD"

# SPA path segment under ``.../cortex/retrieval/{spa_route}``
RETRIEVAL_SURFACE_SPA_ROUTES_V1: Final[dict[str, str]] = {
    "retrieval_health_strip": "",
    "coverage_panel": "coverage",
    "policy_digest_inspector": "policy",
    "query_debugger": "query",
    "provenance_inspector": "provenance",
    "replay_inspector": "replay",
    "omission_explorer": "omissions",
    "temporal_explorer": "temporal",
    "lineage_chain_explorer": "lineage",
    "traversal_binding_panel": "traversal",
    "tcre_binding_panel": "tcre",
    "degradation_topology": "degradation",
    "query_audit_trail": "audit",
    "legality_matrix_view": "legality",
    "readiness_economics": "readiness",
    "control_plane_aggregate": "control-plane",
}

RETRIEVAL_OPERATOR_ANSWERABILITY_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "question": "Why was evidence excluded?",
        "surface_id": "omission_explorer",
        "spa_route": "omissions",
    },
    {
        "question": "What degraded?",
        "surface_id": "degradation_topology",
        "spa_route": "degradation",
    },
    {
        "question": "What replay posture existed?",
        "surface_id": "provenance_inspector",
        "spa_route": "provenance",
    },
    {
        "question": "What continuity guarantees?",
        "surface_id": "tcre_binding_panel",
        "spa_route": "tcre",
    },
    {
        "question": "What lineage path?",
        "surface_id": "lineage_chain_explorer",
        "spa_route": "lineage",
    },
    {
        "question": "What traversal coverage?",
        "surface_id": "traversal_binding_panel",
        "spa_route": "traversal",
    },
)

RETRIEVAL_WORKFLOW_SPA_STEPS_V1: Final[dict[str, list[dict[str, str]]]] = {
    "W1": [
        {"label": "Query debugger", "spa_route": "query", "phase": "RESOLVE"},
        {"label": "Omission explorer", "spa_route": "omissions"},
        {"label": "TCRE binding", "spa_route": "tcre"},
        {"label": "Degradation topology", "spa_route": "degradation"},
    ],
    "W2": [
        {"label": "Replay inspector", "spa_route": "replay"},
        {"label": "Legality matrix", "spa_route": "legality"},
        {"label": "Run replay_equivalence", "spa_route": "query", "workload_class": "replay_equivalence"},
    ],
    "W3": [
        {"label": "Readiness economics", "spa_route": "readiness"},
        {"label": "Index rebuild (dangerous)", "spa_route": "index"},
    ],
}

RETRIEVAL_RD_REMEDIATION_LINKS_V1: Final[dict[str, dict[str, str]]] = {
    "RD-CAP-HITS": {
        "spa_route": "policy",
        "hint": "Review selection_policy max_hits cap in policy digest inspector.",
    },
    "RD-CAP-CHRON": {"spa_route": "policy", "hint": "Chronology row cap exceeded — adjust caps."},
    "RD-CAP-EDGE": {"spa_route": "policy", "hint": "Edge cap exceeded — adjust caps."},
    "RD-CAP-LINEAGE": {"spa_route": "lineage", "hint": "Lineage hop cap truncated — lineage explorer."},
    "RD-TCRE-GAP": {
        "spa_route": "tcre",
        "hint": "Upstream TCRE reconstruction gap — inspect TCRE binding panel.",
    },
    "RD-GRAPH-ORPHAN": {
        "spa_route": "traversal",
        "hint": "Graph orphan — traversal/graph binding surfaces.",
    },
    "RD-TRAVERSAL-IDLE": {"spa_route": "traversal", "hint": "Traversal never executed for scope."},
    "RD-TRAVERSAL-BLOCKED": {"spa_route": "traversal", "hint": "Traversal blocked by policy."},
    "RD-LINEAGE-GAP": {"spa_route": "lineage", "hint": "Incomplete lineage chain — lineage explorer."},
    "RD-REPLAY-UNSAFE": {"spa_route": "replay", "hint": "Replay unsafe — replay inspector + W2 workflow."},
    "RD-REPLAY-TWIN": {"spa_route": "replay", "hint": "Twin divergence — replay inspector (G-P07-REPLAY-01)."},
    "RD-INDEX-STALE": {"spa_route": "index", "hint": "Index epoch stale — coverage or index rebuild (W3)."},
    "RD-POLICY-MISMATCH": {"spa_route": "policy", "hint": "Policy digest pin mismatch."},
    "RD-ADDRESSING-UNRESOLVED": {"spa_route": "query", "hint": "Addressing unresolved — query debugger RESOLVE."},
    "RD-TEMPORAL-FUTURE": {"spa_route": "temporal", "hint": "Future-dated temporal scope."},
    "RD-TEMPORAL-PIN": {"spa_route": "temporal", "hint": "Temporal pin violation."},
}


class RetrievalOperatorWorkflowsError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def assert_retrieval_index_rebuild_confirmation_v1(confirmation_phrase: str | None) -> None:
    """**RET-WF-02** — dangerous index rebuild requires exact confirmation phrase."""
    if (confirmation_phrase or "").strip() != RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1:
        raise RetrievalOperatorWorkflowsError(
            "confirmation_phrase_invalid",
            detail={"expected": RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1},
        )


def build_retrieval_spa_route_registry_v1() -> list[dict[str, Any]]:
    """Map all sixteen control-plane surfaces to SPA routes (**Step 24 done-when**)."""
    routes: list[dict[str, Any]] = []
    for surface in RETRIEVAL_CONTROL_PLANE_SURFACES_V1:
        sid = str(surface["surface_id"])
        spa = RETRIEVAL_SURFACE_SPA_ROUTES_V1.get(sid, sid.replace("_", "-"))
        routes.append(
            {
                "surface_number": surface["surface_number"],
                "surface_id": sid,
                "label": surface["label"],
                "spa_route": spa,
                "spa_path": f"/admin/tenants/{{tenant_id}}/cortex/retrieval/{spa}" if spa else (
                    "/admin/tenants/{tenant_id}/cortex/retrieval"
                ),
                "admin_api_routes": list(surface.get("admin_routes") or []),
                "wired": bool(surface.get("wired")),
            }
        )
    routes.append(
        {
            "surface_id": "operator_workflows_hub",
            "label": "Operator workflows",
            "spa_route": "workflows",
            "spa_path": "/admin/tenants/{tenant_id}/cortex/retrieval/workflows",
            "admin_api_routes": ["/workflows"],
            "wired": True,
        }
    )
    routes.append(
        {
            "surface_id": "index_rebuild_dangerous",
            "label": "Index rebuild (dangerous)",
            "spa_route": "index",
            "spa_path": "/admin/tenants/{tenant_id}/cortex/retrieval/index",
            "admin_api_routes": ["/index", "/index/rebuild"],
            "wired": True,
            "dangerous": True,
            "permission": RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1,
        }
    )
    return routes


def build_retrieval_operator_workflows_v1() -> list[dict[str, Any]]:
    """W1–W3 with SPA step links."""
    out: list[dict[str, Any]] = []
    for wf in RETRIEVAL_OPERATOR_WORKFLOWS_V1:
        wid = str(wf["workflow_id"])
        out.append(
            {
                **wf,
                "spa_steps": list(RETRIEVAL_WORKFLOW_SPA_STEPS_V1.get(wid, ())),
                "dangerous": wid == "W3",
            }
        )
    return out


def build_retrieval_rd_remediation_links_v1() -> list[dict[str, Any]]:
    """Guided remediation links for every registered ``RD-*`` code."""
    links: list[dict[str, Any]] = []
    for code in sorted(RETRIEVAL_RD_CODES_REGISTRY_V1):
        meta = RETRIEVAL_RD_REMEDIATION_LINKS_V1.get(code, {})
        links.append(
            {
                "retrieval_omission_class": code,
                "spa_route": meta.get("spa_route", "omissions"),
                "hint": meta.get("hint", "See omission explorer and degradation topology."),
            }
        )
    return links


def build_retrieval_operator_workflows_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin ``GET .../workflows`` — workflows, answerability, remediation, SPA registry."""
    registry = build_retrieval_spa_route_registry_v1()
    wired_spa = [r for r in registry if r.get("wired") and r.get("spa_route") is not None]
    return {
        "retrieval_operator_workflows_runtime_schema_version": (
            PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_WF01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_OPERATOR_WORKFLOWS_SPEC_REF_V1,
        "control_plane_spec_ref": RETRIEVAL_CONTROL_PLANE_SPEC_REF_V1,
        "tenant_id": tenant_id,
        "workflows": build_retrieval_operator_workflows_v1(),
        "answerability_table": list(RETRIEVAL_OPERATOR_ANSWERABILITY_V1),
        "remediation_links": build_retrieval_rd_remediation_links_v1(),
        "spa_route_registry": registry,
        "spa_routes_wired_count": len(wired_spa),
        "surfaces_with_spa_routes": len(
            [r for r in registry if r.get("surface_id") != "operator_workflows_hub"]
        ),
        "dangerous_actions": [
            {
                "action_id": "index_rebuild",
                "permission": RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1,
                "confirmation_phrase": RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
                "doctrine_ref": RETRIEVAL_DANGEROUS_ACTION_SAFETY_MODEL_REF_V1,
                "spa_route": "index",
                "workflow_id": "W3",
            }
        ],
    }


def list_remediation_links_for_omissions_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach guided remediation links to omission rows for query debugger UI."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for om in omissions:
        if not isinstance(om, dict):
            continue
        rd = str(om.get("retrieval_omission_class") or "")
        if not rd or rd in seen:
            continue
        seen.add(rd)
        meta = RETRIEVAL_RD_REMEDIATION_LINKS_V1.get(rd, {})
        out.append(
            {
                "retrieval_omission_class": rd,
                "spa_route": meta.get("spa_route", "omissions"),
                "hint": meta.get("hint", ""),
            }
        )
    return out


def _wf_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_WF01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_wf01_spa_routes_complete_static() -> dict[str, Any]:
    """**G-P07-WF-01** — sixteen surfaces have SPA routes; workflows + dangerous gate."""
    errors: list[str] = []
    registry = build_retrieval_spa_route_registry_v1()
    surface_routes = [
        r for r in registry if r.get("surface_id") not in ("operator_workflows_hub", "index_rebuild_dangerous")
    ]
    if len(surface_routes) != 16:
        errors.append(f"surface_route_count:{len(surface_routes)}")
    for surface in RETRIEVAL_CONTROL_PLANE_SURFACES_V1:
        sid = str(surface["surface_id"])
        if sid not in RETRIEVAL_SURFACE_SPA_ROUTES_V1:
            errors.append(f"missing_spa_map:{sid}")
    if len(RETRIEVAL_OPERATOR_ANSWERABILITY_V1) != 6:
        errors.append("answerability_count")
    if len(RETRIEVAL_OPERATOR_WORKFLOWS_V1) != 3:
        errors.append("workflow_count")
    for code in RETRIEVAL_RD_CODES_REGISTRY_V1:
        if code not in RETRIEVAL_RD_REMEDIATION_LINKS_V1:
            errors.append(f"missing_remediation:{code}")
    try:
        assert_retrieval_index_rebuild_confirmation_v1(RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1)
    except RetrievalOperatorWorkflowsError:
        errors.append("confirmation_phrase_should_pass")
    try:
        assert_retrieval_index_rebuild_confirmation_v1("wrong")
        errors.append("confirmation_phrase_should_fail")
    except RetrievalOperatorWorkflowsError:
        pass
    cat = build_retrieval_operator_workflows_catalog_v1()
    if cat["gate_id"] != GP07_WF01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _wf_meta("gp07_wf01_spa_routes_complete", errors)
