"""RUNTIME-03 — replay diff from persisted job artifacts (canonical tuple compare)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vector.domains.cortex.reasoning.runtime.replay_diff_projection import build_replay_diff_v1


def _rows_from_artifacts(
    artifacts: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None, dict[str, Any] | None]:
    chronology: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    chain: dict[str, Any] | None = None
    octs: dict[str, Any] | None = None
    for art in artifacts:
        kind = str(art.get("artifact_kind") or "")
        key = str(art.get("artifact_key") or "")
        digest = str(art.get("artifact_digest") or "")
        body = dict(art.get("body_json") or {})
        if kind == "chronology_receipt":
            chronology.append(
                {
                    "materialization_id": key,
                    "receipt_digest": digest,
                }
            )
        elif kind == "causal_edge":
            edges.append({"tcre_causal_edge_id": key})
        elif kind == "causal_chain":
            chain = {"causal_chain_id": key}
        elif kind == "octs_binding":
            octs = body
    chronology.sort(key=lambda r: r["materialization_id"])
    edges.sort(key=lambda r: r["tcre_causal_edge_id"])
    return chronology, edges, chain, octs


def build_persisted_replay_diff_v1(
    artifacts_a: Sequence[Mapping[str, Any]],
    artifacts_b: Sequence[Mapping[str, Any]],
    *,
    policy_digest_a: str,
    policy_digest_b: str,
) -> dict[str, Any]:
    ch_a, ed_a, chain_a, octs_a = _rows_from_artifacts(artifacts_a)
    ch_b, ed_b, chain_b, octs_b = _rows_from_artifacts(artifacts_b)
    run_a = {
        "chronology_rows": ch_a,
        "edge_rows": ed_a,
        "chain": chain_a,
        "aggregate_digest": "",
        "materialization_count": len(ch_a),
    }
    run_b = {
        "chronology_rows": ch_b,
        "edge_rows": ed_b,
        "chain": chain_b,
        "aggregate_digest": "",
        "materialization_count": len(ch_b),
    }
    diff = build_replay_diff_v1(run_a, run_b, policy_digest_a=policy_digest_a, policy_digest_b=policy_digest_b)
    octs_drift = False
    if octs_a and octs_b:
        octs_drift = octs_a.get("ingestion_replay_identity") != octs_b.get("ingestion_replay_identity")
    diff["octs_replay_identity_drift"] = octs_drift
    if octs_drift:
        diff["identical"] = False
    return diff


def build_replay_divergence_receipt_v1(
    *,
    replay_diff: Mapping[str, Any],
    source_job_id: str,
    twin_job_id: str,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any]:
    """Persisted divergence receipt when replay equivalence fails."""
    divergence_class = "replay_equivalence_mismatch"
    if replay_diff.get("octs_replay_identity_drift"):
        divergence_class = "traversal_replay_identity_drift"
    elif replay_diff.get("chronology_divergence"):
        divergence_class = "chronology_receipt_mismatch"
    elif replay_diff.get("edge_divergence"):
        divergence_class = "causal_edge_mismatch"
    elif replay_diff.get("chain_divergence"):
        divergence_class = "causal_chain_mismatch"
    body = {
        "receipt_type": "reasoning_replay_divergence_receipt",
        "divergence_class": divergence_class,
        "source_job_id": source_job_id,
        "twin_job_id": twin_job_id,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "replay_diff": dict(replay_diff),
    }
    from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
        hash_reasoning_canonical_json_sha256_v1,
    )

    return {"receipt_body": body, "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body)}
