"""RUNTIME-02 — deterministic chronology explanation projections (template-only)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

TCRE_OPERATOR_CHRONOLOGY_EXPLANATION_SCHEMA_VERSION: Final[int] = 1

_DERIVATION_RULE_PREFIX = "CHRON-PROJ"


def chronology_projection_rule_id_v1(*, matched_projection_row_index: int, partitioned: bool) -> str:
    base = f"{_DERIVATION_RULE_PREFIX}-{matched_projection_row_index:02d}"
    if partitioned:
        return f"{base}-PARTITIONED"
    return base


def build_chronology_explanation_summary_v1(
    *,
    replay_safe_ordering: str,
    chronology_legality_class: str,
    projection_rule_id: str,
    skew_detected: bool,
    late_arrival: bool,
    export_sequence_conflict: bool,
    partitioned_exception_applied: bool,
) -> str:
    parts: list[str] = [
        f"Contract replay_safe_ordering={replay_safe_ordering}; "
        f"policy projected chronology_legality_class={chronology_legality_class} "
        f"via {projection_rule_id}."
    ]
    if skew_detected:
        parts.append("skew_detected=true on snapshot.")
    if late_arrival:
        parts.append("late_arrival=true (observed_at after occurred_at).")
    if export_sequence_conflict:
        parts.append("export_sequence_conflict=true on snapshot.")
    if partitioned_exception_applied:
        parts.append("§2.2 partitioned_exception row applied.")
    if chronology_legality_class == "chronology_degraded":
        parts.append(f"Degradation code {CD_CHRON} eligible when emitted in tenant slice.")
    return " ".join(parts)


def project_chronology_explanation_v1(
    *,
    materialization_id: str,
    canonical_object_kind: str | None,
    bundle_id: str | None,
    occurred_at_iso: str | None,
    observed_at_iso: str | None,
    chronology_row: Mapping[str, Any],
    tcre_policy_bundle_digest: str,
    replay_posture: str,
) -> dict[str, Any]:
    """Serializable chronology explanation (hash-stable body excluding summary text ordering)."""
    snap = dict(chronology_row.get("snapshot") or {})
    legality = str(chronology_row.get("chronology_legality_class") or "")
    idx = int(chronology_row.get("matched_projection_row_index") or 0)
    partitioned = bool(chronology_row.get("partitioned_exception_applied"))
    rso = str(snap.get("replay_safe_ordering") or "")
    rule_id = chronology_projection_rule_id_v1(
        matched_projection_row_index=idx,
        partitioned=partitioned,
    )
    receipt_body = chronology_row.get("receipt_body") or {}
    receipt_digest = str(chronology_row.get("receipt_digest") or "")
    skew = bool(snap.get("skew_detected"))
    late = bool(snap.get("late_arrival"))
    export_conf = bool(snap.get("export_sequence_conflict"))
    summary = build_chronology_explanation_summary_v1(
        replay_safe_ordering=rso,
        chronology_legality_class=legality,
        projection_rule_id=rule_id,
        skew_detected=skew,
        late_arrival=late,
        export_sequence_conflict=export_conf,
        partitioned_exception_applied=partitioned,
    )
    body = {
        "schema_version": TCRE_OPERATOR_CHRONOLOGY_EXPLANATION_SCHEMA_VERSION,
        "materialization_id": materialization_id,
        "canonical_object_kind": canonical_object_kind,
        "bundle_id": bundle_id,
        "occurred_at": occurred_at_iso,
        "observed_at": observed_at_iso,
        "replay_safe_ordering": rso,
        "chronology_legality_class": legality,
        "chronology_projection_rule_id": rule_id,
        "matched_projection_row_index": idx,
        "partitioned_exception_applied": partitioned,
        "skew_detected": skew,
        "late_arrival": late,
        "export_sequence_conflict": export_conf,
        "replay_posture": replay_posture,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "chronology_receipt_digest": receipt_digest,
        "degradation_codes": [CD_CHRON] if legality == "chronology_degraded" else [],
        "retrieval_lookup_id": f"chronology:{materialization_id}",
        "chronology_window_ref": materialization_id,
    }
    explanation_digest = hash_reasoning_canonical_json_sha256_v1(body)
    return {
        **body,
        "explanation_summary": summary,
        "explanation_digest": explanation_digest,
        "receipt_body": dict(receipt_body) if isinstance(receipt_body, Mapping) else {},
    }
