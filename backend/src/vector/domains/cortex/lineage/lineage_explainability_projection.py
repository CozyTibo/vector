"""Operator explainability for lineage chains."""

from __future__ import annotations

from typing import Any


def build_lineage_explainability_v1(chain: dict[str, Any]) -> dict[str, Any]:
    edges = chain.get("edges") or []
    omissions: list[dict[str, Any]] = []
    degradations: list[dict[str, Any]] = []
    for e in edges:
        om = e.get("omission_summary") or {}
        if om:
            omissions.append({"edge": e.get("lineage_edge_id"), "omission": om})
        deg = e.get("degradation_propagation") or {}
        if deg:
            degradations.append({"edge": e.get("lineage_edge_id"), "propagation": deg})
    return {
        "lineage_chain_digest": chain.get("lineage_chain_digest"),
        "node_count": len(chain.get("nodes") or []),
        "edge_count": len(edges),
        "omission_points": omissions,
        "degradation_path": degradations,
        "replay_identity_lineage": [
            e.get("replay_identity") for e in edges if e.get("replay_identity")
        ],
    }
