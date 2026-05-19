"""Phase 08.5 P085-30 — admin operational cockpit (**G-P085-CP-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-admin-cockpit-spec.md``.
Nineteen operator surfaces, RBAC matrix, command center aggregate, DB-backed rollups.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.phase_boundaries import (
    list_registered_cesp_admin_route_paths_v1,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score import (
    evaluate_autonomous_recovery_score_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions import (
    evaluate_operational_health_dimensions_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    build_operational_maturity_card_v1,
    evaluate_multidimensional_operational_maturity_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_explorers import (
    build_operational_explorers_index_v1,
)
from vector.domains.cortex.operational_runtime.substrate_progression_timeline_causal import (
    build_overview_integration_v1,
    build_pipeline_progression_timeline_v1,
)

__all__ = (
    "build_density_trend_rollups_7d_v1",
    "build_operational_cockpit_catalog_v1",
    "build_operational_cockpit_v1",
    "build_operational_command_center_v1",
    "build_pipeline_progression_timeline_v1",
    "build_substrate_operational_heatmap_v1",
    "verify_gp085_cp01_static",
    "verify_operational_cockpit_surface_registry_static",
)
from vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification import (
    build_synthesis_idle_classification_panel_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    detect_stalled_substrate_pipelines_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE085_OPERATIONAL_COCKPIT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_OPERATIONAL_COCKPIT_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-admin-cockpit-spec.md"
)

GP085_CP01_GATE_ID_V1: Final[str] = "G-P085-CP-01"

OPERATIONAL_COCKPIT_CONTRACT_V1: Final[str] = "operational_cockpit_v1"

P085_CP01_RULE_ID_V1: Final[str] = "P085-CP-01"

OPERATIONAL_RBAC_PERMISSION_READ_V1: Final[str] = "cortex.operational.read"
OPERATIONAL_RBAC_PERMISSION_DANGEROUS_V1: Final[str] = "cortex.operational.dangerous"

_FORBIDDEN_PATH_SUBSTRINGS_CP01_V1: Final[tuple[str, ...]] = (
    "summarize",
    "prompt=",
    "/llm/generate",
    "insight",
    "semantic-summary",
)

_SUBSTRATE_PIPELINE_ADMIN_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/runs",
    "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/runs/{pipeline_run_id}",
    "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/runs/{pipeline_run_id}/stuck-phases",
    "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/continuation",
    "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/operational-health",
    "/admin/catalog/cortex/substrate-pipeline/stalled",
    "/admin/catalog/cortex/substrate-pipeline/stalled/{pipeline_run_id}/recover",
    "/admin/catalog/cortex/substrate-pipeline/runs/{pipeline_run_id}/recovery-receipts",
    "/admin/catalog/cortex/substrate-pipeline/continuity-watchdog/run",
)

_COCKPIT_AGGREGATE_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/operational-runtime/cockpit",
    "/admin/catalog/cortex/operational-runtime/cockpit-gate",
    "/admin/catalog/cortex/operational-runtime/explorers",
    "/admin/catalog/cortex/operational-runtime/explorers-gate",
    "/admin/catalog/cortex/operational-runtime/progression-timeline",
    "/admin/catalog/cortex/operational-runtime/progression-timeline-gate",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/command-center",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/timeline",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/heatmap",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/density-trends",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/{explorer_id}",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/progression-timeline",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/causal-failure-chain",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/overview-integration",
)

OPERATIONAL_COCKPIT_SURFACES_V1: Final[tuple[dict[str, Any], ...]] = (
    {
        "surface_number": 1,
        "surface_id": "operational_command_center",
        "label": "Operational command center",
        "surface_kind": "derived_aggregate",
        "operator_question": "Maturity radar, health dimensions, next action",
        "admin_routes": ["/cockpit/command-center", "/overview-integration"],
        "wired": True,
        "closure_step": 32,
    },
    {
        "surface_number": 2,
        "surface_id": "pipeline_progression_timeline",
        "label": "Pipeline progression timeline",
        "surface_kind": "runtime_backed",
        "operator_question": "Phases 02–08 timestamps + continuation",
        "admin_routes": [
            "/cockpit/timeline",
            "/progression-timeline",
            "/substrate-pipeline/runs/{pipeline_run_id}",
        ],
        "wired": True,
        "closure_step": 32,
    },
    {
        "surface_number": 3,
        "surface_id": "stalled_substrate_explorer",
        "label": "Stalled substrate explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "WAITING/STALLED rows + recover",
        "admin_routes": ["/catalog/cortex/substrate-pipeline/stalled"],
        "wired": True,
        "closure_step": 9,
    },
    {
        "surface_number": 4,
        "surface_id": "continuation_inspector",
        "label": "Continuation inspector",
        "surface_kind": "runtime_backed",
        "operator_question": "Nonce, receipts, heartbeats",
        "admin_routes": ["/substrate-pipeline/continuation"],
        "wired": True,
        "closure_step": 5,
    },
    {
        "surface_number": 5,
        "surface_id": "retrieval_starvation_explorer",
        "label": "Retrieval starvation explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Reports, RET-SKIP histogram",
        "admin_routes": ["/retrieval-starvation"],
        "wired": True,
        "closure_step": 22,
    },
    {
        "surface_number": 6,
        "surface_id": "retrieval_density_trends",
        "label": "Retrieval density trends",
        "surface_kind": "derived_aggregate",
        "operator_question": "Acceptance rate, empty epoch rate",
        "admin_routes": ["/retrieval-density", "/cockpit/density-trends"],
        "wired": True,
        "closure_step": 21,
    },
    {
        "surface_number": 7,
        "surface_id": "graph_density_explorer",
        "label": "Graph density explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Orphans, candidates, promotion queue",
        "admin_routes": ["/graph-density", "/graph-density-promotion"],
        "wired": True,
        "closure_step": 14,
    },
    {
        "surface_number": 8,
        "surface_id": "traversal_pending_explorer",
        "label": "Traversal pending explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Walks, blockers",
        "admin_routes": ["/traversal-scheduling", "/traversal-explainability"],
        "wired": True,
        "closure_step": 15,
    },
    {
        "surface_number": 9,
        "surface_id": "tcre_saturation_explorer",
        "label": "TCRE saturation explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Pending reconstructions",
        "admin_routes": ["/tcre-saturation-scheduling", "/tcre-density"],
        "wired": True,
        "closure_step": 18,
    },
    {
        "surface_number": 10,
        "surface_id": "synthesis_activation_explorer",
        "label": "Synthesis activation explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Scopes vs jobs",
        "admin_routes": ["/synthesis-activation-scheduling"],
        "wired": True,
        "closure_step": 24,
    },
    {
        "surface_number": 11,
        "surface_id": "why_synthesis_empty",
        "label": "Why synthesis empty",
        "surface_kind": "runtime_backed",
        "operator_question": "Panel messages for empty synthesis",
        "admin_routes": ["/synthesis-idle-classification/panel"],
        "wired": True,
        "closure_step": 25,
    },
    {
        "surface_number": 12,
        "surface_id": "synthesis_eligibility_explain",
        "label": "Synthesis eligibility explain",
        "surface_kind": "runtime_backed",
        "operator_question": "Structured blockers",
        "admin_routes": ["/synthesis-eligibility/explain"],
        "wired": True,
        "closure_step": 25,
    },
    {
        "surface_number": 13,
        "surface_id": "recovery_action_console",
        "label": "Recovery action console",
        "surface_kind": "runtime_backed",
        "operator_question": "Policy-gated recover actions",
        "admin_routes": [
            "/catalog/cortex/substrate-pipeline/stalled/{pipeline_run_id}/recover",
            "/catalog/cortex/substrate-pipeline/continuity-watchdog/run",
        ],
        "wired": True,
        "closure_step": 9,
    },
    {
        "surface_number": 14,
        "surface_id": "causal_failure_chain",
        "label": "Causal failure chain",
        "surface_kind": "derived_aggregate",
        "operator_question": "Degradation propagation in timeline",
        "admin_routes": ["/cockpit/timeline", "/causal-failure-chain"],
        "wired": True,
        "closure_step": 32,
    },
    {
        "surface_number": 15,
        "surface_id": "substrate_heatmap",
        "label": "Substrate heatmap",
        "surface_kind": "derived_aggregate",
        "operator_question": "Stage × health grid",
        "admin_routes": ["/cockpit/heatmap"],
        "wired": True,
        "closure_step": 30,
    },
    {
        "surface_number": 16,
        "surface_id": "runtime_maturity_dashboard",
        "label": "Runtime maturity dashboard",
        "surface_kind": "runtime_backed",
        "operator_question": "Six dimensions + maturity class",
        "admin_routes": ["/operational-maturity"],
        "wired": True,
        "closure_step": 27,
    },
    {
        "surface_number": 17,
        "surface_id": "replay_divergence_strip",
        "label": "Replay divergence strip",
        "surface_kind": "cross_link",
        "operator_question": "Cross-link synthesis/retrieval replay explorers",
        "admin_routes": [
            "/synthesis-throughput",
            "/retrieval-completeness-propagation",
        ],
        "wired": True,
        "closure_step": 30,
    },
    {
        "surface_number": 18,
        "surface_id": "density_trend_charts",
        "label": "Density trend charts",
        "surface_kind": "derived_aggregate",
        "operator_question": "7d rollups (DB-backed)",
        "admin_routes": ["/cockpit/density-trends"],
        "wired": True,
        "closure_step": 30,
    },
    {
        "surface_number": 19,
        "surface_id": "operational_health_api",
        "label": "Operational health API",
        "surface_kind": "runtime_backed",
        "operator_question": "Aggregate health JSON",
        "admin_routes": ["/operational-health", "/substrate-pipeline/operational-health"],
        "wired": True,
        "closure_step": 28,
    },
)


def _build_operational_admin_openapi_operations_v1() -> dict[str, dict[str, str]]:
    ops: dict[str, dict[str, str]] = {}
    for path in list_registered_cesp_admin_route_paths_v1():
        ops[path] = {"get": OPERATIONAL_RBAC_PERMISSION_READ_V1}
    for path in _SUBSTRATE_PIPELINE_ADMIN_PATHS_V1:
        method = OPERATIONAL_RBAC_PERMISSION_DANGEROUS_V1 if "recover" in path or "watchdog/run" in path else OPERATIONAL_RBAC_PERMISSION_READ_V1
        verb = "post" if "recover" in path or "watchdog/run" in path else "get"
        ops[path] = {verb: method}
    for path in _COCKPIT_AGGREGATE_PATHS_V1:
        ops[path] = {"get": OPERATIONAL_RBAC_PERMISSION_READ_V1}
    return ops


OPERATIONAL_ADMIN_OPENAPI_OPERATIONS_V1: Final[dict[str, dict[str, str]]] = (
    _build_operational_admin_openapi_operations_v1()
)

OPERATIONAL_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = tuple(
    sorted(OPERATIONAL_ADMIN_OPENAPI_OPERATIONS_V1),
)


def build_operational_rbac_matrix_v1() -> dict[str, Any]:
    return {
        "permissions": {
            OPERATIONAL_RBAC_PERMISSION_READ_V1: "Read operational cockpit and explorer surfaces",
            OPERATIONAL_RBAC_PERMISSION_DANGEROUS_V1: "Recover stalled pipelines and run watchdog",
        },
        "deny_by_default": True,
        "admin_role_grants": {
            "admin_basic": [OPERATIONAL_RBAC_PERMISSION_READ_V1],
            "admin_dangerous": [
                OPERATIONAL_RBAC_PERMISSION_READ_V1,
                OPERATIONAL_RBAC_PERMISSION_DANGEROUS_V1,
            ],
        },
        "openapi_operations": dict(OPERATIONAL_ADMIN_OPENAPI_OPERATIONS_V1),
    }


def build_operational_cockpit_surface_checklist_v1() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for surface in OPERATIONAL_COCKPIT_SURFACES_V1:
        routes = list(surface.get("admin_routes") or [])
        openapi_paths = [
            p
            for p in OPERATIONAL_ADMIN_OPENAPI_PATHS_V1
            if any(r.strip("/") in p for r in routes)
        ]
        out.append(
            {
                **surface,
                "openapi_paths": sorted(set(openapi_paths)),
                "wired_at_closure": bool(surface.get("wired")),
            }
        )
    return out


def build_operational_command_center_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Surface #1 — maturity radar, health dimensions, next action."""
    maturity = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)
    health = evaluate_operational_health_dimensions_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    recovery = evaluate_autonomous_recovery_score_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    eligibility = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    next_step = str(eligibility.get("next_required_step") or "observe_substrate_progression")

    return {
        "surface_kind": "operational_command_center",
        "gate_id": GP085_CP01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "maturity_class": maturity.get("maturity_class"),
        "operational_confidence_score": maturity.get("operational_confidence_score"),
        "dimension_scores": maturity.get("dimension_scores"),
        "health_dimensions": health.get("health_dimensions"),
        "overall_health": health.get("overall_health"),
        "recovery_score": dict(dict(recovery.get("metrics") or {})).get("recovery_score"),
        "operational_stability": recovery.get("operational_stability"),
        "overview_badges": build_overview_integration_v1(
            session,
            tenant_id=tenant_id,
            stall_threshold_seconds=stall_threshold_seconds,
        )["overview_badges"],
        "next_required_step": next_step,
        "synthesis_classification": eligibility.get("classification"),
        "stalled_pipeline_count": health.get("stalled_pipeline_count"),
    }


