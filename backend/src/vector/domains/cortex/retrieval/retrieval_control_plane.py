"""Phase 07 P07-23 — retrieval admin control plane catalog (**G-P07-CP-01**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-admin-control-plane-spec.md``.
Sixteen operator surfaces, RBAC matrix, OpenAPI path registry, structural aggregate.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.query_contract import RETRIEVAL_WORKLOAD_CLASSES_V1
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    build_retrieval_queries_by_legality_histogram_v1,
)
from vector.domains.cortex.retrieval.retrieval_observability import (
    build_retrieval_health_strip_v1,
    get_retrieval_queries_total_v1,
    snapshot_retrieval_metrics_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_query_audit import CortexRetrievalQueryAudit

PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_CP01_GATE_ID_V1: Final[str] = "G-P07-CP-01"

RETRIEVAL_CONTROL_PLANE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-admin-control-plane-spec.md"
)

RETRIEVAL_CONTROL_PLANE_CONTRACT_V1: Final[str] = "retrieval_control_plane_v1"

RET_CP01_RULE_ID_V1: Final[str] = "RET-CP-01"

RETRIEVAL_RBAC_PERMISSION_QUERY_V1: Final[str] = "cortex.retrieval.query"

RETRIEVAL_RBAC_PERMISSION_READ_V1: Final[str] = "cortex.retrieval.read"

RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1: Final[str] = "cortex.retrieval.index_rebuild"

_FORBIDDEN_PATH_SUBSTRINGS_CP01_V1: Final[tuple[str, ...]] = (
    "summarize",
    "prompt=",
    "/llm",
    "insight",
)

# OpenAPI path → HTTP methods → RBAC permission
RETRIEVAL_ADMIN_OPENAPI_OPERATIONS_V1: Final[dict[str, dict[str, str]]] = {
    "/admin/tenants/{tenant_id}/cortex/retrieval/legality": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/runtime-legality-matrix": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/index": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/index/rebuild": {
        "post": RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/omission-explorer": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/degradation-topology": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/ranking-selection": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/graph-binding": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/traversal-binding": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/tcre-binding": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/temporal-explorer": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/provenance-inspector": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/addressing": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/replay-inspector": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/query-contract": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/ingress": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/health": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/observability": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/overview": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/coverage": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/query": {"post": RETRIEVAL_RBAC_PERMISSION_QUERY_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/lineage-explorer": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/lineage/{artifact_kind}/{artifact_ref}": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/walks/{walk_id}/replay-lineage": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/walks/replay-equivalence": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/continuity-topology": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/control-plane": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/audit": {"get": RETRIEVAL_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/retrieval/workflows": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/readiness-economics": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/tenant-verification-slice": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/certification-pack": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
    "/admin/tenants/{tenant_id}/cortex/retrieval/program-closure": {
        "get": RETRIEVAL_RBAC_PERMISSION_READ_V1
    },
}

RETRIEVAL_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = tuple(
    sorted(RETRIEVAL_ADMIN_OPENAPI_OPERATIONS_V1)
)

RETRIEVAL_CONTROL_PLANE_SURFACES_V1: Final[tuple[dict[str, Any], ...]] = (
    {
        "surface_number": 1,
        "surface_id": "retrieval_health_strip",
        "label": "Retrieval health strip",
        "operator_question": "Is retrieval replay-safe? Index epoch? Divergence count?",
        "admin_routes": ["/health", "/overview"],
        "wired": True,
        "closure_step": 22,
    },
    {
        "surface_number": 2,
        "surface_id": "coverage_panel",
        "label": "Coverage panel",
        "operator_question": "eligible vs indexed vs queried",
        "admin_routes": ["/coverage"],
        "wired": True,
        "closure_step": 20,
    },
    {
        "surface_number": 3,
        "surface_id": "policy_digest_inspector",
        "label": "Policy digest inspector",
        "operator_question": "Active retrieval_policy_digest, caps",
        "admin_routes": ["/legality", "/query-contract", "/ranking-selection", "/index"],
        "wired": True,
        "closure_step": 13,
    },
    {
        "surface_number": 4,
        "surface_id": "query_debugger",
        "label": "Query debugger",
        "operator_question": "Why this query returned these hits",
        "admin_routes": ["/query"],
        "wired": True,
        "closure_step": 6,
    },
    {
        "surface_number": 5,
        "surface_id": "provenance_inspector",
        "label": "Provenance inspector",
        "operator_question": "Per-hit upstream digests + legality",
        "admin_routes": ["/provenance-inspector"],
        "wired": True,
        "closure_step": 10,
    },
    {
        "surface_number": 6,
        "surface_id": "replay_inspector",
        "label": "Replay inspector",
        "operator_question": "Twin run diff, retrieval_query_replay_identity",
        "admin_routes": ["/replay-inspector"],
        "wired": True,
        "closure_step": 18,
    },
    {
        "surface_number": 7,
        "surface_id": "omission_explorer",
        "label": "Omission explorer",
        "operator_question": "RD-* classes + counts + triggers",
        "admin_routes": ["/omission-explorer"],
        "wired": True,
        "closure_step": 13,
    },
    {
        "surface_number": 8,
        "surface_id": "temporal_explorer",
        "label": "Temporal explorer",
        "operator_question": "t_as_of, windows, epoch pins",
        "admin_routes": ["/temporal-explorer"],
        "wired": True,
        "closure_step": 11,
    },
    {
        "surface_number": 9,
        "surface_id": "lineage_chain_explorer",
        "label": "Lineage chain explorer",
        "operator_question": "terminal → root chain",
        "admin_routes": ["/lineage-explorer", "/lineage/{artifact_kind}/{artifact_ref}"],
        "wired": True,
        "closure_step": 21,
    },
    {
        "surface_number": 10,
        "surface_id": "traversal_binding_panel",
        "label": "Traversal binding panel",
        "operator_question": "walk_id, hop coverage, epoch match",
        "admin_routes": ["/traversal-binding"],
        "wired": True,
        "closure_step": 16,
    },
    {
        "surface_number": 11,
        "surface_id": "tcre_binding_panel",
        "label": "TCRE binding panel",
        "operator_question": "job id, chain id, chronology class",
        "admin_routes": ["/tcre-binding"],
        "wired": True,
        "closure_step": 15,
    },
    {
        "surface_number": 12,
        "surface_id": "degradation_topology",
        "label": "Degradation topology",
        "operator_question": "Rollup graph of RD-* / upstream",
        "admin_routes": ["/degradation-topology"],
        "wired": True,
        "closure_step": 19,
    },
    {
        "surface_number": 13,
        "surface_id": "query_audit_trail",
        "label": "Query audit trail",
        "operator_question": "Historical receipts (filter legality)",
        "admin_routes": ["/audit"],
        "wired": True,
        "closure_step": 22,
    },
    {
        "surface_number": 14,
        "surface_id": "legality_matrix_view",
        "label": "Legality matrix view",
        "operator_question": "R-LEG predicates + forbidden deployments",
        "admin_routes": ["/runtime-legality-matrix", "/legality"],
        "wired": True,
        "closure_step": 7,
    },
    {
        "surface_number": 15,
        "surface_id": "readiness_economics",
        "label": "Readiness economics",
        "operator_question": "Numeric readiness receipt (mirror P05/P06)",
        "admin_routes": [
            "/readiness-economics",
            "/tenant-verification-slice",
            "/certification-pack",
            "/program-closure",
        ],
        "wired": True,
        "closure_step": 30,
    },
    {
        "surface_number": 16,
        "surface_id": "control_plane_aggregate",
        "label": "Control plane aggregate",
        "operator_question": "Queue depth, workload histogram",
        "admin_routes": ["/control-plane"],
        "wired": True,
        "closure_step": 23,
    },
)

RETRIEVAL_OPERATOR_WORKFLOWS_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "workflow_id": "W1",
        "title": "Debug why empty result?",
        "steps": "Query debugger → RESOLVE trail → Omission explorer → TCRE/Graph cross-link",
    },
    {
        "workflow_id": "W2",
        "title": "Verify replay safety before Phase 08",
        "steps": "replay_equivalence workload → Replay inspector → Legality matrix R-LEG green",
    },
    {
        "workflow_id": "W3",
        "title": "Index rebuild (dangerous)",
        "steps": "tenant + index_epoch bump → confirmation phrase → readiness economics duration",
    },
)


def retrieval_admin_openapi_path_v1() -> Path:
    """Generated OpenAPI 3 document for admin retrieval paths."""
    tail = (
        "DOCS",
        "cortex",
        "retrieval",
        "schemas",
        "generated",
        "retrieval_admin_v1.openapi.json",
    )
    here = Path(__file__).resolve()
    for root in [here, *here.parents]:
        candidate = root.joinpath(*tail)
        if candidate.is_file():
            return candidate
    for root in [here, *here.parents]:
        candidate = root / "backend" / Path(*tail)
        if candidate.is_file():
            return candidate
    return here.parents[5].joinpath(*tail)


def build_retrieval_admin_openapi_document_v1() -> dict[str, Any]:
    """Build OpenAPI 3.0 document for **G-P07-CP-01** matrix."""
    paths: dict[str, Any] = {}
    for ep, methods in sorted(RETRIEVAL_ADMIN_OPENAPI_OPERATIONS_V1.items()):
        entry: dict[str, Any] = {}
        for method, permission in sorted(methods.items()):
            entry[method] = {
                "operationId": f"retrieval_{method}_{len(paths)}",
                "summary": f"Retrieval admin {method.upper()} {ep}",
                "security": [{"admin_basic": []}],
                "x-rbac-permission": permission,
                "responses": {"200": {"description": "OK"}},
            }
        paths[ep] = entry
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Vector Cortex Retrieval Admin API",
            "version": "1.0.0",
            "description": "Phase 07 retrieval operator control plane surfaces",
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "admin_basic": {"type": "http", "scheme": "basic"},
            }
        },
    }


def write_retrieval_admin_openapi_v1(path: Path | None = None) -> Path:
    target = path or retrieval_admin_openapi_path_v1()
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = build_retrieval_admin_openapi_document_v1()
    target.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def build_retrieval_rbac_matrix_v1() -> dict[str, Any]:
    return {
        "permissions": {
            RETRIEVAL_RBAC_PERMISSION_QUERY_V1: "execute retrieval queries (POST /query)",
            RETRIEVAL_RBAC_PERMISSION_READ_V1: "all GET admin retrieval surfaces",
            RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1: "dangerous index rebuild (POST /index/rebuild)",
        },
        "dangerous_operations": [
            {
                "path": "/admin/tenants/{tenant_id}/cortex/retrieval/index/rebuild",
                "method": "post",
                "permission": RETRIEVAL_RBAC_PERMISSION_INDEX_REBUILD_V1,
            }
        ],
    }


def build_retrieval_control_plane_surface_checklist_v1() -> list[dict[str, Any]]:
    """Sixteen surfaces with wiring status for operator closure checklist."""
    prefix = "/admin/tenants/{tenant_id}/cortex/retrieval"
    out: list[dict[str, Any]] = []
    for surface in RETRIEVAL_CONTROL_PLANE_SURFACES_V1:
        routes = surface.get("admin_routes") or []
        openapi_paths = [f"{prefix}{route}" for route in routes]
        out.append(
            {
                **surface,
                "openapi_paths": openapi_paths,
                "wired_at_closure": bool(surface.get("wired")),
            }
        )
    return out


def list_retrieval_query_audit_trail_v1(
    session: Session,
    *,
    tenant_id: Any,
    limit: int = 50,
    result_legality_class: str | None = None,
) -> list[dict[str, Any]]:
    """Historical query audit rows for surface #13."""
    cap = max(1, min(int(limit), 200))
    stmt = (
        select(CortexRetrievalQueryAudit)
        .where(CortexRetrievalQueryAudit.tenant_id == tenant_id)
        .order_by(CortexRetrievalQueryAudit.created_at.desc())
        .limit(cap)
    )
    if result_legality_class:
        stmt = stmt.where(
            CortexRetrievalQueryAudit.result_legality_class == str(result_legality_class)
        )
    rows = session.scalars(stmt).all()
    return [
        {
            "audit_id": str(row.id),
            "receipt_digest": row.receipt_digest,
            "query_envelope_hash": row.query_envelope_hash,
            "result_legality_class": row.result_legality_class,
            "retrieval_query_replay_identity": row.retrieval_query_replay_identity,
            "workload_class": row.workload_class,
            "intent": row.intent,
            "hit_count": int(row.hit_count),
            "omission_count": int(row.omission_count),
            "duration_ms": int(row.duration_ms),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def build_retrieval_workload_histogram_v1(
    session: Session,
    *,
    tenant_id: Any,
) -> dict[str, int]:
    """Workload histogram from durable audit trail (integers only)."""
    hist = {wl: 0 for wl in sorted(RETRIEVAL_WORKLOAD_CLASSES_V1)}
    rows = session.execute(
        select(CortexRetrievalQueryAudit.workload_class, func.count())
        .where(CortexRetrievalQueryAudit.tenant_id == tenant_id)
        .group_by(CortexRetrievalQueryAudit.workload_class)
    ).all()
    for wl, count in rows:
        key = str(wl)
        if key in hist:
            hist[key] = int(count)
        else:
            hist[key] = int(count)
    return hist


def build_retrieval_control_plane_v1(
    session: Session,
    *,
    tenant_id: Any,
) -> dict[str, Any]:
    """Structural control plane aggregate (surface #16)."""
    checklist = build_retrieval_control_plane_surface_checklist_v1()
    wired_count = sum(1 for s in checklist if s.get("wired_at_closure"))
    workload_hist = build_retrieval_workload_histogram_v1(session, tenant_id=tenant_id)
    metrics = snapshot_retrieval_metrics_v1()
    return {
        "retrieval_control_plane_contract": RETRIEVAL_CONTROL_PLANE_CONTRACT_V1,
        "retrieval_control_plane_runtime_schema_version": (
            PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_CP01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_CONTROL_PLANE_SPEC_REF_V1,
        "tenant_id": str(tenant_id),
        "surface_checklist": checklist,
        "surfaces_wired_count": wired_count,
        "surfaces_total": len(RETRIEVAL_CONTROL_PLANE_SURFACES_V1),
        "workload_histogram": workload_hist,
        "queries_by_legality_index_proxy": build_retrieval_queries_by_legality_histogram_v1(
            session, tenant_id=tenant_id
        ),
        "query_queue_depth_proxy": int(metrics.get("retrieval_queries_total") or 0),
        "global_retrieval_queries_total": get_retrieval_queries_total_v1(),
        "health_strip": build_retrieval_health_strip_v1(session, tenant_id=tenant_id),
        "metrics": metrics,
        "rbac_matrix": build_retrieval_rbac_matrix_v1(),
        "operator_workflows": list(RETRIEVAL_OPERATOR_WORKFLOWS_V1),
        "openapi_document_path": str(retrieval_admin_openapi_path_v1()),
        "openapi_path_count": len(RETRIEVAL_ADMIN_OPENAPI_PATHS_V1),
    }


def verify_retrieval_control_plane_surface_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(RETRIEVAL_CONTROL_PLANE_SURFACES_V1) != 16:
        errors.append("surface_count_not_16")
    numbers = [int(s["surface_number"]) for s in RETRIEVAL_CONTROL_PLANE_SURFACES_V1]
    if sorted(numbers) != list(range(1, 17)):
        errors.append("surface_numbers_not_1_to_16")
    wired = [s for s in RETRIEVAL_CONTROL_PLANE_SURFACES_V1 if s.get("wired")]
    if len(wired) != 16:
        errors.append(f"expected_16_wired_got_{len(wired)}")
    return _cp_meta("retrieval_control_plane_surface_registry", errors)


def verify_gp07_cp01_retrieval_control_plane_rbac_static() -> dict[str, Any]:
    """**G-P07-CP-01** — OpenAPI matrix + RBAC + sixteen surfaces."""
    errors: list[str] = []
    reg = verify_retrieval_control_plane_surface_registry_static()
    if not reg.get("passed"):
        errors.extend(reg.get("detail", {}).get("errors") or [])

    for sub in _FORBIDDEN_PATH_SUBSTRINGS_CP01_V1:
        for p in RETRIEVAL_ADMIN_OPENAPI_PATHS_V1:
            if sub in p.lower():
                errors.append(f"forbidden_substring:{sub}:{p}")

    openapi_path = retrieval_admin_openapi_path_v1()
    if not openapi_path.is_file():
        try:
            write_retrieval_admin_openapi_v1(openapi_path)
        except OSError as exc:
            errors.append(f"openapi_write_failed:{exc}")
    if not openapi_path.is_file():
        errors.append(f"missing_openapi:{openapi_path}")
    else:
        try:
            doc = json.loads(openapi_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"openapi_json_invalid:{exc}")
            doc = {}
        paths = doc.get("paths") if isinstance(doc, dict) else None
        if not isinstance(paths, dict):
            errors.append("openapi_paths_missing")
        else:
            for ep, methods in RETRIEVAL_ADMIN_OPENAPI_OPERATIONS_V1.items():
                if ep not in paths:
                    errors.append(f"missing_path:{ep}")
                    continue
                entry = paths[ep]
                if not isinstance(entry, dict):
                    errors.append(f"path_not_object:{ep}")
                    continue
                for method, permission in methods.items():
                    if method not in entry:
                        errors.append(f"missing_method:{ep}:{method}")
                        continue
                    op = entry[method]
                    if not isinstance(op, dict):
                        errors.append(f"op_not_object:{ep}:{method}")
                        continue
                    if op.get("security") != [{"admin_basic": []}]:
                        errors.append(f"rbac_security_not_admin_basic:{ep}:{method}")
                    if op.get("x-rbac-permission") != permission:
                        errors.append(f"rbac_permission_mismatch:{ep}:{method}")

    rb = build_retrieval_rbac_matrix_v1()
    if RETRIEVAL_RBAC_PERMISSION_QUERY_V1 not in rb.get("permissions", {}):
        errors.append("rbac_query_permission_missing")

    return _cp_meta("gp07_cp01_retrieval_control_plane_rbac_openapi", errors)


def _cp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_CP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "path_count": len(RETRIEVAL_ADMIN_OPENAPI_PATHS_V1),
            "surface_count": len(RETRIEVAL_CONTROL_PLANE_SURFACES_V1),
        },
    }
