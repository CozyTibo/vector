"""Phase S1 helpers — honest phase-03 receipts and phase-04 skip when identity delta is zero."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.identity_substrate_health_v1 import (
    evaluate_identity_substrate_health_v1,
    phase_03_forbids_completed_empty_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
    read_phase_receipt_from_output,
)


def infer_phase_03_processed_count_v1(raw: dict[str, Any]) -> int:
    """Phase 03 processed count from substrate work, not missing org_link_edges."""
    audit = raw.get("identity_substrate_audit")
    aud = audit if isinstance(audit, dict) else {}
    substrate = raw.get("identity_continuity_substrate")
    sub = substrate if isinstance(substrate, dict) else {}

    backfill = aud.get("anchor_backfill")
    if not isinstance(backfill, dict):
        backfill = {k: v for k, v in sub.items() if k != "candidate_regeneration"}

    entities = int((backfill or {}).get("entities_upserted") or 0)
    candidates = int(aud.get("candidates_generated_count") or sub.get("candidate_regeneration", {}).get("candidate_count") or 0)
    return entities + candidates


def identity_substrate_has_zero_delta_v1(raw: dict[str, Any]) -> bool:
    """True when phase 03 produced no entity upserts and no new distinct candidate pairs."""
    audit = raw.get("identity_substrate_audit")
    aud = audit if isinstance(audit, dict) else {}
    delta = aud.get("distinct_candidate_pairs_delta")
    if delta is None:
        delta = raw.get("distinct_candidate_pairs_delta")
    entities = int((aud.get("anchor_backfill") or {}).get("entities_upserted") or 0)
    return int(delta or 0) == 0 and entities == 0


def phase_03_outcome_is_completed_empty_v1(raw: dict[str, Any]) -> bool:
    receipt = read_phase_receipt_from_output(raw)
    if receipt is None:
        return infer_phase_03_processed_count_v1(raw) == 0
    return receipt.get("outcome") == PHASE_OUTCOME_COMPLETED_EMPTY


def resolve_phase_03_outcome_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    raw_output: dict[str, Any],
) -> tuple[str, str | None]:
    """Map repair slice + substrate health to a truthful phase-03 receipt outcome."""
    health = raw_output.get("identity_substrate_health_after")
    if not isinstance(health, dict):
        health = evaluate_identity_substrate_health_v1(session, tenant_id=tenant_id)

    processed = infer_phase_03_processed_count_v1(raw_output)
    repair = (raw_output.get("identity_continuity_substrate") or {}).get("identity_substrate_repair") or {}
    exhausted = bool(repair.get("anchor_backfill_exhausted"))
    counts_after = (raw_output.get("identity_substrate_audit") or {}).get("counts_after") or raw_output.get(
        "counts_after"
    )
    human_after = 0
    if isinstance(counts_after, dict):
        human_after = int(counts_after.get("org_entities_active") or 0)

    status = str(health.get("status") or "healthy")
    if status == "broken":
        if human_after > 0:
            return PHASE_OUTCOME_COMPLETED, None
        if processed > 0:
            return PHASE_OUTCOME_COMPLETED, None
        if not exhausted:
            return PHASE_OUTCOME_COMPLETED, "identity_substrate_repair_in_progress"
        return PHASE_OUTCOME_FAILED, "identity_substrate_broken_unrecoverable"

    if phase_03_forbids_completed_empty_v1(health) and identity_substrate_has_zero_delta_v1(raw_output):
        if not exhausted:
            return PHASE_OUTCOME_COMPLETED, "identity_substrate_repair_in_progress"
        return PHASE_OUTCOME_FAILED, "identity_substrate_degraded_no_progress"

    if processed == 0 and not raw_output.get("skipped"):
        return PHASE_OUTCOME_COMPLETED_EMPTY, None
    return PHASE_OUTCOME_COMPLETED, None


def should_skip_phase_04_after_identity_v1(phase_03_output: dict[str, Any]) -> bool:
    """Skip graph projection when identity substrate had zero delta (S1.6)."""
    if phase_03_output.get("skipped"):
        return False
    health = phase_03_output.get("identity_substrate_health_after")
    if isinstance(health, dict) and str(health.get("status") or "") in ("degraded", "broken"):
        return False
    if not phase_03_outcome_is_completed_empty_v1(phase_03_output):
        return False
    return identity_substrate_has_zero_delta_v1(phase_03_output)
