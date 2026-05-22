"""Phase 07 P07-14 — retrieval index materialization + publish barrier.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md`` §Index.
**RET-IDX-01**, **G-P07-REPLAY-02**.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RETRIEVAL_RD_INDEX_STALE_V1,
    RetrievalIngressError,
    validate_retrieval_index_entry_derived_read_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    classify_retrieval_legality_v1,
    retrieval_policy_digest_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch

PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_REPLAY02_GATE_ID_V1: Final[str] = "G-P07-REPLAY-02"

GP07_IDX01_GATE_ID_V1: Final[str] = "RET-IDX-01"

RETRIEVAL_INDEX_MATERIALIZATION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md"
)

RETRIEVAL_INDEX_BUILD_STATES_V1: Final[frozenset[str]] = frozenset(
    {"QUEUED", "BUILDING", "PUBLISHED"}
)

RETRIEVAL_INDEX_BUILD_TRANSITIONS_V1: Final[dict[str, frozenset[str]]] = {
    "QUEUED": frozenset({"BUILDING"}),
    "BUILDING": frozenset({"PUBLISHED"}),
    "PUBLISHED": frozenset(),
}


class RetrievalIndexMaterializationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def validate_index_build_state_transition_v1(*, from_state: str, to_state: str) -> None:
    allowed = RETRIEVAL_INDEX_BUILD_TRANSITIONS_V1.get(from_state, frozenset())
    if to_state not in allowed:
        raise RetrievalIndexMaterializationError(
            "index_build_illegal_transition",
            detail={"from_state": from_state, "to_state": to_state},
        )


def compute_index_build_idempotency_key_v1(
    *,
    tenant_id: uuid.UUID | str,
    index_epoch: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {"tenant_id": str(tenant_id), "index_epoch": index_epoch}
    )


def get_published_index_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> str | None:
    """Current **published** epoch for tenant (**RET-IDX-01**)."""
    row = session.scalar(
        select(CortexRetrievalIndexEpoch.index_epoch)
        .where(
            CortexRetrievalIndexEpoch.tenant_id == tenant_id,
            CortexRetrievalIndexEpoch.build_state == "PUBLISHED",
        )
        .order_by(CortexRetrievalIndexEpoch.published_at.desc())
        .limit(1)
    )
    return str(row) if row else None


def get_index_epoch_row_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> CortexRetrievalIndexEpoch | None:
    return session.scalar(
        select(CortexRetrievalIndexEpoch).where(
            CortexRetrievalIndexEpoch.tenant_id == tenant_id,
            CortexRetrievalIndexEpoch.index_epoch == index_epoch,
        )
    )


def assert_index_epoch_published_for_read_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch_on_row: str | None,
    pinned_index_epoch: str | None = None,
) -> None:
    """**RET-IDX-01** — only published epoch rows are readable."""
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    epoch = (index_epoch_on_row or "").strip()
    if not published:
        raise RetrievalIngressError(
            RETRIEVAL_RD_INDEX_STALE_V1,
            detail={"reason": "no_published_epoch", "row_index_epoch": epoch},
        )
    if epoch != published:
        raise RetrievalIngressError(
            RETRIEVAL_RD_INDEX_STALE_V1,
            detail={
                "reason": "partial_or_stale_epoch",
                "published_index_epoch": published,
                "row_index_epoch": epoch,
            },
        )
    validate_retrieval_index_entry_derived_read_v1(
        index_epoch_on_row=epoch,
        pinned_index_epoch=pinned_index_epoch,
    )


def start_retrieval_index_build_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None = None,
) -> CortexRetrievalIndexEpoch:
    """Create index build job in ``QUEUED`` state."""
    epoch_name = (index_epoch or f"epoch-{uuid.uuid4().hex[:12]}").strip()
    existing = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=epoch_name)
    if existing is not None:
        return existing
    row = CortexRetrievalIndexEpoch(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        index_epoch=epoch_name,
        build_state="QUEUED",
        entry_count=0,
        idempotency_key=compute_index_build_idempotency_key_v1(
            tenant_id=tenant_id, index_epoch=epoch_name
        ),
    )
    session.add(row)
    session.flush()
    return row


def transition_retrieval_index_build_v1(
    session: Session,
    *,
    epoch_row: CortexRetrievalIndexEpoch,
    to_state: str,
) -> CortexRetrievalIndexEpoch:
    if to_state not in RETRIEVAL_INDEX_BUILD_STATES_V1:
        raise RetrievalIndexMaterializationError("invalid_build_state", detail={"state": to_state})
    validate_index_build_state_transition_v1(
        from_state=epoch_row.build_state,
        to_state=to_state,
    )
    epoch_row.build_state = to_state
    if to_state == "PUBLISHED":
        epoch_row.published_at = datetime.now(UTC)
    session.flush()
    return epoch_row


def compute_output_index_hash_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> str:
    rows = session.scalars(
        select(CortexRetrievalIndexEntry.retrieval_lookup_id)
        .where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_epoch == index_epoch,
        )
        .order_by(CortexRetrievalIndexEntry.retrieval_lookup_id)
    ).all()
    return hash_reasoning_canonical_json_sha256_v1({"lookup_ids": list(rows)})


def publish_retrieval_index_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> CortexRetrievalIndexEpoch:
    """Publish barrier — transition ``BUILDING`` → ``PUBLISHED`` (**RET-IDX-01**)."""
    row = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    if row is None:
        row = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    if row.build_state == "QUEUED":
        row = transition_retrieval_index_build_v1(session, epoch_row=row, to_state="BUILDING")
    count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == index_epoch,
            )
        )
        or 0
    )
    row.entry_count = count
    row.output_index_hash = compute_output_index_hash_v1(
        session, tenant_id=tenant_id, index_epoch=index_epoch
    )
    if row.build_state != "PUBLISHED":
        row = transition_retrieval_index_build_v1(session, epoch_row=row, to_state="PUBLISHED")
    session.flush()
    return row


def ensure_published_index_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> CortexRetrievalIndexEpoch:
    """Test/admin helper — ensure epoch exists and is ``PUBLISHED``."""
    row = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    if row is None:
        row = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    if row.build_state != "PUBLISHED":
        if row.build_state == "QUEUED":
            transition_retrieval_index_build_v1(session, epoch_row=row, to_state="BUILDING")
        publish_retrieval_index_epoch_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
        row = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    assert row is not None
    return row


def materialize_retrieval_index_entry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    causal_chain_id: str | None = None,
    replay_identity: str,
    index_epoch: str,
    index_kind: str = "causal_chain",
    index_key: str | None = None,
    chronology_legality_class: str = "strict",
    causal_legality_class: str = "verified",
    degradation_posture: str = "stable",
    continuity_posture: str = "stable",
    artifact_ref: Mapping[str, Any] | None = None,
    omission_summary: Mapping[str, Any] | None = None,
    auto_publish: bool = True,
) -> CortexRetrievalIndexEntry:
    """Materialize one index row under ``index_epoch`` (publish optional)."""
    epoch = index_epoch.strip()
    if not epoch:
        raise RetrievalIndexMaterializationError("index_epoch_required")
    if auto_publish:
        ensure_published_index_epoch_v1(session, tenant_id=tenant_id, index_epoch=epoch)
    kind = str(index_kind or "causal_chain").strip()
    if index_key:
        ikey = str(index_key).strip()
    elif causal_chain_id:
        ikey = f"causal_chain:{causal_chain_id}"
        kind = kind or "causal_chain"
    else:
        raise RetrievalIndexMaterializationError("index_key_or_causal_chain_id_required")
    lookup_id = derive_retrieval_lookup_id_v1(
        index_kind=kind,
        index_key=ikey,
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
        existing.index_epoch = epoch
        existing.traversal_epoch = epoch
        session.flush()
        return existing
    ref = dict(artifact_ref or {})
    if causal_chain_id and "causal_chain_id" not in ref:
        ref.setdefault("causal_chain_id", causal_chain_id)
    row = CortexRetrievalIndexEntry(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        retrieval_lookup_id=lookup_id,
        index_kind=kind,
        index_key=ikey,
        replay_identity=replay_identity,
        traversal_epoch=epoch,
        index_epoch=epoch,
        chronology_legality_class=chronology_legality_class,
        causal_legality_class=causal_legality_class,
        retrieval_legality_class=legality,
        degradation_posture=degradation_posture,
        continuity_posture=continuity_posture,
        artifact_ref_json=ref,
        omission_summary=dict(omission_summary or {}),
        retrieval_policy_digest=retrieval_policy_digest_v1(),
    )
    session.add(row)
    session.flush()
    return row


def derive_admin_bootstrap_replay_identity_v1(*, tenant_id: uuid.UUID) -> str:
    """Deterministic replay identity for operator index bootstrap (tenant-scoped)."""
    return hash_reasoning_canonical_json_sha256_v1(
        {"tenant_id": str(tenant_id), "purpose": "admin_index_bootstrap_v1"}
    )


def derive_substrate_pipeline_replay_identity_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> str:
    """Deterministic replay identity for pipeline-driven retrieval materialization."""
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(pipeline_run_id),
            "purpose": "substrate_pipeline_retrieval_v1",
        }
    )


def materialize_retrieval_index_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    max_tcre_jobs: int = 25,
) -> dict[str, Any]:
    """Incremental retrieval materialization after pipeline TCRE completes (idempotent)."""
    from vector.domains.cortex.retrieval.retrieval_component_materialization import (
        is_retrieval_component_scope_enabled_v1,
        materialize_retrieval_index_for_largest_island_v1,
    )

    if is_retrieval_component_scope_enabled_v1():
        return materialize_retrieval_index_for_largest_island_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            max_tcre_jobs=max_tcre_jobs,
        )

    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        RetrievalGraphBindingError,
        materialize_retrieval_index_from_graph_ref_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_octs_binding import (
        RetrievalOctsBindingError,
        durable_row_from_walk_record_v1,
        materialize_retrieval_index_from_walk_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
        RetrievalTcreBindingError,
        materialize_retrieval_index_from_tcre_job_v1,
    )
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
        CortexTcreReconstructionJob,
    )

    replay = derive_substrate_pipeline_replay_identity_v1(
        tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
    )
    epoch_row = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=None)
    epoch_row = transition_retrieval_index_build_v1(session, epoch_row=epoch_row, to_state="BUILDING")
    epoch_name = epoch_row.index_epoch

    tcre_candidates = int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        )
        or 0
    )
    store = resolve_octs_walk_store_v1(session)
    walks_candidates = sum(
        1
        for record in store.list_walk_records_for_tenant_v1(tenant_id)
        if str(record.status) == "completed" and record.walk_payload
    )
    org_link_candidates = int(
        session.scalar(
            select(func.count()).select_from(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id)
        )
        or 0
    )

    stats: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id),
        "index_epoch": epoch_name,
        "entries_materialized": 0,
        "skip_reasons": [],
        "tcre_candidates": tcre_candidates,
        "walks_candidates": walks_candidates,
        "org_link_candidates": org_link_candidates,
    }

    job = session.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status == "completed",
            CortexTcreReconstructionJob.job_kind == "reconstruct",
        )
        .order_by(CortexTcreReconstructionJob.completed_at.desc())
        .limit(1)
    )
    if job is not None:
        try:
            out = materialize_retrieval_index_from_tcre_job_v1(
                session,
                tenant_id=tenant_id,
                job=job,
                replay_identity=replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["entries_materialized"] += len(out.get("materialized_lookup_ids") or [])
            stats["tcre_job_id"] = str(job.id)
        except (RetrievalTcreBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append({"source": "tcre_job", "code": exc.code})

    for record in store.list_walk_records_for_tenant_v1(tenant_id):
        if str(record.status) != "completed" or not record.walk_payload:
            continue
        walk_replay = replay
        durable_row = durable_row_from_walk_record_v1(
            session, tenant_id=tenant_id, walk_id=record.walk_id
        )
        if durable_row is not None and durable_row.replay_identity:
            walk_replay = str(durable_row.replay_identity)
        try:
            materialize_retrieval_index_from_walk_v1(
                session,
                tenant_id=tenant_id,
                record=record,
                replay_identity=walk_replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["entries_materialized"] += 1
        except (RetrievalOctsBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append(
                {"source": "walk", "walk_id": str(record.walk_id), "code": exc.code}
            )

    for link in session.scalars(
        select(CortexOrgLink).where(CortexOrgLink.tenant_id == tenant_id).limit(500)
    ).all():
        try:
            materialize_retrieval_index_from_graph_ref_v1(
                session,
                tenant_id=tenant_id,
                ref_kind="org_link_id",
                ref_value=str(link.id),
                replay_identity=replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["entries_materialized"] += 1
        except (RetrievalGraphBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append(
                {"source": "org_link", "org_link_id": str(link.id), "code": exc.code}
            )

    published = publish_retrieval_index_epoch_v1(
        session, tenant_id=tenant_id, index_epoch=epoch_name
    )
    stats["build_state"] = published.build_state
    stats["entry_count"] = published.entry_count
    stats["output_index_hash"] = published.output_index_hash
    stats["ok"] = published.build_state == "PUBLISHED"
    from vector.domains.cortex.execution.progression_status import (
        classify_retrieval_materialization_outcome_v1,
    )

    stats["retrieval_card_classification"] = classify_retrieval_materialization_outcome_v1(
        entries_materialized=int(stats.get("entries_materialized") or 0),
        entry_count=int(published.entry_count or 0),
        tcre_candidates=tcre_candidates,
        walks_candidates=walks_candidates,
        org_link_candidates=org_link_candidates,
    )

    from vector.domains.cortex.retrieval.retrieval_materialization_diagnostics import (
        persist_retrieval_materialization_report_v1,
    )

    persist_retrieval_materialization_report_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        stats=stats,
        tcre_candidates=tcre_candidates,
        walks_candidates=walks_candidates,
        org_link_candidates=org_link_candidates,
    )
    return stats


def bootstrap_retrieval_index_from_upstream_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None = None,
    max_tcre_jobs: int = 100,
    max_graph_links: int = 500,
) -> dict[str, Any]:
    """Materialize index rows from completed TCRE jobs, walks, and org links, then publish."""
    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        RetrievalGraphBindingError,
        materialize_retrieval_index_from_graph_ref_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_octs_binding import (
        RetrievalOctsBindingError,
        materialize_retrieval_index_from_walk_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
        RetrievalTcreBindingError,
        materialize_retrieval_index_from_tcre_job_v1,
    )
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
        CortexTcreReconstructionJob,
    )

    epoch_row = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    epoch_row = transition_retrieval_index_build_v1(session, epoch_row=epoch_row, to_state="BUILDING")
    epoch_name = epoch_row.index_epoch
    bootstrap_replay = derive_admin_bootstrap_replay_identity_v1(tenant_id=tenant_id)

    stats: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "index_epoch": epoch_name,
        "tcre_jobs_processed": 0,
        "tcre_jobs_skipped": 0,
        "walks_materialized": 0,
        "walks_skipped": 0,
        "graph_links_materialized": 0,
        "graph_links_skipped": 0,
        "entries_materialized": 0,
        "skip_reasons": [],
    }

    jobs = session.scalars(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status == "completed",
            CortexTcreReconstructionJob.job_kind == "reconstruct",
        )
        .order_by(CortexTcreReconstructionJob.completed_at.desc())
        .limit(max(1, int(max_tcre_jobs)))
    ).all()
    for job in jobs:
        try:
            out = materialize_retrieval_index_from_tcre_job_v1(
                session,
                tenant_id=tenant_id,
                job=job,
                replay_identity=bootstrap_replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            count = len(out.get("materialized_lookup_ids") or [])
            stats["tcre_jobs_processed"] += 1
            stats["entries_materialized"] += count
        except (RetrievalTcreBindingError, RetrievalLegalityError) as exc:
            stats["tcre_jobs_skipped"] += 1
            stats["skip_reasons"].append({"source": "tcre_job", "job_id": str(job.id), "code": exc.code})

    store = resolve_octs_walk_store_v1(session)
    for record in store.list_walk_records_for_tenant_v1(tenant_id):
        if str(record.status) != "completed" or not record.walk_payload:
            continue
        walk_replay = bootstrap_replay
        try:
            from vector.domains.cortex.retrieval.retrieval_octs_binding import (
                durable_row_from_walk_record_v1,
            )

            durable_row = durable_row_from_walk_record_v1(
                session, tenant_id=tenant_id, walk_id=record.walk_id
            )
            if durable_row is not None and durable_row.replay_identity:
                walk_replay = str(durable_row.replay_identity)
            materialize_retrieval_index_from_walk_v1(
                session,
                tenant_id=tenant_id,
                record=record,
                replay_identity=walk_replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["walks_materialized"] += 1
            stats["entries_materialized"] += 1
        except (RetrievalOctsBindingError, RetrievalLegalityError) as exc:
            stats["walks_skipped"] += 1
            stats["skip_reasons"].append(
                {"source": "walk", "walk_id": str(record.walk_id), "code": exc.code}
            )

    links = session.scalars(
        select(CortexOrgLink)
        .where(CortexOrgLink.tenant_id == tenant_id)
        .limit(max(1, int(max_graph_links)))
    ).all()
    for link in links:
        try:
            materialize_retrieval_index_from_graph_ref_v1(
                session,
                tenant_id=tenant_id,
                ref_kind="org_link_id",
                ref_value=str(link.id),
                replay_identity=bootstrap_replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["graph_links_materialized"] += 1
            stats["entries_materialized"] += 1
        except (RetrievalGraphBindingError, RetrievalLegalityError) as exc:
            stats["graph_links_skipped"] += 1
            stats["skip_reasons"].append(
                {"source": "org_link", "org_link_id": str(link.id), "code": exc.code}
            )

    published = publish_retrieval_index_epoch_v1(
        session, tenant_id=tenant_id, index_epoch=epoch_name
    )
    stats["build_state"] = published.build_state
    stats["entry_count"] = published.entry_count
    stats["output_index_hash"] = published.output_index_hash
    stats["published_at"] = published.published_at.isoformat() if published.published_at else None
    return stats


def run_retrieval_index_rebuild_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None = None,
) -> dict[str, Any]:
    """Admin rebuild: QUEUED → BUILDING → PUBLISHED for tenant scope."""
    job = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    job = transition_retrieval_index_build_v1(session, epoch_row=job, to_state="BUILDING")
    published = publish_retrieval_index_epoch_v1(
        session, tenant_id=tenant_id, index_epoch=job.index_epoch
    )
    return {
        "tenant_id": str(tenant_id),
        "index_epoch": published.index_epoch,
        "build_state": published.build_state,
        "entry_count": published.entry_count,
        "output_index_hash": published.output_index_hash,
        "published_at": published.published_at.isoformat() if published.published_at else None,
    }


def compute_index_lag_epochs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Observability: lag between entry epochs and published epoch."""
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    distinct = session.scalars(
        select(CortexRetrievalIndexEntry.index_epoch)
        .where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_epoch.isnot(None),
        )
        .distinct()
    ).all()
    epochs = sorted({str(e) for e in distinct if e})
    stale_epochs = [e for e in epochs if e != published] if published else epochs
    return {
        "published_index_epoch": published,
        "materialized_epochs": epochs,
        "stale_epoch_count": len(stale_epochs),
        "stale_epochs": stale_epochs,
    }


