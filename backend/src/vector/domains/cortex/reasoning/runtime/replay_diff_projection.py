"""RUNTIME-02 — deterministic replay twin diff (canonical tuple compare, no fuzzy match)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

TCRE_OPERATOR_REPLAY_DIFF_SCHEMA_VERSION: Final[int] = 1


def _chronology_tuple_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in rows:
        mid = str(r.get("materialization_id") or "")
        out[mid] = str(r.get("receipt_digest") or "")
    return dict(sorted(out.items()))


def _edge_tuple_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in rows:
        eid = str(r.get("tcre_causal_edge_id") or "")
        out[eid] = str(r.get("tcre_causal_edge_id") or "")
    return dict(sorted(out.items()))


def _chain_tuple(chain: Mapping[str, Any] | None) -> tuple[str | None, str | None]:
    if not chain:
        return None, None
    return (
        str(chain.get("causal_chain_id") or "") or None,
        str(chain.get("causal_chain_id") or "") or None,
    )


def build_replay_diff_v1(
    run_a: Mapping[str, Any],
    run_b: Mapping[str, Any],
    *,
    policy_digest_a: str,
    policy_digest_b: str,
) -> dict[str, Any]:
    """Structural diff from two in-memory reconstruction runs."""
    ch_a = _chronology_tuple_map(run_a.get("chronology_rows") or [])
    ch_b = _chronology_tuple_map(run_b.get("chronology_rows") or [])
    ed_a = _edge_tuple_map(run_a.get("edge_rows") or [])
    ed_b = _edge_tuple_map(run_b.get("edge_rows") or [])
    chain_a_id, _ = _chain_tuple(run_a.get("chain"))
    chain_b_id, _ = _chain_tuple(run_b.get("chain"))

    chronology_divergence: list[dict[str, str]] = []
    all_mats = sorted(set(ch_a) | set(ch_b))
    for mid in all_mats:
        da, db = ch_a.get(mid), ch_b.get(mid)
        if da != db:
            chronology_divergence.append(
                {"materialization_id": mid, "digest_a": da or "", "digest_b": db or ""}
            )

    edge_divergence: list[dict[str, str | bool]] = []
    all_edges = sorted(set(ed_a) | set(ed_b))
    for eid in all_edges:
        if ed_a.get(eid) != ed_b.get(eid):
            edge_divergence.append({"edge_id": eid, "present_a": eid in ed_a, "present_b": eid in ed_b})

    chain_divergence = chain_a_id != chain_b_id
    digest_a = str(run_a.get("aggregate_digest") or "")
    digest_b = str(run_b.get("aggregate_digest") or "")
    policy_mismatch = policy_digest_a != policy_digest_b
    count_a = len(run_a.get("chronology_rows") or []) + len(run_a.get("edge_rows") or [])
    count_b = len(run_b.get("chronology_rows") or []) + len(run_b.get("edge_rows") or [])
    artifact_count_mismatch = count_a != count_b

    identical = (
        not chronology_divergence
        and not edge_divergence
        and not chain_divergence
        and digest_a == digest_b
        and not policy_mismatch
        and not artifact_count_mismatch
    )

    body = {
        "schema_version": TCRE_OPERATOR_REPLAY_DIFF_SCHEMA_VERSION,
        "identical": identical,
        "chronology_divergence": chronology_divergence,
        "edge_divergence": edge_divergence,
        "chain_divergence": chain_divergence,
        "chain_id_a": chain_a_id,
        "chain_id_b": chain_b_id,
        "digest_mismatch": digest_a != digest_b,
        "aggregate_digest_a": digest_a,
        "aggregate_digest_b": digest_b,
        "policy_mismatch": policy_mismatch,
        "policy_digest_a": policy_digest_a,
        "policy_digest_b": policy_digest_b,
        "artifact_count_mismatch": artifact_count_mismatch,
        "artifact_count_a": count_a,
        "artifact_count_b": count_b,
        "materialization_count_a": int(run_a.get("materialization_count") or 0),
        "materialization_count_b": int(run_b.get("materialization_count") or 0),
    }
    body["replay_diff_digest"] = hash_reasoning_canonical_json_sha256_v1(
        {k: v for k, v in body.items() if k != "replay_diff_digest"}
    )
    return body
