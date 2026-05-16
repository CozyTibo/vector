"""Build deterministic lineage chain toward a retrieval artifact."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import query_lineage_edges_v1
from vector.domains.cortex.lineage.lineage_receipt_projection import lineage_receipt_digest_v1


def build_artifact_lineage_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    terminal_artifact_kind: str,
    terminal_artifact_ref: str,
    max_hops: int = 32,
) -> dict[str, Any]:
    edges = query_lineage_edges_v1(
        session,
        tenant_id=tenant_id,
        artifact_kind=terminal_artifact_kind,
        artifact_ref=terminal_artifact_ref,
    )
    nodes: dict[str, dict[str, Any]] = {
        f"{terminal_artifact_kind}:{terminal_artifact_ref}": {
            "artifact_kind": terminal_artifact_kind,
            "artifact_ref": terminal_artifact_ref,
        }
    }
    chain_edges: list[dict[str, Any]] = []
    frontier = [(terminal_artifact_kind, terminal_artifact_ref)]
    hops = 0
    while frontier and hops < max_hops:
        next_frontier: list[tuple[str, str]] = []
        for kind, ref in frontier:
            for e in edges:
                if e.to_artifact_kind == kind and e.to_artifact_ref == ref:
                    fk = f"{e.from_artifact_kind}:{e.from_artifact_ref}"
                    tk = f"{e.to_artifact_kind}:{e.to_artifact_ref}"
                    nodes[fk] = {
                        "artifact_kind": e.from_artifact_kind,
                        "artifact_ref": e.from_artifact_ref,
                    }
                    chain_edges.append(
                        {
                            "lineage_edge_id": e.lineage_edge_id,
                            "from": fk,
                            "to": tk,
                            "edge_kind": e.edge_kind,
                            "degradation_propagation": dict(e.degradation_propagation or {}),
                            "omission_summary": dict(e.omission_summary or {}),
                            "replay_identity": e.replay_identity,
                        }
                    )
                    next_frontier.append((e.from_artifact_kind, e.from_artifact_ref))
        frontier = next_frontier
        hops += 1
    ordered_nodes = [nodes[k] for k in sorted(nodes)]
    body = {
        "tenant_id": str(tenant_id),
        "terminal": {"kind": terminal_artifact_kind, "ref": terminal_artifact_ref},
        "nodes": ordered_nodes,
        "edges": sorted(chain_edges, key=lambda x: x["lineage_edge_id"]),
    }
    body["lineage_chain_digest"] = lineage_receipt_digest_v1(body)
    return body
