"""Topology-aware materialization planning (DAG stages, quarantine, external parent gates)."""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def classify_orphan_missing_ref(
    missing_parent_ref: str,
    *,
    child_resource_type: str | None = None,
) -> str:
    """Deterministic orphan class from dependency key prefix (no semantic healing)."""
    ref = str(missing_parent_ref or "").strip()
    crt = str(child_resource_type or "").strip()
    if ref.startswith("calls.meeting:") and crt in {"calls.transcript", "calls.transcript_segment"}:
        return "missing_transcript"
    if ref.startswith("calls.meeting:") and crt == "calls.recording":
        return "missing_parent"
    if ref.startswith("slack.message:"):
        return "missing_root_thread"
    if ref.startswith("github.workflow_run:"):
        return "missing_workflow"
    if ref.startswith("github.deployment:"):
        return "missing_deployment"
    if ref.startswith("notion.database:") or ref.startswith("notion.block:"):
        return "missing_parent"
    return "missing_parent"


def _has_materialization(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
) -> bool:
    row = db.scalars(
        select(CortexCanonicalTransformMaterialization).where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            CortexCanonicalTransformMaterialization.raw_record_id == int(raw_record_id),
        )
    ).first()
    return row is not None


def build_materialization_stage_plan(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    rows: list[RawIngestionRecord],
    temporal_key_by_id: dict[int, str],
) -> dict[str, Any]:
    """Partition routable raw rows into topological stages with explicit quarantine/deferred queues.

    - **Quarantine A**: topology orphan (declared dependency key not resolved inside this row set).
    - **Quarantine B**: parent raw row exists in tenant DB but is outside this row set and not yet
      materialized under ``bundle_id`` (dependency blocker; no fuzzy fix).
    """
    scope_ids = {int(r.id) for r in rows}
    if not scope_ids:
        return {
            "topology_schema_version": 1,
            "stages": [],
            "quarantine": [],
            "deferred_dependency_queue": [],
            "topology_stage_count": 0,
            "stage_sizes": [],
            "stage_dependency_wait_count": 0,
            "deferred_child_count": 0,
            "replay_blocker_count": 0,
            "cycle_detected": False,
            "dependency_edge_count": 0,
        }

    topo = build_replay_dependency_topology(rows, temporal_key_by_id=temporal_key_by_id)
    edges = [
        (int(e["parent_raw_record_id"]), int(e["child_raw_record_id"]))
        for e in (topo.get("dependency_edges") or [])
        if isinstance(e, dict)
    ]
    orphan_refs = [o for o in (topo.get("orphan_refs") or []) if isinstance(o, dict)]
    rid_to_rt = {int(r.id): str(r.resource_type) for r in rows}
    quarantine: list[dict[str, Any]] = []
    for o in orphan_refs:
        ref = str(o.get("missing_parent_ref") or "")
        rid = int(o.get("raw_record_id") or 0)
        crt = rid_to_rt.get(rid) or str(o.get("resource_type") or "")
        quarantine.append(
            {
                "raw_record_id": rid,
                "resource_type": crt or o.get("resource_type"),
                "missing_parent_ref": ref,
                "orphan_class": classify_orphan_missing_ref(ref, child_resource_type=crt),
                "queue": "topology_orphan",
                "permanent": False,
            }
        )

    topo_orphan_children = {int(o.get("raw_record_id") or 0) for o in orphan_refs}
    active = scope_ids - topo_orphan_children

    deferred: list[dict[str, Any]] = []
    blocked_children: set[int] = set()
    external_unmaterialized = 0
    for p, c in edges:
        if c not in active:
            continue
        if p not in scope_ids:
            if not _has_materialization(db, tenant_id=tenant_id, bundle_id=bundle_id, raw_record_id=p):
                blocked_children.add(c)
                external_unmaterialized += 1
                deferred.append(
                    {
                        "raw_record_id": c,
                        "parent_raw_record_id": p,
                        "orphan_class": "missing_parent",
                        "queue": "external_parent_unmaterialized",
                        "permanent": False,
                    }
                )

    materializable = set(active) - blocked_children
    internal_edges = [(p, c) for p, c in edges if p in materializable and c in materializable]

    incoming: dict[int, int] = defaultdict(int)
    outgoing: dict[int, list[int]] = defaultdict(list)
    for rid in materializable:
        incoming.setdefault(rid, 0)
    for p, c in internal_edges:
        outgoing[p].append(c)
        incoming[c] += 1

    stages: list[list[int]] = []
    frontier = sorted([rid for rid in materializable if incoming[rid] == 0], key=lambda x: temporal_key_by_id.get(x, ""))
    processed: set[int] = set()
    while frontier:
        stage = list(frontier)
        stages.append(stage)
        processed.update(stage)
        next_frontier: list[int] = []
        for cur in stage:
            for nxt in sorted(outgoing.get(cur, []), key=lambda x: temporal_key_by_id.get(x, "")):
                incoming[nxt] -= 1
                if incoming[nxt] == 0:
                    next_frontier.append(nxt)
        frontier = sorted(set(next_frontier), key=lambda x: temporal_key_by_id.get(x, ""))

    leftover = sorted(materializable - processed, key=lambda x: temporal_key_by_id.get(x, ""))
    cycle_extra = bool(leftover)
    if leftover:
        stages.append(leftover)

    stage_sizes = [len(s) for s in stages]
    return {
        "topology_schema_version": 1,
        "stages": stages,
        "quarantine": quarantine,
        "deferred_dependency_queue": deferred,
        "topology_stage_count": len(stages),
        "stage_sizes": stage_sizes,
        "stage_dependency_wait_count": int(external_unmaterialized),
        "deferred_child_count": len(blocked_children),
        "replay_blocker_count": len(quarantine) + len(blocked_children),
        "cycle_detected": bool(topo.get("cycle_detected")) or cycle_extra,
        "dependency_edge_count": len(edges),
        "ordered_scope_ids": [rid for stage in stages for rid in stage],
    }
