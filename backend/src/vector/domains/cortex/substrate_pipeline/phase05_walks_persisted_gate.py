"""Phase B step B4 — require walks persisted when traversal scheduling is eligible."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    evaluate_traversal_schedule_v1,
    run_octs_walk_schedule_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_SKIPPED_BY_POLICY,
)

PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION: Final[int] = 1
P0_B4_STEP: Final[str] = "step_b4_phase05_walks_persisted"
BLOCK_REASON_WALKS_NOT_PERSISTED_WHEN_ELIGIBLE_V1: Final[str] = (
    "walks_not_persisted_when_scheduling_eligible"
)


def is_phase05_walks_gate_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_phase05_require_walks_when_scheduling_eligible)
    except Exception:  # noqa: BLE001
        return True


def evaluate_phase05_schedule_context_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str = TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
) -> dict[str, Any]:
    """Whether G-P085-WALK-01 would schedule walks for this tenant (post phase 05)."""
    evaluation = evaluate_traversal_schedule_v1(
        session,
        tenant_id=tenant_id,
        trigger=trigger,
    )
    return {
        "phase_b4_schema_version": PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
        "trigger": trigger,
        "scheduling_eligible": bool(evaluation.get("should_schedule")),
        "evaluation": evaluation,
    }


def summarize_phase05_walk_output_v1(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize walk counters from phase 05 slice or schedule pass output."""
    walks_persisted = int(raw.get("walks_persisted") or 0)
    walk_ids = [str(w) for w in (raw.get("walk_ids") or []) if str(w).strip()]
    supplement = dict(raw.get("walk_schedule_supplement") or {})
    if supplement:
        walks_persisted = max(
            walks_persisted,
            int(supplement.get("walks_persisted") or 0),
        )
        for wid in supplement.get("walk_ids") or []:
            s = str(wid).strip()
            if s and s not in walk_ids:
                walk_ids.append(s)
    walks_available = len(walk_ids)
    return {
        "walks_persisted": walks_persisted,
        "walk_ids": walk_ids,
        "walks_available": walks_available,
        "primary_octs_walk_id": raw.get("primary_octs_walk_id"),
        "skipped_idempotent": int(raw.get("skipped_idempotent") or 0),
        "starts_selected": int(raw.get("starts_selected") or 0),
        "reason": raw.get("reason"),
    }


def supplement_phase05_walks_when_eligible_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    raw_output: dict[str, Any],
    schedule_context: dict[str, Any],
    graph_projection_stable_hash: str | None = None,
) -> dict[str, Any]:
    """When scheduling is eligible but slice persisted zero walks, run schedule pass once."""
    if not is_phase05_walks_gate_enabled_v1():
        return raw_output
    if not bool(schedule_context.get("scheduling_eligible")):
        return raw_output

    summary = summarize_phase05_walk_output_v1(raw_output)
    if summary["walks_persisted"] > 0 or summary["walks_available"] > 0:
        return raw_output

    pass_out = run_octs_walk_schedule_pass_v1(
        session,
        tenant_id=tenant_id,
        trigger=str(schedule_context.get("trigger") or TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1),
        pipeline_run_id=pipeline_run_id,
        graph_projection_stable_hash=graph_projection_stable_hash,
    )
    mat = dict(pass_out.get("materialization") or {})
    supplement = {
        "scheduled": bool(pass_out.get("scheduled")),
        "walks_persisted": int(mat.get("walks_persisted") or 0),
        "walk_ids": list(mat.get("walk_ids") or []),
        "primary_octs_walk_id": mat.get("primary_octs_walk_id"),
        "skipped_idempotent": int(mat.get("skipped_idempotent") or 0),
        "reason": mat.get("reason"),
        "pass_reason": pass_out.get("reason"),
    }
    merged = {**raw_output, "walk_schedule_supplement": supplement}
    if supplement["walks_persisted"] > 0 or supplement["walk_ids"]:
        merged["walks_persisted"] = max(
            int(merged.get("walks_persisted") or 0),
            supplement["walks_persisted"],
        )
        merged["walk_ids"] = supplement["walk_ids"]
        merged["primary_octs_walk_id"] = (
            supplement.get("primary_octs_walk_id") or merged.get("primary_octs_walk_id")
        )
        merged["skipped_idempotent"] = int(merged.get("skipped_idempotent") or 0) + supplement[
            "skipped_idempotent"
        ]
    merged["phase05_walks_gate"] = {
        "supplement_attempted": True,
        "supplement": supplement,
    }
    return merged


