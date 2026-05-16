"""Phase 06 P06-04 — organizational continuity reasoning (upstream Phase 04 law).

Normative: ``DOCS/cortex/reasoning/organizational-continuity-reasoning.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# Phase 04 authoritative org-meaning plane (see ``phase-04-graph-projection-export-doctrine.md``).
LINK_AUTHORITY_AUTHORITATIVE: Final[str] = "authoritative"

# Canonical ``ambiguity_class_id`` literals (Unicode hyphen U+2011 per ``ambiguity-registry-v1.md`` §1).
AMB_NONE: Final[str] = "AMB\u2011NONE"
AMB_OWN_PARALLEL: Final[str] = "AMB\u2011OWN\u2011parallel"
AMB_CHRON_PARTIAL: Final[str] = "AMB\u2011CHRON\u2011partial"
AMB_CHRON_CONFLICT: Final[str] = "AMB\u2011CHRON\u2011conflict"
AMB_PART_STORYLINE: Final[str] = "AMB\u2011PART\u2011storyline"
AMB_BRIDGE_WEAK: Final[str] = "AMB\u2011BRIDGE\u2011weak"
AMB_ACK_CONFLICTED: Final[str] = "AMB\u2011ACK\u2011conflicted"
AMB_ANCH_MISSING: Final[str] = "AMB\u2011ANCH\u2011missing"

KNOWN_AMBIGUITY_CLASS_IDS: Final[frozenset[str]] = frozenset(
    {
        AMB_NONE,
        AMB_OWN_PARALLEL,
        AMB_CHRON_PARTIAL,
        AMB_CHRON_CONFLICT,
        AMB_PART_STORYLINE,
        AMB_BRIDGE_WEAK,
        AMB_ACK_CONFLICTED,
        AMB_ANCH_MISSING,
    }
)

REPLAY_POSTURE_REPLAY_CONFLICTED: Final[str] = "replay_conflicted"


class OrganizationalContinuityReasoningError(ValueError):
    """Raised when org continuity / walk handoff rules for TCRE are violated."""


def validate_ambiguity_class_id_registered(value: object) -> None:
    """Reject unknown ``ambiguity_class_id`` strings (registry alignment)."""
    if not isinstance(value, str) or value not in KNOWN_AMBIGUITY_CLASS_IDS:
        raise OrganizationalContinuityReasoningError(
            f"ambiguity_class_id must be a registered canonical id; got {value!r}"
        )


def validate_authoritative_link_gates_for_tcre_support(link_support: Mapping[str, Any]) -> None:
    """§2 rule 1 — authoritative org link support requires authority + temporal gate."""
    la = link_support.get("link_authority")
    if la != LINK_AUTHORITY_AUTHORITATIVE:
        raise OrganizationalContinuityReasoningError(
            "authoritative link support requires link_authority="
            f"{LINK_AUTHORITY_AUTHORITATIVE!r}; got {la!r}"
        )
    if link_support.get("temporal_validity_ok") is not True:
        raise OrganizationalContinuityReasoningError(
            "authoritative link support requires temporal_validity_ok is True"
        )


def validate_candidate_or_hint_not_sole_without_bridge_weak(bundle: Mapping[str, Any]) -> None:
    """§2 rule 2 — candidate/hint must not be sole support except under ``AMB‑BRIDGE‑weak``."""
    sole = bundle.get("sole_support_kind")
    if sole not in ("candidate", "hint"):
        return
    amb = bundle.get("ambiguity_class_id")
    if amb is None:
        raise OrganizationalContinuityReasoningError(
            "sole_support_kind candidate/hint requires ambiguity_class_id (expected "
            f"{AMB_BRIDGE_WEAK!r})"
        )
    validate_ambiguity_class_id_registered(amb)
    if amb != AMB_BRIDGE_WEAK:
        raise OrganizationalContinuityReasoningError(
            "sole_support_kind candidate/hint may only be carried as sole support with "
            f"ambiguity_class_id={AMB_BRIDGE_WEAK!r}; got {amb!r}"
        )


def validate_evidence_lineage_has_raw_or_ledger_hop(lineage: object) -> None:
    """§2 rule 3 — causal claims must cite raw or ledger-shaped lineage (substrate hops)."""
    if not isinstance(lineage, list) or not lineage:
        raise OrganizationalContinuityReasoningError("evidence_lineage must be a non-empty list")
    ok = False
    for hop in lineage:
        if not isinstance(hop, Mapping):
            continue
        hk = hop.get("hop_kind")
        if hk == "raw_record" and hop.get("raw_record_id") is not None:
            ok = True
            break
        if hk == "normalized_reference" and hop.get("reference") is not None:
            ok = True
            break
        if hk == "cross_link":
            ok = True
            break
    if not ok:
        raise OrganizationalContinuityReasoningError(
            "evidence_lineage must include at least one raw_record, normalized_reference, "
            "or cross_link hop closing to substrate evidence"
        )


def validate_replay_conflicted_walk_propagates(
    *,
    walk_replay_posture: str,
    dependent_replay_posture: str,
) -> None:
    """§3 — walk ``replay_conflicted`` must propagate to dependent TCRE outputs."""
    if walk_replay_posture == REPLAY_POSTURE_REPLAY_CONFLICTED:
        if dependent_replay_posture != REPLAY_POSTURE_REPLAY_CONFLICTED:
            raise OrganizationalContinuityReasoningError(
                "walk replay_posture is replay_conflicted but dependent output is "
                f"{dependent_replay_posture!r}; must emit replay_conflicted"
            )


def verify_gp06_cont01_authoritative_link_gate_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_authoritative_link_gates_for_tcre_support(
            {"link_authority": "authoritative", "temporal_validity_ok": True}
        )
    except OrganizationalContinuityReasoningError as exc:
        errors.append(f"unexpected_reject_good:{exc}")
    try:
        validate_authoritative_link_gates_for_tcre_support(
            {"link_authority": "non_authoritative", "temporal_validity_ok": True}
        )
    except OrganizationalContinuityReasoningError:
        pass
    else:
        errors.append("expected_reject_non_authoritative")
    passed = len(errors) == 0
    return {
        "id": "P06-04-cont-authoritative-gate",
        "name": "authoritative_link_gates",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_org_continuity_runtime_schema_version": PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp06_cont02_candidate_hint_sole_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_candidate_or_hint_not_sole_without_bridge_weak(
            {
                "sole_support_kind": "hint",
                "ambiguity_class_id": AMB_BRIDGE_WEAK,
            }
        )
    except OrganizationalContinuityReasoningError as exc:
        errors.append(f"unexpected_reject_hint_bridge:{exc}")
    try:
        validate_candidate_or_hint_not_sole_without_bridge_weak(
            {"sole_support_kind": "hint", "ambiguity_class_id": AMB_NONE}
        )
    except OrganizationalContinuityReasoningError:
        pass
    else:
        errors.append("expected_reject_hint_without_bridge_weak")
    passed = len(errors) == 0
    return {
        "id": "P06-04-cont-candidate-hint-sole",
        "name": "candidate_hint_sole_bridge_weak",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_org_continuity_runtime_schema_version": PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp06_cont03_evidence_lineage_substrate_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_evidence_lineage_has_raw_or_ledger_hop(
            [{"hop_kind": "raw_record", "raw_record_id": 1}]
        )
    except OrganizationalContinuityReasoningError as exc:
        errors.append(f"unexpected_reject_good_lineage:{exc}")
    try:
        validate_evidence_lineage_has_raw_or_ledger_hop([])
    except OrganizationalContinuityReasoningError:
        pass
    else:
        errors.append("expected_reject_empty_lineage")
    passed = len(errors) == 0
    return {
        "id": "P06-04-cont-lineage-substrate",
        "name": "evidence_lineage_substrate",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_org_continuity_runtime_schema_version": PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp06_cont04_replay_conflicted_propagation_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_replay_conflicted_walk_propagates(
            walk_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
            dependent_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
        )
    except OrganizationalContinuityReasoningError as exc:
        errors.append(f"unexpected_reject_matching_conflict:{exc}")
    try:
        validate_replay_conflicted_walk_propagates(
            walk_replay_posture=REPLAY_POSTURE_REPLAY_CONFLICTED,
            dependent_replay_posture="replay_equivalent",
        )
    except OrganizationalContinuityReasoningError:
        pass
    else:
        errors.append("expected_reject_missing_conflict_propagation")
    passed = len(errors) == 0
    return {
        "id": "P06-04-cont-replay-conflicted",
        "name": "replay_conflicted_propagation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_org_continuity_runtime_schema_version": PHASE06_ORG_CONTINUITY_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }
