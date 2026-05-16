"""Bind lineage edges to replay identities."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.traversal.runtime.traversal_lineage_repository import list_walk_replay_lineage_v1


def bind_walk_lineage_to_tcre_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
    tcre_job_id: str,
    causal_chain_id: str,
    replay_identity: str,
) -> None:
    walk_ref = str(walk_id)
    persist_lineage_edge_v1(
        session,
        tenant_id=tenant_id,
        from_artifact_kind="octs_traversal",
        from_artifact_ref=walk_ref,
        to_artifact_kind="tcre_chain",
        to_artifact_ref=causal_chain_id,
        edge_kind="octs_binds_tcre",
        replay_identity=replay_identity,
    )
    persist_lineage_edge_v1(
        session,
        tenant_id=tenant_id,
        from_artifact_kind="tcre_chain",
        from_artifact_ref=causal_chain_id,
        to_artifact_kind="chronology_legality",
        to_artifact_ref=tcre_job_id,
        edge_kind="tcre_chronology",
        replay_identity=replay_identity,
    )
    for hop in list_walk_replay_lineage_v1(session, tenant_id=tenant_id, walk_id=walk_id):
        if hop.get("parent_walk_id"):
            persist_lineage_edge_v1(
                session,
                tenant_id=tenant_id,
                from_artifact_kind="octs_traversal",
                from_artifact_ref=str(hop["parent_walk_id"]),
                to_artifact_kind="octs_traversal",
                to_artifact_ref=str(hop["walk_id"]),
                edge_kind="replay_of",
                replay_identity=replay_identity,
            )
