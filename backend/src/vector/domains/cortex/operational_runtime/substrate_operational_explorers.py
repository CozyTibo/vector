"""Phase 08.5 P085-31 — dedicated operational explorer surfaces (**G-P085-CP-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-admin-cockpit-spec.md`` §Explorers.
Tables-first list/detail JSON for admin SPA; each explorer reconciles to DB-backed sources.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density import compute_graph_density_metrics_v1
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    classify_tenant_graph_orphans_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    count_unpromoted_link_candidates_v1,
    evaluate_promotion_backlog_schedule_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.recovery_receipts import (
    list_recovery_receipts_v1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    continuation_row_to_public_dict_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    compute_retrieval_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    build_retrieval_starvation_panel_v1,
    explain_retrieval_eligibility_v1,
)
from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
    evaluate_synthesis_activation_schedule_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    compute_tcre_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    evaluate_tcre_saturation_schedule_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_explainability import (
    build_traversal_explainability_panel_v1,
    compute_traversal_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    evaluate_traversal_schedule_v1,
)
from vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification import (
    build_synthesis_idle_classification_panel_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    detect_stalled_substrate_pipelines_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (
    CortexSynthesisActivationAudit,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_OPERATIONAL_EXPLORERS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_OPERATIONAL_EXPLORERS_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-admin-cockpit-spec.md"
)

GP085_CP02_GATE_ID_V1: Final[str] = "G-P085-CP-02"

P085_CP02_RULE_ID_V1: Final[str] = "P085-CP-02"

EXPLORER_STALLED_SUBSTRATE_V1: Final[str] = "stalled_substrate"
EXPLORER_CONTINUATION_V1: Final[str] = "continuation"
EXPLORER_RETRIEVAL_STARVATION_V1: Final[str] = "retrieval_starvation"
EXPLORER_RETRIEVAL_DENSITY_V1: Final[str] = "retrieval_density"
EXPLORER_GRAPH_DENSITY_V1: Final[str] = "graph_density"
EXPLORER_TRAVERSAL_PENDING_V1: Final[str] = "traversal_pending"
EXPLORER_TCRE_SATURATION_V1: Final[str] = "tcre_saturation"
EXPLORER_SYNTHESIS_ACTIVATION_V1: Final[str] = "synthesis_activation"
EXPLORER_WHY_SYNTHESIS_EMPTY_V1: Final[str] = "why_synthesis_empty"
EXPLORER_SYNTHESIS_ELIGIBILITY_V1: Final[str] = "synthesis_eligibility"

OPERATIONAL_EXPLORER_IDS_V1: Final[tuple[str, ...]] = (
    EXPLORER_STALLED_SUBSTRATE_V1,
    EXPLORER_CONTINUATION_V1,
    EXPLORER_RETRIEVAL_STARVATION_V1,
    EXPLORER_RETRIEVAL_DENSITY_V1,
    EXPLORER_GRAPH_DENSITY_V1,
    EXPLORER_TRAVERSAL_PENDING_V1,
    EXPLORER_TCRE_SATURATION_V1,
    EXPLORER_SYNTHESIS_ACTIVATION_V1,
    EXPLORER_WHY_SYNTHESIS_EMPTY_V1,
    EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
)

OPERATIONAL_EXPLORER_SURFACES_V1: Final[tuple[dict[str, Any], ...]] = (
    {
        "explorer_id": EXPLORER_STALLED_SUBSTRATE_V1,
        "label": "Stalled substrate explorer",
        "cockpit_surface_id": "stalled_substrate_explorer",
        "list_row_schema": "stalled_substrate_list_row_v1",
        "admin_route": "/admin/catalog/cortex/substrate-pipeline/stalled",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/stalled_substrate"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_CONTINUATION_V1,
        "label": "Continuation inspector",
        "cockpit_surface_id": "continuation_inspector",
        "list_row_schema": "continuation_inspector_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/substrate-pipeline/continuation",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/continuation"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_RETRIEVAL_STARVATION_V1,
        "label": "Retrieval starvation explorer",
        "cockpit_surface_id": "retrieval_starvation_explorer",
        "list_row_schema": "retrieval_starvation_panel_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-starvation",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/retrieval_starvation"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_RETRIEVAL_DENSITY_V1,
        "label": "Retrieval density trends",
        "cockpit_surface_id": "retrieval_density_trends",
        "list_row_schema": "retrieval_density_metrics_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-density",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/retrieval_density"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_GRAPH_DENSITY_V1,
        "label": "Graph density explorer",
        "cockpit_surface_id": "graph_density_explorer",
        "list_row_schema": "graph_density_explorer_row_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-density",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/graph_density"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_TRAVERSAL_PENDING_V1,
        "label": "Traversal pending explorer",
        "cockpit_surface_id": "traversal_pending_explorer",
        "list_row_schema": "traversal_pending_row_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/operational-runtime/traversal-scheduling",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/traversal_pending"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_TCRE_SATURATION_V1,
        "label": "TCRE saturation explorer",
        "cockpit_surface_id": "tcre_saturation_explorer",
        "list_row_schema": "tcre_reconstruction_job_row_v1",
        "admin_route": "/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-saturation-scheduling",
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/tcre_saturation"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_SYNTHESIS_ACTIVATION_V1,
        "label": "Synthesis activation explorer",
        "cockpit_surface_id": "synthesis_activation_explorer",
        "list_row_schema": "synthesis_activation_audit_row_v1",
        "admin_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-activation-scheduling"
        ),
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/synthesis_activation"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_WHY_SYNTHESIS_EMPTY_V1,
        "label": "Why synthesis empty",
        "cockpit_surface_id": "why_synthesis_empty",
        "list_row_schema": "synthesis_idle_message_v1",
        "admin_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-idle-classification/panel"
        ),
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/why_synthesis_empty"
        ),
        "wired": True,
    },
    {
        "explorer_id": EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
        "label": "Synthesis eligibility explain",
        "cockpit_surface_id": "synthesis_eligibility_explain",
        "list_row_schema": "synthesis_eligibility_blocker_v1",
        "admin_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-eligibility/explain"
        ),
        "tenant_explorer_route": (
            "/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/synthesis_eligibility"
        ),
        "wired": True,
    },
)


def _explorer_shell(
    *,
    explorer_id: str,
    tenant_id: uuid.UUID,
    columns: list[dict[str, str]],
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    detail: dict[str, Any] | None = None,
    actions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    meta = next((s for s in OPERATIONAL_EXPLORER_SURFACES_V1 if s["explorer_id"] == explorer_id), {})
    return {
        "surface_kind": "operational_explorer",
        "gate_id": GP085_CP02_GATE_ID_V1,
        "explorer_id": explorer_id,
        "label": meta.get("label", explorer_id),
        "list_row_schema": meta.get("list_row_schema"),
        "tenant_id": str(tenant_id),
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "summary": summary,
        "detail": detail or {},
        "actions": list(actions or []),
        "upstream_admin_route": meta.get("admin_route"),
        "detail_route": meta.get("tenant_explorer_route", "").replace("{tenant_id}", str(tenant_id)),
    }


def build_stalled_substrate_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> dict[str, Any]:
    stalled = detect_stalled_substrate_pipelines_v1(session, limit=limit)
    tenant_rows = [r for r in stalled if str(r.get("tenant_id")) == str(tenant_id)]
    rows = [
        {
            "pipeline_run_id": r.get("pipeline_run_id"),
            "continuation_status": r.get("continuation_status"),
            "waiting_on": r.get("waiting_on"),
            "stalled_seconds": r.get("stalled_seconds"),
            "recovery_recommendation": r.get("recovery_recommendation"),
            "pipeline_run_status": r.get("pipeline_run_status"),
        }
        for r in tenant_rows
    ]
    return _explorer_shell(
        explorer_id=EXPLORER_STALLED_SUBSTRATE_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "pipeline_run_id", "label": "Pipeline run"},
            {"key": "continuation_status", "label": "Status"},
            {"key": "waiting_on", "label": "Waiting on"},
            {"key": "stalled_seconds", "label": "Stalled (s)"},
            {"key": "recovery_recommendation", "label": "Recommendation"},
        ],
        rows=rows,
        summary={"stalled_count": len(rows)},
        actions=[
            {
                "action_id": "recover_stalled",
                "method": "POST",
                "route": "/admin/catalog/cortex/substrate-pipeline/stalled/{pipeline_run_id}/recover",
                "permission": "cortex.operational.dangerous",
            },
        ],
    )


def build_continuation_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    cont = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if running is not None
        else None
    )
    receipts: list[dict[str, Any]] = []
    if cont is not None:
        receipts = list_recovery_receipts_v1(cont)
    cont_public = continuation_row_to_public_dict_v1(cont) if cont is not None else None
    rows = (
        [
            {
                "pipeline_run_id": str(running.id),
                "continuation_status": cont.continuation_status,
                "waiting_on": cont.waiting_on,
                "recovery_receipt_count": len(receipts),
            }
        ]
        if cont is not None and running is not None
        else []
    )
    return _explorer_shell(
        explorer_id=EXPLORER_CONTINUATION_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "pipeline_run_id", "label": "Pipeline run"},
            {"key": "continuation_status", "label": "Status"},
            {"key": "waiting_on", "label": "Waiting on"},
            {"key": "recovery_receipt_count", "label": "Receipts"},
        ],
        rows=rows,
        summary={
            "has_running_pipeline": running is not None,
            "has_continuation": cont is not None,
        },
        detail={
            "continuation": cont_public,
            "recovery_receipts": receipts,
        },
    )


def build_retrieval_starvation_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    panel = build_retrieval_starvation_panel_v1(session, tenant_id=tenant_id)
    explain = explain_retrieval_eligibility_v1(session, tenant_id=tenant_id)
    histogram = dict(explain.get("ret_skip_histogram") or {})
    rows = [
        {"ret_skip_code": code, "count": int(count)}
        for code, count in sorted(histogram.items(), key=lambda x: (-x[1], x[0]))
    ]
    return _explorer_shell(
        explorer_id=EXPLORER_RETRIEVAL_STARVATION_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "ret_skip_code", "label": "RET-SKIP code"},
            {"key": "count", "label": "Count"},
        ],
        rows=rows,
        summary={
            "operational_starvation": panel.get("operational_starvation"),
            "idle_class": panel.get("idle_class"),
            "index_stale": dict(panel.get("index_freshness") or {}).get("index_stale"),
        },
        detail={"panel": panel, "eligibility_explain": explain},
    )


def build_retrieval_density_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    snap = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(snap.get("metrics") or {})
    rows = [
        {
            "metric_id": key,
            "value": value,
            "denominator_documented": key.endswith("_percent") or key.endswith("_rate"),
        }
        for key, value in sorted(metrics.items())
    ]
    return _explorer_shell(
        explorer_id=EXPLORER_RETRIEVAL_DENSITY_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "metric_id", "label": "Metric"},
            {"key": "value", "label": "Value"},
            {"key": "denominator_documented", "label": "Has denominator"},
        ],
        rows=rows,
        summary={
            "retrieval_maturity_class": snap.get("retrieval_maturity_class"),
            "published_index_epoch": metrics.get("published_index_epoch"),
            "retrieval_density_score": metrics.get("retrieval_density_score"),
        },
        detail=snap,
    )


def build_graph_density_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sample_limit: int = 25,
) -> dict[str, Any]:
    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    orphans = classify_tenant_graph_orphans_v1(
        session,
        tenant_id=tenant_id,
        sample_limit=sample_limit,
    )
    promotion = evaluate_promotion_backlog_schedule_v1(session, tenant_id=tenant_id)
    rows = list(orphans.get("samples") or [])
    unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
    return _explorer_shell(
        explorer_id=EXPLORER_GRAPH_DENSITY_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "org_entity_id", "label": "Entity"},
            {"key": "orphan_class", "label": "Orphan class"},
            {"key": "recommended_action", "label": "Action"},
            {"key": "ret_skip_code", "label": "RET-SKIP"},
        ],
        rows=rows,
        summary={
            "graph_maturity_stage": density.get("graph_maturity_stage"),
            "orphan_entity_count": orphans.get("orphan_entity_count"),
            "unpromoted_link_candidate_count": unpromoted,
            "should_schedule_promotion": promotion.get("should_schedule"),
        },
        detail={"density": density, "orphan_inventory": orphans, "promotion": promotion},
        actions=[
            {
                "action_id": "run_promotion",
                "method": "POST",
                "route": (
                    "/admin/tenants/{tenant_id}/cortex/operational-runtime/"
                    "graph-density-promotion/run"
                ),
                "permission": "cortex.operational.dangerous",
            },
        ],
    )


def build_traversal_pending_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    schedule = evaluate_traversal_schedule_v1(session, tenant_id=tenant_id)
    panel = build_traversal_explainability_panel_v1(session, tenant_id=tenant_id)
    metrics = compute_traversal_density_metrics_v1(session, tenant_id=tenant_id)
    blockers = list(panel.get("walk_blocker_reasons") or [])
    rows = [
        {
            "walk_id": str(b.get("walk_id") or ""),
            "status": b.get("status"),
            "blocker": b.get("blocker") or b.get("stall_reason"),
            "poison_candidate": bool(b.get("poison_candidate")),
        }
        for b in blockers[:50]
    ]
    return _explorer_shell(
        explorer_id=EXPLORER_TRAVERSAL_PENDING_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "walk_id", "label": "Walk"},
            {"key": "status", "label": "Status"},
            {"key": "blocker", "label": "Blocker"},
            {"key": "poison_candidate", "label": "Poison?"},
        ],
        rows=rows,
        summary={
            "should_schedule": schedule.get("should_schedule"),
            "walk_queue_depth": schedule.get("walk_queue_depth"),
            "walks_completed_rate": metrics.get("walks_completed_rate"),
            "traversal_density_score": metrics.get("traversal_density_score"),
        },
        detail={"schedule": schedule, "panel": panel, "metrics": metrics},
    )


def build_tcre_saturation_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 50,
) -> dict[str, Any]:
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    schedule = evaluate_tcre_saturation_schedule_v1(session, tenant_id=tenant_id)
    pending_jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status.notin_(("completed", "failed")),
            )
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .limit(max(1, int(limit)))
        ).all()
    )
    rows = [
        {
            "job_id": str(job.id),
            "status": job.status,
            "job_kind": job.job_kind,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "error_detail": (job.error_detail or "")[:200] or None,
        }
        for job in pending_jobs
    ]
    dm = dict(density.get("metrics") or {})
    return _explorer_shell(
        explorer_id=EXPLORER_TCRE_SATURATION_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "job_id", "label": "Job"},
            {"key": "status", "label": "Status"},
            {"key": "job_kind", "label": "Kind"},
            {"key": "created_at", "label": "Created"},
        ],
        rows=rows,
        summary={
            "tcre_maturity_class": density.get("tcre_maturity_class"),
            "tcre_saturation_percent": dm.get("tcre_saturation_percent"),
            "tcre_pending_count": dm.get("tcre_pending_count"),
            "should_schedule_saturation": schedule.get("should_schedule"),
        },
        detail={"density": density, "schedule": schedule},
    )


def build_synthesis_activation_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 32,
) -> dict[str, Any]:
    schedule = evaluate_synthesis_activation_schedule_v1(session, tenant_id=tenant_id)
    since = datetime.now(tz=UTC) - timedelta(days=7)
    audits = list(
        session.scalars(
            select(CortexSynthesisActivationAudit)
            .where(
                CortexSynthesisActivationAudit.tenant_id == tenant_id,
                CortexSynthesisActivationAudit.created_at >= since,
            )
            .order_by(CortexSynthesisActivationAudit.created_at.desc())
            .limit(max(1, int(limit)))
        ).all()
    )
    rows = [
        {
            "audit_id": str(a.id),
            "pipeline_run_id": str(a.pipeline_run_id) if a.pipeline_run_id else None,
            "scopes_generated": int(a.scopes_generated),
            "scopes_skipped": int(a.scopes_skipped),
            "jobs_enqueued": int(a.synthesis_jobs_enqueued),
            "jobs_completed": int(a.synthesis_jobs_completed),
            "empty_scope_reason": a.empty_scope_reason,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in audits
    ]
    recent_jobs = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.created_at >= since,
            )
        )
        or 0
    )
    return _explorer_shell(
        explorer_id=EXPLORER_SYNTHESIS_ACTIVATION_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "audit_id", "label": "Audit"},
            {"key": "scopes_generated", "label": "Scopes gen"},
            {"key": "jobs_enqueued", "label": "Jobs queued"},
            {"key": "jobs_completed", "label": "Jobs done"},
            {"key": "empty_scope_reason", "label": "Empty reason"},
        ],
        rows=rows,
        summary={
            "eligible_scopes": schedule.get("eligible_scopes"),
            "should_activate": schedule.get("should_activate"),
            "activation_reason": schedule.get("activation_reason"),
            "synthesis_jobs_7d": recent_jobs,
        },
        detail={"schedule": schedule},
    )


def build_why_synthesis_empty_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    panel = build_synthesis_idle_classification_panel_v1(session, tenant_id=tenant_id)
    messages = list(panel.get("messages") or [])
    rows = [{"message_index": i, "message": msg} for i, msg in enumerate(messages)]
    return _explorer_shell(
        explorer_id=EXPLORER_WHY_SYNTHESIS_EMPTY_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "message_index", "label": "#"},
            {"key": "message", "label": "Message"},
        ],
        rows=rows,
        summary={
            "classification": panel.get("classification"),
            "ui_color": panel.get("ui_color"),
        },
        detail=panel,
    )


def build_synthesis_eligibility_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    expl = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    blockers = list(expl.get("blocked_by") or [])
    empty_causes = list(expl.get("empty_index_causes") or [])
    rows = [{"blocker_id": b, "kind": "blocked_by"} for b in blockers]
    rows.extend({"blocker_id": c, "kind": "empty_index_cause"} for c in empty_causes)
    return _explorer_shell(
        explorer_id=EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
        tenant_id=tenant_id,
        columns=[
            {"key": "blocker_id", "label": "Blocker / cause"},
            {"key": "kind", "label": "Kind"},
        ],
        rows=rows,
        summary={
            "synthesis_ready": expl.get("synthesis_ready"),
            "eligible_scopes": expl.get("eligible_scopes"),
            "classification": expl.get("classification"),
            "next_required_step": expl.get("next_required_step"),
        },
        detail=expl,
    )


_EXPLORER_BUILDERS_V1: dict[str, Callable[..., dict[str, Any]]] = {
    EXPLORER_STALLED_SUBSTRATE_V1: build_stalled_substrate_explorer_v1,
    EXPLORER_CONTINUATION_V1: build_continuation_explorer_v1,
    EXPLORER_RETRIEVAL_STARVATION_V1: build_retrieval_starvation_explorer_v1,
    EXPLORER_RETRIEVAL_DENSITY_V1: build_retrieval_density_explorer_v1,
    EXPLORER_GRAPH_DENSITY_V1: build_graph_density_explorer_v1,
    EXPLORER_TRAVERSAL_PENDING_V1: build_traversal_pending_explorer_v1,
    EXPLORER_TCRE_SATURATION_V1: build_tcre_saturation_explorer_v1,
    EXPLORER_SYNTHESIS_ACTIVATION_V1: build_synthesis_activation_explorer_v1,
    EXPLORER_WHY_SYNTHESIS_EMPTY_V1: build_why_synthesis_empty_explorer_v1,
    EXPLORER_SYNTHESIS_ELIGIBILITY_V1: build_synthesis_eligibility_explorer_v1,
}


def build_operational_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    explorer_id: str,
) -> dict[str, Any]:
    """Build one **G-P085-CP-02** explorer by id."""
    if explorer_id not in _EXPLORER_BUILDERS_V1:
        return {
            "error": "explorer_not_found",
            "explorer_id": explorer_id,
            "allowed_explorer_ids": list(OPERATIONAL_EXPLORER_IDS_V1),
        }
    return _EXPLORER_BUILDERS_V1[explorer_id](session, tenant_id=tenant_id)


def build_operational_explorers_index_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant explorer hub — summary card per explorer without full row payloads."""
    cards: list[dict[str, Any]] = []
    for explorer_id in OPERATIONAL_EXPLORER_IDS_V1:
        built = build_operational_explorer_v1(session, tenant_id=tenant_id, explorer_id=explorer_id)
        cards.append(
            {
                "explorer_id": explorer_id,
                "label": built.get("label"),
                "row_count": built.get("row_count"),
                "summary": built.get("summary"),
                "detail_route": built.get("detail_route"),
            }
        )
    return {
        "surface_kind": "operational_explorers_index",
        "gate_id": GP085_CP02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "explorers_total": len(OPERATIONAL_EXPLORER_IDS_V1),
        "explorers": cards,
    }


