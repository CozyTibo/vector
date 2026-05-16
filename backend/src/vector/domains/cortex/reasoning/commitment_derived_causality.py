"""Phase 06 P06-18 — commitment-derived causality (``tcre_commitment_transition``).

Normative:
``DOCS/cortex/reasoning/causal-reconstruction-doctrine.md``,
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (§3 row, §4.2 sentinel closure).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
    ExecutionCausalityConstraintError,
    validate_tcre_edge_v1_stub,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    OrganizationalContinuityReasoningError,
    validate_evidence_lineage_has_raw_or_ledger_hop,
)

PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TCRE_COMMITMENT_TRANSITION_KIND: Final[str] = "tcre_commitment_transition"

# Frozen reducer naming — ``CommitmentLifecycle.state_history`` carries ``rule_id``;
# TCRE cites mapping id.
TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1: Final[str] = "TCRE_MAP_commitment_"


class CommitmentDerivedCausalityError(ValueError):
    """Fail-closed ``tcre_commitment_transition`` registry + §4.2 sentinel lineage law."""


def _underlying_ids_str_list(edge: Mapping[str, Any]) -> list[str]:
    raw = edge.get("underlying_coordination_edge_ids")
    if not isinstance(raw, list):
        raise CommitmentDerivedCausalityError("underlying_coordination_edge_ids must be a list")
    return [str(x) for x in raw]


def underlying_coordination_edge_ids_sentinel_only_v1(edge: Mapping[str, Any]) -> bool:
    """True when ids are exactly the single coordination sentinel."""
    ids = _underlying_ids_str_list(edge)
    return len(ids) == 1 and ids[0] == NO_COORDINATION_EDGE_SENTINEL


def lineage_includes_commitment_contract_hop_v1(lineage: object) -> bool:
    """§4.2 — a hop has non-empty ``commitment_id`` (commitment contract closure)."""
    if not isinstance(lineage, list):
        return False
    for hop in lineage:
        if not isinstance(hop, Mapping):
            continue
        cid = hop.get("commitment_id")
        if isinstance(cid, str) and cid.strip():
            return True
    return False


def lineage_includes_raw_record_hop_v1(lineage: object) -> bool:
    """§4.2 — sentinel path requires raw substrate closure."""
    if not isinstance(lineage, list):
        return False
    for hop in lineage:
        if not isinstance(hop, Mapping):
            continue
        if hop.get("hop_kind") == "raw_record" and hop.get("raw_record_id") is not None:
            return True
    return False


def validate_tcre_commitment_transition_derivation_rule_v1(edge: Mapping[str, Any]) -> None:
    """Registry §3 — mapping id must name commitment lifecycle derivation (frozen prefix)."""
    rid = edge.get("derivation_rule_id")
    if not isinstance(rid, str) or not rid.strip():
        raise CommitmentDerivedCausalityError("derivation_rule_id must be a non-empty string")
    if not rid.strip().startswith(TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1):
        raise CommitmentDerivedCausalityError(
            "tcre_commitment_transition derivation_rule_id must start with "
            f"{TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1!r}"
        )


def validate_tcre_commitment_transition_sentinel_lineage_v1(edge: Mapping[str, Any]) -> None:
    """Registry §4.2 — sentinel-only list must close to **raw** and **commitment** contract ids."""
    if not underlying_coordination_edge_ids_sentinel_only_v1(edge):
        return
    lineage = edge.get("evidence_lineage")
    if not lineage_includes_raw_record_hop_v1(lineage):
        raise CommitmentDerivedCausalityError(
            "tcre_commitment_transition with sentinel underlying_coordination_edge_ids requires "
            "evidence_lineage hop_kind=raw_record with raw_record_id (§4.2)"
        )
    if not lineage_includes_commitment_contract_hop_v1(lineage):
        raise CommitmentDerivedCausalityError(
            "tcre_commitment_transition with sentinel underlying_coordination_edge_ids requires "
            "evidence_lineage hop carrying non-empty commitment_id (§4.2)"
        )


def _apply_commitment_transition_doctrine_after_stub_v1(edge: Mapping[str, Any]) -> None:
    validate_tcre_commitment_transition_derivation_rule_v1(edge)
    try:
        validate_evidence_lineage_has_raw_or_ledger_hop(edge.get("evidence_lineage"))
    except OrganizationalContinuityReasoningError as exc:
        raise CommitmentDerivedCausalityError(str(exc)) from exc
    validate_tcre_commitment_transition_sentinel_lineage_v1(edge)


def validate_tcre_commitment_transition_causality_v1(edge: Mapping[str, Any]) -> None:
    """P06-18 — stub law + derivation prefix + §4.2 sentinel lineage when applicable."""
    kind = edge.get("tcre_causal_edge_kind")
    if kind != TCRE_COMMITMENT_TRANSITION_KIND:
        raise CommitmentDerivedCausalityError(
            f"tcre_causal_edge_kind must be {TCRE_COMMITMENT_TRANSITION_KIND!r}; got {kind!r}"
        )
    try:
        validate_tcre_edge_v1_stub(edge)
    except ExecutionCausalityConstraintError as exc:
        raise CommitmentDerivedCausalityError(str(exc)) from exc
    _apply_commitment_transition_doctrine_after_stub_v1(edge)


def validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1(
    edge: Mapping[str, Any],
) -> None:
    """P06-14 substrate + **P06-18** commitment transition law (single reducer entry)."""
    from vector.domains.cortex.reasoning.causal_reconstruction_substrate import (
        CausalReconstructionSubstrateError,
        validate_tcre_causal_edge_v1_reconstruction_substrate,
    )

    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(edge)
    except CausalReconstructionSubstrateError as exc:
        raise CommitmentDerivedCausalityError(str(exc)) from exc
    if edge.get("tcre_causal_edge_kind") != TCRE_COMMITMENT_TRANSITION_KIND:
        raise CommitmentDerivedCausalityError(
            "validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1 "
            f"requires tcre_causal_edge_kind={TCRE_COMMITMENT_TRANSITION_KIND!r}"
        )
    _apply_commitment_transition_doctrine_after_stub_v1(edge)


def verify_gp06_cmt01_sentinel_requires_raw_and_commitment_hop_static() -> dict[str, Any]:
    errors: list[str] = []
    base = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_commitment_transition_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    try:
        validate_tcre_commitment_transition_causality_v1(base)
    except CommitmentDerivedCausalityError:
        pass
    else:
        errors.append("expected_reject_missing_commitment_hop")

    good = {
        **base,
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"hop_kind": "normalized_reference", "reference": "ref/x", "commitment_id": "cmt-1"},
        ],
    }
    try:
        validate_tcre_commitment_transition_causality_v1(good)
    except CommitmentDerivedCausalityError as exc:
        errors.append(f"unexpected_reject_good_sentinel:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-18-cmt-sentinel-lineage",
        "name": "gp06_cmt01_sentinel_requires_raw_and_commitment_hop",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_commitment_derived_causality_runtime_schema_version": (
                PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cmt02_concrete_coordination_skips_extra_commitment_hop_static() -> dict[str, Any]:
    """Concrete underlying ids — substrate lineage only (no extra commitment hop)."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": ["coord-e1"],
        "derivation_rule_id": "TCRE_MAP_commitment_transition_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
    }
    try:
        validate_tcre_commitment_transition_causality_v1(edge)
    except CommitmentDerivedCausalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-18-cmt-concrete-ids",
        "name": "gp06_cmt02_concrete_coordination_skips_extra_commitment_hop",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_commitment_derived_causality_runtime_schema_version": (
                PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cmt03_bad_derivation_rule_prefix_rejected_static() -> dict[str, Any]:
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"commitment_id": "c1"},
        ],
    }
    try:
        validate_tcre_commitment_transition_causality_v1(edge)
    except CommitmentDerivedCausalityError:
        pass
    else:
        errors.append("expected_reject_bad_derivation_prefix")
    passed = len(errors) == 0
    return {
        "id": "P06-18-cmt-derivation-prefix",
        "name": "gp06_cmt03_bad_derivation_rule_prefix_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_commitment_derived_causality_runtime_schema_version": (
                PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cmt04_wrong_kind_rejected_static() -> dict[str, Any]:
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["a"],
        "derivation_rule_id": "TCRE_MAP_commitment_transition_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    try:
        validate_tcre_commitment_transition_causality_v1(edge)
    except CommitmentDerivedCausalityError:
        pass
    else:
        errors.append("expected_reject_wrong_kind")
    passed = len(errors) == 0
    return {
        "id": "P06-18-cmt-wrong-kind",
        "name": "gp06_cmt04_wrong_kind_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_commitment_derived_causality_runtime_schema_version": (
                PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cmt05_substrate_plus_commitment_law_static() -> dict[str, Any]:
    """Static — P06-14 + P06-18 combined entry accepts a lawful sentinel commitment edge."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_commitment_transition_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 9},
            {"hop_kind": "cross_link", "commitment_id": "cmt-zz"},
        ],
        "confidence_source": "explicit_rule_id",
    }
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1(edge)
    except CommitmentDerivedCausalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-18-cmt-substrate-combined",
        "name": "gp06_cmt05_substrate_plus_commitment_law",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_commitment_derived_causality_runtime_schema_version": (
                PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