def build_substrate_operational_heatmap_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Surface #15 — stage × health grid from live projections."""
    health = evaluate_operational_health_dimensions_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    dims = dict(health.get("health_dimensions") or {})
    rows = [
        {"stage_id": "graph", "health": dims.get("retrieval_density_health"), "label": "graph"},
        {
            "stage_id": "traversal",
            "health": dims.get("substrate_continuity_health"),
            "label": "traversal",
        },
        {
            "stage_id": "tcre",
            "health": dims.get("orchestration_progress_health"),
            "label": "tcre",
        },
        {
            "stage_id": "retrieval",
            "health": dims.get("retrieval_density_health"),
            "label": "retrieval",
        },
        {
            "stage_id": "synthesis",
            "health": dims.get("synthesis_activation_health"),
            "label": "synthesis",
        },
    ]
    return {
        "surface_kind": "substrate_heatmap",
        "tenant_id": str(tenant_id),
        "overall_health": health.get("overall_health"),
        "grid": rows,
        "health_dimensions": dims,
    }


def build_density_trend_rollups_7d_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_days: int = 7,
) -> dict[str, Any]:
    """Surface #18 — DB-backed 7d density rollups (not ephemeral-only)."""
    since = datetime.now(tz=UTC) - timedelta(days=max(1, int(window_days)))
    day_col_ret = cast(CortexRetrievalMaterializationReport.created_at, Date)
    ret_rows = session.execute(
        select(
            day_col_ret.label("day"),
            func.count().label("reports"),
            func.coalesce(func.sum(CortexRetrievalMaterializationReport.accepted_rows), 0).label(
                "accepted_rows"
            ),
        )
        .where(
            CortexRetrievalMaterializationReport.tenant_id == tenant_id,
            CortexRetrievalMaterializationReport.created_at >= since,
        )
        .group_by(day_col_ret)
        .order_by(day_col_ret.asc())
    ).all()

    day_col_syn = cast(CortexSynthesisJob.created_at, Date)
    syn_rows = session.execute(
        select(
            day_col_syn.label("day"),
            func.count().label("jobs"),
        )
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.created_at >= since,
            CortexSynthesisJob.status == "completed",
        )
        .group_by(day_col_syn)
        .order_by(day_col_syn.asc())
    ).all()

    day_col_pipe = cast(CortexSubstratePipelineRun.completed_at, Date)
    pipe_rows = session.execute(
        select(
            day_col_pipe.label("day"),
            func.count().label("completed_runs"),
        )
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePipelineRun.status == "completed",
            CortexSubstratePipelineRun.completed_at >= since,
        )
        .group_by(day_col_pipe)
        .order_by(day_col_pipe.asc())
    ).all()

    def _serialize_day_rows(rows: Any) -> list[dict[str, Any]]:
        out_rows: list[dict[str, Any]] = []
        for row in rows:
            mapping = dict(row._mapping)
            day_val = mapping.pop("day", None)
            if isinstance(day_val, date):
                day_str = day_val.isoformat()
            else:
                day_str = str(day_val) if day_val is not None else ""
            out_rows.append(
                {
                    "day": day_str,
                    **{k: int(v) for k, v in mapping.items()},
                }
            )
        return out_rows

    return {
        "surface_kind": "density_trend_charts",
        "tenant_id": str(tenant_id),
        "window_days": int(window_days),
        "window_started_at": since.isoformat(),
        "retrieval_materialization_by_day": _serialize_day_rows(ret_rows),
        "synthesis_jobs_completed_by_day": _serialize_day_rows(syn_rows),
        "pipeline_completions_by_day": _serialize_day_rows(pipe_rows),
        "data_sources": [
            "cortex_retrieval_materialization_reports",
            "cortex_synthesis_jobs",
            "cortex_substrate_pipeline_runs",
        ],
    }


