"""Phase 06 P06-19 — negative-signal causality (``tcre_negative_signal`` + silence law).

Normative:
``DOCS/cortex/reasoning/causal-reconstruction-doctrine.md`` §5,
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (§3, §4.2),
``DOCS/cortex/reasoning/silence-causality-law.md`` §§1, 4.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import NegativeSignalKind
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
    ExecutionCausalityConstraintError,
    validate_tcre_edge_v1_stub,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    OrganizationalContinuityReasoningError,
    validate_evidence_lineage_has_raw_or_ledger_hop,
)

PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TCRE_NEGATIVE_SIGNAL_KIND: Final[str] = "tcre_negative_signal"

TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1: Final[str] = "TCRE_MAP_negative_signal_"

# ``silence-causality-law.md`` §1 — ``NegativeExecutionSignal`` kinds that reference silence /
# unanswered patterns (closed subset of ``NegativeSignalKind``).
NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1: Final[frozenset[str]] = frozenset(
    {
        NegativeSignalKind.UNANSWERED_REQUEST.value,
        NegativeSignalKind.IGNORED_ESCALATION.value,
        NegativeSignalKind.ABANDONED_COORDINATION_THREAD.value,
        NegativeSignalKind.MISSING_ACKNOWLEDGMENT.value,
        NegativeSignalKind.REPEATED_FOLLOW_UP.value,
        NegativeSignalKind.SILENT_DELIVERY_DRIFT.value,
    }
)


class NegativeSignalCausalityError(ValueError):
    """Fail-closed ``tcre_negative_signal`` + silence-causality law."""


def _underlying_ids_str_list(edge: Mapping[str, Any]) -> list[str]:
    raw = edge.get("underlying_coordination_edge_ids")
    if not isinstance(raw, list):
        raise NegativeSignalCausalityError("underlying_coordination_edge_ids must be a list")
    return [str(x) for x in raw]


def underlying_coordination_edge_ids_sentinel_only_negative_v1(edge: Mapping[str, Any]) -> bool:
    """True when ids are exactly ``[NO_COORDINATION_EDGE_SENTINEL]`` (registry §4.2)."""
    ids = _underlying_ids_str_list(edge)
    return len(ids) == 1 and ids[0] == NO_COORDINATION_EDGE_SENTINEL


def lineage_includes_raw_record_hop_negative_v1(lineage: object) -> bool:
    """Doctrine §5 / registry §4.2 — raw closure for sentinel path."""
    if not isinstance(lineage, list):
        return False
    for hop in lineage:
        if not isinstance(hop, Mapping):
            continue
        if hop.get("hop_kind") == "raw_record" and hop.get("raw_record_id") is not None:
            return True
    return False


def lineage_includes_negative_signal_contract_hop_v1(lineage: object) -> bool:
    """Doctrine §5 — a hop carries non-empty ``signal_id`` (``NegativeExecutionSignal`` closure)."""
    if not isinstance(lineage, list):
        return False
    for hop in lineage:
        if not isinstance(hop, Mapping):
            continue
        sid = hop.get("signal_id")
        if isinstance(sid, str) and sid.strip():
            return True
    return False


def resolve_negative_signal_kind_v1(
    edge: Mapping[str, Any],
    *,
    negative_signal_kind: str | None,
) -> str:
    """Resolve ``NegativeSignalKind`` literal from kwargs then known edge keys."""
    if negative_signal_kind is not None:
        if isinstance(negative_signal_kind, str) and negative_signal_kind.strip():
            return negative_signal_kind.strip()
        raise NegativeSignalCausalityError(
            "negative_signal_kind must be a non-empty string when passed"
        )
    for key in ("negative_signal_kind", "source_negative_signal_kind"):
        v = edge.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    raise NegativeSignalCausalityError(
        "tcre_negative_signal requires negative_signal_kind (kwarg) or "
        "edge['negative_signal_kind'] / edge['source_negative_signal_kind']"
    )


def validate_tcre_negative_signal_kind_silence_law_v1(*, negative_signal_kind: str) -> None:
    """``silence-causality-law.md`` §1 — only lawful silence/unanswered enum literals."""
    if negative_signal_kind not in NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1:
        allowed = ", ".join(sorted(NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1))
        raise NegativeSignalCausalityError(
            f"negative_signal_kind {negative_signal_kind!r} is not lawful for silence causality; "
            f"allowed: {allowed}"
        )


def validate_tcre_negative_signal_derivation_rule_v1(edge: Mapping[str, Any]) -> None:
    """Registry §3 — ``NegativeExecutionSignal`` mapping uses frozen derivation prefix."""
    rid = edge.get("derivation_rule_id")
    if not isinstance(rid, str) or not rid.strip():
        raise NegativeSignalCausalityError("derivation_rule_id must be a non-empty string")
    if not rid.strip().startswith(TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1):
        raise NegativeSignalCausalityError(
            "tcre_negative_signal derivation_rule_id must start with "
            f"{TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1!r}"
        )


def validate_tcre_negative_signal_sentinel_lineage_v1(edge: Mapping[str, Any]) -> None:
    """Doctrine §5 + registry §4.2 — sentinel-only requires **raw** + **signal_id** on hops."""
    if not underlying_coordination_edge_ids_sentinel_only_negative_v1(edge):
        return
    lineage = edge.get("evidence_lineage")
    if not lineage_includes_raw_record_hop_negative_v1(lineage):
        raise NegativeSignalCausalityError(
            "tcre_negative_signal with sentinel underlying_coordination_edge_ids requires "
            "evidence_lineage hop_kind=raw_record with raw_record_id"
        )
    if not lineage_includes_negative_signal_contract_hop_v1(lineage):
        raise NegativeSignalCausalityError(
            "tcre_negative_signal with sentinel underlying_coordination_edge_ids requires "
            "evidence_lineage hop carrying non-empty signal_id (NegativeExecutionSignal closure)"
        )


def _apply_negative_signal_doctrine_after_stub_v1(
    edge: Mapping[str, Any],
    *,
    negative_signal_kind: str | None,
) -> None:
    validate_tcre_negative_signal_derivation_rule_v1(edge)
    try:
        validate_evidence_lineage_has_raw_or_ledger_hop(edge.get("evidence_lineage"))
    except OrganizationalContinuityReasoningError as exc:
        raise NegativeSignalCausalityError(str(exc)) from exc
    sk = resolve_negative_signal_kind_v1(edge, negative_signal_kind=negative_signal_kind)
    validate_tcre_negative_signal_kind_silence_law_v1(negative_signal_kind=sk)
    validate_tcre_negative_signal_sentinel_lineage_v1(edge)


def validate_tcre_negative_signal_causality_v1(
    edge: Mapping[str, Any],
    *,
    negative_signal_kind: str | None = None,
) -> None:
    """P06-19 — stub + derivation + silence-lawful ``NegativeSignalKind`` + §4.2 sentinel."""
    kind = edge.get("tcre_causal_edge_kind")
    if kind != TCRE_NEGATIVE_SIGNAL_KIND:
        raise NegativeSignalCausalityError(
            f"tcre_causal_edge_kind must be {TCRE_NEGATIVE_SIGNAL_KIND!r}; got {kind!r}"
        )
    try:
        validate_tcre_edge_v1_stub(edge)
    except ExecutionCausalityConstraintError as exc:
        raise NegativeSignalCausalityError(str(exc)) from exc
    _apply_negative_signal_doctrine_after_stub_v1(edge, negative_signal_kind=negative_signal_kind)


def validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1(
    edge: Mapping[str, Any],
    *,
    negative_signal_kind: str | None = None,
) -> None:
    """P06-14 substrate + **P06-19** negative-signal law."""
    from vector.domains.cortex.reasoning.causal_reconstruction_substrate import (
        CausalReconstructionSubstrateError,
        validate_tcre_causal_edge_v1_reconstruction_substrate,
    )

    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate(edge)
    except CausalReconstructionSubstrateError as exc:
        raise NegativeSignalCausalityError(str(exc)) from exc
    if edge.get("tcre_causal_edge_kind") != TCRE_NEGATIVE_SIGNAL_KIND:
        raise NegativeSignalCausalityError(
            "validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1 "
            f"requires tcre_causal_edge_kind={TCRE_NEGATIVE_SIGNAL_KIND!r}"
        )
    _apply_negative_signal_doctrine_after_stub_v1(edge, negative_signal_kind=negative_signal_kind)


def verify_gp06_neg01_sentinel_requires_raw_and_signal_hop_static() -> dict[str, Any]:
    errors: list[str] = []
    base = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_negative_signal_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "negative_signal_kind": NegativeSignalKind.UNANSWERED_REQUEST.value,
    }
    try:
        validate_tcre_negative_signal_causality_v1(base)
    except NegativeSignalCausalityError:
        pass
    else:
        errors.append("expected_reject_missing_signal_hop")

    good = {
        **base,
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"hop_kind": "cross_link", "signal_id": "sig-neg-1"},
        ],
    }
    try:
        validate_tcre_negative_signal_causality_v1(good)
    except NegativeSignalCausalityError as exc:
        errors.append(f"unexpected_reject_good_sentinel:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-19-neg-sentinel-lineage",
        "name": "gp06_neg01_sentinel_requires_raw_and_signal_hop",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_negative_signal_causality_runtime_schema_version": (
                PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_neg02_concrete_coordination_skips_extra_signal_hop_static() -> dict[str, Any]:
    """Concrete underlying ids — substrate lineage only."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": ["coord-n1"],
        "derivation_rule_id": "TCRE_MAP_negative_signal_unanswered_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
        "negative_signal_kind": NegativeSignalKind.IGNORED_ESCALATION.value,
    }
    try:
        validate_tcre_negative_signal_causality_v1(edge)
    except NegativeSignalCausalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-19-neg-concrete-ids",
        "name": "gp06_neg02_concrete_coordination_skips_extra_signal_hop",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_negative_signal_causality_runtime_schema_version": (
                PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_neg03_bad_derivation_rule_prefix_rejected_static() -> dict[str, Any]:
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"signal_id": "s1"},
        ],
        "negative_signal_kind": NegativeSignalKind.UNANSWERED_REQUEST.value,
    }
    try:
        validate_tcre_negative_signal_causality_v1(edge)
    except NegativeSignalCausalityError:
        pass
    else:
        errors.append("expected_reject_bad_derivation_prefix")
    passed = len(errors) == 0
    return {
        "id": "P06-19-neg-derivation-prefix",
        "name": "gp06_neg03_bad_derivation_rule_prefix_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_negative_signal_causality_runtime_schema_version": (
                PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_neg04_unlawful_negative_signal_kind_rejected_static() -> dict[str, Any]:
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_negative_signal_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"signal_id": "s2"},
        ],
        "negative_signal_kind": NegativeSignalKind.STALE_BLOCKER.value,
    }
    try:
        validate_tcre_negative_signal_causality_v1(edge)
    except NegativeSignalCausalityError:
        pass
    else:
        errors.append("expected_reject_unlawful_signal_kind")
    passed = len(errors) == 0
    return {
        "id": "P06-19-neg-signal-kind",
        "name": "gp06_neg04_unlawful_negative_signal_kind_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_negative_signal_causality_runtime_schema_version": (
                PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_neg05_substrate_plus_negative_signal_law_static() -> dict[str, Any]:
    """P06-14 + P06-19 combined entry — lawful sentinel negative-signal edge."""
    errors: list[str] = []
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_negative_signal_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 9},
            {"hop_kind": "cross_link", "signal_id": "sig-zz"},
        ],
        "confidence_source": "explicit_rule_id",
        "negative_signal_kind": NegativeSignalKind.SILENT_DELIVERY_DRIFT.value,
    }
    try:
        validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1(edge)
    except NegativeSignalCausalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-19-neg-substrate-combined",
        "name": "gp06_neg05_substrate_plus_negative_signal_law",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_negative_signal_causality_runtime_schema_version": (
                PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
