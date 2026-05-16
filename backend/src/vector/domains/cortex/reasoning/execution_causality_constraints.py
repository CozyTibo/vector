"""Phase 06 P06-03 / P06-20 — execution causality constraints (observed vs derived boundary).

Normative: ``DOCS/cortex/reasoning/execution-causality-constraints.md``;
``tcre-causal-edge-registry-v1.md`` (``TCRECausalEdge_v1`` shape).

P06-20 (§4): closed ``causal_legality_class`` enum + ``CAUSAL_LEGALITY_ENUM_VERSION_V1``;
``validate_tcre_edge_v1_stub`` rejects unknown literals when the field is present;
static gates ``verify_gp06_clc01`` … ``verify_gp06_clc04``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final, get_args

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import CoordinationEdgeKind

EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION: Final[int] = 2

# ``execution-causality-constraints.md`` §4 freeze — bump when literals change (gap matrix).
CAUSAL_LEGALITY_ENUM_VERSION_V1: Final[int] = 1

NO_COORDINATION_EDGE_SENTINEL: Final[str] = "__NO_COORDINATION_EDGE__"

TCRE_CAUSAL_EDGE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "tcre_coordination_escalation",
        "tcre_coordination_block",
        "tcre_coordination_dependency",
        "tcre_coordination_handoff",
        "tcre_coordination_thread_context",
        "tcre_coordination_temporal_order",
        "tcre_commitment_transition",
        "tcre_negative_signal",
        "tcre_follow_through_gap",
        "tcre_silence_window_obligation",
    }
)

_TCRE_KINDS_ALLOWING_SENTINEL_ONLY: Final[frozenset[str]] = frozenset(
    {
        "tcre_commitment_transition",
        "tcre_negative_signal",
        "tcre_follow_through_gap",
        "tcre_silence_window_obligation",
    }
)

TCRE_KINDS_ALLOWING_COORDINATION_SENTINEL_ONLY: Final[frozenset[str]] = (
    _TCRE_KINDS_ALLOWING_SENTINEL_ONLY
)

_CAUSAL_LEGALITY_LITERALS_DOCTRINE_V1: Final[frozenset[str]] = frozenset(
    {
        "causal_replay_equivalent",
        "causal_replay_degraded",
        "causal_chronology_blocked",
        "causal_ambiguous_partitioned",
        "causal_forbidden_substrate",
        "causal_unverifiable",
    }
)

CAUSAL_LEGALITY_CLASSES: Final[frozenset[str]] = _CAUSAL_LEGALITY_LITERALS_DOCTRINE_V1

_KNOWN_COORDINATION_EDGE_KINDS: Final[frozenset[str]] = frozenset(get_args(CoordinationEdgeKind))

_LREL_FORBIDDEN_TOP_LEVEL_KEYS_LOWER: Final[frozenset[str]] = frozenset(
    {
        "execution_reliability_profile",
        "coordination_reliability_vector",
        "execution_volatility_window",
    }
)


class ExecutionCausalityConstraintError(ValueError):
    """Raised when a TCRE / causality payload violates execution-causality-constraints."""


def validate_causal_legality_class(value: object) -> None:
    """§4 — ``causal_legality_class`` must be one of the closed enum literals."""
    if not isinstance(value, str) or value not in CAUSAL_LEGALITY_CLASSES:
        allowed = ", ".join(sorted(CAUSAL_LEGALITY_CLASSES))
        raise ExecutionCausalityConstraintError(
            f"causal_legality_class must be one of: {allowed}; got {value!r}"
        )


def validate_parent_artifact_ids_sorted_unique(ids: object) -> None:
    """§3 — ``parent_artifact_ids`` must be sorted ascending (strict) and unique."""
    if not isinstance(ids, list):
        raise ExecutionCausalityConstraintError("parent_artifact_ids must be a list")
    if not all(isinstance(x, str) for x in ids):
        raise ExecutionCausalityConstraintError("parent_artifact_ids must be a list[str]")
    if len(set(ids)) != len(ids):
        raise ExecutionCausalityConstraintError("parent_artifact_ids must be unique")
    if ids != sorted(ids):
        raise ExecutionCausalityConstraintError(
            "parent_artifact_ids must be sorted ascending for hash stability"
        )


def list_lrel_forbidden_keys_on_mapping(body: Mapping[str, Any]) -> list[str]:
    """§5 L-REL — forbid reliability / volatility / score fields on edge payloads (default)."""
    hits: list[str] = []
    for k in body:
        if not isinstance(k, str):
            continue
        lk = k.lower()
        if lk in _LREL_FORBIDDEN_TOP_LEVEL_KEYS_LOWER:
            hits.append(k)
        elif lk.endswith("_score") or lk.endswith("_rate_bps"):
            hits.append(k)
    return hits


def _underlying_coordination_edge_ids_valid(
    kind: str,
    ids: list[str],
    *,
    max_concrete_coordination_edges: int = 1,
) -> None:
    if not ids:
        raise ExecutionCausalityConstraintError(
            "underlying_coordination_edge_ids must be non-empty"
        )
    if not all(isinstance(x, str) and x for x in ids):
        raise ExecutionCausalityConstraintError(
            "underlying_coordination_edge_ids must be non-empty str"
        )
    if len(set(ids)) != len(ids):
        raise ExecutionCausalityConstraintError("underlying_coordination_edge_ids must be unique")
    if ids != sorted(ids):
        raise ExecutionCausalityConstraintError(
            "underlying_coordination_edge_ids must be sorted ascending for hash stability"
        )

    sentinel_only = ids == [NO_COORDINATION_EDGE_SENTINEL]
    if sentinel_only and kind not in _TCRE_KINDS_ALLOWING_SENTINEL_ONLY:
        raise ExecutionCausalityConstraintError(
            f"tcre_causal_edge_kind {kind!r} may not use {NO_COORDINATION_EDGE_SENTINEL!r} alone"
        )
    if not sentinel_only and NO_COORDINATION_EDGE_SENTINEL in ids:
        raise ExecutionCausalityConstraintError(
            "underlying_coordination_edge_ids must not mix sentinel with concrete edge ids"
        )
    if not sentinel_only:
        if max_concrete_coordination_edges < 1:
            raise ExecutionCausalityConstraintError("max_concrete_coordination_edges must be >= 1")
        if len(ids) > max_concrete_coordination_edges:
            raise ExecutionCausalityConstraintError(
                f"underlying_coordination_edge_ids must contain at most "
                f"{max_concrete_coordination_edges} coordination edge_id(s) for this kind "
                f"unless sentinel-only path is permitted"
            )


def validate_tcre_edge_v1_stub(
    edge: Mapping[str, Any],
    *,
    max_concrete_coordination_edges: int | None = None,
) -> None:
    """Minimal structural law for ``TCRECausalEdge_v1`` stubs (registry §2 + constraints §3/§5).

    ``max_concrete_coordination_edges`` defaults to **1** (**M‑INJ‑1**). Pass a larger cap when the
    active policy's ``merge_rules_coordination_edges`` permits merged coordination ids for the kind.

    Raises:
        ExecutionCausalityConstraintError: on illegal shapes.
    """
    rel_hits = list_lrel_forbidden_keys_on_mapping(edge)
    if rel_hits:
        raise ExecutionCausalityConstraintError(
            "L-REL: forbidden reliability/score fields on edge: " + ", ".join(rel_hits[:8])
        )

    kind = edge.get("tcre_causal_edge_kind")
    if not isinstance(kind, str) or kind not in TCRE_CAUSAL_EDGE_KINDS:
        raise ExecutionCausalityConstraintError(
            f"tcre_causal_edge_kind must be a known registry literal; got {kind!r}"
        )

    raw_ids = edge.get("underlying_coordination_edge_ids")
    if not isinstance(raw_ids, list):
        raise ExecutionCausalityConstraintError("underlying_coordination_edge_ids must be a list")
    ids = [str(x) for x in raw_ids]
    cap = 1 if max_concrete_coordination_edges is None else max_concrete_coordination_edges
    _underlying_coordination_edge_ids_valid(kind, ids, max_concrete_coordination_edges=cap)

    deriv = edge.get("derivation_rule_id")
    if not isinstance(deriv, str) or not deriv.strip():
        raise ExecutionCausalityConstraintError("derivation_rule_id must be a non-empty string")

    lineage = edge.get("evidence_lineage")
    if not isinstance(lineage, list):
        raise ExecutionCausalityConstraintError("evidence_lineage must be a list")

    if "parent_artifact_ids" in edge:
        validate_parent_artifact_ids_sorted_unique(edge["parent_artifact_ids"])

    if "causal_legality_class" in edge:
        validate_causal_legality_class(edge.get("causal_legality_class"))


def _gp06_detail_execution_causality(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "execution_causality_runtime_schema_version": (
            EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION
        ),
    }


def _gp06_detail_causal_legality_step(errors: list[str]) -> dict[str, Any]:
    return {
        "causal_legality_enum_version_v1": CAUSAL_LEGALITY_ENUM_VERSION_V1,
        "errors": errors,
        "execution_causality_runtime_schema_version": (
            EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION
        ),
    }


def coordination_edge_kind_is_known(value: object) -> bool:
    """True when ``value`` is a literal ``CoordinationEdgeKind`` from substrate contracts."""
    return isinstance(value, str) and value in _KNOWN_COORDINATION_EDGE_KINDS


def verify_gp06_ecc01_causal_legality_enum_static() -> dict[str, Any]:
    """Static checks for ``causal_legality_class`` closed enum."""
    errors: list[str] = []
    try:
        validate_causal_legality_class("causal_replay_equivalent")
    except ExecutionCausalityConstraintError as exc:
        errors.append(f"unexpected_reject_legal:{exc}")
    try:
        validate_causal_legality_class("not_a_legality")
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_reject_unknown_legality")
    passed = len(errors) == 0
    return {
        "id": "P06-03-ecc-legality-enum",
        "name": "causal_legality_class_enum",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_execution_causality(errors),
    }


def verify_gp06_ecc02_parent_artifact_ids_static() -> dict[str, Any]:
    """Static checks for sorted unique ``parent_artifact_ids``."""
    errors: list[str] = []
    try:
        validate_parent_artifact_ids_sorted_unique(["b", "a"])
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_reject_unsorted_ids")
    try:
        validate_parent_artifact_ids_sorted_unique(["a", "a"])
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_reject_duplicate_ids")
    try:
        validate_parent_artifact_ids_sorted_unique(["a", "b"])
    except ExecutionCausalityConstraintError as exc:
        errors.append(f"unexpected_reject_sorted_pair:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-03-ecc-parent-ids",
        "name": "parent_artifact_ids_sorted_unique",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_execution_causality(errors),
    }


def _legal_escalation_edge() -> dict[str, Any]:
    return {
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": ["edge-01"],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }


def verify_gp06_ecc03_tcre_edge_shape_static() -> dict[str, Any]:
    """Static checks for ``TCRECausalEdge_v1`` minimal law + L-REL."""
    errors: list[str] = []
    try:
        validate_tcre_edge_v1_stub(_legal_escalation_edge())
    except ExecutionCausalityConstraintError as exc:
        errors.append(f"unexpected_reject_legal_edge:{exc}")

    poison = _legal_escalation_edge()
    poison["reliability_score"] = 0.9
    try:
        validate_tcre_edge_v1_stub(poison)
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_lrel_reject_reliability_score")

    bad_sentinel = {
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "x",
        "evidence_lineage": [],
    }
    try:
        validate_tcre_edge_v1_stub(bad_sentinel)
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_reject_sentinel_on_coordination_kind")

    good_sentinel = {
        "tcre_causal_edge_kind": "tcre_negative_signal",
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "NEG_SIG_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
    }
    try:
        validate_tcre_edge_v1_stub(good_sentinel)
    except ExecutionCausalityConstraintError as exc:
        errors.append(f"unexpected_reject_good_sentinel:{exc}")

    passed = len(errors) == 0
    return {
        "id": "P06-03-ecc-tcre-edge",
        "name": "tcre_edge_v1_stub_shape",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_execution_causality(errors),
    }


def verify_gp06_clc01_literal_table_oracle_static() -> dict[str, Any]:
    """P06-20 — ``execution-causality-constraints.md`` §4 table matches runtime frozen set."""
    errors: list[str] = []
    oracle = frozenset(
        {
            "causal_replay_equivalent",
            "causal_replay_degraded",
            "causal_chronology_blocked",
            "causal_ambiguous_partitioned",
            "causal_forbidden_substrate",
            "causal_unverifiable",
        }
    )
    if CAUSAL_LEGALITY_CLASSES != oracle:
        errors.append("causal_legality_classes_mismatch_doctrine_v1_table")
    if len(CAUSAL_LEGALITY_CLASSES) != 6:
        errors.append("expected_six_causal_legality_literals")
    passed = len(errors) == 0
    return {
        "id": "P06-20-clc-literal-table",
        "name": "gp06_clc01_literal_table_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_causal_legality_step(errors),
    }


def verify_gp06_clc02_tcre_stub_accepts_each_legal_literal_static() -> dict[str, Any]:
    """P06-20 — ``causal_legality_class`` on a legal stub accepts every closed literal."""
    errors: list[str] = []
    for cls in sorted(CAUSAL_LEGALITY_CLASSES):
        edge = _legal_escalation_edge()
        edge["causal_legality_class"] = cls
        try:
            validate_tcre_edge_v1_stub(edge)
        except ExecutionCausalityConstraintError as exc:
            errors.append(f"unexpected_reject_{cls!r}:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-20-clc-stub-accepts",
        "name": "gp06_clc02_tcre_stub_accepts_each_legal_literal",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_causal_legality_step(errors),
    }


def verify_gp06_clc03_tcre_stub_rejects_unknown_causal_legality_static() -> dict[str, Any]:
    """P06-20 — unknown ``causal_legality_class`` fails ``validate_tcre_edge_v1_stub``."""
    errors: list[str] = []
    edge = _legal_escalation_edge()
    edge["causal_legality_class"] = "causal_magic_inference"
    try:
        validate_tcre_edge_v1_stub(edge)
    except ExecutionCausalityConstraintError:
        pass
    else:
        errors.append("expected_reject_unknown_causal_legality_class")
    passed = len(errors) == 0
    return {
        "id": "P06-20-clc-stub-reject-unknown",
        "name": "gp06_clc03_tcre_stub_rejects_unknown_causal_legality",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_causal_legality_step(errors),
    }


def verify_gp06_clc04_tcre_stub_omits_causal_legality_class_static() -> dict[str, Any]:
    """P06-20 — field is optional until emitters require it; omission stays lawful."""
    errors: list[str] = []
    try:
        validate_tcre_edge_v1_stub(_legal_escalation_edge())
    except ExecutionCausalityConstraintError as exc:
        errors.append(f"unexpected_reject_without_causal_legality_class:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-20-clc-optional-field",
        "name": "gp06_clc04_tcre_stub_omits_causal_legality_class",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _gp06_detail_causal_legality_step(errors),
    }