def resolve_phase05_traversal_outcome_v1(
    raw_output: dict[str, Any],
    schedule_context: dict[str, Any],
) -> tuple[str, str | None, dict[str, Any]]:
    """Map phase 05 output to receipt outcome — block fake-green empty when eligible."""
    summary = summarize_phase05_walk_output_v1(raw_output)
    eligible = bool(schedule_context.get("scheduling_eligible"))
    gate: dict[str, Any] = {
        "schema_version": PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
        "enabled": is_phase05_walks_gate_enabled_v1(),
        "scheduling_eligible": eligible,
        **summary,
    }
    raw_output = {**raw_output, "phase05_walks_gate": gate, "scheduling_eligible": eligible}

    if not gate["enabled"]:
        if summary["walks_persisted"] > 0 or summary["walks_available"] > 0:
            return PHASE_OUTCOME_COMPLETED, None, raw_output
        if str(summary.get("reason") or "") in ("no_start_nodes", "missing_projection"):
            return PHASE_OUTCOME_COMPLETED_EMPTY, None, raw_output
        return PHASE_OUTCOME_COMPLETED_EMPTY, None, raw_output

    if not eligible:
        if summary["walks_persisted"] > 0 or summary["walks_available"] > 0:
            return PHASE_OUTCOME_COMPLETED, None, raw_output
        if str(summary.get("reason") or "") in ("no_start_nodes", "missing_projection"):
            return PHASE_OUTCOME_SKIPPED_BY_POLICY, "traversal_not_schedulable", raw_output
        return PHASE_OUTCOME_COMPLETED_EMPTY, None, raw_output

    if summary["walks_persisted"] > 0 or summary["walks_available"] > 0:
        gate["ok"] = True
        raw_output["phase05_walks_gate"] = gate
        return PHASE_OUTCOME_COMPLETED, None, raw_output

    gate["ok"] = False
    gate["blocked_reason"] = BLOCK_REASON_WALKS_NOT_PERSISTED_WHEN_ELIGIBLE_V1
    raw_output["phase05_walks_gate"] = gate
    return PHASE_OUTCOME_BLOCKED, BLOCK_REASON_WALKS_NOT_PERSISTED_WHEN_ELIGIBLE_V1, raw_output


def enforce_schedule_pass_walks_persisted_v1(
    schedule_result: dict[str, Any],
    *,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """After ``schedule_octs_walks_for_tenant_v1`` inline pass — fail closed when eligible but empty."""
    out = dict(schedule_result)
    should = bool(evaluation.get("should_schedule"))
    pass_body = dict(out.get("pass") or {})
    mat = dict(pass_body.get("materialization") or {})
    persisted = int(mat.get("walks_persisted") or 0)
    walk_ids = list(mat.get("walk_ids") or [])
    gate = {
        "schema_version": PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
        "scheduling_eligible": should,
        "walks_persisted": persisted,
        "walks_available": len(walk_ids),
        "ok": (not should) or persisted > 0 or len(walk_ids) > 0,
    }
    out["phase05_walks_gate"] = gate
    if should and bool(out.get("scheduled")) and not gate["ok"]:
        out["scheduled"] = False
        out["reason"] = BLOCK_REASON_WALKS_NOT_PERSISTED_WHEN_ELIGIBLE_V1
        if pass_body:
            pass_body["scheduled"] = False
            pass_body["reason"] = BLOCK_REASON_WALKS_NOT_PERSISTED_WHEN_ELIGIBLE_V1
            out["pass"] = pass_body
    return out
