"""Deterministic execution continuity topology."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.control_plane import build_identity_control_plane


def build_continuity_topology_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    cp = build_identity_control_plane(session, tenant_id=tenant_id)
    cards = cp.get("cards") or {}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    handles = int((cards.get("org_handles") or {}).get("value") or 0)
    if handles:
        nodes.append({"node_id": "identity_substrate", "kind": "identity", "count": handles})
    pending = int((cards.get("pending_merges") or {}).get("value") or 0)
    if pending:
        nodes.append({"node_id": "continuity_pending", "kind": "continuity_unverified", "count": pending})
        edges.append(
            {
                "from": "identity_substrate",
                "to": "continuity_pending",
                "edge_kind": "continuity_frontier",
            }
        )
    replay_drift = int((cards.get("replay_drift") or {}).get("value") or 0)
    if replay_drift:
        nodes.append({"node_id": "replay_conflict", "kind": "replay_conflicted", "count": replay_drift})
        edges.append(
            {
                "from": "identity_substrate",
                "to": "replay_conflict",
                "edge_kind": "replay_conflicted_continuity",
            }
        )
    return {
        "tenant_id": str(tenant_id),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "continuity_posture": "replay_unsafe" if replay_drift else ("partial" if pending else "stable"),
    }
