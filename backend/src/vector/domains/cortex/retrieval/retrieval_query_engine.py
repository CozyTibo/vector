"""Deterministic retrieval query engine (lawful index only)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.query_execution import execute_retrieval_query_envelope_v1
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_entry_v1,
)
from vector.domains.cortex.retrieval.retrieval_graph_binding import (
    materialize_retrieval_index_from_graph_ref_v1,
)
from vector.domains.cortex.retrieval.retrieval_octs_binding import (
    load_durable_walk_record_v1,
    materialize_retrieval_index_from_walk_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry


def index_tcre_chain_for_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    causal_chain_id: str,
    replay_identity: str,
    traversal_epoch: str | None,
    chronology_legality_class: str = "strict",
    causal_legality_class: str = "verified",
    degradation_posture: str = "stable",
    continuity_posture: str = "stable",
    artifact_ref: dict[str, Any] | None = None,
    omission_summary: dict[str, Any] | None = None,
    tcre_reconstruction_job_id: uuid.UUID | str | None = None,
) -> CortexRetrievalIndexEntry:
    epoch = (traversal_epoch or f"epoch-{uuid.uuid4().hex[:8]}").strip()
    if tcre_reconstruction_job_id is not None:
        from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
            load_tcre_reconstruction_job_v1,
            materialize_retrieval_index_from_tcre_job_v1,
        )

        job = load_tcre_reconstruction_job_v1(
            session,
            tenant_id=tenant_id,
            job_id=tcre_reconstruction_job_id,
        )
        if job is None:
            raise ValueError("tcre_reconstruction_job_not_found")
        out = materialize_retrieval_index_from_tcre_job_v1(
            session,
            tenant_id=tenant_id,
            job=job,
            replay_identity=replay_identity,
            index_epoch=epoch,
        )
        chain_map = out["lookup_map"].get("by_causal_chain_id") or {}
        if causal_chain_id in chain_map:
            lookup_id = chain_map[causal_chain_id]["retrieval_lookup_id"]
            row = session.scalar(
                select(CortexRetrievalIndexEntry).where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.retrieval_lookup_id == lookup_id,
                )
            )
            if row is not None:
                return row
    return materialize_retrieval_index_entry_v1(
        session,
        tenant_id=tenant_id,
        causal_chain_id=causal_chain_id,
        replay_identity=replay_identity,
        index_epoch=epoch,
        chronology_legality_class=chronology_legality_class,
        causal_legality_class=causal_legality_class,
        degradation_posture=degradation_posture,
        continuity_posture=continuity_posture,
        artifact_ref=artifact_ref,
        omission_summary=omission_summary,
        auto_publish=True,
    )


def index_walk_for_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID | str,
    replay_identity: str,
    traversal_epoch: str | None,
) -> CortexRetrievalIndexEntry:
    epoch = (traversal_epoch or f"epoch-{uuid.uuid4().hex[:8]}").strip()
    record = load_durable_walk_record_v1(session, tenant_id=tenant_id, walk_id=walk_id)
    if record is None:
        raise ValueError("octs_walk_not_found")
    out = materialize_retrieval_index_from_walk_v1(
        session,
        tenant_id=tenant_id,
        record=record,
        replay_identity=replay_identity,
        index_epoch=epoch,
    )
    row = out["retrieval_index_entry"]
    assert isinstance(row, CortexRetrievalIndexEntry)
    return row


def index_graph_ref_for_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
    index_epoch: str | None,
    execution_partition: str = "authoritative",
) -> CortexRetrievalIndexEntry:
    epoch = (index_epoch or f"epoch-{uuid.uuid4().hex[:8]}").strip()
    out = materialize_retrieval_index_from_graph_ref_v1(
        session,
        tenant_id=tenant_id,
        ref_kind=ref_kind,
        ref_value=ref_value,
        replay_identity=replay_identity,
        index_epoch=epoch,
        execution_partition=execution_partition,
    )
    row = out["retrieval_index_entry"]
    assert isinstance(row, CortexRetrievalIndexEntry)
    return row


def execute_retrieval_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_lookup_id: str | None = None,
    expected_replay_identity: str | None = None,
    execution_partition: str = "authoritative",
    upstream_triggers: dict[str, Any] | None = None,
    policy_override_exploration: bool = False,
    index_epoch: str | None = None,
    ingress_scope: dict[str, Any] | None = None,
    workload_class: str | None = None,
    intent: str | None = None,
    envelope_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute retrieval via lawful envelope FSM (P07-06); accepts minimal or full envelope body."""
    body: dict[str, Any] = dict(envelope_body or {})
    if retrieval_lookup_id:
        body.setdefault("retrieval_lookup_id", retrieval_lookup_id)
    if workload_class is not None:
        body.setdefault("workload_class", workload_class)
    if intent is not None:
        body.setdefault("intent", intent)
    if execution_partition:
        body.setdefault("execution_partition", execution_partition)
    if upstream_triggers is not None:
        body.setdefault("upstream_triggers", upstream_triggers)
    if policy_override_exploration:
        body["policy_override_exploration"] = True
    if index_epoch is not None:
        body.setdefault("index_epoch", index_epoch)
    if ingress_scope is not None:
        body.setdefault("ingress_scope", ingress_scope)
    if expected_replay_identity is not None:
        body.setdefault("expected_replay_identity", expected_replay_identity)
    return execute_retrieval_query_envelope_v1(
        session,
        tenant_id=tenant_id,
        body=body,
        expected_replay_identity=expected_replay_identity,
    )
