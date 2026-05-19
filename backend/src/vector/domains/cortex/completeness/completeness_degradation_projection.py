"""Deterministic downstream degradation propagation from stage omissions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

_PROPAGATION_RULES_V1: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("ingestion", "canonical", "ingestion_gap_detected", "canonical_degraded_from_ingestion_gap"),
    ("ingestion", "traversal", "partial_api_failure", "traversal_degraded_from_ingestion_failure"),
    ("canonical", "identity", "parse_failure", "identity_unresolved_from_canonical_parse_failure"),
    ("canonical", "tcre", "canonical_backlog_unmaterialized", "tcre_skipped_from_unmaterialized_raw"),
    ("canonical", "tcre", "reconstruction_coverage_gap", "tcre_bounded_from_canonical_coverage_gap"),
    ("identity", "graph", "orphan_identity_cluster", "graph_orphan_from_identity_fragmentation"),
    ("graph", "traversal", "orphan_artifacts", "traversal_blocked_from_disconnected_graph"),
    ("graph", "traversal", "pending_link_candidates", "traversal_blocked_from_unpromoted_links"),
    (
        "graph",
        "traversal",
        "orphan_disconnected_component",
        "traversal_blocked_ret_skip_graph_disconnected",
    ),
    (
        "graph",
        "traversal",
        "orphan_awaiting_promotion",
        "traversal_blocked_awaiting_link_promotion",
    ),
    (
        "graph",
        "traversal",
        "orphan_identity_unresolved",
        "traversal_blocked_identity_unresolved",
    ),
    (
        "graph",
        "retrieval",
        "orphan_disconnected_component",
        "retrieval_degraded_graph_disconnected",
    ),
    (
        "graph",
        "retrieval",
        "orphan_awaiting_promotion",
        "retrieval_degraded_graph_promotion_backlog",
    ),
    ("identity", "tcre", "replay_conflicted_identity", "tcre_chronology_impact_from_identity_replay"),
    ("traversal", "tcre", "traversal_replay_unverified", "tcre_unbound_from_traversal_unverified"),
    ("traversal", "tcre", "traversal_frontier_cutoff", "tcre_bounded_from_traversal_frontier"),
    (
        "tcre",
        "retrieval",
        "reconstruction_not_yet_run",
        "retrieval_starved_from_tcre_not_run",
    ),
    (
        "tcre",
        "retrieval",
        "reconstruction_coverage_gap",
        "retrieval_degraded_from_tcre_coverage_gap",
    ),
    (
        "tcre",
        "synthesis",
        "reconstruction_not_yet_run",
        "synthesis_starved_from_tcre_not_run",
    ),
    (
        "retrieval",
        "synthesis",
        "retrieval_index_never_built",
        "synthesis_degraded_from_retrieval_index_gap",
    ),
    (
        "retrieval",
        "synthesis",
        "retrieval_index_stale",
        "synthesis_degraded_from_stale_retrieval_index",
    ),
    (
        "retrieval",
        "synthesis",
        "retrieval_upstream_tcre_gap",
        "synthesis_degraded_from_retrieval_upstream_gap",
    ),
    (
        "retrieval",
        "synthesis",
        "retrieval_operational_starvation",
        "synthesis_starved_from_retrieval_operational_starvation",
    ),
    (
        "retrieval",
        "synthesis",
        "retrieval_index_empty",
        "synthesis_starved_from_retrieval_index_empty",
    ),
    (
        "synthesis",
        "synthesis",
        "synthesis_operational_starvation",
        "synthesis_operational_starvation_self_block",
    ),
)


def build_degradation_propagation_chain_v1(
    stages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Emit visible propagation edges when upstream omission_classes are non-zero."""
    by_id = {str(s.get("stage_id")): s for s in stages}
    chain: list[dict[str, Any]] = []
    for from_id, to_id, trigger_class, consequence in _PROPAGATION_RULES_V1:
        upstream = by_id.get(from_id) or {}
        omissions = upstream.get("omission_classes") or {}
        if not isinstance(omissions, dict):
            continue
        count = int(omissions.get(trigger_class) or 0)
        if count <= 0:
            continue
        chain.append(
            {
                "from_stage": from_id,
                "to_stage": to_id,
                "triggering_omission_class": trigger_class,
                "trigger_count": count,
                "propagation_consequence": consequence,
                "explanation_summary": (
                    f"{from_id} omission {trigger_class} (count={count}) "
                    f"propagates to {to_id} as {consequence}."
                ),
            }
        )
    return chain


def build_completeness_degradation_envelope_v1(
    stages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    chain = build_degradation_propagation_chain_v1(stages)
    body = {"propagation_chain": chain, "propagation_count": len(chain)}
    body["envelope_digest"] = hash_reasoning_canonical_json_sha256_v1(body)
    return body
