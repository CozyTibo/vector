"""Phase 07 P07-08 — query replay identity + pins (**G-P07-REPLAY-01**).

Normative: ``DOCS/cortex/retrieval/phase-07-replay-equivalence-retrieval-spec.md``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1

PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_REPLAY_01_GATE_ID_V1: Final[str] = "G-P07-REPLAY-01"

RETRIEVAL_RD_POLICY_MISMATCH_V1: Final[str] = "RD-POLICY-MISMATCH"

RETRIEVAL_REPLAY_EQUIVALENCE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-replay-equivalence-retrieval-spec.md"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")

# Canonical replay pin fields (query envelope ``replay_pins`` + provenance §Replay).
RETRIEVAL_REPLAY_PIN_FIELD_IDS_V1: Final[tuple[str, ...]] = (
    "retrieval_policy_digest",
    "tcre_policy_bundle_digest",
    "octs_engine_build_ref",
    "index_epoch",
    "retrieval_replay_identity",
    "replay_identity",
    "expected_replay_identity",
)

_REPLAY_IDENTITY_ENVELOPE_EXCLUDE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "retrieval_query_receipt",
        "execution_trace",
        "receipt_digest",
    }
)

_RETRIEVAL_REPLAY_DIVERGENCE_TOTAL_V1: int = 0


class RetrievalReplayEquivalenceError(ValueError):
    """Fail-closed retrieval replay identity / double-run law."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_replay_divergence_total_v1() -> int:
    return _RETRIEVAL_REPLAY_DIVERGENCE_TOTAL_V1


def record_retrieval_replay_divergence_v1(
    *,
    tenant_id: str,
    retrieval_query_replay_identity_a: str,
    retrieval_query_replay_identity_b: str,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record **G-P07-REPLAY-01** divergence (observability counter)."""
    global _RETRIEVAL_REPLAY_DIVERGENCE_TOTAL_V1
    _RETRIEVAL_REPLAY_DIVERGENCE_TOTAL_V1 += 1
    from vector.domains.cortex.replay_divergence_observability import (
        REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1,
        on_replay_divergence_observed_v1,
    )

    on_replay_divergence_observed_v1(
        tenant_id=tenant_id,
        source=REPLAY_DIVERGENCE_SOURCE_RETRIEVAL_V1,
        detail=dict(detail or {}),
    )
    return {
        "event": "retrieval_replay_divergence",
        "gate_id": GP07_REPLAY_01_GATE_ID_V1,
        "tenant_id": tenant_id,
        "retrieval_query_replay_identity_a": retrieval_query_replay_identity_a,
        "retrieval_query_replay_identity_b": retrieval_query_replay_identity_b,
        "detail": dict(detail or {}),
    }


def normalize_retrieval_query_envelope_for_replay_identity_v1(
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Envelope bytes for replay identity (exclude receipt / trace fields)."""
    out: dict[str, Any] = {}
    for key, val in envelope.items():
        if key in _REPLAY_IDENTITY_ENVELOPE_EXCLUDE_KEYS:
            continue
        out[key] = val
    return out


def normalize_retrieval_hit_upstream_digests_v1(
    hits: Sequence[Mapping[str, Any]],
    *,
    fallback_lookup_id: str | None = None,
    fallback_upstream_digest: str | None = None,
) -> list[list[str]]:
    """Sorted list of ``[retrieval_lookup_id, upstream_digest]`` tuples."""
    tuples: list[list[str]] = []
    for hit in hits:
        lookup = str(hit.get("retrieval_lookup_id") or "").strip()
        upstream = str(hit.get("upstream_digest") or "").strip()
        if not upstream:
            prov = hit.get("provenance")
            if isinstance(prov, dict):
                upstream = hash_reasoning_canonical_json_sha256_v1(prov)
        if lookup and upstream:
            tuples.append([lookup, upstream])
    if not tuples and fallback_lookup_id and fallback_upstream_digest:
        tuples.append([fallback_lookup_id, fallback_upstream_digest])
    tuples.sort(key=lambda row: (row[0], row[1]))
    return tuples


def normalize_retrieval_omission_multiset_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> list[list[str]]:
    """Sorted list of ``[retrieval_omission_class, trigger_key]`` tuples."""
    tuples: list[list[str]] = []
    for row in omissions:
        oclass = str(
            row.get("retrieval_omission_class") or row.get("rd_code") or ""
        ).strip()
        trigger = str(row.get("upstream_trigger") or row.get("trigger_key") or "").strip()
        if oclass:
            tuples.append([oclass, trigger])
    tuples.sort(key=lambda row: (row[0], row[1]))
    return tuples


def build_retrieval_query_replay_identity_vector_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_policy_digest: str,
    hits: Sequence[Mapping[str, Any]],
    omissions: Sequence[Mapping[str, Any]],
    fallback_lookup_id: str | None = None,
    fallback_upstream_digest: str | None = None,
) -> dict[str, Any]:
    """Canonical JSON scope for ``retrieval_query_replay_identity`` (pre-hash)."""
    return {
        "query_envelope": normalize_retrieval_query_envelope_for_replay_identity_v1(envelope),
        "retrieval_policy_digest": retrieval_policy_digest,
        "hit_upstream_digests_sorted": normalize_retrieval_hit_upstream_digests_v1(
            hits,
            fallback_lookup_id=fallback_lookup_id,
            fallback_upstream_digest=fallback_upstream_digest,
        ),
        "omission_multiset_sorted": normalize_retrieval_omission_multiset_v1(omissions),
    }


