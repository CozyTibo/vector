"""Phase 05 P05-02 — observed vs derived traversal (pure validators).

Normative: ``DOCS/cortex/05-traversal/phase-05-observed-vs-derived-doctrine.md``.
Walk execution strategy enums: ``phase-05-walk-execution-strategy-doctrine.md`` §3.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

OVD_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PROVENANCE_CLASS_OBSERVED: Final[str] = "observed"
PROVENANCE_CLASS_DERIVED: Final[str] = "derived"

WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED: Final[str] = "ONLINE_OBSERVED"
WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED: Final[str] = "MATERIALIZED_DERIVED"
WALK_EXECUTION_STRATEGY_HYBRID_PINNED: Final[str] = "HYBRID_PINNED"

_STRATEGIES_REQUIRING_DERIVED_FLAG_AND_INDEX_PIN: Final[frozenset[str]] = frozenset(
    {
        WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
        WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    }
)


class ObservedDerivedInvariantError(ValueError):
    """Raised when hop receipts or walk flags violate OCTS observed/derived rules."""


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _authority_binding_present(authority_binding: object) -> bool:
    """True when binding is a non-empty dict (FS-OVD-01 / negative examples)."""
    return isinstance(authority_binding, dict) and bool(authority_binding)


def validate_hop_receipt_observed_derived(receipt: Mapping[str, Any]) -> None:
    """RULE OVD-01 + FS-OVD-01; derived branch aligns with hop HR-03 (derivation_rule_id).

    Raises:
        ObservedDerivedInvariantError: on illegal receipt shapes.
    """
    pc = receipt.get("provenance_class")
    if pc not in (PROVENANCE_CLASS_OBSERVED, PROVENANCE_CLASS_DERIVED):
        msg = "hop_receipt.provenance_class must be 'observed' or 'derived'"
        raise ObservedDerivedInvariantError(msg)

    ab = receipt.get("authority_binding")
    deriv = receipt.get("derivation_rule_id")

    if pc == PROVENANCE_CLASS_OBSERVED:
        if not _authority_binding_present(ab):
            msg = "FS-OVD-01: provenance_class=observed requires non-empty authority_binding"
            raise ObservedDerivedInvariantError(msg)
        return

    # derived
    if not _non_empty_str(deriv):
        msg = "derived hop_receipt requires non-empty derivation_rule_id"
        raise ObservedDerivedInvariantError(msg)
    # OVD §7: binding nullable only when derived and derivation_rule_id present — satisfied;
    # if binding is present it must still be a mapping (object), not a string.
    if ab is not None and not isinstance(ab, dict):
        msg = "authority_binding must be null or an object when provenance_class=derived"
        raise ObservedDerivedInvariantError(msg)


def validate_hop_receipt_sequence(hop_receipts: Sequence[Mapping[str, Any]]) -> None:
    """RULE OVD serialization: ascending contiguous ``hop_sequence`` 0..N-1 (§8)."""
    for i, rec in enumerate(hop_receipts):
        seq = rec.get("hop_sequence")
        if not isinstance(seq, int) or seq != i:
            msg = f"hop_sequence must be contiguous 0..N-1; expected {i}, got {seq!r}"
            raise ObservedDerivedInvariantError(msg)


def validate_walk_observed_derived_consistency(
    *,
    walk_execution_strategy: str,
    hop_receipts: Sequence[Mapping[str, Any]],
    walk_result: Mapping[str, Any],
    temporal_anchor: Mapping[str, Any] | None,
) -> None:
    """RULE OVD-02 + FS-OVD-02; index pin per walk execution strategy (WES §6).

    ``walk_result`` MUST expose ``execution_path_contains_derived`` (bool).

    Raises:
        ObservedDerivedInvariantError: when flags or anchor violate doctrine.
    """
    if walk_execution_strategy not in (
        WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
        WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
        WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    ):
        msg = f"unknown walk_execution_strategy: {walk_execution_strategy!r}"
        raise ObservedDerivedInvariantError(msg)

    contains_derived = walk_result.get("execution_path_contains_derived")
    if not isinstance(contains_derived, bool):
        msg = "walk_result.execution_path_contains_derived must be a boolean"
        raise ObservedDerivedInvariantError(msg)

    any_derived_hop = any(
        r.get("provenance_class") == PROVENANCE_CLASS_DERIVED for r in hop_receipts
    )
    if any_derived_hop and contains_derived is not True:
        msg = "FS-OVD-02: derived hop(s) require execution_path_contains_derived=true"
        raise ObservedDerivedInvariantError(msg)

    if walk_execution_strategy in _STRATEGIES_REQUIRING_DERIVED_FLAG_AND_INDEX_PIN:
        if contains_derived is not True:
            msg = (
                "OVD-02: materialized or hybrid strategy requires "
                "execution_path_contains_derived=true"
            )
            raise ObservedDerivedInvariantError(msg)
        if temporal_anchor is None or "pinned_index_epoch" not in temporal_anchor:
            msg = (
                "OVD-02 / WES-§6: MATERIALIZED_DERIVED or HYBRID_PINNED requires "
                "temporal_anchor.pinned_index_epoch"
            )
            raise ObservedDerivedInvariantError(msg)
        epoch = temporal_anchor.get("pinned_index_epoch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
            msg = "temporal_anchor.pinned_index_epoch must be a non-negative int (not bool)"
            raise ObservedDerivedInvariantError(msg)


def verify_gp05_ovd01_observed_hop_bindings_static() -> dict[str, Any]:
    """G-P05-OVD-01 — receipt audit for observed authority_binding."""
    errors: list[str] = []

    illegal_observed = {
        "hop_sequence": 0,
        "provenance_class": PROVENANCE_CLASS_OBSERVED,
        "authority_binding": None,
    }
    try:
        validate_hop_receipt_observed_derived(illegal_observed)
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection for observed hop with null authority_binding")

    illegal_observed_empty = {
        "hop_sequence": 0,
        "provenance_class": PROVENANCE_CLASS_OBSERVED,
        "authority_binding": {},
    }
    try:
        validate_hop_receipt_observed_derived(illegal_observed_empty)
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection for observed hop with empty authority_binding")

    derived_no_rule = {
        "hop_sequence": 0,
        "provenance_class": PROVENANCE_CLASS_DERIVED,
        "authority_binding": None,
    }
    try:
        validate_hop_receipt_observed_derived(derived_no_rule)
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection for derived hop without derivation_rule_id")

    try:
        validate_hop_receipt_observed_derived(
            {
                "hop_sequence": 0,
                "provenance_class": PROVENANCE_CLASS_OBSERVED,
                "authority_binding": {"org_link_id": "01HZ", "edge_fingerprint": "sha256:ab"},
            }
        )
    except ObservedDerivedInvariantError as exc:
        errors.append(f"unexpected rejection on legal observed receipt: {exc}")

    try:
        validate_hop_receipt_observed_derived(
            {
                "hop_sequence": 0,
                "provenance_class": PROVENANCE_CLASS_DERIVED,
                "authority_binding": None,
                "derivation_rule_id": "DERIVED_ADJ_v3",
            }
        )
    except ObservedDerivedInvariantError as exc:
        errors.append(f"unexpected rejection on legal derived receipt: {exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-OVD-01",
        "name": "observed_hop_authority_binding",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ovd_runtime_schema_version": OVD_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_ovd02_strategy_and_derived_flags_static() -> dict[str, Any]:
    """G-P05-OVD-02 — strategy forces derived flag + index epoch; FS-OVD-02."""
    errors: list[str] = []
    anchor = {"pinned_index_epoch": 42}

    good_receipts = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_OBSERVED,
            "authority_binding": {"org_link_id": "x", "edge_fingerprint": "sha256:00"},
        }
    ]
    try:
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
            hop_receipts=good_receipts,
            walk_result={"execution_path_contains_derived": True},
            temporal_anchor=anchor,
        )
    except ObservedDerivedInvariantError as exc:
        errors.append(f"unexpected rejection materialized good: {exc}")

    try:
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
            hop_receipts=good_receipts,
            walk_result={"execution_path_contains_derived": False},
            temporal_anchor=None,
        )
    except ObservedDerivedInvariantError as exc:
        errors.append(f"unexpected rejection online observed only: {exc}")

    try:
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
            hop_receipts=good_receipts,
            walk_result={"execution_path_contains_derived": False},
            temporal_anchor=anchor,
        )
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection when materialized strategy omits derived flag")

    derived_hops = [
        {
            "hop_sequence": 0,
            "provenance_class": PROVENANCE_CLASS_DERIVED,
            "authority_binding": None,
            "derivation_rule_id": "DERIVED_ADJ_v3",
        }
    ]
    try:
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
            hop_receipts=derived_hops,
            walk_result={"execution_path_contains_derived": False},
            temporal_anchor=None,
        )
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection for derived hop without execution_path_contains_derived")

    try:
        validate_walk_observed_derived_consistency(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
            hop_receipts=derived_hops,
            walk_result={"execution_path_contains_derived": True},
            temporal_anchor=None,
        )
    except ObservedDerivedInvariantError:
        pass
    else:
        errors.append("expected rejection for materialized strategy without pinned_index_epoch")

    passed = len(errors) == 0
    return {
        "id": "G-P05-OVD-02",
        "name": "strategy_requires_derived_flag_and_epoch",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ovd_runtime_schema_version": OVD_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }
