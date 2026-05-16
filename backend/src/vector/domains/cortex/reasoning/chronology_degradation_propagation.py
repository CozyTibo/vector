"""Phase 06 P06-11 — chronology degradation propagation (CD‑CHRON + policy caps).

Normative:
``DOCS/cortex/reasoning/causal-degradation-spec.md``,
``DOCS/cortex/reasoning/chronology-replay-legality-state-machine.md`` §6,
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (caps + degradation_thresholds).
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_legality import (
    ChronologyLegalityError,
    load_default_reasoning_policy_pack,
    should_emit_cd_chron_from_policy,
)

PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# Doctrine uses U+2011 (non-breaking hyphen) between ``CD`` and the suffix.
_NBHY: Final[str] = "\u2011"

CD_CHRON: Final[str] = f"CD{_NBHY}CHRON"
CD_CONT: Final[str] = f"CD{_NBHY}CONT"
CD_REPLAY: Final[str] = f"CD{_NBHY}REPLAY"
CD_NEG: Final[str] = f"CD{_NBHY}NEG"
CD_COMMIT: Final[str] = f"CD{_NBHY}COMMIT"

CANONICAL_DEGRADATION_CODES: Final[frozenset[str]] = frozenset(
    {CD_CHRON, CD_CONT, CD_REPLAY, CD_NEG, CD_COMMIT}
)

CHRONOLOGY_LEGALITY_CLASSES_EMITTING_CD_CHRON: Final[frozenset[str]] = frozenset(
    {
        "chronology_partial",
        "chronology_unresolved",
        "chronology_degraded",
    }
)

# ``causal-degradation-spec.md`` §3 — corpus aliases → canonical ``CD‑*``.
_CORPUS_ALIAS_TO_CANONICAL: Final[dict[str, str]] = {
    "replay_skew": CD_REPLAY,
    "stale_verification": CD_REPLAY,
    "chronology_cap_applied": CD_CHRON,
    "continuity_bridge_weak": CD_CONT,
    "partitioned_negative_signal": CD_NEG,
    "commitment_lifecycle_conflict": CD_COMMIT,
}

RULE_ID_CD_CHRON_FROM_CHRONOLOGY_V1: Final[str] = "tcre_cd_chron_from_chronology_legality_v1"


class ChronologyDegradationPropagationError(ValueError):
    """Fail-closed chronology ↔ CD‑* propagation / corpus / policy caps."""


def degradation_severity_rank_v1(code: str) -> int:
    """``causal-degradation-spec.md`` §2 — ordinal for ``severity_rank(CD‑*)``."""
    c = normalize_degradation_corpus_token_v1(code)
    return {
        CD_COMMIT: 5,
        CD_REPLAY: 4,
        CD_NEG: 4,
        CD_CHRON: 3,
        CD_CONT: 2,
    }[c]


def normalize_degradation_corpus_token_v1(token: str) -> str:
    """§3 + **G‑P06‑DEG‑01** — map legacy / operator aliases and ASCII hyphens to canonical."""
    if not isinstance(token, str) or not token.strip():
        raise ChronologyDegradationPropagationError("degradation corpus token must be a non-empty string")
    t = token.strip()
    if t in _CORPUS_ALIAS_TO_CANONICAL:
        return _CORPUS_ALIAS_TO_CANONICAL[t]
    if t in CANONICAL_DEGRADATION_CODES:
        return t
    t_ascii = t.replace("-", _NBHY)
    if t_ascii in CANONICAL_DEGRADATION_CODES:
        return t_ascii
    raise ChronologyDegradationPropagationError(f"unknown degradation corpus token: {token!r}")


def normalize_expected_degradation_classes_corpus_v1(classes: object) -> list[str]:
    """Validate a corpus ``expected_degradation_classes`` list; return sorted unique canonical codes."""
    if not isinstance(classes, list):
        raise ChronologyDegradationPropagationError("expected_degradation_classes must be a list")
    out: list[str] = []
    for i, item in enumerate(classes):
        if not isinstance(item, str):
            raise ChronologyDegradationPropagationError(f"expected_degradation_classes[{i}] must be string")
        out.append(normalize_degradation_corpus_token_v1(item))
    return sorted(set(out))


def sort_cd_codes_deg_mon_1_display_v1(codes: Sequence[str]) -> list[str]:
    """**DEG‑MON‑1** — stable display order: ``(-severity_rank, code, rule_id)`` with ``rule_id`` omitted here."""
    canon = [normalize_degradation_corpus_token_v1(c) for c in codes]
    return sorted(canon, key=lambda c: (-degradation_severity_rank_v1(c), c))


def degradation_coarse_tag_v1(codes: Sequence[str]) -> str:
    """``reasoning-provenance-law.md`` — ``composite`` iff ``len(CD_codes) > 1`` (list cardinality)."""
    if len(codes) == 0:
        return "none"
    if len(codes) > 1:
        for c in codes:
            normalize_degradation_corpus_token_v1(c)
        return "composite"
    normalize_degradation_corpus_token_v1(codes[0])
    return "none"


def list_cd_chron_from_chronology_legality_v1(
    *,
    chronology_legality_class: str,
    policy: Mapping[str, Any],
) -> list[str]:
    """State machine §6 — emit ``CD‑CHRON`` when policy thresholds fire on non‑strict chronology band."""
    if chronology_legality_class not in CHRONOLOGY_LEGALITY_CLASSES_EMITTING_CD_CHRON:
        return []
    if not should_emit_cd_chron_from_policy(
        chronology_legality_class=chronology_legality_class,
        policy=policy,
    ):
        return []
    return [CD_CHRON]


def effective_max_causal_hops_v1(
    *,
    chronology_legality_class: str,
    policy: Mapping[str, Any],
) -> int:
    """When ``CD‑CHRON`` band applies per ``list_cd_chron_from_chronology_legality_v1``, use degraded hop cap."""
    caps_obj = policy.get("caps")
    if not isinstance(caps_obj, Mapping):
        raise ChronologyDegradationPropagationError("policy.caps must be a mapping")
    default_h = caps_obj.get("max_causal_hops_default")
    degraded_h = caps_obj.get("max_causal_hops_degraded")
    if not isinstance(default_h, int) or default_h < 0:
        raise ChronologyDegradationPropagationError("caps.max_causal_hops_default must be int >= 0")
    if not isinstance(degraded_h, int) or degraded_h < 0:
        raise ChronologyDegradationPropagationError("caps.max_causal_hops_degraded must be int >= 0")
    if list_cd_chron_from_chronology_legality_v1(
        chronology_legality_class=chronology_legality_class,
        policy=policy,
    ):
        return degraded_h
    return default_h


def validate_policy_caps_g_p06_pol01_v1(policy: Mapping[str, Any]) -> None:
    """``reasoning-policy-pack-v1.md`` §6 — **G‑P06‑POL‑01** sketch: caps shape + degraded ≤ default."""
    caps_obj = policy.get("caps")
    if not isinstance(caps_obj, Mapping):
        raise ChronologyDegradationPropagationError("policy.caps must be a mapping")
    required = (
        "max_causal_hops_default",
        "max_causal_hops_degraded",
        "max_transitive_closure_hops",
        "max_breakpoints_per_chain",
        "max_tcre_edges_per_chain",
    )
    for key in required:
        if key not in caps_obj:
            raise ChronologyDegradationPropagationError(f"policy.caps missing key: {key!r}")
        v = caps_obj[key]
        if not isinstance(v, int) or v < 0:
            raise ChronologyDegradationPropagationError(f"policy.caps.{key} must be int >= 0")
    d = caps_obj["max_causal_hops_default"]
    g = caps_obj["max_causal_hops_degraded"]
    if g > d:
        raise ChronologyDegradationPropagationError(
            "G-P06-POL-01: max_causal_hops_degraded must be <= max_causal_hops_default"
        )


def degradation_receipt_entry_v1(
    *,
    code: str,
    rule_id: str,
    upstream_artifact_ids_sorted: Sequence[str],
    before_hash: str,
    after_hash_optional: str | None = None,
) -> dict[str, Any]:
    """``causal-degradation-spec.md`` §4 — single sorted-list receipt row (caller sorts bundle)."""
    c = normalize_degradation_corpus_token_v1(code)
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise ChronologyDegradationPropagationError("rule_id must be a non-empty string")
    ids = sorted({str(x) for x in upstream_artifact_ids_sorted})
    if not isinstance(before_hash, str) or not before_hash.strip():
        raise ChronologyDegradationPropagationError("before_hash must be a non-empty string")
    row: dict[str, Any] = {
        "code": c,
        "rule_id": rule_id.strip(),
        "upstream_artifact_ids_sorted": ids,
        "before_hash": before_hash.strip(),
    }
    if after_hash_optional is not None:
        if not isinstance(after_hash_optional, str) or not after_hash_optional.strip():
            raise ChronologyDegradationPropagationError("after_hash_optional must be non-empty when set")
        row["after_hash_optional"] = after_hash_optional.strip()
    return row


def sort_degradation_receipt_entries_v1(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§4 — deterministic order by ``(code, rule_id)`` on normalized rows."""
    normalized: list[dict[str, Any]] = []
    for i, e in enumerate(entries):
        if not isinstance(e, Mapping):
            raise ChronologyDegradationPropagationError(f"entries[{i}] must be a mapping")
        code = e.get("code")
        rule_id = e.get("rule_id")
        ids = e.get("upstream_artifact_ids_sorted")
        bh = e.get("before_hash")
        if not isinstance(code, str):
            raise ChronologyDegradationPropagationError(f"entries[{i}].code must be string")
        c = normalize_degradation_corpus_token_v1(code)
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ChronologyDegradationPropagationError(f"entries[{i}].rule_id invalid")
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise ChronologyDegradationPropagationError(
                f"entries[{i}].upstream_artifact_ids_sorted must be list[str]"
            )
        if not isinstance(bh, str) or not bh.strip():
            raise ChronologyDegradationPropagationError(f"entries[{i}].before_hash invalid")
        row: dict[str, Any] = {
            "code": c,
            "rule_id": rule_id.strip(),
            "upstream_artifact_ids_sorted": sorted(set(ids)),
            "before_hash": bh.strip(),
        }
        ah = e.get("after_hash_optional")
        if ah is not None:
            if not isinstance(ah, str) or not ah.strip():
                raise ChronologyDegradationPropagationError(f"entries[{i}].after_hash_optional invalid")
            row["after_hash_optional"] = ah.strip()
        normalized.append(row)
    return sorted(normalized, key=lambda r: (r["code"], r["rule_id"]))