def hash_retrieval_query_replay_identity_v1(vector: Mapping[str, Any]) -> str:
    return hash_reasoning_canonical_json_sha256_v1(vector)


def compute_retrieval_query_replay_identity_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_policy_digest: str,
    hits: Sequence[Mapping[str, Any]],
    omissions: Sequence[Mapping[str, Any]],
    fallback_lookup_id: str | None = None,
    fallback_upstream_digest: str | None = None,
) -> str:
    """64-char hex sha256 ``retrieval_query_replay_identity``."""
    vector = build_retrieval_query_replay_identity_vector_v1(
        envelope=envelope,
        retrieval_policy_digest=retrieval_policy_digest,
        hits=hits,
        omissions=omissions,
        fallback_lookup_id=fallback_lookup_id,
        fallback_upstream_digest=fallback_upstream_digest,
    )
    return hash_retrieval_query_replay_identity_v1(vector)


def build_retrieval_query_replay_pins_v1(
    *,
    workload_class: str,
    intent: str,
    tenant_id: str | None = None,
    replay_pins: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge workload/intent scope with envelope replay pins for inspector surfaces."""
    from vector.domains.cortex.retrieval.query_contract import (
        build_retrieval_query_replay_identity_scope_v1,
    )

    scope = build_retrieval_query_replay_identity_scope_v1(
        workload_class=workload_class,
        intent=intent,
        tenant_id=tenant_id,
        extra_pins=replay_pins,
    )
    pins = dict(replay_pins or {})
    scope["replay_pins"] = pins
    scope["required_pin_fields"] = list(RETRIEVAL_REPLAY_PIN_FIELD_IDS_V1)
    return scope


def list_retrieval_replay_pin_violations_v1(
    replay_pins: Mapping[str, Any] | None,
    *,
    actual_policy_digest: str,
    execution_partition: str,
) -> list[dict[str, Any]]:
    """Return ``RD-POLICY-MISMATCH`` omission rows when authoritative pins disagree."""
    if execution_partition != "authoritative":
        return []
    pins = replay_pins if isinstance(replay_pins, dict) else {}
    pinned = pins.get("retrieval_policy_digest")
    if pinned is None or not str(pinned).strip():
        return []
    if str(pinned).strip() != actual_policy_digest:
        return [
            {
                "retrieval_omission_class": RETRIEVAL_RD_POLICY_MISMATCH_V1,
                "upstream_trigger": "retrieval_policy_digest_pin",
                "pinned_digest": str(pinned).strip(),
                "actual_digest": actual_policy_digest,
            }
        ]
    return []


def enforce_retrieval_replay_pins_authoritative_v1(
    replay_pins: Mapping[str, Any] | None,
    *,
    actual_policy_digest: str,
    execution_partition: str,
) -> None:
    """Fail closed on policy digest mismatch in authoritative partition."""
    violations = list_retrieval_replay_pin_violations_v1(
        replay_pins,
        actual_policy_digest=actual_policy_digest,
        execution_partition=execution_partition,
    )
    if violations:
        raise RetrievalReplayEquivalenceError(
            RETRIEVAL_RD_POLICY_MISMATCH_V1,
            detail={"violations": violations},
        )


def compare_gp07_replay_01_double_run_v1(
    result_a: Mapping[str, Any],
    result_b: Mapping[str, Any],
) -> None:
    """**G-P07-REPLAY-01** — require identical identity, receipt, hits, omissions."""
    id_a = str(result_a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    id_b = str(result_b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    if id_a != id_b:
        raise RetrievalReplayEquivalenceError(
            f"{GP07_REPLAY_01_GATE_ID_V1}: retrieval_query_replay_identity mismatch",
            detail={"a": id_a, "b": id_b},
        )
    rec_a = result_a.get("retrieval_query_receipt") or {}
    rec_b = result_b.get("retrieval_query_receipt") or {}
    assert isinstance(rec_a, dict)
    assert isinstance(rec_b, dict)
    dig_a = str(rec_a.get("receipt_digest") or "")
    dig_b = str(rec_b.get("receipt_digest") or "")
    if dig_a != dig_b:
        raise RetrievalReplayEquivalenceError(
            f"{GP07_REPLAY_01_GATE_ID_V1}: receipt_digest mismatch",
            detail={"a": dig_a, "b": dig_b},
        )
    hits_a = result_a.get("hits")
    hits_b = result_b.get("hits")
    if not isinstance(hits_a, list) or not isinstance(hits_b, list):
        raise RetrievalReplayEquivalenceError("hits_must_be_lists")
    if len(hits_a) != len(hits_b):
        raise RetrievalReplayEquivalenceError(
            f"{GP07_REPLAY_01_GATE_ID_V1}: hit_count mismatch",
            detail={"count_a": len(hits_a), "count_b": len(hits_b)},
        )
    om_a = normalize_retrieval_omission_multiset_v1(result_a.get("omissions") or [])  # type: ignore[arg-type]
    om_b = normalize_retrieval_omission_multiset_v1(result_b.get("omissions") or [])  # type: ignore[arg-type]
    if om_a != om_b:
        raise RetrievalReplayEquivalenceError(
            f"{GP07_REPLAY_01_GATE_ID_V1}: omission_multiset mismatch",
            detail={"a": om_a, "b": om_b},
        )


def build_retrieval_replay_equivalence_twin_diff_v1(
    result_a: Mapping[str, Any],
    result_b: Mapping[str, Any],
) -> dict[str, Any]:
    """Twin workload structural diff (``replay_equivalence``)."""
    rec_a = result_a.get("retrieval_query_receipt") or {}
    rec_b = result_b.get("retrieval_query_receipt") or {}
    assert isinstance(rec_a, dict)
    assert isinstance(rec_b, dict)
    hits_a = result_a.get("hits")
    hits_b = result_b.get("hits")
    count_a = len(hits_a) if isinstance(hits_a, list) else 0
    count_b = len(hits_b) if isinstance(hits_b, list) else 0
    om_a = normalize_retrieval_omission_multiset_v1(result_a.get("omissions") or [])  # type: ignore[arg-type]
    om_b = normalize_retrieval_omission_multiset_v1(result_b.get("omissions") or [])  # type: ignore[arg-type]
    ordering_divergence = normalize_retrieval_hit_upstream_digests_v1(
        hits_a if isinstance(hits_a, list) else []
    ) != normalize_retrieval_hit_upstream_digests_v1(
        hits_b if isinstance(hits_b, list) else []
    )
    return {
        "receipt_digest_a": str(rec_a.get("receipt_digest") or ""),
        "receipt_digest_b": str(rec_b.get("receipt_digest") or ""),
        "retrieval_query_replay_identity_a": str(
            result_a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or ""
        ),
        "retrieval_query_replay_identity_b": str(
            result_b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or ""
        ),
        "hit_count_mismatch": count_a != count_b,
        "ordering_divergence": ordering_divergence,
        "omission_multiset_delta": om_a != om_b,
        "gp07_replay_01_passed": (
            str(result_a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
            == str(result_b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
            and str(rec_a.get("receipt_digest") or "")
            == str(rec_b.get("receipt_digest") or "")
            and count_a == count_b
            and not ordering_divergence
            and om_a == om_b
        ),
    }


def build_retrieval_replay_inspector_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin replay inspector — canonical scope + pin law + divergence counter."""
    return {
        "tenant_id": tenant_id or "",
        "retrieval_replay_equivalence_runtime_schema_version": (
            PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_REPLAY_01_GATE_ID_V1,
        "replay_identity_field": PHASE07_REPLAY_IDENTITY_FIELD_V1,
        "canonical_scope": {
            "query_envelope_excludes": sorted(_REPLAY_IDENTITY_ENVELOPE_EXCLUDE_KEYS),
            "includes": [
                "query_envelope",
                "retrieval_policy_digest",
                "hit_upstream_digests_sorted",
                "omission_multiset_sorted",
            ],
        },
        "replay_pin_fields": list(RETRIEVAL_REPLAY_PIN_FIELD_IDS_V1),
        "rd_policy_mismatch": RETRIEVAL_RD_POLICY_MISMATCH_V1,
        "retrieval_replay_divergence_total": get_retrieval_replay_divergence_total_v1(),
        "doctrine_anchor": RETRIEVAL_REPLAY_EQUIVALENCE_SPEC_REF_V1,
        "actual_retrieval_policy_digest": retrieval_policy_digest_v1(),
    }


def _replay_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_REPLAY_01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_replay_01_canonical_identity_stable_static() -> dict[str, Any]:
    errors: list[str] = []
    env = {
        "schema_version": 1,
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"retrieval_lookup_id": "sha256:aa"},
    }
    hits = [{"retrieval_lookup_id": "sha256:aa", "upstream_digest": "b" * 64}]
    omissions: list[dict[str, Any]] = []
    digest = retrieval_policy_digest_v1()
    id1 = compute_retrieval_query_replay_identity_v1(
        envelope=env,
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=omissions,
    )
    id2 = compute_retrieval_query_replay_identity_v1(
        envelope=env,
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=omissions,
    )
    if id1 != id2:
        errors.append("identity_not_stable")
    if not _SHA256_HEX_RE.match(id1):
        errors.append("identity_not_sha256_hex")
    id3 = compute_retrieval_query_replay_identity_v1(
        envelope={**env, "intent": "audit"},
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=omissions,
    )
    if id1 == id3:
        errors.append("identity_should_differ_on_envelope_change")
    return _replay_meta("gp07_replay_01_canonical_identity_stable", errors)


def verify_gp07_replay_01_double_run_match_static() -> dict[str, Any]:
    errors: list[str] = []
    digest = retrieval_policy_digest_v1()
    base: dict[str, Any] = {
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "a" * 64,
        "retrieval_query_receipt": {"receipt_digest": "b" * 64},
        "hits": [{"retrieval_lookup_id": "x", "upstream_digest": "c" * 64}],
        "omissions": [{"retrieval_omission_class": "RD-TCRE-GAP", "upstream_trigger": "t"}],
    }
    try:
        compare_gp07_replay_01_double_run_v1(base, dict(base))
    except RetrievalReplayEquivalenceError as exc:
        errors.append(str(exc))
    mismatched = dict(base)
    mismatched[PHASE07_REPLAY_IDENTITY_FIELD_V1] = "d" * 64
    try:
        compare_gp07_replay_01_double_run_v1(base, mismatched)
    except RetrievalReplayEquivalenceError:
        pass
    else:
        errors.append("expected_mismatch_rejection")
    return _replay_meta("gp07_replay_01_double_run_match", errors)


def verify_gp07_replay_01_policy_pin_mismatch_static() -> dict[str, Any]:
    errors: list[str] = []
    actual = retrieval_policy_digest_v1()
    violations = list_retrieval_replay_pin_violations_v1(
        {"retrieval_policy_digest": "f" * 64},
        actual_policy_digest=actual,
        execution_partition="authoritative",
    )
    if not violations or violations[0]["retrieval_omission_class"] != RETRIEVAL_RD_POLICY_MISMATCH_V1:
        errors.append("expected_rd_policy_mismatch")
    try:
        enforce_retrieval_replay_pins_authoritative_v1(
            {"retrieval_policy_digest": "f" * 64},
            actual_policy_digest=actual,
            execution_partition="authoritative",
        )
    except RetrievalReplayEquivalenceError as exc:
        if exc.code != RETRIEVAL_RD_POLICY_MISMATCH_V1:
            errors.append(f"wrong_code:{exc.code}")
    else:
        errors.append("expected_enforce_raise")
    return _replay_meta("gp07_replay_01_policy_pin_mismatch", errors)
