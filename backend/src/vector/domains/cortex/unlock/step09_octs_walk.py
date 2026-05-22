"""War-room step 9 — OCTS execution continuity (alive criterion A5)."""

from __future__ import annotations

from typing import Any

A5_WEDGE_MIN_COMPLETED_WALKS = 1
A5_WEDGE_MIN_AUTHORITATIVE_HOPS = 1


def pick_start_node_ids_on_authoritative_edges_v1(
    projection_inner: dict[str, Any],
    *,
    limit: int = 8,
) -> list[str]:
    """Prefer org entities incident to authoritative meaning links (GRAPH wedge)."""
    edges = projection_inner.get("edges")
    if not isinstance(edges, list):
        return []
    incident: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("link_authority") or "") != "authoritative":
            continue
        for key in ("source_entity_id", "target_entity_id"):
            nid = str(edge.get(key) or "").strip()
            if nid:
                incident.add(nid)
    return sorted(incident)[: max(1, int(limit))]


def authoritative_hops_on_walk_payload_v1(
    walk_payload: dict[str, Any] | None,
    *,
    projection_edges: list[dict[str, Any]] | None = None,
) -> int:
    """Count authoritative link hops on a completed walk (path fingerprints ∩ auth edges)."""
    if not walk_payload:
        return 0
    wr = walk_payload.get("walk_result") or {}
    hb = wr.get("hash_body") or {}
    fps = list(hb.get("path_edge_fingerprints_ordered") or [])
    if not fps:
        telem = walk_payload.get("telemetry") or {}
        hops = int(telem.get("hops_emitted") or 0)
        return hops if hops > 0 else 0

    if not projection_edges:
        return len(fps)

    from vector.domains.cortex.traversal import compute_edge_fingerprint_v1

    auth_fps: set[str] = set()
    for edge in projection_edges:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("link_authority") or "") != "authoritative":
            continue
        auth_fps.add(compute_edge_fingerprint_v1(edge))
    return sum(1 for fp in fps if fp in auth_fps)


def evaluate_a5_octs_execution_continuity_v1(
    *,
    completed_walks: int,
    walks_with_authoritative_hop: int,
    walks_persisted: int | None = None,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A5 after GRAPH/traversal wedge."""
    completed = int(completed_walks)
    with_hop = int(walks_with_authoritative_hop)
    persisted = int(walks_persisted) if walks_persisted is not None else None

    if completed >= A5_WEDGE_MIN_COMPLETED_WALKS and with_hop >= A5_WEDGE_MIN_AUTHORITATIVE_HOPS:
        if persisted is not None and persisted > 0:
            return (
                True,
                f"completed_walks={completed}:authoritative_hop_walks={with_hop}:walks_persisted={persisted}",
            )
        return True, f"completed_walks={completed}:authoritative_hop_walks={with_hop}"

    if completed >= A5_WEDGE_MIN_COMPLETED_WALKS and with_hop <= 0:
        return (
            False,
            f"completed_walks={completed} but authoritative_hop_walks={with_hop}",
        )
    if persisted is not None and persisted > 0 and with_hop > 0:
        return True, f"walks_persisted={persisted}:authoritative_hop_walks={with_hop}"
    return (
        False,
        f"completed_walks={completed} below wedge minimum {A5_WEDGE_MIN_COMPLETED_WALKS}",
    )