def validate_degradation_multiset_monotonic_extension_v1(
    before_codes: Sequence[str],
    after_codes: Sequence[str],
) -> None:
    """§2 / §6 — removing evidence must not silently drop ``CD‑*`` counts (multiset non‑decreasing)."""
    b = Counter(normalize_degradation_corpus_token_v1(c) for c in before_codes)
    a = Counter(normalize_degradation_corpus_token_v1(c) for c in after_codes)
    for code, n in b.items():
        if a[code] < n:
            raise ChronologyDegradationPropagationError(
                f"DEG-MON-1 multiset regression: code {code!r} count {a[code]} < prior {n}"
            )


def verify_gp06_deg01_corpus_alias_registry_static() -> dict[str, Any]:
    """Static — alias table covers doctrine §3 and maps only to canonical ``CD‑*``."""
    errors: list[str] = []
    for alias, canon in _CORPUS_ALIAS_TO_CANONICAL.items():
        if canon not in CANONICAL_DEGRADATION_CODES:
            errors.append(f"alias_targets_non_canonical:{alias}->{canon!r}")
    for code in CANONICAL_DEGRADATION_CODES:
        try:
            assert normalize_degradation_corpus_token_v1(code) == code
        except ChronologyDegradationPropagationError as exc:
            errors.append(f"canonical_not_self_normalizing:{code!r}:{exc}")
    for alias in _CORPUS_ALIAS_TO_CANONICAL:
        try:
            normalize_degradation_corpus_token_v1(alias)
        except ChronologyDegradationPropagationError as exc:
            errors.append(f"alias_normalization_failed:{alias!r}:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-11-deg-corpus-aliases",
        "name": "gp06_deg01_corpus_alias_registry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_chronology_degradation_runtime_schema_version": (
                PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_deg02_severity_sort_oracle_static() -> dict[str, Any]:
    """Static — **DEG‑MON‑1** sort key matches doctrine ranks."""
    errors: list[str] = []
    sample = [CD_CONT, CD_COMMIT, CD_CHRON, CD_REPLAY, CD_NEG]
    got = sort_cd_codes_deg_mon_1_display_v1(sample)
    want = [CD_COMMIT, CD_NEG, CD_REPLAY, CD_CHRON, CD_CONT]
    if got != want:
        errors.append(f"severity_sort_mismatch:got={got}:want={want}")
    passed = len(errors) == 0
    return {
        "id": "P06-11-deg-severity-sort",
        "name": "gp06_deg02_severity_sort_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_chronology_degradation_runtime_schema_version": (
                PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_deg03_default_policy_caps_static() -> dict[str, Any]:
    """Static — default fixture satisfies **G‑P06‑POL‑01** caps sketch."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack()
        validate_policy_caps_g_p06_pol01_v1(pack)
    except (ChronologyDegradationPropagationError, ChronologyLegalityError, OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-11-deg-default-caps",
        "name": "gp06_deg03_default_policy_caps",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_chronology_degradation_runtime_schema_version": (
                PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
