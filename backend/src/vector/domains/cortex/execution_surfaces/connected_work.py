"""Cross-tool connected work chains within a declared domain."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution_surfaces.omissions import CHAIN_RELATIONSHIP_KINDS
from vector.domains.cortex.graph.relationship_kinds import label_for_kind
from vector.domains.cortex.canon.notion_display_labels import enrich_notion_display_labels
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.graph_relationship import STATUS_ACTIVE, GraphRelationship

_MAX_CHAINS = 12
_MAX_CHAIN_LEN = 6
_MIN_CHAIN_LEN = 2
_MIN_DISTINCT_TYPES = 2


def _entity_node(entity: CanonEntity, *, display_label: str) -> dict[str, Any]:
    return {
        "entity_id": str(entity.id),
        "entity_type": entity.entity_type,
        "connector": entity.connector,
        "display_label": display_label,
        "entity_key": entity.entity_key,
    }


def _load_member_graph(
    session: Session,
    tenant_id: uuid.UUID,
    member_ids: set[uuid.UUID],
) -> tuple[dict[uuid.UUID, list[tuple[uuid.UUID, GraphRelationship]]], dict[uuid.UUID, CanonEntity]]:
    if not member_ids:
        return {}, {}
    rows = list(
        session.scalars(
            select(GraphRelationship).where(
                GraphRelationship.tenant_id == tenant_id,
                GraphRelationship.status == STATUS_ACTIVE,
                GraphRelationship.relationship_kind.in_(tuple(CHAIN_RELATIONSHIP_KINDS)),
                or_(
                    GraphRelationship.from_entity_id.in_(member_ids),
                    GraphRelationship.to_entity_id.in_(member_ids),
                ),
            ),
        ).all(),
    )
    involved: set[uuid.UUID] = set(member_ids)
    for row in rows:
        involved.add(row.from_entity_id)
        involved.add(row.to_entity_id)
    entities = {
        e.id: e
        for e in session.scalars(select(CanonEntity).where(CanonEntity.id.in_(involved))).all()
    }
    labels = enrich_notion_display_labels(session, entities.values())
    adj: dict[uuid.UUID, list[tuple[uuid.UUID, GraphRelationship]]] = defaultdict(list)
    for row in rows:
        if row.from_entity_id not in entities or row.to_entity_id not in entities:
            continue
        adj[row.from_entity_id].append((row.to_entity_id, row))
        adj[row.to_entity_id].append((row.from_entity_id, row))
    return adj, {eid: entities[eid] for eid in entities}


def _chain_score(types: list[str]) -> int:
    return len(set(types))


def _find_chains(
    adj: dict[uuid.UUID, list[tuple[uuid.UUID, GraphRelationship]]],
    entities: dict[uuid.UUID, CanonEntity],
    *,
    seed: uuid.UUID,
) -> list[list[tuple[uuid.UUID, GraphRelationship | None]]]:
    """DFS paths from seed; edge None only for start node."""
    found: list[list[tuple[uuid.UUID, GraphRelationship | None]]] = []
    start_ent = entities.get(seed)
    if start_ent is None:
        return found

    def dfs(
        path_nodes: list[uuid.UUID],
        path_edges: list[GraphRelationship],
        visited_edges: set[uuid.UUID],
    ) -> None:
        if len(path_nodes) >= _MAX_CHAIN_LEN:
            return
        current = path_nodes[-1]
        for neighbor, edge in adj.get(current, []):
            if edge.id in visited_edges:
                continue
            if neighbor in path_nodes:
                continue
            new_nodes = path_nodes + [neighbor]
            new_edges = path_edges + [edge]
            types = [entities[n].entity_type for n in new_nodes if n in entities]
            if len(new_nodes) >= _MIN_CHAIN_LEN and _chain_score(types) >= _MIN_DISTINCT_TYPES:
                seq: list[tuple[uuid.UUID, GraphRelationship | None]] = [(new_nodes[0], None)]
                for i, edge_row in enumerate(new_edges):
                    seq.append((new_nodes[i + 1], edge_row))
                found.append(seq)
            if len(new_nodes) < _MAX_CHAIN_LEN:
                dfs(new_nodes, new_edges, visited_edges | {edge.id})

    dfs([seed], [], set())
    return found


def build_connected_work(
    session: Session,
    tenant_id: uuid.UUID,
    member_ids: set[uuid.UUID],
) -> dict[str, Any]:
    if not member_ids:
        return {
            "chains": [],
            "count": 0,
            "omission": {
                "code": "no_domain_members",
                "message": "No domain members to trace cross-tool chains.",
                "remediation": "Expand declared domain membership (canon seeds, graph Level 1).",
            },
        }

    adj, entities = _load_member_graph(session, tenant_id, member_ids)
    if not adj:
        return {
            "chains": [],
            "count": 0,
            "omission": {
                "code": "no_graph_relationships",
                "message": "No graph relationships found among domain members.",
                "remediation": "Improve graph projection — add references and cross-tool extractors.",
            },
        }

    labels = enrich_notion_display_labels(session, entities.values())
    all_chains: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()

    # Prefer document / work_item / pull_request seeds
    seed_order = sorted(
        member_ids,
        key=lambda eid: (
            0
            if entities.get(eid) and entities[eid].entity_type in ("document", "work_item", "pull_request")
            else 1,
            str(eid),
        ),
    )
    for seed in seed_order:
        for path in _find_chains(adj, entities, seed=seed):
            sig = "->".join(str(n) for n, _ in path)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            hops: list[dict[str, Any]] = []
            for idx, (node_id, edge) in enumerate(path):
                ent = entities[node_id]
                hop: dict[str, Any] = {
                    "entity": _entity_node(ent, display_label=labels.get(ent.id, ent.display_label)),
                }
                if edge is not None:
                    hop["relationship"] = {
                        "id": str(edge.id),
                        "relationship_kind": edge.relationship_kind,
                        "relationship_kind_label": label_for_kind(edge.relationship_kind),
                        "confidence": edge.confidence,
                        "extractor_rule": edge.extractor_rule,
                        "evidence_kind": edge.evidence_kind,
                        "evidence_ref": edge.evidence_ref,
                        "observed_at": edge.observed_at.isoformat(),
                        "source": edge.extractor_rule.split(".", 1)[0]
                        if "." in edge.extractor_rule
                        else "graph",
                    }
                hops.append(hop)
            all_chains.append({"hops": hops, "hop_count": len(hops)})
            if len(all_chains) >= _MAX_CHAINS:
                break
        if len(all_chains) >= _MAX_CHAINS:
            break

    # Sort: longer chains first, then more entity types
    def sort_key(c: dict[str, Any]) -> tuple[int, int]:
        types = {h["entity"]["entity_type"] for h in c["hops"]}
        return (len(c["hops"]), len(types))

    all_chains.sort(key=sort_key, reverse=True)

    if not all_chains:
        return {
            "chains": [],
            "count": 0,
            "omission": {
                "code": "insufficient_cross_tool_links",
                "message": "Graph edges exist but no multi-type chains could be formed within this domain.",
                "remediation": "Improve references extraction and domain graph expansion.",
            },
        }

    return {"chains": all_chains[:_MAX_CHAINS], "count": len(all_chains[:_MAX_CHAINS]), "omission": None}
