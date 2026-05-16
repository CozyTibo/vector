"""Deterministic retrieval query engine (lawful index only)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.lineage_chain_builder import build_artifact_lineage_chain_v1
from vector.domains.cortex.lineage.lineage_explainability_projection import (
    build_lineage_explainability_v1,
)
from vector.domains.cortex.retrieval.retrieval_degradation_projection import (
    build_retrieval_degradation_envelope_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    assert_retrieval_lawful_v1,
    classify_retrieval_legality_v1,
    retrieval_policy_digest_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
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
) -> CortexRetrievalIndexEntry:
    index_kind = "causal_chain"
    index_key = f"causal_chain:{causal_chain_id}"
    lookup_id = derive_retrieval_lookup_id_v1(
        index_kind=index_kind,
        index_key=index_key,
        replay_identity=replay_identity,
    )
    legality = classify_retrieval_legality_v1(
        replay_identity_match=True,
        chronology_legality_class=chronology_legality_class,
        causal_legality_class=causal_legality_class,
        degradation_posture=degradation_posture,
        continuity_posture=continuity_posture,
        traversal_degraded=False,
    )
    if legality == "retrieval_unverifiable":
        raise RetrievalLegalityError("index_forbidden_unverifiable")
    existing = session.scalar(
        select(CortexRetrievalIndexEntry).where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.retrieval_lookup_id == lookup_id,
        )
    )
    if existing is not None:
        return existing
    row = CortexRetrievalIndexEntry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        retrieval_lookup_id=lookup_id,
        index_kind=index_kind,
        index_key=index_key,
        replay_identity=replay_identity,
        traversal_epoch=traversal_epoch,
        chronology_legality_class=chronology_legality_class,
        causal_legality_class=causal_legality_class,
        retrieval_legality_class=legality,
        degradation_posture=degradation_posture,
        continuity_posture=continuity_posture,
        artifact_ref_json=dict(artifact_ref or {"causal_chain_id": causal_chain_id}),
        omission_summary=dict(omission_summary or {}),
        retrieval_policy_digest=retrieval_policy_digest_v1(),
    )
    session.add(row)
    session.flush()
    return row


def execute_retrieval_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_lookup_id: str,
    expected_replay_identity: str | None = None,
) -> dict[str, Any]:
    row = session.scalar(
        select(CortexRetrievalIndexEntry).where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.retrieval_lookup_id == retrieval_lookup_id,
        )
    )
    if row is None:
        raise RetrievalLegalityError("retrieval_lookup_not_found")
    replay_match = (
        expected_replay_identity is None or row.replay_identity == expected_replay_identity
    )
    legality = classify_retrieval_legality_v1(
        replay_identity_match=replay_match,
        chronology_legality_class=row.chronology_legality_class,
        causal_legality_class=row.causal_legality_class,
        degradation_posture=row.degradation_posture,
        continuity_posture=row.continuity_posture,
        traversal_degraded=row.degradation_posture == "degraded",
    )
    replay_posture = "stable" if replay_match and legality == "retrieval_replay_safe" else (
        "partial" if legality == "retrieval_partial" else "unsafe"
    )
    assert_retrieval_lawful_v1(legality_class=legality, replay_posture=replay_posture)
    chain = build_artifact_lineage_chain_v1(
        session,
        tenant_id=tenant_id,
        terminal_artifact_kind="retrieval_index",
        terminal_artifact_ref=retrieval_lookup_id,
    )
    explain = build_lineage_explainability_v1(chain)
    degradation = build_retrieval_degradation_envelope_v1(
        degradation_posture=row.degradation_posture,
        omission_summary=dict(row.omission_summary or {}),
    )
    return {
        "retrieval_lookup_id": row.retrieval_lookup_id,
        "retrieval_policy_digest": row.retrieval_policy_digest,
        "retrieval_replay_identity": row.replay_identity,
        "chronology_legality_class": row.chronology_legality_class,
        "causal_legality_class": row.causal_legality_class,
        "retrieval_legality_class": legality,
        "degradation_posture": row.degradation_posture,
        "continuity_posture": row.continuity_posture,
        "omission_summary": dict(row.omission_summary or {}),
        "replay_posture": replay_posture,
        "artifact_ref": dict(row.artifact_ref_json or {}),
        "degradation_envelope": degradation,
        "lineage": explain,
    }
