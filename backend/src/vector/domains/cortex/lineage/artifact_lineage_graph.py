"""Deterministic artifact lineage graph edges."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_artifact_lineage_edge import CortexArtifactLineageEdge

LINEAGE_ARTIFACT_KINDS_V1: tuple[str, ...] = (
    "raw_event",
    "canonical_artifact",
    "identity_continuity",
    "graph_edge",
    "octs_traversal",
    "chronology_legality",
    "tcre_chain",
    "retrieval_index",
    "retrieval_result",
)


def lineage_edge_id_v1(
    *,
    from_kind: str,
    from_ref: str,
    to_kind: str,
    to_ref: str,
    edge_kind: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "from_kind": from_kind,
            "from_ref": from_ref,
            "to_kind": to_kind,
            "to_ref": to_ref,
            "edge_kind": edge_kind,
        }
    )[:32]


def persist_lineage_edge_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    from_artifact_kind: str,
    from_artifact_ref: str,
    to_artifact_kind: str,
    to_artifact_ref: str,
    edge_kind: str,
    replay_identity: str | None = None,
    degradation_propagation: dict[str, Any] | None = None,
    omission_summary: dict[str, Any] | None = None,
) -> CortexArtifactLineageEdge:
    eid = lineage_edge_id_v1(
        from_kind=from_artifact_kind,
        from_ref=from_artifact_ref,
        to_kind=to_artifact_kind,
        to_ref=to_artifact_ref,
        edge_kind=edge_kind,
    )
    existing = session.scalar(
        select(CortexArtifactLineageEdge).where(
            CortexArtifactLineageEdge.tenant_id == tenant_id,
            CortexArtifactLineageEdge.lineage_edge_id == eid,
        )
    )
    if existing is not None:
        return existing
    row = CortexArtifactLineageEdge(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        lineage_edge_id=eid,
        from_artifact_kind=from_artifact_kind,
        from_artifact_ref=from_artifact_ref,
        to_artifact_kind=to_artifact_kind,
        to_artifact_ref=to_artifact_ref,
        edge_kind=edge_kind,
        replay_identity=replay_identity,
        degradation_propagation=dict(degradation_propagation or {}),
        omission_summary=dict(omission_summary or {}),
    )
    session.add(row)
    session.flush()
    return row


def query_lineage_edges_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_kind: str | None = None,
    artifact_ref: str | None = None,
    limit: int = 500,
) -> list[CortexArtifactLineageEdge]:
    stmt = select(CortexArtifactLineageEdge).where(
        CortexArtifactLineageEdge.tenant_id == tenant_id,
    )
    if artifact_kind and artifact_ref:
        stmt = stmt.where(
            or_(
                (CortexArtifactLineageEdge.from_artifact_kind == artifact_kind)
                & (CortexArtifactLineageEdge.from_artifact_ref == artifact_ref),
                (CortexArtifactLineageEdge.to_artifact_kind == artifact_kind)
                & (CortexArtifactLineageEdge.to_artifact_ref == artifact_ref),
            )
        )
    stmt = stmt.order_by(CortexArtifactLineageEdge.created_at.asc()).limit(max(1, min(limit, 2000)))
    return list(session.scalars(stmt).all())
