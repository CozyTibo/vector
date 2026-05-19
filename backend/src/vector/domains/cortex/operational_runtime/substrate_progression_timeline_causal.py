"""Phase 08.5 P085-32 — progression timeline + causal chains (**G-P085-CP-03**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-admin-cockpit-spec.md`` §Timeline, §Overview.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)
from vector.domains.cortex.completeness.substrate_completeness_ledger import (
    build_substrate_completeness_ledger_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_explorers import (
    EXPLORER_GRAPH_DENSITY_V1,
    EXPLORER_RETRIEVAL_STARVATION_V1,
    EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
    EXPLORER_TCRE_SATURATION_V1,
    EXPLORER_TRAVERSAL_PENDING_V1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    evaluate_multidimensional_operational_maturity_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions import (
    evaluate_operational_health_dimensions_v1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    continuation_row_to_public_dict_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.synthesis.synthesis_idle_classification import (
    SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1,
    SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
    SYNTHESIS_CLASSIFICATION_PROGRESSING_V1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_receipts import (
    build_pipeline_execution_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_PROGRESSION_TIMELINE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_PROGRESSION_TIMELINE_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-admin-cockpit-spec.md"
)

GP085_CP03_GATE_ID_V1: Final[str] = "G-P085-CP-03"

P085_CP03_RULE_ID_V1: Final[str] = "P085-CP-03"

PROGRESSION_TIMELINE_CONTRACT_V1: Final[str] = "progression_timeline_causal_v1"

OPERATIONAL_STAGE_CARD_IDS_V1: Final[tuple[str, ...]] = (
    "graph",
    "traversal",
    "tcre",
    "retrieval",
    "synthesis",
)

_STAGE_EXPLORER_ID_V1: Final[dict[str, str]] = {
    "graph": EXPLORER_GRAPH_DENSITY_V1,
    "traversal": EXPLORER_TRAVERSAL_PENDING_V1,
    "tcre": EXPLORER_TCRE_SATURATION_V1,
    "retrieval": EXPLORER_RETRIEVAL_STARVATION_V1,
    "synthesis": EXPLORER_SYNTHESIS_ELIGIBILITY_V1,
}

_FORBIDDEN_UI_PATTERNS_CP03_V1: Final[tuple[str, ...]] = (
    "healthy_with_zero_objects_without_idle_classification",
    "success_percent_without_denominator",
    "hiding_reconstruction_not_yet_run_behind_green_tcre_card",
)

_PROGRESSION_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/catalog/cortex/operational-runtime/progression-timeline",
    "/admin/catalog/cortex/operational-runtime/progression-timeline-gate",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/progression-timeline",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/causal-failure-chain",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/overview-integration",
    "/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/timeline",
)


def _phase_status_glyph_v1(status: str) -> str:
    if status == "completed":
        return "ok"
    if status == "skipped":
        return "skip"
    if status == "running":
        return "running"
    if status == "failed":
        return "fail"
    if status == "queued":
        return "queued"
    return "pending"


def _glyph_display_char_v1(glyph: str) -> str:
    return {
        "ok": "✓",
        "skip": "—",
        "running": "⏳",
        "fail": "✗",
        "queued": "○",
        "pending": "—",
    }.get(glyph, "?")


def _phase_short_id_v1(phase_id: str) -> str:
    if phase_id.startswith("phase_") and len(phase_id) >= 8:
        return phase_id[6:8]
    return phase_id[:2]


def _derive_stage_card_classification_v1(stage: dict[str, Any]) -> str:
    """idle | starved | progressing per **G-P085-CP-03**."""
    metrics = dict(stage.get("metrics") or {})
    substrate_state = str(stage.get("substrate_state") or "unknown")
    total = int(stage.get("total_objects") or 0)
    processed = int(stage.get("processed_count") or 0)

    syn_class = str(metrics.get("synthesis_classification") or "")
    if syn_class == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1:
        return "starved"
    if metrics.get("operational_starvation") is True:
        return "starved"
    ret_class = str(metrics.get("retrieval_card_classification") or "")
    if ret_class == "operational_starvation":
        return "starved"

    if syn_class == SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1 and total == 0:
        return "idle"
    if substrate_state == "healthy" and total == 0 and processed == 0:
        return "idle"

    if substrate_state in ("degraded", "critical") and processed < total and total > 0:
        return "progressing"
    if syn_class == SYNTHESIS_CLASSIFICATION_PROGRESSING_V1:
        return "progressing"
    if processed > 0 and processed < total:
        return "progressing"
    if substrate_state == "healthy" and total > 0:
        return "progressing"
    if total == 0 and substrate_state != "healthy":
        return "starved"
    return "idle" if total == 0 else "progressing"


def _stage_next_required_step_v1(stage_id: str, stage: dict[str, Any]) -> str:
    metrics = dict(stage.get("metrics") or {})
    if stage_id == "synthesis":
        blocker = metrics.get("synthesis_blocker_id")
        if blocker:
            return str(blocker)
    if stage_id == "retrieval":
        ret_class = str(metrics.get("retrieval_card_classification") or "")
        if ret_class == "operational_starvation":
            return "materialize_retrieval_index"
        if ret_class == "healthy_idle":
            return "observe_retrieval_idle"
    if stage_id == "tcre":
        if int(metrics.get("reconstruction_not_yet_run") or 0) > 0:
            return "run_tcre_saturation_pass"
    if stage_id == "graph":
        if int(metrics.get("pending_link_candidates") or 0) > 0:
            return "run_graph_promotion_pass"
    if stage_id == "traversal":
        pending = int(metrics.get("walks_pending_gauge") or metrics.get("pending_walk_count") or 0)
        if pending > 0:
            return "schedule_traversal_batch"
    drift = list(stage.get("drift_warnings") or [])
    if drift:
        return str(drift[0]).split(":")[0]
    return "observe_substrate_progression"


def build_operational_stage_cards_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Truthful stage cards — classification, next step, explorer link."""
    ledger = build_substrate_completeness_ledger_v1(session, tenant_id=tenant_id)
    by_id = {str(s.get("stage_id")): s for s in ledger.get("stages") or []}
    cards: list[dict[str, Any]] = []
    for stage_id in OPERATIONAL_STAGE_CARD_IDS_V1:
        stage = dict(by_id.get(stage_id) or {})
        classification = _derive_stage_card_classification_v1(stage)
        explorer_id = _STAGE_EXPLORER_ID_V1.get(stage_id)
        cards.append(
            {
                "stage_id": stage_id,
                "label": str(stage.get("label") or stage_id.title()),
                "substrate_state": stage.get("substrate_state"),
                "total_objects": int(stage.get("total_objects") or 0),
                "processed_count": int(stage.get("processed_count") or 0),
                "classification": classification,
                "next_required_step": _stage_next_required_step_v1(stage_id, stage),
                "explorer_id": explorer_id,
                "explorer_route": (
                    f"/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/{explorer_id}"
                    if explorer_id
                    else None
                ),
                "detail_route": stage.get("detail_route"),
                "omission_classes": dict(stage.get("omission_classes") or {}),
                "drift_warnings": list(stage.get("drift_warnings") or []),
            }
        )
    return cards


