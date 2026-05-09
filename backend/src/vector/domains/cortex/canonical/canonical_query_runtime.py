"""Phase 03 Step 13 — bounded canonical query + retrieval with anti-goal enforcement.

Normative: `DOCS/cortex/03-canonical/phase-03-canonical-query-doctrine.md`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import nullslast, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.canonical.identity_runtime import (
    canonical_entity_id_for_materialization,
    get_identity_anchor,
    identity_anchor_public_dict,
)
from vector.domains.cortex.canonical.provenance_runtime import (
    get_provenance_for_materialization,
    list_provenance_for_raw_record,
    provenance_public_dict,
)
from vector.domains.cortex.canonical.replay_runtime import (
    get_replay_job,
    list_replay_jobs,
    replay_job_public_dict,
)
from vector.domains.cortex.canonical.transform_runtime import materialization_public_dict
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

CanonicalQueryClass = Literal[
    "point_lookup_materialization",
    "point_lookup_identity_anchor",
    "evidence_backtrace",
    "forward_trace",
    "timeline_slice",
    "graph_neighborhood",
    "replay_debug_snapshot",
]

_ALLOWED_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "evidence_retrieval",
        "point_lookup",
        "evidence_backtrace",
        "forward_trace",
        "timeline_retrieval",
        "neighborhood_retrieval",
        "replay_debug",
    }
)
_BLOCKED_TERMS: Final[frozenset[str]] = frozenset(
    {
        "semantic",
        "similarity",
        "embedding",
        "vector",
        "ranking",
        "importance",
        "urgency",
        "summary",
        "narrative",
        "llm",
        "gpt",
        "cluster",
        "topic",
        "reasoning",
        "inference",
        "infer",
        "causal",
        "intelligence",
    }
)


class CanonicalQueryError(Exception):
    """Deterministic validation failure for canonical query requests."""


def enforce_canonical_query_anti_goals(*, intent: str | None, query_text: str | None) -> None:
    intent_norm = (intent or "evidence_retrieval").strip().lower()
    text_norm = (query_text or "").strip().lower()
    if intent_norm not in _ALLOWED_INTENTS:
        msg = "Unsupported canonical query intent; use bounded retrieval intents only."
        raise CanonicalQueryError(msg)
    if any(t in intent_norm for t in _BLOCKED_TERMS) or any(t in text_norm for t in _BLOCKED_TERMS):
        msg = "Semantic search, ranking, summaries, and intelligence-style queries are blocked."
        raise CanonicalQueryError(msg)


def _uuid_param(params: dict[str, Any], key: str) -> uuid.UUID:
    raw = params.get(key)
    if raw is None:
        raise CanonicalQueryError(f"missing_param:{key}")
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise CanonicalQueryError(f"invalid_uuid_param:{key}") from exc


def _int_param(params: dict[str, Any], key: str) -> int:
    raw = params.get(key)
    if raw is None:
        raise CanonicalQueryError(f"missing_param:{key}")
    try:
        return int(raw)
    except (ValueError, TypeError) as exc:
        raise CanonicalQueryError(f"invalid_int_param:{key}") from exc


def _optional_iso_dt(key: str, params: dict[str, Any]) -> datetime | None:
    raw = params.get(key)
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        s = str(raw).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            raise CanonicalQueryError(f"invalid_datetime_param:{key}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _neighbor_compact(mat: CortexCanonicalTransformMaterialization) -> dict[str, Any]:
    return {
        "id": mat.id,
        "bundle_id": mat.bundle_id,
        "raw_record_id": mat.raw_record_id,
        "canonical_object_kind": mat.canonical_object_kind,
        "logical_key_hash": mat.logical_key_hash,
        "temporal_ordering_key": mat.temporal_ordering_key,
        "occurred_at": mat.occurred_at,
    }


def execute_canonical_query(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    query_class: CanonicalQueryClass,
    intent: str | None = None,
    query_text: str | None = None,
    params: dict[str, Any] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Run one bounded canonical query class (raises CanonicalQueryError on invalid input)."""
    enforce_canonical_query_anti_goals(intent=intent, query_text=query_text)
    p = dict(params or {})
    lim = max(1, min(limit, 200))

    if query_class == "point_lookup_materialization":
        mid = _uuid_param(p, "materialization_id")
        mat = db.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.id == mid,
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            )
            .options(selectinload(CortexCanonicalTransformMaterialization.field_lineage))
        ).first()
        if mat is None:
            return {
                "query_class": query_class,
                "result_kind": "materialization",
                "payload": {"found": False},
                "truncation": None,
            }
        return {
            "query_class": query_class,
            "result_kind": "materialization",
            "payload": {"found": True, "materialization": materialization_public_dict(mat)},
            "truncation": None,
        }

    if query_class == "point_lookup_identity_anchor":
        eid = _uuid_param(p, "canonical_entity_id")
        row = get_identity_anchor(db, tenant_id=tenant_id, canonical_entity_id=eid)
        if row is None:
            return {
                "query_class": query_class,
                "result_kind": "identity_anchor",
                "payload": {"found": False},
                "truncation": None,
            }
        return {
            "query_class": query_class,
            "result_kind": "identity_anchor",
            "payload": {"found": True, "anchor": identity_anchor_public_dict(row)},
            "truncation": None,
        }

    if query_class == "evidence_backtrace":
        rid = _int_param(p, "raw_record_id")
        rows = list_provenance_for_raw_record(db, tenant_id=tenant_id, raw_record_id=rid, limit=lim)
        return {
            "query_class": query_class,
            "result_kind": "provenance_records",
            "payload": {
                "raw_record_id": rid,
                "records": [provenance_public_dict(r) for r in rows],
            },
            "truncation": {"capped_at": lim} if len(rows) >= lim else None,
        }

    if query_class == "forward_trace":
        mid = _uuid_param(p, "materialization_id")
        prov = get_provenance_for_materialization(db, tenant_id=tenant_id, materialization_id=mid)
        raw_ids = list(prov.primary_raw_record_ids) if prov is not None else []
        raw_stubs: list[dict[str, Any]] = []
        if p.get("include_raw_stub") is True and raw_ids:
            cap = min(10, len(raw_ids))
            qrows = db.scalars(
                select(RawIngestionRecord).where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.id.in_(raw_ids[:cap]),
                )
            ).all()
            by_id = {r.id: r for r in qrows}
            for i in raw_ids[:cap]:
                r = by_id.get(i)
                if r is not None:
                    raw_stubs.append(
                        {
                            "id": r.id,
                            "connector": r.connector,
                            "resource_type": r.resource_type,
                            "external_id": r.external_id,
                            "fetched_at": r.fetched_at,
                            "source_identity_key": r.source_identity_key,
                            "source_revision_key": r.source_revision_key,
                        }
                    )
        trunc = None
        if len(raw_ids) > 10 and p.get("include_raw_stub") is True:
            trunc = {"raw_stub_cap": 10}
        return {
            "query_class": query_class,
            "result_kind": "forward_trace",
            "payload": {
                "materialization_id": str(mid),
                "provenance": provenance_public_dict(prov) if prov is not None else None,
                "referenced_raw_record_ids": raw_ids,
                "raw_stubs": raw_stubs,
            },
            "truncation": trunc,
        }

    if query_class == "timeline_slice":
        bundle_id = p.get("bundle_id")
        bundle_filter = str(bundle_id).strip() if bundle_id else None
        start = _optional_iso_dt("occurred_after", p)
        end = _optional_iso_dt("occurred_before", p)
        q = select(CortexCanonicalTransformMaterialization).where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
        )
        if bundle_filter:
            q = q.where(CortexCanonicalTransformMaterialization.bundle_id == bundle_filter)
        if start is not None:
            q = q.where(CortexCanonicalTransformMaterialization.occurred_at >= start)
        if end is not None:
            q = q.where(CortexCanonicalTransformMaterialization.occurred_at <= end)
        q = (
            q.options(selectinload(CortexCanonicalTransformMaterialization.field_lineage))
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.temporal_ordering_key.asc()),
                CortexCanonicalTransformMaterialization.id.asc(),
            )
            .limit(lim)
        )
        mats = list(db.scalars(q).all())
        return {
            "query_class": query_class,
            "result_kind": "materializations",
            "payload": {
                "materializations": [materialization_public_dict(m) for m in mats],
            },
            "truncation": {"capped_at": lim} if len(mats) >= lim else None,
        }

    if query_class == "graph_neighborhood":
        center_id = _uuid_param(p, "center_materialization_id")
        max_n = int(p.get("max_results", 20))
        max_n = max(1, min(max_n, 50))
        center = db.scalars(
            select(CortexCanonicalTransformMaterialization).where(
                CortexCanonicalTransformMaterialization.id == center_id,
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            )
        ).first()
        if center is None:
            return {
                "query_class": query_class,
                "result_kind": "neighborhood",
                "payload": {"found": False},
                "truncation": None,
            }
        entity_id = canonical_entity_id_for_materialization(center)
        peers = db.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.bundle_id == center.bundle_id,
                CortexCanonicalTransformMaterialization.logical_key_hash == center.logical_key_hash,
                CortexCanonicalTransformMaterialization.id != center.id,
            )
            .order_by(nullslast(CortexCanonicalTransformMaterialization.temporal_ordering_key.desc()))
            .limit(max_n)
        ).all()
        trunc = len(peers) >= max_n
        return {
            "query_class": query_class,
            "result_kind": "neighborhood",
            "payload": {
                "found": True,
                "center_materialization_id": str(center.id),
                "canonical_entity_id": str(entity_id),
                "neighborhood_semantics": "same_bundle_same_logical_key_hash",
                "neighbors": [_neighbor_compact(m) for m in peers],
            },
            "truncation": {"neighbor_cap": max_n} if trunc else None,
        }

    if query_class == "replay_debug_snapshot":
        job_uuid = p.get("job_id")
        job = None
        if job_uuid is not None and str(job_uuid).strip():
            job = get_replay_job(db, tenant_id=tenant_id, job_id=_uuid_param(p, "job_id"))
        else:
            jobs = list_replay_jobs(db, tenant_id=tenant_id, limit=1)
            job = jobs[0] if jobs else None
        if job is None:
            return {
                "query_class": query_class,
                "result_kind": "replay_job",
                "payload": {"found": False},
                "truncation": None,
            }
        return {
            "query_class": query_class,
            "result_kind": "replay_job",
            "payload": {"found": True, "job": replay_job_public_dict(job)},
            "truncation": None,
        }

    raise CanonicalQueryError(f"unknown_query_class:{query_class}")
