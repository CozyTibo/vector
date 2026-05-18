"""Production substrate traversal — reference walks persisted to durable OCTS store."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final, cast

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.projection_export import build_org_graph_projection_export_document
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
from vector.domains.cortex.traversal.runtime_execution_model import (
    RuntimeExecutionModelError,
    run_reference_frontier_walk_v1,
)
from vector.domains.cortex.traversal.walk_policy import (
    compute_policy_hash_v1,
    validate_walk_policy_for_request_v1,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    compute_walk_result_hash_v1,
    validate_walk_result_hash_body_contract_v1,
)

SUBSTRATE_TRAVERSAL_MAX_STARTS_V1: Final[int] = 8
SUBSTRATE_WALK_POLICY_V1: Final[dict[str, Any]] = {
    "max_hops": 8,
    "max_frontier": 64,
    "max_edges_visited": 500,
    "max_wall_ms": 30_000,
    "hop_class_allowlist": ["org.handle_links_canonical"],
    "tie_break": ["fingerprint", "org_link_id"],
    "respect_validity": True,
    "policy_version": 1,
}


def _pick_start_node_ids_v1(projection_inner: Mapping[str, Any], *, limit: int) -> list[str]:
    nodes = projection_inner.get("nodes")
    if not isinstance(nodes, list):
        return []
    ids: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if str(node.get("kind")) != "org_entity":
            continue
        nid = str(node.get("id") or "").strip()
        if nid:
            ids.append(nid)
        if len(ids) >= limit:
            break
    return ids


def _edge_fingerprints_for_visit_order_v1(
    projection_inner: Mapping[str, Any],
    visited_link_ids: list[str],
) -> list[str]:
    from vector.domains.cortex.traversal import compute_edge_fingerprint_v1

    edges = projection_inner.get("edges")
    if not isinstance(edges, list):
        return []
    by_lid: dict[str, Mapping[str, Any]] = {}
    for edge in edges:
        if isinstance(edge, dict):
            lid = str(edge.get("link_row_stable_id") or edge.get("id") or "")
            if lid:
                by_lid[lid] = edge
    fps: list[str] = []
    for lid in visited_link_ids:
        edge = by_lid.get(lid)
        if edge is not None:
            fps.append(compute_edge_fingerprint_v1(edge))
    return fps


def build_reference_walk_payload_v1(
    request: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
    projection_inner: Mapping[str, Any],
    start_node_id: str,
) -> dict[str, Any]:
    """Build completed walk payload from reference frontier walk (durable replay substrate)."""
    policy = dict(request["walk_policy"])
    strategy = str(request["walk_execution_strategy"])
    policy_hash = compute_policy_hash_v1(policy, walk_execution_strategy=strategy)
    ta = dict(request["temporal_anchor"])
    ref = run_reference_frontier_walk_v1(
        projection_inner,
        start_node_id=start_node_id,
        target_node_id=None,
        max_hops=int(policy["max_hops"]),
        max_frontier=int(policy["max_frontier"]),
        max_edges_visited=int(policy["max_edges_visited"]),
        detect_cycles=True,
        stop_on_cycle=True,
        t_as_of_unix_ns=None,
    )
    visited = list(ref.get("visited_link_row_stable_ids_in_order") or [])
    path_fps = _edge_fingerprints_for_visit_order_v1(projection_inner, visited)
    hash_body: dict[str, Any] = {
        "octs_schema_version": 1,
        "temporal_anchor": ta,
        "policy_hash": policy_hash,
        "start_node_ids": [start_node_id],
        "termination_reason": str(ref.get("termination_reason") or "empty_frontier"),
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": path_fps,
    }
    validate_walk_result_hash_body_contract_v1(hash_body)
    walk_hash = compute_walk_result_hash_v1(hash_body)
    return {
        "walk_result": {"hash_body": hash_body, "walk_result_hash": walk_hash},
        "telemetry": {
            "wall_ms": 0,
            "worker_hostname": "substrate_pipeline",
            "engine_build_id": "substrate_reference_walk_v1",
            "hops_emitted": int(ref.get("hops_emitted") or 0),
        },
    }


def run_substrate_traversal_materialization_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    graph_projection_stable_hash: str | None = None,
    max_starts: int = SUBSTRATE_TRAVERSAL_MAX_STARTS_V1,
) -> dict[str, Any]:
    """Execute bounded reference walks and persist to ``CortexOctsDurableWalkRecord``."""
    export_doc = build_org_graph_projection_export_document(session, tenant_id=tenant_id)
    inner = export_doc.get("projection")
    if not isinstance(inner, dict):
        return {"ok": False, "reason": "missing_projection", "walks_persisted": 0}

    stable_hash = graph_projection_stable_hash or str(export_doc.get("stable_hash_sha256") or "")
    export_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"org-graph-export:{tenant_id}:{stable_hash}")
    projection_hash = f"sha256:{stable_hash}" if stable_hash and not stable_hash.startswith("sha256:") else stable_hash
    temporal_anchor = {
        "tenant_id": str(tenant_id),
        "export_id": str(export_id),
        "export_sequence": 0,
        "projection_content_hash": projection_hash,
        "snapshot_unix_ns": {"unix_ns": 0},
        "graph_as_of_unix_ns": {"unix_ns": 0},
    }

    starts = _pick_start_node_ids_v1(inner, limit=max(1, int(max_starts)))
    if not starts:
        return {"ok": True, "reason": "no_start_nodes", "walks_persisted": 0, "walk_ids": []}

    store = resolve_octs_walk_store_v1(session)
    walk_ids: list[str] = []
    skipped = 0
    persisted_new = 0
    for start in starts:
        idem = hash_reasoning_canonical_json_sha256_v1(
            {
                "tenant_id": str(tenant_id),
                "projection_hash": stable_hash,
                "start_node_id": start,
                "purpose": "substrate_traversal_v1",
            }
        )[:64]
        existing = store.lookup_idempotency(tenant_id, idem)
        if existing is not None:
            walk_ids.append(str(existing))
            skipped += 1
            continue
        request_body = {
            "temporal_anchor": temporal_anchor,
            "walk_policy": dict(SUBSTRATE_WALK_POLICY_V1),
            "start_node_ids": [start],
            "walk_execution_strategy": "ONLINE_OBSERVED",
            "exploration_mode": False,
        }
        try:
            validate_walk_policy_for_request_v1(
                cast(Mapping[str, Any], request_body["walk_policy"]),
                walk_execution_strategy="ONLINE_OBSERVED",
                exploration_mode=False,
                enforce_sync_caps=False,
            )
            payload = build_reference_walk_payload_v1(
                request_body,
                tenant_id=tenant_id,
                projection_inner=cast(Mapping[str, Any], inner),
                start_node_id=start,
            )
        except (RuntimeExecutionModelError, ValueError) as exc:
            skipped += 1
            continue
        walk_id = uuid.uuid4()
        store.insert_completed_sync(
            tenant_id=tenant_id,
            walk_id=walk_id,
            request_body=request_body,
            walk_payload=payload,
            idempotency_key=idem,
        )
        walk_ids.append(str(walk_id))
        persisted_new += 1

    session.flush()
    primary_walk_id = walk_ids[0] if walk_ids else None
    return {
        "ok": True,
        "walks_persisted": persisted_new,
        "walk_ids": walk_ids,
        "primary_octs_walk_id": primary_walk_id,
        "skipped_idempotent": skipped,
        "graph_projection_stable_hash_sha256": stable_hash,
    }
