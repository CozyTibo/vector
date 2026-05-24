"""Operator inspect chain builders (R5 — retrieval, synthesis, execution thread)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    build_retrieval_lineage_explorer_chain_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_query import build_artifact_query_summary_v1
from vector.domains.cortex.traversal.runtime.traversal_lineage_repository import (
    find_walks_by_replay_identity_v1,
    list_walk_replay_lineage_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob


def build_operator_retrieval_epochs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 5,
) -> dict[str, Any]:
    lim = max(1, min(int(limit), 20))
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEpoch)
            .where(CortexRetrievalIndexEpoch.tenant_id == tenant_id)
            .order_by(CortexRetrievalIndexEpoch.created_at.desc())
            .limit(lim)
        ).all()
    )
    epochs = [
        {
            "index_epoch": row.index_epoch,
            "build_state": row.build_state,
            "entry_count": int(row.entry_count or 0),
            "published_at": row.published_at,
            "created_at": row.created_at,
            "mix_note": _epoch_mix_note_v1(session, tenant_id=tenant_id, index_epoch=row.index_epoch),
            "error_detail": None if row.build_state != "FAILED" else "build_failed",
        }
        for row in rows
    ]
    return {
        "surface_kind": "operator_retrieval_epochs_v1",
        "tenant_id": str(tenant_id),
        "epochs": epochs,
        "limit": lim,
        "generated_at_utc": datetime.now(UTC),
    }


def search_operator_retrieval_entries_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: str | None = None,
    scope_ref: str | None = None,
    index_kind: str | None = None,
    walk_id: str | None = None,
    external_url: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))
    clauses: list[Any] = []
    if index_kind and index_kind.strip():
        clauses.append(CortexRetrievalIndexEntry.index_kind == index_kind.strip())
    for term in (entity_id, scope_ref, walk_id, external_url):
        if term and str(term).strip():
            needle = f"%{str(term).strip()}%"
            clauses.append(
                or_(
                    CortexRetrievalIndexEntry.index_key.ilike(needle),
                    CortexRetrievalIndexEntry.retrieval_lookup_id.ilike(needle),
                    cast(CortexRetrievalIndexEntry.artifact_ref_json, String).ilike(needle),
                )
            )
    if not clauses:
        raise ValueError("search_query_required")

    base = (
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
        or_(*clauses),
    )
    total = int(
        session.scalar(select(func.count()).select_from(CortexRetrievalIndexEntry).where(*base)) or 0
    )
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry)
            .where(*base)
            .order_by(CortexRetrievalIndexEntry.created_at.desc())
            .offset(off)
            .limit(lim)
        ).all()
    )
    items = [_retrieval_entry_row_v1(row) for row in rows]
    return {
        "surface_kind": "operator_retrieval_entries_v1",
        "tenant_id": str(tenant_id),
        "query": {
            "entity_id": entity_id,
            "scope_ref": scope_ref,
            "index_kind": index_kind,
            "walk_id": walk_id,
            "external_url": external_url,
        },
        "items": items,
        "total": total,
        "limit": lim,
        "offset": off,
        "generated_at_utc": datetime.now(UTC),
    }


def build_operator_retrieval_lineage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_kind: str,
    artifact_ref: str,
    max_hops: int = 64,
) -> dict[str, Any]:
    chain = build_retrieval_lineage_explorer_chain_v1(
        session,
        tenant_id=tenant_id,
        artifact_kind=artifact_kind,
        artifact_ref=artifact_ref,
        max_hops=max_hops,
    )
    return {
        "surface_kind": "operator_retrieval_lineage_v1",
        "tenant_id": str(tenant_id),
        "artifact_kind": artifact_kind,
        "artifact_ref": artifact_ref,
        "chain": chain,
        "generated_at_utc": datetime.now(UTC),
    }


def search_operator_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))
    filters: list[Any] = [CortexSynthesisJob.tenant_id == tenant_id]
    if status and status.strip() and status.strip() != "all":
        filters.append(CortexSynthesisJob.status == status.strip())
    if q and q.strip():
        needle = f"%{q.strip()}%"
        filters.append(
            or_(
                CortexSynthesisJob.synthesis_intent.ilike(needle),
                CortexSynthesisJob.synthesis_workload_class.ilike(needle),
                CortexSynthesisJob.error_detail.ilike(needle),
                cast(CortexSynthesisJob.id, String).ilike(needle),
            )
        )

    base = tuple(filters)
    total = int(session.scalar(select(func.count()).select_from(CortexSynthesisJob).where(*base)) or 0)
    rows = list(
        session.scalars(
            select(CortexSynthesisJob)
            .where(*base)
            .order_by(CortexSynthesisJob.created_at.desc())
            .offset(off)
            .limit(lim)
        ).all()
    )
    jobs = [
        {
            "job_id": str(row.id),
            "status": row.status,
            "synthesis_workload_class": row.synthesis_workload_class,
            "synthesis_intent": row.synthesis_intent,
            "synthesis_legality_class": row.synthesis_legality_class,
            "error_detail": (row.error_detail or "")[:500] or None,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
        }
        for row in rows
    ]
    recent_artifacts = list(
        session.scalars(
            select(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(True),
            )
            .order_by(CortexSynthesisArtifact.created_at.desc())
            .limit(3)
        ).all()
    )
    return {
        "surface_kind": "operator_synthesis_jobs_v1",
        "tenant_id": str(tenant_id),
        "query": {"status": status, "q": q},
        "jobs": jobs,
        "total": total,
        "limit": lim,
        "offset": off,
        "recent_artifacts": [build_artifact_query_summary_v1(row) for row in recent_artifacts],
        "generated_at_utc": datetime.now(UTC),
    }


def search_operator_execution_thread_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID | None = None,
    tcre_job_id: uuid.UUID | None = None,
    scope_ref: str | None = None,
    replay_identity: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    if not any([walk_id, tcre_job_id, scope_ref, replay_identity]):
        raise ValueError("search_query_required")

    lim = max(1, min(int(limit), 100))
    walk_lineage: list[dict[str, Any]] = []
    tcre_jobs: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []

    if walk_id is not None:
        walk_lineage = list_walk_replay_lineage_v1(session, tenant_id=tenant_id, walk_id=walk_id)
        index_entries.extend(
            _search_index_entries_for_term_v1(
                session, tenant_id=tenant_id, term=str(walk_id), limit=lim
            )
        )

    if tcre_job_id is not None:
        job = session.get(CortexTcreReconstructionJob, tcre_job_id)
        if job is not None and job.tenant_id == tenant_id:
            tcre_jobs.append(_tcre_job_row_v1(job))
            scope = dict(job.scope_json or {})
            scope_id = scope.get("scope_id") or scope.get("island_scope_id")
            if scope_id:
                index_entries.extend(
                    _search_index_entries_for_term_v1(
                        session, tenant_id=tenant_id, term=str(scope_id), limit=lim
                    )
                )

    if scope_ref and scope_ref.strip():
        term = scope_ref.strip()
        needle = f"%{term}%"
        jobs = list(
            session.scalars(
                select(CortexTcreReconstructionJob)
                .where(
                    CortexTcreReconstructionJob.tenant_id == tenant_id,
                    cast(CortexTcreReconstructionJob.scope_json, String).ilike(needle),
                )
                .order_by(CortexTcreReconstructionJob.created_at.desc())
                .limit(lim)
            ).all()
        )
        tcre_jobs.extend(_tcre_job_row_v1(row) for row in jobs)
        index_entries.extend(
            _search_index_entries_for_term_v1(session, tenant_id=tenant_id, term=term, limit=lim)
        )

    if replay_identity and replay_identity.strip():
        walks = find_walks_by_replay_identity_v1(
            session,
            tenant_id=tenant_id,
            replay_identity=replay_identity.strip(),
        )
        for walk in walks[:lim]:
            walk_lineage.extend(
                list_walk_replay_lineage_v1(session, tenant_id=tenant_id, walk_id=walk.walk_id)
            )
        index_entries.extend(
            _search_index_entries_for_term_v1(
                session, tenant_id=tenant_id, term=replay_identity.strip(), limit=lim
            )
        )

    deduped_tcre = _dedupe_by_key(tcre_jobs, "job_id")
    deduped_entries = _dedupe_by_key(index_entries, "entry_id")
    deduped_walk = _dedupe_by_key(walk_lineage, "walk_id")

    return {
        "surface_kind": "operator_execution_thread_v1",
        "tenant_id": str(tenant_id),
        "query": {
            "walk_id": str(walk_id) if walk_id else None,
            "tcre_job_id": str(tcre_job_id) if tcre_job_id else None,
            "scope_ref": scope_ref,
            "replay_identity": replay_identity,
        },
        "walk_lineage": deduped_walk[:lim],
        "tcre_jobs": deduped_tcre[:lim],
        "index_entries": deduped_entries[:lim],
        "generated_at_utc": datetime.now(UTC),
    }


def _epoch_mix_note_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> str | None:
    rows = session.execute(
        select(CortexRetrievalIndexEntry.index_kind, func.count())
        .where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.index_epoch == index_epoch,
        )
        .group_by(CortexRetrievalIndexEntry.index_kind)
        .order_by(func.count().desc())
    ).all()
    if not rows:
        return None
    total = sum(int(c) for _, c in rows)
    if total <= 0:
        return None
    top_kind, top_count = rows[0]
    pct = round(100.0 * int(top_count) / total, 1)
    if len(rows) == 1:
        return f"100% {top_kind}"
    return f"{top_kind} {pct}% · {total} entries"


def _retrieval_entry_row_v1(row: CortexRetrievalIndexEntry) -> dict[str, Any]:
    artifact_ref = dict(row.artifact_ref_json or {})
    lineage_kind, lineage_ref = _lineage_ref_from_entry_v1(row, artifact_ref)
    return {
        "entry_id": str(row.id),
        "retrieval_lookup_id": row.retrieval_lookup_id,
        "index_kind": row.index_kind,
        "index_key": row.index_key,
        "index_epoch": row.index_epoch,
        "traversal_epoch": row.traversal_epoch,
        "created_at": row.created_at,
        "lineage_artifact_kind": lineage_kind,
        "lineage_artifact_ref": lineage_ref,
        "artifact_ref": artifact_ref,
    }


def _lineage_ref_from_entry_v1(
    row: CortexRetrievalIndexEntry,
    artifact_ref: dict[str, Any],
) -> tuple[str | None, str | None]:
    kind = artifact_ref.get("artifact_kind")
    ref = artifact_ref.get("artifact_ref")
    if kind and ref:
        return str(kind), str(ref)
    if row.index_kind in {"walk", "causal_chain", "org_link", "materialization", "octs_walk_record"}:
        return str(row.index_kind), str(row.index_key or row.retrieval_lookup_id)
    walk_id = artifact_ref.get("walk_id")
    if walk_id:
        return "octs_walk_record", str(walk_id)
    return str(row.index_kind) if row.index_kind else None, str(row.index_key or row.retrieval_lookup_id)


def _search_index_entries_for_term_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    term: str,
    limit: int,
) -> list[dict[str, Any]]:
    needle = f"%{term.strip()}%"
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                or_(
                    CortexRetrievalIndexEntry.index_key.ilike(needle),
                    CortexRetrievalIndexEntry.retrieval_lookup_id.ilike(needle),
                    cast(CortexRetrievalIndexEntry.artifact_ref_json, String).ilike(needle),
                ),
            )
            .order_by(CortexRetrievalIndexEntry.created_at.desc())
            .limit(limit)
        ).all()
    )
    return [_retrieval_entry_row_v1(row) for row in rows]


def _tcre_job_row_v1(job: CortexTcreReconstructionJob) -> dict[str, Any]:
    return {
        "job_id": str(job.id),
        "job_kind": job.job_kind,
        "status": job.status,
        "scope_json": dict(job.scope_json or {}),
        "error_detail": (job.error_detail or "")[:500] or None,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


def _dedupe_by_key(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        val = str(row.get(key) or "")
        if not val or val in seen:
            continue
        seen.add(val)
        out.append(row)
    return out
