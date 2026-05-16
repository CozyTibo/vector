"""Phase 06 P06-13 — causal interval closure (half-open influence windows + policy caps).

Normative:
``DOCS/cortex/reasoning/deterministic-causal-chain-spec.md`` (hop caps, acyclicity sketch),
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``caps``),
``DOCS/cortex/reasoning/temporal-reasoning-doctrine.md`` (half-open law via P06-05 validators).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    ChronologyDegradationPropagationError,
    effective_max_causal_hops_v1,
)
from vector.domains.cortex.reasoning.chronology_legality import (
    ChronologyLegalityError,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.interval_continuity import (
    IntervalContinuityError,
    validate_half_open_interval_chain_continuity_v1,
)

PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION: Final[int] = 1


class CausalIntervalClosureError(ValueError):
    """Fail-closed causal influence interval chain / hop or breakpoint caps."""


def canonical_sorted_tcre_causal_edge_ids_v1(edge_ids: Sequence[str]) -> list[str]:
    """``deterministic-causal-chain-spec.md`` — canonical ``tcre_edges`` list order (lex sort, unique)."""
    if not isinstance(edge_ids, (list, tuple)):
        raise CausalIntervalClosureError("edge_ids must be a list or tuple")
    out: list[str] = []
    for i, e in enumerate(edge_ids):
        if not isinstance(e, str) or not e.strip():
            raise CausalIntervalClosureError(f"edge_ids[{i}] must be a non-empty string")
        out.append(e.strip())
    if len(set(out)) != len(out):
        raise CausalIntervalClosureError("tcre_causal_edge_id list must not contain duplicates (acyclic chain)")
    return sorted(out)


def validate_causal_influence_half_open_chain_v1(
    intervals: Sequence[Mapping[str, Any]],
    *,
    chronology_legality_class: str,
    policy: Mapping[str, Any],
    breakpoint_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Half-open **T‑TEMP‑01** slices + interval continuity, hop cap, breakpoint cap, canonical edge ids.

    Each row **must** include ``tcre_causal_edge_id`` plus temporal / lineage fields accepted by
    ``validate_half_open_interval_chain_continuity_v1`` (``start_iso``, ``end_iso``, ``derivation_rule_id``, …).
    """
    if not isinstance(intervals, (list, tuple)):
        raise CausalIntervalClosureError("intervals must be a sequence")
    if not intervals:
        raise CausalIntervalClosureError("causal influence interval chain must be non-empty")
    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(intervals):
        if not isinstance(raw, Mapping):
            raise CausalIntervalClosureError(f"intervals[{i}] must be a mapping")
        eid = raw.get("tcre_causal_edge_id")
        if not isinstance(eid, str) or not eid.strip():
            raise CausalIntervalClosureError(f"intervals[{i}].tcre_causal_edge_id must be a non-empty string")
        rows.append(dict(raw))
    try:
        temporal_chain = validate_half_open_interval_chain_continuity_v1(rows)
    except IntervalContinuityError as exc:
        raise CausalIntervalClosureError(str(exc)) from exc

    edge_ids_time_order = [str(r["tcre_causal_edge_id"]).strip() for r in temporal_chain]
    if len(set(edge_ids_time_order)) != len(edge_ids_time_order):
        raise CausalIntervalClosureError(
            "duplicate tcre_causal_edge_id after temporal sort — chain must be acyclic (no repeated edge)"
        )
    sorted_ids = canonical_sorted_tcre_causal_edge_ids_v1(tuple(edge_ids_time_order))
    hop_cap = effective_max_causal_hops_v1(
        chronology_legality_class=chronology_legality_class,
        policy=policy,
    )
    if len(edge_ids_time_order) > hop_cap:
        raise CausalIntervalClosureError(
            f"hop cap exceeded: len(chain)={len(edge_ids_time_order)} > max_causal_hops_effective={hop_cap}"
        )
    caps = policy.get("caps")
    if not isinstance(caps, Mapping):
        raise CausalIntervalClosureError("policy.caps must be a mapping for breakpoint cap")
    bp_cap = caps.get("max_breakpoints_per_chain")
    if not isinstance(bp_cap, int) or bp_cap < 0:
        raise CausalIntervalClosureError("policy.caps.max_breakpoints_per_chain must be int >= 0")
    if breakpoint_ids is None:
        bps: Sequence[str] = ()
    elif not isinstance(breakpoint_ids, (list, tuple)):
        raise CausalIntervalClosureError("breakpoint_ids must be a list or tuple when provided")
    else:
        bps = breakpoint_ids
    if not all(isinstance(x, str) and x.strip() for x in bps):
        raise CausalIntervalClosureError("breakpoint_ids must be non-empty strings")
    if len(bps) > bp_cap:
        raise CausalIntervalClosureError(
            f"breakpoint cap exceeded: len(breakpoint_ids)={len(bps)} > max_breakpoints_per_chain={bp_cap}"
        )
    return {
        "sorted_tcre_causal_edge_ids": sorted_ids,
        "temporal_chain_rows": temporal_chain,
        "hop_count": len(edge_ids_time_order),
        "max_causal_hops_effective": hop_cap,
    }


