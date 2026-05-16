"""Phase 06 P06-17 — ownership continuity in causal graphs (authoritative org links + TCRE ids).

Normative:
``DOCS/cortex/reasoning/organizational-continuity-reasoning.md`` §2,
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (``underlying_coordination_edge_ids``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.causal_reconstruction_substrate import (
    CausalReconstructionSubstrateError,
    validate_tcre_causal_edge_v1_reconstruction_substrate,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    OrganizationalContinuityReasoningError,
    validate_authoritative_link_gates_for_tcre_support,
    validate_candidate_or_hint_not_sole_without_bridge_weak,
    validate_evidence_lineage_has_raw_or_ledger_hop,
)

PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1


class CausalGraphOwnershipContinuityError(ValueError):
    """Fail-closed TCRE ↔ Phase **04** continuity bundle (authoritative links + lineage)."""


def tcre_edge_cites_concrete_coordination_edge_ids_v1(edge: Mapping[str, Any]) -> bool:
    """True when ids list real coordination ``edge_id`` values (not §4.2 sentinel-only)."""
    raw = edge.get("underlying_coordination_edge_ids")
    if not isinstance(raw, list):
        return False
    ids = [str(x) for x in raw]
    return not (len(ids) == 1 and ids[0] == NO_COORDINATION_EDGE_SENTINEL)


def validate_tcre_causal_graph_ownership_continuity_v1(
    edge: Mapping[str, Any],
    *,
    org_link_support: Mapping[str, Any] | None,
    sole_support_bundle: Mapping[str, Any] | None = None,
    require_substrate_lineage: bool = True,
) -> None:
    """Doctrine §2 — authoritative org support when citing coordination; lineage; sole-support."""
    if sole_support_bundle is not None:
        try:
            validate_candidate_or_hint_not_sole_without_bridge_weak(sole_support_bundle)
        except OrganizationalContinuityReasoningError as exc:
            raise CausalGraphOwnershipContinuityError(str(exc)) from exc

    if require_substrate_lineage:
        try:
            validate_evidence_lineage_has_raw_or_ledger_hop(edge.get("evidence_lineage"))
        except OrganizationalContinuityReasoningError as exc:
            raise CausalGraphOwnershipContinuityError(str(exc)) from exc

    if not tcre_edge_cites_concrete_coordination_edge_ids_v1(edge):
        return

    if org_link_support is None:
        raise CausalGraphOwnershipContinuityError(
            "TCRE edges citing concrete underlying_coordination_edge_ids require org_link_support "
            "(Phase 04 authoritative continuity bundle)"
        )
    try:
        validate_authoritative_link_gates_for_tcre_support(org_link_support)
    except OrganizationalContinuityReasoningError as exc:
        raise CausalGraphOwnershipContinuityError(str(exc)) from exc


def validate_tcre_causal_edge_v1_reconstruction_substrate_with_ownership_v1(
    edge: Mapping[str, Any],
    *,
    org_link_support: Mapping[str, Any] | None,
    sole_support_bundle: Mapping[str, Any] | None = None,
) -> None:
    """P06-14 substrate law + **P06-17** ownership continuity (single reducer-friendly entry)."""
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(edge)
    except CausalReconstructionSubstrateError as exc:
        raise CausalGraphOwnershipContinuityError(str(exc)) from exc
    validate_tcre_causal_graph_ownership_continuity_v1(
        edge,
        org_link_support=org_link_support,
        sole_support_bundle=sole_support_bundle,
        require_substrate_lineage=True,
    )


def verify_gp06_own01_concrete_ids_require_authoritative_org_support_static() -> dict[str, Any]:
    """Static — concrete ids require ``org_link_support`` (authoritative + temporal gate)."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["coord-edge-a"],
        "derivation_rule_id": "TCRE_MAP_depends_on_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "confidence_source": "explicit_rule_id",
    }
    try:
        validate_tcre_causal_graph_ownership_continuity_v1(edge, org_link_support=None)
    except CausalGraphOwnershipContinuityError:
        pass
    else:
        errors.append("expected_reject_missing_org_link_support")

    try:
        validate_tcre_causal_graph_ownership_continuity_v1(
            edge,
            org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
        )
    except CausalGraphOwnershipContinuityError as exc:
        errors.append(f"unexpected_reject_good_support:{exc}")

    passed = len(errors) == 0
    return {
        "id": "P06-17-own-concrete-authoritative",
        "name": "gp06_own01_concrete_ids_require_authoritative_org_support",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_graph_ownership_continuity_runtime_schema_version": (
                PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_own02_sentinel_path_skips_org_link_support_static() -> dict[str, Any]:
    """Static — §4.2 sentinel-only path does not require ``org_link_support``."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": "tcre_negative_signal",
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "NEG_SIG_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
    }
    try:
        validate_tcre_causal_graph_ownership_continuity_v1(edge, org_link_support=None)
    except CausalGraphOwnershipContinuityError as exc:
        errors.append(f"unexpected_reject_sentinel_path:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-17-own-sentinel-skip",
        "name": "gp06_own02_sentinel_path_skips_org_link_support",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_graph_ownership_continuity_runtime_schema_version": (
                PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_own03_non_authoritative_org_support_rejected_static() -> dict[str, Any]:
    """Static — non-authoritative ``link_authority`` cannot justify coordination-citing TCRE."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": ["e1"],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 3}],
    }
    try:
        validate_tcre_causal_graph_ownership_continuity_v1(
            edge,
            org_link_support={"link_authority": "hint", "temporal_validity_ok": True},
        )
    except CausalGraphOwnershipContinuityError:
        pass
    else:
        errors.append("expected_reject_non_authoritative_link_authority")
    passed = len(errors) == 0
    return {
        "id": "P06-17-own-reject-non-authoritative",
        "name": "gp06_own03_non_authoritative_org_support_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_graph_ownership_continuity_runtime_schema_version": (
                PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_own04_substrate_plus_ownership_combined_entry_static() -> dict[str, Any]:
    """Static — combined P06-14+P06-17 entry accepts a lawful coordination-citing edge."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_block",
        "underlying_coordination_edge_ids": ["blk-9"],
        "derivation_rule_id": "TCRE_MAP_blocks_v1",
        "evidence_lineage": [{"hop_kind": "normalized_reference", "reference": "ref/1"}],
        "confidence_source": "explicit_rule_id",
    }
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate_with_ownership_v1(
            edge,
            org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
        )
    except CausalGraphOwnershipContinuityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-17-own-combined-entry",
        "name": "gp06_own04_substrate_plus_ownership_combined_entry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_graph_ownership_continuity_runtime_schema_version": (
                PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
