"""Lawful multi-artifact evidence assembly for reconstruction-centric queries."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_continuity_projection import (
    expand_retrieval_continuity_context_v1,
)
from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
    build_retrieval_evidence_hits_from_index_v1,
    normalize_retrieval_omission_rows_v1,
)
from vector.domains.cortex.retrieval.runtime.reconstruction.lineage_propagation import (
    attach_upstream_lineage_to_hits_v1,
    verify_lineage_continuity_v1,
)
from vector.domains.cortex.retrieval.runtime.reconstruction.reconstruction_receipt import (
    build_reconstruction_receipt_v1,
)
from vector.domains.cortex.retrieval.runtime.reconstruction.scope_planner import (
    LINEAGE_OMISSION_CLASSES_V1,
    lineage_omission_class_to_rd_v1,
    plan_reconstruction_scope_v1,
    workload_uses_reconstruction_v1,
)


def _artifact_ref_record(kind: str, ref: str, *, source: str) -> dict[str, Any]:
    return {"artifact_kind": kind, "artifact_ref": ref, "source": source}


def assemble_reconstruction_evidence_hits_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    row: Any,
    retrieval_lookup_id: str,
    workload_class: str,
    execution_partition: str,
    replay_pins: Mapping[str, Any],
    replay_identity_match: bool,
    partial_addressing: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build one or more evidence hits from persisted upstream artifacts."""
    scope = plan_reconstruction_scope_v1(
        session,
        tenant_id=tenant_id,
        envelope=envelope,
        row=row,
        retrieval_lookup_id=retrieval_lookup_id,
    )
    hits: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    omissions: list[dict[str, Any]] = []

    base_hits = build_retrieval_evidence_hits_from_index_v1(
        tenant_id=tenant_id,
        retrieval_lookup_id=retrieval_lookup_id,
        row=row,
        replay_posture="stable" if replay_identity_match else "unsafe",
        workload_class=workload_class,
        execution_partition=execution_partition,
        replay_pins=replay_pins,
        replay_identity_match=replay_identity_match,
        partial_addressing=partial_addressing,
    )
    hits.extend(base_hits)
    resolved.append(_artifact_ref_record("retrieval_index", retrieval_lookup_id, source="index_row"))

    chain_id = scope.get("causal_chain_id")
    if chain_id:
        resolved.append(_artifact_ref_record("tcre_chain", str(chain_id), source="artifact_ref"))

    job_id = scope.get("tcre_reconstruction_job_id")
    if job_id:
        from vector.domains.cortex.retrieval.retrieval_tcre_binding import load_tcre_reconstruction_job_v1

        job = load_tcre_reconstruction_job_v1(session, tenant_id=tenant_id, job_id=job_id)
        if job is not None:
            resolved.append(
                _artifact_ref_record("tcre_reconstruction_job", str(job.id), source="persisted_job")
            )
        else:
            omissions.append(
                {
                    "retrieval_omission_class": "RD-TCRE-GAP",
                    "upstream_trigger": "missing_tcre_job",
                }
            )

    walk_id = scope.get("octs_walk_id")
    if walk_id:
        from vector.domains.cortex.retrieval.retrieval_octs_binding import load_durable_walk_record_v1

        rec = load_durable_walk_record_v1(session, tenant_id=tenant_id, walk_id=walk_id)
        if rec is not None:
            resolved.append(_artifact_ref_record("octs_traversal", str(walk_id), source="durable_walk"))
        else:
            omissions.append(
                {
                    "retrieval_omission_class": lineage_omission_class_to_rd_v1("traversal_lineage_gap"),
                    "upstream_trigger": "missing_durable_walk",
                }
            )

    for gap in scope.get("lineage_gaps") or []:
        if gap in LINEAGE_OMISSION_CLASSES_V1:
            omissions.append(
                {
                    "retrieval_omission_class": lineage_omission_class_to_rd_v1(gap),
                    "upstream_trigger": "reconstruction_scope",
                }
            )

    hits, lineage_omissions = attach_upstream_lineage_to_hits_v1(
        session,
        tenant_id=tenant_id,
        hits=hits,
        scope=scope,
        envelope=envelope,
    )
    omissions.extend(lineage_omissions)
    continuity = expand_retrieval_continuity_context_v1(
        session,
        tenant_id=tenant_id,
        row=row,
        scope=scope,
    )
    for hit in hits:
        if isinstance(hit, dict):
            hit["continuity_context"] = continuity.get("continuity_context")
            hit["continuity_replay_posture"] = continuity.get("replay_posture")

    verify_lineage_continuity_v1(session, tenant_id=tenant_id, scope=scope, omissions=omissions)
    return hits, omissions, resolved


def apply_reconstruction_to_query_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    row: Any,
    retrieval_lookup_id: str,
    workload_class: str,
    execution_partition: str,
    replay_pins: Mapping[str, Any],
    replay_identity_match: bool,
    partial_addressing: bool,
) -> dict[str, Any]:
    """Reconstruction-centric path: multi-artifact hits + structural receipt."""
    if not workload_uses_reconstruction_v1(workload_class):
        hits = build_retrieval_evidence_hits_from_index_v1(
            tenant_id=tenant_id,
            retrieval_lookup_id=retrieval_lookup_id,
            row=row,
            replay_posture="stable" if replay_identity_match else "unsafe",
            workload_class=workload_class,
            execution_partition=execution_partition,
            replay_pins=replay_pins,
            replay_identity_match=replay_identity_match,
            partial_addressing=partial_addressing,
        )
        return {
            "hits": hits,
            "omissions": [],
            "reconstruction_receipt": None,
            "reconstruction_applied": False,
        }

    hits, omissions, resolved = assemble_reconstruction_evidence_hits_v1(
        session,
        tenant_id=tenant_id,
        envelope=envelope,
        row=row,
        retrieval_lookup_id=retrieval_lookup_id,
        workload_class=workload_class,
        execution_partition=execution_partition,
        replay_pins=replay_pins,
        replay_identity_match=replay_identity_match,
        partial_addressing=partial_addressing,
    )
    receipt = build_reconstruction_receipt_v1(
        scope=plan_reconstruction_scope_v1(
            session,
            tenant_id=tenant_id,
            envelope=envelope,
            row=row,
            retrieval_lookup_id=retrieval_lookup_id,
        ),
        artifact_refs_resolved=resolved,
        hit_count=len(hits),
        omission_count=len(omissions),
    )
    return {
        "hits": hits,
        "omissions": normalize_retrieval_omission_rows_v1(omissions, partial_addressing=partial_addressing),
        "reconstruction_receipt": receipt,
        "reconstruction_applied": True,
    }