def build_causal_failure_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Surface #14 — structured degradation propagation + pipeline faults."""
    ledger = build_substrate_completeness_ledger_v1(session, tenant_id=tenant_id)
    stages = list(ledger.get("stages") or [])
    propagation_chain = build_degradation_propagation_chain_v1(stages)

    pipeline_links: list[dict[str, Any]] = []
    run: CortexSubstratePipelineRun | None = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is not None and run.tenant_id != tenant_id:
            run = None
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if run is None:
        run = session.scalar(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(1)
        )

    if run is not None:
        phases_db = list(
            session.scalars(
                select(CortexSubstratePhaseRun)
                .where(CortexSubstratePhaseRun.pipeline_run_id == run.id)
                .order_by(CortexSubstratePhaseRun.phase_ordinal.asc())
            ).all()
        )
        for row in phases_db:
            if row.error_detail:
                pipeline_links.append(
                    {
                        "kind": "phase_failure",
                        "phase_id": row.phase_id,
                        "status": row.status,
                        "error_detail": str(row.error_detail)[:300],
                    }
                )
        cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=run.id)
        if cont is not None and cont.continuation_status in (
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_STALLED,
        ):
            pipeline_links.append(
                {
                    "kind": "continuation_block",
                    "continuation_status": cont.continuation_status,
                    "waiting_on": str(cont.waiting_on or ""),
                }
            )

    legacy_tokens: list[str] = []
    for link in pipeline_links:
        if link.get("kind") == "phase_failure":
            legacy_tokens.append(f"{link['phase_id']}:{link['status']}")
        elif link.get("kind") == "continuation_block":
            legacy_tokens.append(
                f"continuation:{link['continuation_status']}:{link['waiting_on']}"
            )

    return {
        "surface_kind": "causal_failure_chain",
        "gate_id": GP085_CP03_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id) if run is not None else None,
        "propagation_chain": propagation_chain,
        "propagation_count": len(propagation_chain),
        "pipeline_links": pipeline_links,
        "causal_failure_chain": legacy_tokens,
        "degradation_propagation_digest": (
            dict(ledger.get("degradation_propagation") or {}).get("envelope_digest")
        ),
    }


