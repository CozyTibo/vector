"""Phase S1 helpers — honest phase-03 receipts and phase-04 skip when identity delta is zero."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
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


def should_skip_phase_04_after_identity_v1(phase_03_output: dict[str, Any]) -> bool:
    """Skip graph projection when identity substrate had zero delta (S1.6)."""
    if phase_03_output.get("skipped"):
        return False
    if not phase_03_outcome_is_completed_empty_v1(phase_03_output):
        return False
    return identity_substrate_has_zero_delta_v1(phase_03_output)