def build_operational_cockpit_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Full **G-P085-CP-01** cockpit aggregate for a tenant."""
    checklist = build_operational_cockpit_surface_checklist_v1()
    wired_count = sum(1 for s in checklist if s.get("wired_at_closure"))
    stalled = detect_stalled_substrate_pipelines_v1(session, limit=10)
    stalled_tenant = [s for s in stalled if str(s.get("tenant_id")) == str(tenant_id)]

    return {
        "operational_cockpit_contract": OPERATIONAL_COCKPIT_CONTRACT_V1,
        "operational_cockpit_runtime_schema_version": int(
            PHASE085_OPERATIONAL_COCKPIT_RUNTIME_SCHEMA_VERSION,
        ),
        "gate_id": GP085_CP01_GATE_ID_V1,
        "spec_ref": PHASE085_OPERATIONAL_COCKPIT_SPEC_REF_V1,
        "tenant_id": str(tenant_id),
        "surface_checklist": checklist,
        "surfaces_wired_count": wired_count,
        "surfaces_total": len(OPERATIONAL_COCKPIT_SURFACES_V1),
        "command_center": build_operational_command_center_v1(
            session,
            tenant_id=tenant_id,
            stall_threshold_seconds=stall_threshold_seconds,
        ),
        "timeline": build_pipeline_progression_timeline_v1(session, tenant_id=tenant_id),
        "heatmap": build_substrate_operational_heatmap_v1(
            session,
            tenant_id=tenant_id,
            stall_threshold_seconds=stall_threshold_seconds,
        ),
        "density_trends_7d": build_density_trend_rollups_7d_v1(session, tenant_id=tenant_id),
        "maturity_card": build_operational_maturity_card_v1(session, tenant_id=tenant_id),
        "synthesis_idle_panel": build_synthesis_idle_classification_panel_v1(
            session,
            tenant_id=tenant_id,
        ),
        "stalled_pipelines": stalled_tenant,
        "explorers_index": build_operational_explorers_index_v1(session, tenant_id=tenant_id),
        "overview_integration": build_overview_integration_v1(session, tenant_id=tenant_id),
        "rbac_matrix": build_operational_rbac_matrix_v1(),
        "openapi_path_count": len(OPERATIONAL_ADMIN_OPENAPI_PATHS_V1),
        "forbidden_ui_patterns": [
            "semantic_summaries_without_receipts",
            "success_percent_without_denominator",
            "hiding_reconstruction_not_yet_run_behind_green_tcre_card",
        ],
    }


def build_operational_cockpit_catalog_v1() -> dict[str, Any]:
    checklist = build_operational_cockpit_surface_checklist_v1()
    wired = sum(1 for s in checklist if s.get("wired_at_closure"))
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_operational_cockpit_runtime_schema_version": int(
            PHASE085_OPERATIONAL_COCKPIT_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_OPERATIONAL_COCKPIT_SPEC_REF_V1,
        "primary_gate_id": GP085_CP01_GATE_ID_V1,
        "surfaces_total": len(OPERATIONAL_COCKPIT_SURFACES_V1),
        "surfaces_wired_count": wired,
        "surface_ids": [s["surface_id"] for s in OPERATIONAL_COCKPIT_SURFACES_V1],
        "evaluation_entrypoint": "build_operational_cockpit_v1",
        "runtime_package": "vector.domains.cortex.operational_runtime.operational_cockpit",
    }


def verify_operational_cockpit_surface_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(OPERATIONAL_COCKPIT_SURFACES_V1) != 19:
        errors.append("surface_count_not_19")
    numbers = [int(s["surface_number"]) for s in OPERATIONAL_COCKPIT_SURFACES_V1]
    if sorted(numbers) != list(range(1, 20)):
        errors.append("surface_numbers_not_1_to_19")
    wired = [s for s in OPERATIONAL_COCKPIT_SURFACES_V1 if s.get("wired")]
    if len(wired) < 12:
        errors.append(f"expected_at_least_12_wired_got_{len(wired)}")
    if len(wired) != 19:
        errors.append(f"expected_19_wired_at_step_30_got_{len(wired)}")
    return _cp_meta("operational_cockpit_surface_registry", errors)


def verify_gp085_cp01_static() -> dict[str, Any]:
    """**G-P085-CP-01** — nineteen surfaces + RBAC + command center."""
    errors: list[str] = []
    reg = verify_operational_cockpit_surface_registry_static()
    if not reg.get("passed"):
        errors.extend(reg.get("detail", {}).get("errors") or [])

    cat = build_operational_cockpit_catalog_v1()
    if cat["primary_gate_id"] != GP085_CP01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if int(cat["surfaces_wired_count"]) < 12:
        errors.append("wired_surface_count_below_closure_threshold")

    for sub in _FORBIDDEN_PATH_SUBSTRINGS_CP01_V1:
        for p in OPERATIONAL_ADMIN_OPENAPI_PATHS_V1:
            if sub in p.lower():
                errors.append(f"forbidden_substring:{sub}:{p}")

    if "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit" not in (
        OPERATIONAL_ADMIN_OPENAPI_OPERATIONS_V1
    ):
        errors.append("missing_cockpit_aggregate_path")

    rb = build_operational_rbac_matrix_v1()
    if OPERATIONAL_RBAC_PERMISSION_DANGEROUS_V1 not in rb.get("permissions", {}):
        errors.append("rbac_dangerous_permission_missing")

    from vector.domains.cortex.operational_runtime import operational_cockpit as oc

    if not callable(oc.build_operational_command_center_v1):
        errors.append("missing_command_center_builder")

    if "build_overview_integration_v1" not in inspect.getsource(oc.build_operational_command_center_v1):
        errors.append("command_center_missing_overview_integration")

    if "build_operational_explorers_index_v1" not in inspect.getsource(oc.build_operational_cockpit_v1):
        errors.append("cockpit_missing_explorers_index")

    from vector.domains.cortex.operational_runtime import substrate_operational_explorers as soe

    if not callable(soe.build_operational_explorer_v1):
        errors.append("missing_build_operational_explorer_v1")

    from vector.domains.cortex.operational_runtime import (
        substrate_progression_timeline_causal as ptc,
    )

    cp03 = ptc.verify_gp085_cp03_static()
    if not cp03.get("passed"):
        errors.append("gp085_cp03_static_failed")

    if "overview_integration" not in inspect.getsource(oc.build_operational_cockpit_v1):
        errors.append("cockpit_missing_overview_integration")

    passed = not errors
    return {
        "id": GP085_CP01_GATE_ID_V1,
        "name": "cesp_operational_cockpit",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def _cp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP085_CP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase085_operational_cockpit_runtime_schema_version": int(
                PHASE085_OPERATIONAL_COCKPIT_RUNTIME_SCHEMA_VERSION,
            ),
        },
    }
