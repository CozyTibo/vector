"""Phase 06 P06-12 — cross-system time reconciliation (``rank(S)`` + policy floor + chronology gates).

Normative:
``DOCS/cortex/reasoning/cross-system-causal-continuity.md``,
``DOCS/cortex/reasoning/chronology-legality-law.md`` (downstream gates),
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``cross_system_causal_min_rank``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import IdentityLinkDerivation
from vector.domains.cortex.reasoning.chronology_legality import (
    CHRONOLOGY_LEGALITY_CLASSES,
    ChronologyLegalityError,
    load_default_reasoning_policy_pack,
)

PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# ``cross-system-causal-continuity.md`` §1 — frozen ordinal (higher = stronger substrate).
CONTINUITY_BRIDGE_STRENGTH_TO_RANK_V1: Final[dict[str, int]] = {
    "unverifiable": 1,
    "weak": 2,
    "partial": 3,
    "continuity_backed": 4,
    "direct": 5,
    "authoritative": 6,
}

CONTINUITY_BRIDGE_STRENGTHS_V1: Final[frozenset[str]] = frozenset(CONTINUITY_BRIDGE_STRENGTH_TO_RANK_V1)

CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1: Final[int] = 4

_RANK4_ALLOWED_IDENTITY_LINK_DERIVATIONS: Final[frozenset[str]] = frozenset(
    {
        IdentityLinkDerivation.EXPLICIT_LINKAGE.value,
        IdentityLinkDerivation.SHARED_EXECUTION_REFERENCE.value,
    }
)


class CrossSystemTimeReconciliationError(ValueError):
    """Fail-closed cross-system causal / chronology reconciliation."""


def continuity_bridge_strength_rank_v1(strength: str) -> int:
    """§1 — ``rank(S)``; **no** string comparator outside this table."""
    if not isinstance(strength, str) or strength not in CONTINUITY_BRIDGE_STRENGTHS_V1:
        allowed = ", ".join(sorted(CONTINUITY_BRIDGE_STRENGTHS_V1))
        raise CrossSystemTimeReconciliationError(
            f"continuity_bridge_strength must be one of: {allowed}; got {strength!r}"
        )
    return CONTINUITY_BRIDGE_STRENGTH_TO_RANK_V1[strength]


def continuity_bridge_strictly_stronger_v1(left_strength: str, right_strength: str) -> bool:
    """§1 comparison law — ``rank(S_left) > rank(S_right)``."""
    return continuity_bridge_strength_rank_v1(left_strength) > continuity_bridge_strength_rank_v1(right_strength)


def cross_system_causal_effective_min_rank_v1(policy: Mapping[str, Any]) -> int:
    """Policy ``cross_system_causal_min_rank`` floored at **4** (constitutional cross-origin minimum)."""
    raw = policy.get("cross_system_causal_min_rank", CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1)
    if not isinstance(raw, int) or raw < 1 or raw > 6:
        raise CrossSystemTimeReconciliationError(
            "policy.cross_system_causal_min_rank must be int in [1, 6] when present"
        )
    return max(CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1, raw)


def skew_flag_tuple_from_reasoning_snapshot_v1(snapshot: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    """Substrate skew / export flags for operator strip + chronology skew projection (typed when present)."""
    out: list[bool] = []
    for key in ("skew_detected", "late_arrival", "export_sequence_conflict"):
        if key not in snapshot:
            out.append(False)
            continue
        v = snapshot[key]
        if not isinstance(v, bool):
            raise CrossSystemTimeReconciliationError(f"snapshot.{key} must be bool when present")
        out.append(v)
    return out[0], out[1], out[2]


def validate_chronology_allows_strict_temporal_order_claim_v1(
    chronology_legality_class: str,
    *,
    asserts_strict_temporal_total_order: bool,
) -> None:
    """``chronology-legality-law.md`` §1 / §2 — strict total-order claims require ``chronology_strict``."""
    if not isinstance(chronology_legality_class, str) or chronology_legality_class not in CHRONOLOGY_LEGALITY_CLASSES:
        allowed = ", ".join(sorted(CHRONOLOGY_LEGALITY_CLASSES))
        raise CrossSystemTimeReconciliationError(
            f"chronology_legality_class must be one of: {allowed}; got {chronology_legality_class!r}"
        )
    if not asserts_strict_temporal_total_order:
        return
    if chronology_legality_class != "chronology_strict":
        raise CrossSystemTimeReconciliationError(
            "strict temporal total-order claim forbidden unless chronology_legality_class is chronology_strict"
        )


def validate_cross_system_causal_continuity_requirements_v1(
    *,
    connector_origin_left: str,
    connector_origin_right: str,
    continuity_bridge_strength: str,
    identity_link_derivation: object,
    policy: Mapping[str, Any],
) -> None:
    """**CROSS-CAUS-1** / **CROSS-CAUS-2** — cross-origin causal influence requires ``rank(S)`` floor + rank‑4 derivation."""
    if not isinstance(connector_origin_left, str) or not connector_origin_left.strip():
        raise CrossSystemTimeReconciliationError("connector_origin_left must be a non-empty string")
    if not isinstance(connector_origin_right, str) or not connector_origin_right.strip():
        raise CrossSystemTimeReconciliationError("connector_origin_right must be a non-empty string")
    left, right = connector_origin_left.strip(), connector_origin_right.strip()
    if left == right:
        return
    rank_s = continuity_bridge_strength_rank_v1(continuity_bridge_strength)
    need = cross_system_causal_effective_min_rank_v1(policy)
    if rank_s < need:
        raise CrossSystemTimeReconciliationError(
            f"CROSS-CAUS-1: rank(S)={rank_s} < effective_min_rank={need} for cross-origin causal edge"
        )
    if rank_s == CONTINUITY_BRIDGE_STRENGTH_TO_RANK_V1["continuity_backed"]:
        if not isinstance(identity_link_derivation, str) or not identity_link_derivation.strip():
            raise CrossSystemTimeReconciliationError(
                "CROSS-CAUS-1: identity_link_derivation required when rank(S)==4 (continuity_backed)"
            )
        d = identity_link_derivation.strip()
        if d not in _RANK4_ALLOWED_IDENTITY_LINK_DERIVATIONS:
            raise CrossSystemTimeReconciliationError(
                "CROSS-CAUS-1: at rank(S)==4, IdentityLinkDerivation must be explicit_linkage "
                "or shared_execution_reference per continuity law"
            )


def verify_gp06_xst01_rank_table_oracle_static() -> dict[str, Any]:
    """Static — §1 ranks strictly increase with intended strength ladder."""
    errors: list[str] = []
    order = (
        "unverifiable",
        "weak",
        "partial",
        "continuity_backed",
        "direct",
        "authoritative",
    )
    prev = 0
    for s in order:
        r = CONTINUITY_BRIDGE_STRENGTH_TO_RANK_V1.get(s)
        if r is None:
            errors.append(f"missing_rank:{s}")
            continue
        if r <= prev:
            errors.append(f"non_monotonic_rank:{s}:{r}:prev={prev}")
        prev = r
    passed = len(errors) == 0
    return {
        "id": "P06-12-xst-rank-oracle",
        "name": "gp06_xst01_rank_table_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_cross_system_time_reconciliation_runtime_schema_version": (
                PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_xst02_default_policy_min_rank_static() -> dict[str, Any]:
    """Static — default fixture carries ``cross_system_causal_min_rank`` aligned with doctrine."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack()
        mr = pack.get("cross_system_causal_min_rank")
        if mr != CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1:
            errors.append(f"expected_min_rank_4_got:{mr!r}")
        if cross_system_causal_effective_min_rank_v1(pack) != CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1:
            errors.append("effective_min_rank_mismatch")
    except (CrossSystemTimeReconciliationError, ChronologyLegalityError, OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-12-xst-default-policy",
        "name": "gp06_xst02_default_policy_min_rank",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_cross_system_time_reconciliation_runtime_schema_version": (
                PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_xst03_cross_caus_rank4_derivation_gate_static() -> dict[str, Any]:
    """Static — rank **4** path rejects forbidden ``IdentityLinkDerivation`` values."""
    errors: list[str] = []
    policy = {"cross_system_causal_min_rank": 4}
    try:
        validate_cross_system_causal_continuity_requirements_v1(
            connector_origin_left="linear",
            connector_origin_right="slack",
            continuity_bridge_strength="continuity_backed",
            identity_link_derivation=IdentityLinkDerivation.TEMPORAL_OVERLAP.value,
            policy=policy,
        )
        errors.append("expected_temporal_overlap_rejected_at_rank4")
    except CrossSystemTimeReconciliationError:
        pass
    try:
        validate_cross_system_causal_continuity_requirements_v1(
            connector_origin_left="a",
            connector_origin_right="b",
            continuity_bridge_strength="continuity_backed",
            identity_link_derivation=IdentityLinkDerivation.EXPLICIT_LINKAGE.value,
            policy=policy,
        )
    except CrossSystemTimeReconciliationError as exc:
        errors.append(f"explicit_linkage_should_pass:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-12-xst-rank4-derivation",
        "name": "gp06_xst03_cross_caus_rank4_derivation_gate",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_cross_system_time_reconciliation_runtime_schema_version": (
                PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