def _tcre_phase_annotation_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> str | None:
    job = session.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status.notin_(("completed", "failed")),
        )
        .order_by(CortexTcreReconstructionJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        return None
    return f"TCRE(job={job.id})"


def build_timeline_ascii_line_v1(
    phases: list[dict[str, Any]],
    *,
    continuation: dict[str, Any] | None,
) -> str:
    """ASCII progression line per cockpit spec."""
    parts: list[str] = []
    for phase in phases:
        short = _phase_short_id_v1(str(phase.get("phase_id") or ""))
        glyph = str(phase.get("glyph") or "pending")
        segment = f"{short} {_glyph_display_char_v1(glyph)}"
        if phase.get("phase_annotation"):
            segment += f"({phase['phase_annotation']})"
        parts.append(segment)
    line = "  ".join(parts)
    if continuation is not None and continuation.get("continuation_status") in (
        CONTINUATION_STATUS_WAITING,
        CONTINUATION_STATUS_STALLED,
    ):
        since = continuation.get("updated_at") or continuation.get("created_at") or "T0"
        line += (
            f"\n         ↑ continuation {continuation['continuation_status']} "
            f"since {since}"
        )
    return line


def build_pipeline_progression_timeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Surface #2 — phases 02–08 with timestamps, continuation, causal chain."""
    run: CortexSubstratePipelineRun | None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            run = None
    else:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
        if run is None:
            run = session.scalar(
                select(CortexSubstratePipelineRun)
                .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
                .order_by(CortexSubstratePipelineRun.created_at.desc())
                .limit(1)
            )

    if run is None:
        causal = build_causal_failure_chain_v1(session, tenant_id=tenant_id)
        return {
            "surface_kind": "pipeline_progression_timeline",
            "gate_id": GP085_CP03_GATE_ID_V1,
            "tenant_id": str(tenant_id),
            "pipeline_run_id": None,
            "phases": [],
            "continuation": None,
            "causal_failure_chain": causal.get("causal_failure_chain") or [],
            "causal_failure_chain_detail": causal,
            "ascii_timeline_line": "",
        }

    phases_db = list(
        session.scalars(
            select(CortexSubstratePhaseRun)
            .where(CortexSubstratePhaseRun.pipeline_run_id == run.id)
            .order_by(CortexSubstratePhaseRun.phase_ordinal.asc())
        ).all()
    )
    by_phase = {p.phase_id: p for p in phases_db}
    timeline_phases: list[dict[str, Any]] = []

    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER:
        row = by_phase.get(phase_id)
        status = row.status if row is not None else "pending"
        entry: dict[str, Any] = {
            "phase_id": phase_id,
            "status": status,
            "glyph": _phase_status_glyph_v1(status),
            "started_at": row.started_at.isoformat() if row and row.started_at else None,
            "completed_at": row.completed_at.isoformat() if row and row.completed_at else None,
        }
        if row is not None and row.error_detail:
            entry["error_detail"] = str(row.error_detail)[:300]
        if phase_id == PHASE_06_TCRE and status == "running":
            annotation = _tcre_phase_annotation_v1(session, tenant_id=tenant_id)
            if annotation:
                entry["phase_annotation"] = annotation
        timeline_phases.append(entry)

    cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=run.id)
    continuation_public = (
        continuation_row_to_public_dict_v1(cont) if cont is not None else None
    )
    receipt = build_pipeline_execution_receipt_v1(session, pipeline_run_id=run.id)
    causal = build_causal_failure_chain_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=run.id,
    )

    return {
        "surface_kind": "pipeline_progression_timeline",
        "gate_id": GP085_CP03_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id),
        "pipeline_status": run.status,
        "phases": timeline_phases,
        "continuation": continuation_public,
        "causal_failure_chain": causal.get("causal_failure_chain") or [],
        "causal_failure_chain_detail": causal,
        "propagation_chain": causal.get("propagation_chain") or [],
        "execution_receipt_digest": receipt.get("pipeline_execution_receipt_digest"),
        "highlight_phases": [PHASE_06_TCRE, PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS],
        "ascii_timeline_line": build_timeline_ascii_line_v1(
            timeline_phases,
            continuation=continuation_public,
        ),
    }