def build_substrate_operational_explorers_catalog_v1() -> dict[str, Any]:
    wired = sum(1 for s in OPERATIONAL_EXPLORER_SURFACES_V1 if s.get("wired"))
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_operational_explorers_runtime_schema_version": int(
            PHASE085_OPERATIONAL_EXPLORERS_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_OPERATIONAL_EXPLORERS_SPEC_REF_V1,
        "primary_gate_id": GP085_CP02_GATE_ID_V1,
        "explorers_total": len(OPERATIONAL_EXPLORER_IDS_V1),
        "explorers_wired_count": wired,
        "explorer_ids": list(OPERATIONAL_EXPLORER_IDS_V1),
        "evaluation_entrypoint": "build_operational_explorer_v1",
        "index_entrypoint": "build_operational_explorers_index_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_operational_explorers"
        ),
    }


def verify_gp085_cp02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_operational_explorers_catalog_v1()
    if cat["primary_gate_id"] != GP085_CP02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if len(OPERATIONAL_EXPLORER_SURFACES_V1) != 10:
        errors.append("explorer_surface_count_not_10")
    if set(_EXPLORER_BUILDERS_V1.keys()) != set(OPERATIONAL_EXPLORER_IDS_V1):
        errors.append("builder_registry_mismatch")
    wired = [s for s in OPERATIONAL_EXPLORER_SURFACES_V1 if s.get("wired")]
    if len(wired) < 10:
        errors.append(f"expected_10_wired_got_{len(wired)}")

    shell = _explorer_shell(
        explorer_id=EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
        tenant_id=uuid.uuid4(),
        columns=[{"key": "k", "label": "K"}],
        rows=[],
        summary={},
    )
    if shell.get("surface_kind") != "operational_explorer":
        errors.append("explorer_shell_kind")

    from vector.domains.cortex.operational_runtime import operational_cockpit as oc

    explorer_to_cockpit = {
        EXPLORER_STALLED_SUBSTRATE_V1: "stalled_substrate_explorer",
        EXPLORER_CONTINUATION_V1: "continuation_inspector",
        EXPLORER_RETRIEVAL_STARVATION_V1: "retrieval_starvation_explorer",
        EXPLORER_RETRIEVAL_DENSITY_V1: "retrieval_density_trends",
        EXPLORER_GRAPH_DENSITY_V1: "graph_density_explorer",
        EXPLORER_TRAVERSAL_PENDING_V1: "traversal_pending_explorer",
        EXPLORER_TCRE_SATURATION_V1: "tcre_saturation_explorer",
        EXPLORER_SYNTHESIS_ACTIVATION_V1: "synthesis_activation_explorer",
        EXPLORER_WHY_SYNTHESIS_EMPTY_V1: "why_synthesis_empty",
        EXPLORER_SYNTHESIS_ELIGIBILITY_V1: "synthesis_eligibility_explain",
    }
    cockpit_surface_ids = {s["surface_id"] for s in oc.OPERATIONAL_COCKPIT_SURFACES_V1}
    for eid, cid in explorer_to_cockpit.items():
        if cid not in cockpit_surface_ids:
            errors.append(f"cockpit_missing_surface:{cid}")

    from vector.domains.cortex.operational_runtime import operational_cockpit as cockpit_mod

    if "build_operational_explorers_index_v1" not in inspect.getsource(
        cockpit_mod.build_operational_cockpit_v1
    ):
        errors.append("cockpit_missing_explorers_index")

    passed = not errors
    return {
        "id": GP085_CP02_GATE_ID_V1,
        "name": "cesp_substrate_operational_explorers",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
