"""Retrieval-native continuity expansion (deterministic, non-semantic)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.continuity.runtime.continuity_topology_graph import (
    build_continuity_topology_v1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

PHASE07_RETRIEVAL_CONTINUITY_PROJECTION_SCHEMA_VERSION: Final[int] = 1

CONTINUITY_OMISSION_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "continuity_break_unresolved",
        "ownership_transfer_gap",
        "execution_continuity_degraded",
        "dependency_continuity_gap",
        "workstream_continuity_gap",
    }
)


def expand_retrieval_continuity_context_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    row: Any,
    scope: Mapping[str, Any],
) -> dict[str, Any]:
    """Lawful continuity context for retrieval hits (topology + row posture)."""
    topology = build_continuity_topology_v1(session, tenant_id=tenant_id)
    posture = str(getattr(row, "continuity_posture", "unknown") or "unknown")
    segments: list[dict[str, Any]] = []
    if scope.get("causal_chain_id"):
        segments.append(
            {
                "continuity_kind": "execution_continuity",
                "artifact_ref": str(scope["causal_chain_id"]),
            }
        )
    if scope.get("org_entity_id"):
        segments.append(
            {
                "continuity_kind": "ownership_continuity",
                "artifact_ref": str(scope["org_entity_id"]),
            }
        )
    if scope.get("octs_walk_id"):
        segments.append(
            {
                "continuity_kind": "dependency_continuity",
                "artifact_ref": str(scope["octs_walk_id"]),
            }
        )
    replay_posture = "replay_safe" if posture in ("stable", "replay_safe") else "degraded"
    digest = hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "continuity_posture": posture,
            "segment_count": len(segments),
        }
    )
    return {
        "continuity_projection_schema_version": PHASE07_RETRIEVAL_CONTINUITY_PROJECTION_SCHEMA_VERSION,
        "continuity_context": {
            "segments": segments,
            "topology_summary": {
                "node_count": topology.get("node_count"),
                "edge_count": topology.get("edge_count"),
                "continuity_posture": topology.get("continuity_posture"),
            },
        },
        "continuity_replay_posture": replay_posture,
        "continuity_digest": digest,
        "surface_kind": "runtime_backed",
    }