def compare_gp07_replay_02_index_permutation_v1(
    result_a: Mapping[str, Any],
    result_b: Mapping[str, Any],
) -> dict[str, Any]:
    """**G-P07-REPLAY-02** — build order must not change authoritative query output."""
    from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1

    hits_a = [
        str(h.get("retrieval_lookup_id", ""))
        for h in (result_a.get("hits") or result_a.get("retrieval_evidence_hits") or [])
        if isinstance(h, dict)
    ]
    hits_b = [
        str(h.get("retrieval_lookup_id", ""))
        for h in (result_b.get("hits") or result_b.get("retrieval_evidence_hits") or [])
        if isinstance(h, dict)
    ]
    id_a = str(result_a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    id_b = str(result_b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or "")
    passed = sorted(hits_a) == sorted(hits_b) and id_a == id_b and id_a != ""
    return {
        "gate_id": GP07_REPLAY02_GATE_ID_V1,
        "gp07_replay_02_passed": passed,
        "hit_multiset_match": sorted(hits_a) == sorted(hits_b),
        "replay_identity_match": id_a == id_b,
        "retrieval_query_replay_identity_a": id_a,
        "retrieval_query_replay_identity_b": id_b,
    }


def build_retrieval_index_catalog_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    return {
        "retrieval_index_materialization_runtime_schema_version": (
            PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION
        ),
        "ret_idx01_gate_id": GP07_IDX01_GATE_ID_V1,
        "gp07_replay02_gate_id": GP07_REPLAY02_GATE_ID_V1,
        "build_states": sorted(RETRIEVAL_INDEX_BUILD_STATES_V1),
        "build_transitions": {
            k: sorted(v) for k, v in sorted(RETRIEVAL_INDEX_BUILD_TRANSITIONS_V1.items())
        },
        "rules": [
            {
                "id": "RET-IDX-01",
                "text": "Queries read only PUBLISHED index_epoch rows",
            },
            {
                "id": "G-P07-REPLAY-02",
                "text": "Index build permutation does not change query replay identity",
            },
        ],
        "doctrine_anchor": RETRIEVAL_INDEX_MATERIALIZATION_SPEC_REF_V1,
        "tenant_id": str(tenant_id) if tenant_id else None,
    }


def _gate_meta(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_idx01_publish_barrier_static() -> dict[str, Any]:
    errors: list[str] = []
    if "PUBLISHED" not in RETRIEVAL_INDEX_BUILD_STATES_V1:
        errors.append("missing_published_state")
    try:
        validate_index_build_state_transition_v1(from_state="QUEUED", to_state="BUILDING")
        validate_index_build_state_transition_v1(from_state="BUILDING", to_state="PUBLISHED")
    except RetrievalIndexMaterializationError as exc:
        errors.append(f"fsm:{exc}")
    try:
        validate_index_build_state_transition_v1(from_state="QUEUED", to_state="PUBLISHED")
    except RetrievalIndexMaterializationError:
        pass
    else:
        errors.append("queued_to_published_should_fail")
    return _gate_meta(GP07_IDX01_GATE_ID_V1, "ret_idx01_publish_barrier", errors)


def verify_gp07_replay02_index_permutation_invariance_static() -> dict[str, Any]:
    errors: list[str] = []
    base = {
        "hits": [{"retrieval_lookup_id": "sha256:" + "a" * 64}],
        "retrieval_query_replay_identity": "b" * 64,
    }
    permuted = {
        "hits": [{"retrieval_lookup_id": "sha256:" + "a" * 64}],
        "retrieval_query_replay_identity": "b" * 64,
    }
    out = compare_gp07_replay_02_index_permutation_v1(base, permuted)
    if not out.get("gp07_replay_02_passed"):
        errors.append("identical_results_should_pass")
    bad = compare_gp07_replay_02_index_permutation_v1(
        base,
        {"hits": [], "retrieval_query_replay_identity": "c" * 64},
    )
    if bad.get("gp07_replay_02_passed"):
        errors.append("divergent_should_fail")
    return _gate_meta(GP07_REPLAY02_GATE_ID_V1, "gp07_replay02_index_permutation", errors)
