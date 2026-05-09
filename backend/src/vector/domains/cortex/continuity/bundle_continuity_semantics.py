"""Bundle + continuity semantics (Phase 3.5) — rules for cross-generation stability.

Phase 04 identity linking and Phase 05 graph projection must not fork universes across bundle pins
without explicit migration records. This module encodes **deterministic interpretation rules** for
continuity keys and replay equivalence at the contract layer.
"""

from __future__ import annotations

from typing import Any, Final, Literal

CONTINUITY_BUNDLE_SEMANTICS_VERSION: Final[int] = 1

ContinuityScopeKind = Literal["bundle_scoped", "reference_plane", "raw_anchored"]


def continuity_scope_for_materialization(*, bundle_id: str) -> dict[str, Any]:
    """Canonical materializations remain bundle-scoped (existing Phase 03 doctrine)."""
    return {
        "continuity_bundle_semantics_version": CONTINUITY_BUNDLE_SEMANTICS_VERSION,
        "scope_kind": "bundle_scoped",
        "bundle_id": bundle_id,
        "interpretation": (
            "Logical keys and materialization rows are authoritative only within this bundle pin; "
            "cross-bundle continuity uses normalized references + Phase 04 linkage ledger."
        ),
    }


def continuity_scope_for_normalized_reference() -> dict[str, Any]:
    """Normalized references are intentionally bundle-agnostic join keys."""
    return {
        "continuity_bundle_semantics_version": CONTINUITY_BUNDLE_SEMANTICS_VERSION,
        "scope_kind": "reference_plane",
        "interpretation": (
            "NormalizedReference canonical_form strings are stable across bundle generations for the same "
            "provider evidence; they do not imply merged identity."
        ),
    }


def continuity_scope_for_raw_record(*, raw_record_id: int) -> dict[str, Any]:
    """Raw rows are the ultimate replay anchor."""
    return {
        "continuity_bundle_semantics_version": CONTINUITY_BUNDLE_SEMANTICS_VERSION,
        "scope_kind": "raw_anchored",
        "raw_record_id": int(raw_record_id),
        "interpretation": "Append-only raw memory is the replay source of truth; transforms may vary by bundle.",
    }


def validate_edge_bundle_alignment(
    *,
    edge_bundle_id: str,
    source_scope: dict[str, Any] | None,
    target_scope: dict[str, Any] | None,
) -> list[str]:
    """Return validation warnings (empty if ok) for mixed bundle endpoints on canonical pointers."""
    warnings: list[str] = []
    if not edge_bundle_id.strip():
        warnings.append("edge_missing_bundle_id")
    # If both endpoints carry canonical_pointer with different bundle ids, flag (Phase 04 may still allow via rule).
    sb = _bundle_from_endpoint(source_scope)
    tb = _bundle_from_endpoint(target_scope)
    if sb and tb and sb != tb:
        warnings.append("cross_bundle_canonical_endpoints_require_explicit_migration_rule")
    return warnings


def _bundle_from_endpoint(scope: dict[str, Any] | None) -> str | None:
    if not scope or not isinstance(scope, dict):
        return None
    cp = scope.get("canonical_pointer")
    if isinstance(cp, dict):
        bid = cp.get("bundle_id")
        return str(bid) if isinstance(bid, str) and bid.strip() else None
    return None
