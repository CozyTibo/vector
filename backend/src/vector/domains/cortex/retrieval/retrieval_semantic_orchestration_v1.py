"""Wave S3 — ordered phase-07 retrieval materialization (walks → TCRE → mats → capped org_link)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_materialization_caps_v1 import (
    get_retrieval_max_org_link_entries_per_epoch_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

WAVE_S3_MATERIALIZATION_ORDER_V1: Final[tuple[str, ...]] = (
    "walk",
    "tcre",
    "canonical_materialization",
    "org_link",
)

RETRIEVAL_SEMANTIC_ORCHESTRATION_SCHEMA_VERSION: Final[int] = 1


def count_index_entries_in_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
    index_kind: str | None = None,
) -> int:
    q = select(func.count()).select_from(CortexRetrievalIndexEntry).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
        CortexRetrievalIndexEntry.index_epoch == index_epoch,
    )
    if index_kind:
        q = q.where(CortexRetrievalIndexEntry.index_kind == index_kind)
    return int(session.scalar(q) or 0)


def materialize_walks_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    replay_identity: str,
    index_epoch: str,
    island: frozenset[uuid.UUID] | None,
    omission_summary: dict[str, Any] | None,
    walk_filter: Any,
    stats: dict[str, Any],
) -> None:
    from vector.domains.cortex.retrieval.retrieval_component_materialization import (
        walk_record_intersects_island_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_octs_binding import (
        RetrievalOctsBindingError,
        durable_row_from_walk_record_v1,
        materialize_retrieval_index_from_walk_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError
    from vector.domains.cortex.retrieval.retrieval_skip_registry import normalize_retrieval_skip_reason_v1
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1

    store = resolve_octs_walk_store_v1(session)
    omit = dict(omission_summary or {})
    for record in store.list_walk_records_for_tenant_v1(tenant_id):
        if str(record.status) != "completed" or not record.walk_payload:
            continue
        if island is not None and not walk_record_intersects_island_v1(record, island):
            continue
        if walk_filter is not None and not walk_filter(record):
            continue
        walk_replay = replay_identity
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
                index_epoch=index_epoch,
                auto_publish=False,
                omission_summary=omit,
            )
            stats["entries_materialized"] = int(stats.get("entries_materialized") or 0) + 1
            stats["walks_materialized"] = int(stats.get("walks_materialized") or 0) + 1
        except (RetrievalOctsBindingError, RetrievalLegalityError) as exc:
            stats.setdefault("skip_reasons", []).append(
                {
                    "source": "walk",
                    "walk_id": str(record.walk_id),
                    "code": normalize_retrieval_skip_reason_v1(getattr(exc, "code", str(exc))),
                }
            )


def materialize_tcre_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    replay_identity: str,
    index_epoch: str,
    island: frozenset[uuid.UUID] | None,
    walk_by_id: dict[uuid.UUID, Any],
    max_tcre_jobs: int,
    stats: dict[str, Any],
) -> None:
    from vector.domains.cortex.retrieval.retrieval_component_materialization import (
        walk_record_intersects_island_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
        RetrievalTcreBindingError,
        materialize_retrieval_index_from_tcre_job_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError

    prid = str(pipeline_run_id)
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(max(1, min(int(max_tcre_jobs), 50)))
        ).all()
    )
    stats["tcre_candidates"] = len(jobs)
    for job in jobs:
        scope = dict(job.scope_json or {})
        job_prid = str(scope.get("substrate_pipeline_run_id") or "")
        if job_prid and job_prid != prid:
            continue
        walk_raw = scope.get("octs_walk_id")
        if island is not None and walk_raw:
            walk = walk_by_id.get(uuid.UUID(str(walk_raw)))
            if walk is None or not walk_record_intersects_island_v1(walk, island):
                continue
        try:
            out = materialize_retrieval_index_from_tcre_job_v1(
                session,
                tenant_id=tenant_id,
                job=job,
                replay_identity=replay_identity,
                index_epoch=index_epoch,
                auto_publish=False,
            )
            added = len(out.get("materialized_lookup_ids") or [])
            stats["entries_materialized"] = int(stats.get("entries_materialized") or 0) + added
            stats["tcre_jobs_materialized"] = int(stats.get("tcre_jobs_materialized") or 0) + 1
        except (RetrievalTcreBindingError, RetrievalLegalityError) as exc:
            stats.setdefault("skip_reasons", []).append(
                {"source": "tcre_job", "code": getattr(exc, "code", str(exc))},
            )


def materialize_canonical_mats_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island: frozenset[uuid.UUID] | None,
    replay_identity: str,
    index_epoch: str,
    omission_summary: dict[str, Any] | None,
    stats: dict[str, Any],
) -> None:
    from vector.domains.cortex.retrieval.retrieval_canonical_materialization_v1 import (
        materialize_canonical_materializations_for_island_v1,
    )

    if island is None or not island:
        stats["canonical_materializations"] = {"materialized_count": 0, "reason": "no_island_scope"}
        return
    out = materialize_canonical_materializations_for_island_v1(
        session,
        tenant_id=tenant_id,
        island=island,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        omission_summary=omission_summary,
    )
    stats["canonical_materializations"] = out
    stats["entries_materialized"] = int(stats.get("entries_materialized") or 0) + int(
        out.get("materialized_count") or 0
    )


def materialize_bounded_org_links_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    replay_identity: str,
    index_epoch: str,
    island: frozenset[uuid.UUID] | None,
    omission_summary: dict[str, Any] | None,
    stats: dict[str, Any],
    max_org_links: int | None = None,
) -> None:
    from vector.domains.cortex.retrieval.retrieval_component_materialization import (
        org_link_within_island_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        RetrievalGraphBindingError,
        materialize_retrieval_index_from_graph_ref_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError

    cap = max_org_links if max_org_links is not None else get_retrieval_max_org_link_entries_per_epoch_v1()
    cap = max(0, int(cap))
    already = count_index_entries_in_epoch_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
        index_kind="org_link",
    )
    remaining = max(0, cap - already)
    stats["org_link_cap"] = cap
    stats["org_link_already_in_epoch"] = already
    stats["org_link_remaining_cap"] = remaining
    if remaining <= 0:
        stats.setdefault("skip_reasons", []).append(
            {"source": "org_link", "code": "org_link_epoch_cap_reached"},
        )
        return

    omit = dict(omission_summary or {})
    q = select(CortexOrgLink).where(
        CortexOrgLink.tenant_id == tenant_id,
        CortexOrgLink.revoked_at.is_(None),
    )
    if island is not None:
        q = q.where(
            CortexOrgLink.source_entity_id.in_(island),
            CortexOrgLink.target_entity_id.in_(island),
        )
    q = q.order_by(CortexOrgLink.created_at.asc()).limit(remaining)
    materialized = 0
    for link in session.scalars(q).all():
        if island is not None and not org_link_within_island_v1(link, island):
            continue
        try:
            materialize_retrieval_index_from_graph_ref_v1(
                session,
                tenant_id=tenant_id,
                ref_kind="org_link_id",
                ref_value=str(link.id),
                replay_identity=replay_identity,
                index_epoch=index_epoch,
                auto_publish=False,
                omission_summary=omit,
            )
            materialized += 1
            stats["entries_materialized"] = int(stats.get("entries_materialized") or 0) + 1
        except (RetrievalGraphBindingError, RetrievalLegalityError) as exc:
            stats.setdefault("skip_reasons", []).append(
                {
                    "source": "org_link",
                    "org_link_id": str(link.id),
                    "code": getattr(exc, "code", str(exc)),
                }
            )
    stats["org_links_materialized"] = materialized


def run_wave_s3_retrieval_materialization_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    index_epoch: str,
    replay_identity: str,
    island: frozenset[uuid.UUID] | None,
    omission_summary: dict[str, Any] | None,
    max_tcre_jobs: int = 25,
) -> dict[str, Any]:
    """Single ordered materialization pass (S3.1)."""
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1

    store = resolve_octs_walk_store_v1(session)
    walk_by_id = {record.walk_id: record for record in store.list_walk_records_for_tenant_v1(tenant_id)}
    stats: dict[str, Any] = {
        "schema_version": RETRIEVAL_SEMANTIC_ORCHESTRATION_SCHEMA_VERSION,
        "materialization_order": list(WAVE_S3_MATERIALIZATION_ORDER_V1),
        "entries_materialized": 0,
        "skip_reasons": [],
        "walks_materialized": 0,
        "tcre_jobs_materialized": 0,
        "org_links_materialized": 0,
    }
    materialize_walks_for_scope_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        island=island,
        omission_summary=omission_summary,
        walk_filter=None,
        stats=stats,
    )
    materialize_tcre_for_scope_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        island=island,
        walk_by_id=walk_by_id,
        max_tcre_jobs=max_tcre_jobs,
        stats=stats,
    )
    materialize_canonical_mats_for_scope_v1(
        session,
        tenant_id=tenant_id,
        island=island,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        omission_summary=omission_summary,
        stats=stats,
    )
    materialize_bounded_org_links_for_scope_v1(
        session,
        tenant_id=tenant_id,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        island=island,
        omission_summary=omission_summary,
        stats=stats,
    )
    return stats