def build_overview_badges_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    maturity: dict[str, Any] | None = None,
    health: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Overview badge strip — maturity, starvation, stall (**G-P085-CP-03**)."""
    if maturity is None:
        maturity = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)
    if health is None:
        health = evaluate_operational_health_dimensions_v1(session, tenant_id=tenant_id)

    badges: list[dict[str, str]] = []
    maturity_class = str(maturity.get("maturity_class") or "STRUCTURAL_ONLY")
    badges.append({"kind": "maturity", "text": f"maturity: {maturity_class}"})

    retrieval_band = str(
        dict(health.get("health_dimensions") or {}).get("retrieval_density_health") or ""
    )
    if retrieval_band == "critical":
        badges.append({"kind": "starvation", "text": "starvation: RETRIEVAL"})
    elif retrieval_band == "degraded":
        badges.append({"kind": "starvation", "text": "starvation: retrieval_degraded"})

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if running is not None:
        cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if cont is not None and cont.continuation_status in (
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_STALLED,
        ):
            waiting_on = str(cont.waiting_on or "async")
            stall_minutes: int | None = None
            if cont.updated_at is not None:
                delta = datetime.now(UTC) - cont.updated_at.replace(tzinfo=UTC)
                stall_minutes = int(delta.total_seconds() // 60)
            stall_text = f"stall: {waiting_on}"
            if stall_minutes is not None:
                stall_text = f"stall: {waiting_on} wait {stall_minutes}m"
            badges.append({"kind": "stall", "text": stall_text})
    return badges


def _detect_forbidden_ui_violations_v1(stage_cards: list[dict[str, Any]]) -> list[str]:
    violations: list[str] = []
    for card in stage_cards:
        if (
            card.get("substrate_state") == "healthy"
            and int(card.get("total_objects") or 0) == 0
            and card.get("classification") not in ("idle",)
        ):
            violations.append(
                f"healthy_with_zero_objects_without_idle:{card.get('stage_id')}"
            )
    return violations


def build_overview_integration_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Full **G-P085-CP-03** overview — badges + stage cards + anti-fake-green checks."""
    maturity = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)
    health = evaluate_operational_health_dimensions_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    eligibility = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    stage_cards = build_operational_stage_cards_v1(session, tenant_id=tenant_id)
    badges = build_overview_badges_v1(
        session,
        tenant_id=tenant_id,
        maturity=maturity,
        health=health,
    )
    violations = _detect_forbidden_ui_violations_v1(stage_cards)

    return {
        "surface_kind": "overview_integration",
        "gate_id": GP085_CP03_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "overview_badges": badges,
        "stage_cards": stage_cards,
        "maturity_class": maturity.get("maturity_class"),
        "overall_health": health.get("overall_health"),
        "next_required_step": str(
            eligibility.get("next_required_step") or "observe_substrate_progression"
        ),
        "synthesis_classification": eligibility.get("classification"),
        "forbidden_ui_patterns": list(_FORBIDDEN_UI_PATTERNS_CP03_V1),
        "forbidden_ui_violations": violations,
        "anti_fake_green_passed": not violations,
    }


def build_progression_timeline_causal_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_progression_timeline_runtime_schema_version": int(
            PHASE085_PROGRESSION_TIMELINE_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_PROGRESSION_TIMELINE_SPEC_REF_V1,
        "primary_gate_id": GP085_CP03_GATE_ID_V1,
        "contract": PROGRESSION_TIMELINE_CONTRACT_V1,
        "stage_card_ids": list(OPERATIONAL_STAGE_CARD_IDS_V1),
        "evaluation_entrypoints": [
            "build_pipeline_progression_timeline_v1",
            "build_causal_failure_chain_v1",
            "build_overview_integration_v1",
        ],
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_progression_timeline_causal"
        ),
    }


def verify_gp085_cp03_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_progression_timeline_causal_catalog_v1()
    if cat["primary_gate_id"] != GP085_CP03_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if len(OPERATIONAL_STAGE_CARD_IDS_V1) != 5:
        errors.append("stage_card_count_not_5")

    sample_phases = [
        {"phase_id": "phase_02_canonical", "glyph": "ok"},
        {"phase_id": "phase_06_tcre", "glyph": "running", "phase_annotation": "TCRE(job=x)"},
    ]
    ascii_line = build_timeline_ascii_line_v1(sample_phases, continuation=None)
    if "02" not in ascii_line or "⏳" not in ascii_line:
        errors.append("ascii_timeline_line_malformed")

    from vector.domains.cortex.operational_runtime import operational_cockpit as oc

    cc_src = inspect.getsource(oc.build_operational_command_center_v1)
    if "build_overview_integration_v1" not in cc_src:
        errors.append("command_center_missing_overview_integration")
    if "substrate_progression_timeline_causal" not in cc_src and (
        "build_overview_integration_v1" not in cc_src
    ):
        errors.append("command_center_not_delegating_cp03")

    if not callable(build_causal_failure_chain_v1):
        errors.append("missing_build_causal_failure_chain_v1")

    passed = not errors
    return {
        "id": GP085_CP03_GATE_ID_V1,
        "name": "cesp_substrate_progression_timeline_causal",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
