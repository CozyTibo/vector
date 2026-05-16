"""Phase 06 P06-14 — causal reconstruction substrate (Option **A** ``TCRECausalEdge_v1``).

Normative:
``DOCS/cortex/reasoning/causal-reconstruction-doctrine.md``,
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (closed enum, **M‑INJ‑1**, §5).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import DeterministicConfidenceSource
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    ExecutionCausalityConstraintError,
    TCRE_CAUSAL_EDGE_KINDS,
    validate_tcre_edge_v1_stub,
)

PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TCRE_CAUSAL_EDGE_REGISTRY_VERSION: Final[int] = 1

# ``tcre-causal-edge-registry-v1.md`` §4.1 — primary ``CoordinationEdgeKind`` → ``tcre_causal_edge_kind``.
COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1: Final[dict[str, str]] = {
    "escalation_of": "tcre_coordination_escalation",
    "blocks": "tcre_coordination_block",
    "depends_on": "tcre_coordination_dependency",
    "handoff": "tcre_coordination_handoff",
    "same_thread": "tcre_coordination_thread_context",
    "temporal_successor": "tcre_coordination_temporal_order",
}

TCRE_WEAK_COORDINATION_DERIVED_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "tcre_coordination_thread_context",
        "tcre_coordination_temporal_order",
    }
)

_DETERMINISTIC_CONFIDENCE_SOURCES_V1: Final[frozenset[str]] = frozenset(
    {member.value for member in DeterministicConfidenceSource}
)


class CausalReconstructionSubstrateError(ValueError):
    """Fail-closed Option **A** substrate: ``TCRECausalEdge_v1`` vs ``ExecutionCoordinationEdge`` separation."""


def primary_tcre_kind_for_coordination_edge_kind_v1(coordination_edge_kind: str) -> str:
    """Registry §4.1 — primary ``tcre_causal_edge_kind`` for a substrate ``CoordinationEdgeKind``."""
    if not isinstance(coordination_edge_kind, str) or not coordination_edge_kind.strip():
        raise CausalReconstructionSubstrateError("coordination_edge_kind must be a non-empty string")
    key = coordination_edge_kind.strip()
    if key not in COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1:
        allowed = ", ".join(sorted(COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1))
        raise CausalReconstructionSubstrateError(
            f"unknown CoordinationEdgeKind for primary TCRE map: {coordination_edge_kind!r}; expected one of: {allowed}"
        )
    return COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1[key]


def validate_tcre_payload_excludes_coordination_edge_shape_v1(edge: Mapping[str, Any]) -> None:
    """Option **A** — a ``TCRECausalEdge_v1`` payload **must not** carry coordination-edge writer keys."""
    if "edge_kind" in edge:
        raise CausalReconstructionSubstrateError(
            "TCRECausalEdge_v1 must not include coordination substrate field edge_kind "
            "(distinct artifact from ExecutionCoordinationEdge)"
        )


def validate_tcre_causal_edge_v1_reconstruction_substrate(edge: Mapping[str, Any]) -> None:
    """Doctrine §1 + registry §2 — stub law plus mandatory ``confidence_source`` (``DeterministicConfidenceSource``)."""
    validate_tcre_payload_excludes_coordination_edge_shape_v1(edge)
    try:
        validate_tcre_edge_v1_stub(edge)
    except ExecutionCausalityConstraintError as exc:
        raise CausalReconstructionSubstrateError(str(exc)) from exc
    cs = edge.get("confidence_source")
    if not isinstance(cs, str) or not cs.strip():
        raise CausalReconstructionSubstrateError(
            "TCRECausalEdge_v1 requires non-empty confidence_source (DeterministicConfidenceSource)"
        )
    if cs.strip() not in _DETERMINISTIC_CONFIDENCE_SOURCES_V1:
        allowed = ", ".join(sorted(_DETERMINISTIC_CONFIDENCE_SOURCES_V1))
        raise CausalReconstructionSubstrateError(
            f"confidence_source must be a DeterministicConfidenceSource literal; got {cs!r}; allowed: {allowed}"
        )


def validate_cross_system_tcre_support_not_weak_only_v1(
    *,
    is_cross_system_causal: bool,
    supporting_tcre_kinds: Sequence[str],
) -> None:
    """Registry §5 — weak coordination-derived kinds cannot be the **sole** support for cross-system causal."""
    if not is_cross_system_causal:
        return
    kinds = [k for k in supporting_tcre_kinds if isinstance(k, str) and k.strip()]
    if not kinds:
        raise CausalReconstructionSubstrateError(
            "cross-system causal claim requires at least one supporting tcre_causal_edge_kind"
        )
    unknown = [k for k in kinds if k not in TCRE_CAUSAL_EDGE_KINDS]
    if unknown:
        raise CausalReconstructionSubstrateError(f"unknown tcre_causal_edge_kind in support set: {unknown!r}")
    if set(kinds) <= TCRE_WEAK_COORDINATION_DERIVED_KINDS_V1:
        raise CausalReconstructionSubstrateError(
            "registry §5: tcre_coordination_thread_context / tcre_coordination_temporal_order "
            "must not be the sole TCRE kinds supporting a cross-system causal claim"
        )


def verify_gp06_crs01_coordination_to_tcre_primary_map_static() -> dict[str, Any]:
    """Static — §4.1 primary map covers every frozen ``CoordinationEdgeKind`` literal."""
    errors: list[str] = []
    expected = {
        "temporal_successor",
        "escalation_of",
        "blocks",
        "depends_on",
        "handoff",
        "same_thread",
    }
    if set(COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1) != expected:
        errors.append("primary_map_key_mismatch")
    for ck, tk in COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1.items():
        if tk not in TCRE_CAUSAL_EDGE_KINDS:
            errors.append(f"map_targets_unknown_tcre:{ck}->{tk}")
        try:
            if primary_tcre_kind_for_coordination_edge_kind_v1(ck) != tk:
                errors.append(f"oracle_mismatch:{ck}")
        except CausalReconstructionSubstrateError as exc:
            errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-14-crs-primary-map",
        "name": "gp06_crs01_coordination_to_tcre_primary_map",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_reconstruction_substrate_runtime_schema_version": (
                PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION
            ),
            "tcre_causal_edge_registry_version": TCRE_CAUSAL_EDGE_REGISTRY_VERSION,
            "errors": errors,
        },
    }


def verify_gp06_crs02_reconstruction_requires_confidence_static() -> dict[str, Any]:
    """Static — reconstruction substrate requires ``confidence_source``."""
    errors: list[str] = []
    base = {
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": ["e1"],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "confidence_source": DeterministicConfidenceSource.EXPLICIT_RULE_ID.value,
    }
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(base)
    except CausalReconstructionSubstrateError as exc:
        errors.append(f"unexpected_reject_good:{exc}")
    bad = dict(base)
    del bad["confidence_source"]
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(bad)
    except CausalReconstructionSubstrateError:
        pass
    else:
        errors.append("expected_missing_confidence_reject")
    passed = len(errors) == 0
    return {
        "id": "P06-14-crs-confidence",
        "name": "gp06_crs02_reconstruction_requires_confidence",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_reconstruction_substrate_runtime_schema_version": (
                PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_crs03_cross_system_weak_only_guard_static() -> dict[str, Any]:
    """Static — §5 rejects weak-only support for cross-system causal."""
    errors: list[str] = []
    try:
        validate_cross_system_tcre_support_not_weak_only_v1(
            is_cross_system_causal=True,
            supporting_tcre_kinds=["tcre_coordination_temporal_order"],
        )
    except CausalReconstructionSubstrateError:
        pass
    else:
        errors.append("expected_weak_only_reject")
    try:
        validate_cross_system_tcre_support_not_weak_only_v1(
            is_cross_system_causal=True,
            supporting_tcre_kinds=["tcre_coordination_temporal_order", "tcre_coordination_block"],
        )
    except CausalReconstructionSubstrateError as exc:
        errors.append(f"unexpected_reject_mixed:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-14-crs-cross-system-weak",
        "name": "gp06_crs03_cross_system_weak_only_guard",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_reconstruction_substrate_runtime_schema_version": (
                PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_crs04_option_a_rejects_coordination_edge_kind_key_static() -> dict[str, Any]:
    """Static — coordination ``edge_kind`` must not appear on TCRE payloads."""
    errors: list[str] = []
    bad = {
        "edge_kind": "escalation_of",
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": ["e1"],
        "derivation_rule_id": "x",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "confidence_source": DeterministicConfidenceSource.EXPLICIT_RULE_ID.value,
    }
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(bad)
    except CausalReconstructionSubstrateError:
        pass
    else:
        errors.append("expected_edge_kind_reject")
    passed = len(errors) == 0
    return {
        "id": "P06-14-crs-option-a-shape",
        "name": "gp06_crs04_option_a_rejects_coordination_edge_kind_key",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_reconstruction_substrate_runtime_schema_version": (
                PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
