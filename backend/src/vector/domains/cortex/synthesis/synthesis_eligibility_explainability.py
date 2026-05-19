"""Deterministic explainability for synthesis eligibility (why eligible_scopes == 0)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
    pipeline_default_workloads_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (
    CortexRetrievalMaterializationReport,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob


def explain_synthesis_eligibility_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    published = scope.get("published_index_epoch")
    index_count = int(scope.get("index_row_count") or 0)
    workloads = list(scope.get("pipeline_default_workloads") or pipeline_default_workloads_v1())
    eligible = int(scope.get("eligible_scopes") or 0)

    blocked_by: list[str] = []
    upstream_missing: list[str] = []
    empty_index_causes: list[str] = []
    next_required_step: str | None = None

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if running is not None
        else None
    )

    if not published:
        blocked_by.append("no_published_retrieval_epoch")
        upstream_missing.append("retrieval_index_publish")
        next_required_step = "complete_phase_07_retrieval_materialization"
    elif index_count == 0:
        blocked_by.append("published_epoch_zero_rows")
        empty_index_causes.append("retrieval_materialization_produced_no_rows")
        upstream_missing.append("retrieval_index_rows")
        next_required_step = "fix_retrieval_materialization_upstream"

    tcre_completed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
            )
        )
        or 0
    )
    if tcre_completed == 0:
        upstream_missing.append("completed_tcre_job")
        if "no_published_retrieval_epoch" not in blocked_by:
            blocked_by.append("no_completed_tcre")

    if continuation is not None and continuation.continuation_status == CONTINUATION_STATUS_WAITING:
        blocked_by.append("pipeline_waiting_on_tcre")
        next_required_step = "await_tcre_completion_or_run_recovery"

    latest_report = session.scalar(
        select(CortexRetrievalMaterializationReport)
        .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
        .order_by(CortexRetrievalMaterializationReport.created_at.desc())
        .limit(1)
    )
    if latest_report is not None and latest_report.accepted_rows == 0:
        report_body = dict(latest_report.report_json or {})
        empty_index_causes.extend(list(report_body.get("empty_scope_causes") or []))
        for skip in list(latest_report.skip_reasons_json or [])[:8]:
            if isinstance(skip, dict) and skip.get("ret_skip_code"):
                empty_index_causes.append(str(skip["ret_skip_code"]))

    synthesis_ready = eligible > 0 and bool(published) and index_count > 0
    if synthesis_ready:
        next_required_step = "run_phase_08_synthesis_or_wait_for_pipeline"

    from vector.domains.cortex.synthesis.synthesis_idle_classification import (
        classify_synthesis_eligibility_v1,
        evaluate_synthesis_classification_context_v1,
    )

    ctx = evaluate_synthesis_classification_context_v1(session, tenant_id=tenant_id)
    classified = classify_synthesis_eligibility_v1(
        eligible_scopes=eligible,
        synthesized_scopes=int(ctx["synthesized_scopes"]),
        retrieval_operational_starvation=bool(ctx["retrieval_operational_starvation"]),
        upstream_work_present=bool(ctx["upstream_work_present"]),
        forbidden_count=int(ctx["forbidden_count"]),
        forbidden_backoff_active=bool(ctx["forbidden_backoff_active"]),
        pipeline_waiting=bool(ctx["pipeline_waiting"]),
        pipeline_stalled=bool(ctx["pipeline_stalled"]),
        replay_unsafe=bool(ctx["replay_unsafe"]),
    )

    return {
        "tenant_id": str(tenant_id),
        "published_epoch_exists": bool(published),
        "published_index_epoch": published,
        "retrieval_row_count": index_count,
        "workloads_enabled": workloads,
        "eligible_scopes": eligible,
        "eligibility_formula": "index_row_count * len(pipeline_default_workloads)",
        "blocked_by": blocked_by,
        "upstream_missing_dependencies": upstream_missing,
        "empty_index_causes": sorted(set(empty_index_causes)),
        "synthesis_ready": synthesis_ready,
        "next_required_step": next_required_step,
        "pipeline_running": running is not None,
        "pipeline_run_id": str(running.id) if running else None,
        "continuation_status": continuation.continuation_status if continuation else None,
        "waiting_on": continuation.waiting_on if continuation else None,
        "classification": classified["classification"],
        "operational_starvation": classified["operational_starvation"],
        "ui_color": classified["synthesis_idle_ui_color"],
    }


def build_synthesis_empty_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator panel: “Why is synthesis empty?”"""
    expl = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    messages: list[str] = []
    if not expl["published_epoch_exists"]:
        messages.append("No published retrieval epoch — phase 07 publish has not succeeded.")
    if expl["retrieval_row_count"] == 0 and expl["published_epoch_exists"]:
        messages.append("Published epoch has zero index rows — retrieval materialization skipped or failed.")
    if "pipeline_waiting_on_tcre" in expl["blocked_by"]:
        messages.append("Substrate pipeline is waiting on async TCRE completion.")
    if "no_completed_tcre" in expl["blocked_by"]:
        messages.append("No completed TCRE reconstruction job for this tenant.")
    for cause in expl.get("empty_index_causes") or []:
        if cause.startswith("RET-SKIP-"):
            messages.append(f"Retrieval skip: {cause}")
    if expl["synthesis_ready"]:
        messages.append("Synthesis is ready — eligible scopes exist; check phase 08 execution.")
    classification = str(expl.get("classification") or "")
    if classification == "operational_starvation":
        messages.append("Classification: operational_starvation — upstream work without eligible scopes.")
    elif classification == "healthy_idle":
        messages.append("Classification: healthy_idle — no eligible scopes and no upstream starvation.")
    return {
        "panel_title": "Why is synthesis empty?",
        "messages": messages,
        "explanation": expl,
    }
