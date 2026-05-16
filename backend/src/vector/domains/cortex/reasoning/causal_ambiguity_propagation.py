"""Phase 06 P06-22 — causal ambiguity propagation (registry + AMB‑S1).

Normative:
``DOCS/cortex/reasoning/bounded-ambiguity-law.md``,
``DOCS/cortex/reasoning/ambiguity-registry-v1.md`` (§§1, 3–4),
``DOCS/cortex/continuity/conflict-resolution-doctrine.md`` §5 (propagation matrix).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    AMB_ACK_CONFLICTED,
    AMB_ANCH_MISSING,
    AMB_BRIDGE_WEAK,
    AMB_CHRON_CONFLICT,
    AMB_CHRON_PARTIAL,
    AMB_NONE,
    AMB_OWN_PARALLEL,
    AMB_PART_STORYLINE,
    KNOWN_AMBIGUITY_CLASS_IDS,
    OrganizationalContinuityReasoningError,
    validate_ambiguity_class_id_registered,
)

PHASE06_CAUSAL_AMBIGUITY_PROPAGATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TCRE_AMBIGUITY_REGISTRY_VERSION: Final[int] = 1

_NBHY: Final[str] = "\u2011"

# ``ambiguity-registry-v1.md`` §3 — legacy / corpus aliases → canonical ``AMB‑*`` ids.
_LEGACY_AMBIGUITY_ALIAS_TO_CANONICAL: Final[dict[str, str]] = {
    "ownership_parallel_assignees": AMB_OWN_PARALLEL,
    "chronology_partial_order": AMB_CHRON_PARTIAL,
    "parallel_cause": AMB_PART_STORYLINE,
    "partitioned_storyline": AMB_PART_STORYLINE,
    "weak_cross_system_bridge": AMB_BRIDGE_WEAK,
    "conflicted_ack": AMB_ACK_CONFLICTED,
    "missing_anchor": AMB_ANCH_MISSING,
    "unresolved_chronology": AMB_CHRON_CONFLICT,
}

_LEGACY_AMBIGUITY_ALIAS_LOWER: Final[dict[str, str]] = {
    k.lower(): v for k, v in _LEGACY_AMBIGUITY_ALIAS_TO_CANONICAL.items()
}

# Normative cross-link (bounded-ambiguity-law §3 — propagation matrix).
CONFLICT_RESOLUTION_AMBIGUITY_PROPAGATION_SECTION_REF_V1: Final[str] = (
    "DOCS/cortex/continuity/conflict-resolution-doctrine.md §5"
)

_AMB_S1_FORBIDDEN_COERCION_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "ambiguity_suppressed",
        "coerce_ambiguity_to_none",
        "silent_ambiguity_clearance",
        "treat_ambiguity_as_resolved",
    }
)


class CausalAmbiguityPropagationError(ValueError):
    """Fail-closed causal ambiguity registry / corpus / AMB‑S1 survivability."""


def _amb_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_causal_ambiguity_propagation_runtime_schema_version": (
            PHASE06_CAUSAL_AMBIGUITY_PROPAGATION_RUNTIME_SCHEMA_VERSION
        ),
        "tcre_ambiguity_registry_version": TCRE_AMBIGUITY_REGISTRY_VERSION,
    }


def validate_ambiguity_class_id_causal_registry_v1(value: object) -> None:
    """``ambiguity-registry-v1.md`` §1 — ``ambiguity_class_id`` must be a registered ``AMB‑*``."""
    try:
        validate_ambiguity_class_id_registered(value)
    except OrganizationalContinuityReasoningError as exc:
        raise CausalAmbiguityPropagationError(str(exc)) from exc


def normalize_ambiguity_corpus_token_to_registry_id_v1(token: str) -> str:
    """§3 + **G‑P06‑AMB‑01** — legacy / operator aliases and ASCII hyphens → canonical ``AMB‑*``."""
    if not isinstance(token, str) or not token.strip():
        raise CausalAmbiguityPropagationError("ambiguity corpus token must be a non-empty string")
    t = token.strip()
    lk = t.lower()
    if lk in _LEGACY_AMBIGUITY_ALIAS_LOWER:
        return _LEGACY_AMBIGUITY_ALIAS_LOWER[lk]
    if t in KNOWN_AMBIGUITY_CLASS_IDS:
        return t
    t_nb = t.replace("-", _NBHY)
    if t_nb in KNOWN_AMBIGUITY_CLASS_IDS:
        return t_nb
    raise CausalAmbiguityPropagationError(f"unknown ambiguity corpus token: {token!r}")


def validate_amb_s1_no_false_certainty_coercion_v1(body: Mapping[str, Any]) -> None:
    """``bounded-ambiguity-law`` §4 + registry §4 — **AMB‑S1** forbids coercion flags."""
    raw = body.get("ambiguity_class_id")
    if raw is None:
        return
    if not isinstance(raw, str) or not raw.strip():
        raise CausalAmbiguityPropagationError("ambiguity_class_id must be non-empty when present")
    canon = normalize_ambiguity_corpus_token_to_registry_id_v1(raw.strip())
    if canon == AMB_NONE:
        return
    for k in _AMB_S1_FORBIDDEN_COERCION_KEYS_V1:
        if body.get(k) is True:
            raise CausalAmbiguityPropagationError(
                f"AMB-S1: forbidden false-certainty coercion when ambiguity is active: {k!r}"
            )


def validate_causal_ambiguity_propagation_bundle_v1(body: Mapping[str, Any]) -> None:
    """P06-22 — optional ``ambiguity_class_id`` + **AMB‑S1** on a TCRE bundle mapping."""
    raw = body.get("ambiguity_class_id")
    if raw is not None:
        if not isinstance(raw, str) or not raw.strip():
            raise CausalAmbiguityPropagationError(
                "ambiguity_class_id must be non-empty when present"
            )
        canon = normalize_ambiguity_corpus_token_to_registry_id_v1(raw.strip())
        validate_ambiguity_class_id_causal_registry_v1(canon)
    validate_amb_s1_no_false_certainty_coercion_v1(body)


def verify_gp06_amb01_registry_literal_oracle_static() -> dict[str, Any]:
    """P06-22 — frozen ``KNOWN_AMBIGUITY_CLASS_IDS`` matches registry §1 table size + membership."""
    errors: list[str] = []
    oracle = frozenset(
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
    if KNOWN_AMBIGUITY_CLASS_IDS != oracle:
        errors.append("known_ambiguity_class_ids_mismatch_oracle")
    if len(KNOWN_AMBIGUITY_CLASS_IDS) != 8:
        errors.append("expected_eight_ambiguity_literals")
    passed = len(errors) == 0
    return {
        "id": "P06-22-amb-registry-oracle",
        "name": "gp06_amb01_registry_literal_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _amb_detail(errors),
    }


def verify_gp06_amb02_legacy_alias_normalization_static() -> dict[str, Any]:
    """P06-22 — §3 alias table normalizes to canonical ids."""
    errors: list[str] = []
    pairs = (
        ("weak_cross_system_bridge", AMB_BRIDGE_WEAK),
        ("partitioned_storyline", AMB_PART_STORYLINE),
        ("unresolved_chronology", AMB_CHRON_CONFLICT),
    )
    for legacy, expected in pairs:
        try:
            got = normalize_ambiguity_corpus_token_to_registry_id_v1(legacy)
        except CausalAmbiguityPropagationError as exc:
            errors.append(f"{legacy!r}:{exc}")
            continue
        if got != expected:
            errors.append(f"{legacy!r}_want_{expected!r}_got_{got!r}")
    passed = len(errors) == 0
    return {
        "id": "P06-22-amb-alias-normalize",
        "name": "gp06_amb02_legacy_alias_normalization",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _amb_detail(errors),
    }


def verify_gp06_amb03_unknown_corpus_token_rejected_static() -> dict[str, Any]:
    """P06-22 — **G‑P06‑AMB‑01** unknown strings fail closed."""
    errors: list[str] = []
    try:
        normalize_ambiguity_corpus_token_to_registry_id_v1("not_a_registered_ambiguity_token")
    except CausalAmbiguityPropagationError:
        pass
    else:
        errors.append("expected_reject_unknown_token")
    passed = len(errors) == 0
    return {
        "id": "P06-22-amb-unknown-token",
        "name": "gp06_amb03_unknown_corpus_token_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _amb_detail(errors),
    }


def verify_gp06_amb04_amb_s1_rejects_coercion_flags_static() -> dict[str, Any]:
    """P06-22 — **AMB‑S1** rejects truthy coercion keys when ambiguity is active."""
    errors: list[str] = []
    bad = {
        "ambiguity_class_id": AMB_CHRON_PARTIAL,
        "ambiguity_suppressed": True,
    }
    try:
        validate_causal_ambiguity_propagation_bundle_v1(bad)
    except CausalAmbiguityPropagationError:
        pass
    else:
        errors.append("expected_reject_ambiguity_suppressed_with_active_ambiguity")
    passed = len(errors) == 0
    return {
        "id": "P06-22-amb-s1-coercion",
        "name": "gp06_amb04_amb_s1_rejects_coercion_flags",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _amb_detail(errors),
    }


def verify_gp06_amb05_bundle_happy_path_static() -> dict[str, Any]:
    """P06-22 — registered id + no coercion flags passes combined bundle validator."""
    errors: list[str] = []
    good = {
        "ambiguity_class_id": AMB_BRIDGE_WEAK,
        "sole_support_kind": "hint",
    }
    try:
        validate_causal_ambiguity_propagation_bundle_v1(good)
    except CausalAmbiguityPropagationError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-22-amb-bundle-happy",
        "name": "gp06_amb05_bundle_happy_path",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _amb_detail(errors),
    }
