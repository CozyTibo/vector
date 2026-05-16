"""RUNTIME-02 — ordered causal chain timeline projection."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

TCRE_OPERATOR_CHAIN_TIMELINE_SCHEMA_VERSION: Final[int] = 1


def build_chain_timeline_v1(
    *,
    chain: Mapping[str, Any] | None,
    edge_explanations: Sequence[Mapping[str, Any]],
    chronology_by_mat_id: Mapping[str, Mapping[str, Any]],
    tcre_policy_bundle_digest: str,
    replay_posture: str,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for i, edge in enumerate(edge_explanations):
        from_id = str(edge.get("from_materialization_id") or "")
        to_id = str(edge.get("to_materialization_id") or "")
        from_chr = chronology_by_mat_id.get(from_id) or {}
        to_chr = chronology_by_mat_id.get(to_id) or {}
        steps.append(
            {
                "step_index": i,
                "tcre_causal_edge_id": edge.get("tcre_causal_edge_id"),
                "source_materialization_id": from_id,
                "target_materialization_id": to_id,
                "edge_kind": edge.get("tcre_causal_edge_kind"),
                "derivation_rule_label": edge.get("derivation_rule_label"),
                "source_chronology_legality_class": from_chr.get("chronology_legality_class"),
                "target_chronology_legality_class": to_chr.get("chronology_legality_class"),
                "source_replay_posture": from_chr.get("replay_posture", replay_posture),
                "target_replay_posture": to_chr.get("replay_posture", replay_posture),
                "causal_legality_class": edge.get("causal_legality_class"),
                "edge_explanation_summary": edge.get("explanation_summary"),
                "continuity_transition": f"{from_id} → {to_id}",
            }
        )
    body = {
        "schema_version": TCRE_OPERATOR_CHAIN_TIMELINE_SCHEMA_VERSION,
        "causal_chain_id": chain.get("causal_chain_id") if chain else None,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "replay_posture": replay_posture,
        "step_count": len(steps),
        "steps": steps,
        "retrieval_chain_ref": (
            f"chain:{chain['causal_chain_id']}" if chain and chain.get("causal_chain_id") else None
        ),
    }
    body["timeline_digest"] = hash_reasoning_canonical_json_sha256_v1(
        {k: v for k, v in body.items() if k != "timeline_digest"}
    )
    return body