def verify_gp06_cic01_default_policy_caps_static() -> dict[str, Any]:
    """Static — default pack supports **hop** + **breakpoint** caps for reducers."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack()
        caps = pack.get("caps")
        if not isinstance(caps, Mapping):
            errors.append("caps_missing")
        else:
            for key in ("max_causal_hops_default", "max_causal_hops_degraded", "max_breakpoints_per_chain"):
                v = caps.get(key)
                if not isinstance(v, int) or v < 0:
                    errors.append(f"bad_cap:{key}:{v!r}")
        h = effective_max_causal_hops_v1(chronology_legality_class="chronology_strict", policy=pack)
        if h < 1:
            errors.append("effective_hops_non_positive")
    except (ChronologyLegalityError, ChronologyDegradationPropagationError) as exc:
        errors.append(str(exc))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"load_error:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-13-cic-default-caps",
        "name": "gp06_cic01_default_policy_caps",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_interval_closure_runtime_schema_version": (
                PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cic02_half_open_closure_oracle_static() -> dict[str, Any]:
    """Static — two half-open causal influence slices meet at UTC boundary."""
    errors: list[str] = []
    policy = {
        "caps": {
            "max_causal_hops_default": 12,
            "max_causal_hops_degraded": 4,
            "max_transitive_closure_hops": 0,
            "max_breakpoints_per_chain": 64,
            "max_tcre_edges_per_chain": 4096,
        },
        "degradation_thresholds": {"emit_cd_chron_on_any_chronology_non_strict": False},
    }
    intervals = [
        {
            "tcre_causal_edge_id": "edge_b",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "lineage": [{"anchor_id": "a1"}],
        },
        {
            "tcre_causal_edge_id": "edge_a",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-02T00:00:00Z",
            "end_iso": "2025-01-03T00:00:00Z",
            "lineage": [{"anchor_id": "a1"}],
        },
    ]
    try:
        out = validate_causal_influence_half_open_chain_v1(
            intervals,
            chronology_legality_class="chronology_strict",
            policy=policy,
        )
        if out["sorted_tcre_causal_edge_ids"] != ["edge_a", "edge_b"]:
            errors.append(f"sorted_ids_mismatch:{out['sorted_tcre_causal_edge_ids']}")
    except CausalIntervalClosureError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-13-cic-half-open-oracle",
        "name": "gp06_cic02_half_open_closure_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_interval_closure_runtime_schema_version": (
                PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_cic03_hop_cap_exceeded_static() -> dict[str, Any]:
    """Static — hop cap rejects long chains."""
    errors: list[str] = []
    policy = {
        "caps": {
            "max_causal_hops_default": 2,
            "max_causal_hops_degraded": 2,
            "max_transitive_closure_hops": 0,
            "max_breakpoints_per_chain": 64,
            "max_tcre_edges_per_chain": 4096,
        },
        "degradation_thresholds": {"emit_cd_chron_on_any_chronology_non_strict": False},
    }
    intervals = [
        {
            "tcre_causal_edge_id": f"e{i}",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": f"2025-01-{i+1:02d}T00:00:00Z",
            "end_iso": f"2025-01-{i+2:02d}T00:00:00Z",
            "lineage": [{"anchor_id": "a1"}],
        }
        for i in range(3)
    ]
    try:
        validate_causal_influence_half_open_chain_v1(
            intervals,
            chronology_legality_class="chronology_strict",
            policy=policy,
        )
        errors.append("expected_hop_cap_failure")
    except CausalIntervalClosureError as exc:
        if "hop cap exceeded" not in str(exc):
            errors.append(f"wrong_error:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-13-cic-hop-cap",
        "name": "gp06_cic03_hop_cap_exceeded",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_interval_closure_runtime_schema_version": (
                PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
