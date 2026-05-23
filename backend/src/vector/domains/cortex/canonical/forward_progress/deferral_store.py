"""Persist and release canonical materialization deferrals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    DEFERRAL_DETAIL_FIRST_SEEN_AT,
    DEFERRAL_DETAIL_LAST_PARENT_PROBE_AT,
    DEFERRAL_DETAIL_LAST_SEEN_AT,
    DEFERRAL_DETAIL_PERMANENT_ORPHAN,
    DEFERRAL_DETAIL_RETRY_COUNT,
    DEFERRAL_QUEUE_EXTERNAL_PARENT,
    DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
    DEFERRAL_REASON_DEPENDENCY_NOT_MATERIALIZED,
    DEFERRAL_REASON_MISSING_DEPLOYMENT,
    DEFERRAL_REASON_MISSING_PAGE_PARENT,
    DEFERRAL_REASON_MISSING_PARENT,
    DEFERRAL_REASON_MISSING_PARENT_COMMIT,
    DEFERRAL_REASON_MISSING_PR,
    DEFERRAL_REASON_TOPOLOGY_ORPHAN,
    PERMANENT_ORPHAN_DEFERRAL_RETRY_THRESHOLD,
)
from vector.domains.cortex.canonical.materialization_topology_engine import classify_orphan_missing_ref
from vector.domains.cortex.canonical.replay_topology import build_node_key_index
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _now() -> datetime:
    return datetime.now(UTC)


def map_orphan_class_to_deferral_reason(orphan_class: str, *, resource_type: str) -> str:
    oc = str(orphan_class or "").strip()
    rt = str(resource_type or "").strip()
    if oc == "missing_deployment":
        return DEFERRAL_REASON_MISSING_DEPLOYMENT
    if oc == "missing_workflow":
        return DEFERRAL_REASON_DEPENDENCY_NOT_MATERIALIZED
    if oc == "missing_root_thread":
        return DEFERRAL_REASON_DEPENDENCY_NOT_MATERIALIZED
    if rt == "github.pull_request_timeline_event" and oc == "missing_parent":
        return DEFERRAL_REASON_MISSING_PR
    if rt == "github.commit" and oc == "missing_parent":
        return DEFERRAL_REASON_MISSING_PARENT_COMMIT
    if rt.startswith("notion.") and oc == "missing_parent":
        return DEFERRAL_REASON_MISSING_PAGE_PARENT
    if oc == "missing_parent":
        return DEFERRAL_REASON_MISSING_PARENT
    return DEFERRAL_REASON_TOPOLOGY_ORPHAN


def _merge_deferral_detail(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    now: datetime,
    queue: str,
    permanent_orphan_threshold: int,
) -> dict[str, Any]:
    base = dict(existing or {})
    merged = {**base, **incoming}
    first = base.get(DEFERRAL_DETAIL_FIRST_SEEN_AT)
    if not isinstance(first, str) or not first.strip():
        merged[DEFERRAL_DETAIL_FIRST_SEEN_AT] = now.isoformat()
    merged[DEFERRAL_DETAIL_LAST_SEEN_AT] = now.isoformat()
    merged[DEFERRAL_DETAIL_LAST_PARENT_PROBE_AT] = now.isoformat()
    retry = int(base.get(DEFERRAL_DETAIL_RETRY_COUNT) or 0) + 1
    merged[DEFERRAL_DETAIL_RETRY_COUNT] = retry
    if queue == DEFERRAL_QUEUE_TOPOLOGY_ORPHAN and retry >= permanent_orphan_threshold:
        merged[DEFERRAL_DETAIL_PERMANENT_ORPHAN] = True
    return merged


def record_topology_deferrals_from_plan(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    pass_key: str | None,
    plan: dict[str, Any],
    raw_rows_by_id: dict[int, RawIngestionRecord],
    cooldown_seconds: int,
    permanent_orphan_threshold: int | None = None,
) -> int:
    """Upsert deferrals for rows skipped by topology planning in this batch."""
    now = _now()
    retry_at = now + timedelta(seconds=max(5, int(cooldown_seconds)))
    orphan_threshold = max(
        1,
        int(permanent_orphan_threshold or PERMANENT_ORPHAN_DEFERRAL_RETRY_THRESHOLD),
    )
    upserted = 0
    entries: list[dict[str, Any]] = []

    existing_detail_by_rid: dict[int, dict[str, Any]] = {}
    candidate_rids = [
        int(item.get("raw_record_id") or 0)
        for block in (plan.get("deferred_dependency_queue") or [], plan.get("quarantine") or [])
        for item in block
        if isinstance(item, dict)
    ]
    candidate_rids = [rid for rid in candidate_rids if rid > 0]
    if candidate_rids:
        for row in db.scalars(
            select(CortexCanonicalMaterializationDeferral).where(
                CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
                CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
                CortexCanonicalMaterializationDeferral.raw_record_id.in_(candidate_rids),
            )
        ).all():
            existing_detail_by_rid[int(row.raw_record_id)] = (
                row.detail_json if isinstance(row.detail_json, dict) else {}
            )

    for item in plan.get("deferred_dependency_queue") or []:
        if not isinstance(item, dict):
            continue
        rid = int(item.get("raw_record_id") or 0)
        if rid <= 0:
            continue
        raw = raw_rows_by_id.get(rid)
        if raw is None:
            continue
        orphan_class = str(item.get("orphan_class") or "missing_parent")
        entries.append(
            {
                "tenant_id": tenant_id,
                "bundle_id": bundle_id,
                "raw_record_id": rid,
                "connector": str(raw.connector),
                "resource_type": str(raw.resource_type),
                "deferral_reason": map_orphan_class_to_deferral_reason(
                    orphan_class, resource_type=str(raw.resource_type)
                ),
                "queue": DEFERRAL_QUEUE_EXTERNAL_PARENT,
                "parent_raw_record_id": int(item["parent_raw_record_id"])
                if item.get("parent_raw_record_id") is not None
                else None,
                "missing_parent_ref": None,
                "pass_key": pass_key,
                "retry_ready_at": retry_at,
                "deferred_at": now,
                "detail_json": _merge_deferral_detail(
                    existing_detail_by_rid.get(rid),
                    {"orphan_class": orphan_class, "source": "stage_plan"},
                    now=now,
                    queue=DEFERRAL_QUEUE_EXTERNAL_PARENT,
                    permanent_orphan_threshold=orphan_threshold,
                ),
            }
        )

    for item in plan.get("quarantine") or []:
        if not isinstance(item, dict):
            continue
        rid = int(item.get("raw_record_id") or 0)
        if rid <= 0:
            continue
        raw = raw_rows_by_id.get(rid)
        if raw is None:
            continue
        ref = str(item.get("missing_parent_ref") or "")
        oc = str(item.get("orphan_class") or classify_orphan_missing_ref(ref, child_resource_type=str(raw.resource_type)))
        entries.append(
            {
                "tenant_id": tenant_id,
                "bundle_id": bundle_id,
                "raw_record_id": rid,
                "connector": str(raw.connector),
                "resource_type": str(raw.resource_type),
                "deferral_reason": map_orphan_class_to_deferral_reason(oc, resource_type=str(raw.resource_type)),
                "queue": DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
                "parent_raw_record_id": None,
                "missing_parent_ref": ref or None,
                "pass_key": pass_key,
                "retry_ready_at": retry_at,
                "deferred_at": now,
                "detail_json": _merge_deferral_detail(
                    existing_detail_by_rid.get(rid),
                    {"orphan_class": oc, "source": "quarantine", "missing_parent_ref": ref or None},
                    now=now,
                    queue=DEFERRAL_QUEUE_TOPOLOGY_ORPHAN,
                    permanent_orphan_threshold=orphan_threshold,
                ),
            }
        )

    if not entries:
        return 0

    for entry in entries:
        detail = entry["detail_json"] if isinstance(entry["detail_json"], dict) else {}
        is_permanent = bool(detail.get(DEFERRAL_DETAIL_PERMANENT_ORPHAN))
        effective_retry_at = (
            now + timedelta(days=3650) if is_permanent else entry["retry_ready_at"]
        )
        stmt = insert(CortexCanonicalMaterializationDeferral).values(
            {**entry, "retry_ready_at": effective_retry_at}
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "bundle_id", "raw_record_id"],
            set_={
                "deferral_reason": entry["deferral_reason"],
                "queue": entry["queue"],
                "parent_raw_record_id": entry["parent_raw_record_id"],
                "missing_parent_ref": entry["missing_parent_ref"],
                "pass_key": entry["pass_key"],
                "retry_ready_at": effective_retry_at,
                "deferred_at": entry["deferred_at"],
                "detail_json": detail,
                "updated_at": now,
            },
        )
        db.execute(stmt)
        upserted += 1
    db.flush()
    return upserted


def clear_deferral_for_raw_record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    raw_record_id: int,
) -> None:
    db.execute(
        delete(CortexCanonicalMaterializationDeferral).where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.raw_record_id == int(raw_record_id),
        )
    )


def raw_record_ids_releasable_for_missing_parent_refs(
    *,
    deferrals: list[tuple[int, str | None]],
    node_key_index: dict[str, int],
    materialized_raw_record_ids: set[int],
) -> list[int]:
    """Child deferral raw ids whose missing_parent_ref parent is materialized (pure helper)."""
    releasable: list[int] = []
    for child_raw_id, missing_ref in deferrals:
        ref = str(missing_ref or "").strip()
        if not ref:
            continue
        parent_raw_id = node_key_index.get(ref)
        if parent_raw_id is not None and parent_raw_id in materialized_raw_record_ids:
            releasable.append(int(child_raw_id))
    return releasable


def release_deferrals_when_missing_parent_ref_materialized_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> int:
    """Drop topology deferrals when the parent node key exists in raw and is materialized."""
    deferral_rows = db.execute(
        select(
            CortexCanonicalMaterializationDeferral.raw_record_id,
            CortexCanonicalMaterializationDeferral.missing_parent_ref,
        ).where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.missing_parent_ref.is_not(None),
            CortexCanonicalMaterializationDeferral.missing_parent_ref != "",
        )
    ).all()
    if not deferral_rows:
        return 0

    parent_kinds = {
        str(ref).split(":", 1)[0]
        for _rid, ref in deferral_rows
        if ref and ":" in str(ref)
    }
    if not parent_kinds:
        return 0
    # Node keys use resource_type strings (e.g. github.pull_request) — scope raw load.
    raw_rows = list(
        db.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.resource_type.in_(sorted(parent_kinds)),
            )
        ).all()
    )
    node_key_index = build_node_key_index(raw_rows)
    mat_ids = {
        int(x)
        for x in db.scalars(
            select(CortexCanonicalTransformMaterialization.raw_record_id).where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            )
        ).all()
    }
    deferrals = [(int(rid), ref) for rid, ref in deferral_rows]
    to_release = raw_record_ids_releasable_for_missing_parent_refs(
        deferrals=deferrals,
        node_key_index=node_key_index,
        materialized_raw_record_ids=mat_ids,
    )
    if not to_release:
        return 0
    res = db.execute(
        delete(CortexCanonicalMaterializationDeferral).where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.raw_record_id.in_(to_release),
        )
    )
    db.flush()
    return int(getattr(res, "rowcount", 0) or 0)


def release_deferrals_with_materialized_parents(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> int:
    """Drop deferrals whose parent raw row is now materialized under bundle."""
    subq = (
        select(CortexCanonicalMaterializationDeferral.raw_record_id)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.parent_raw_record_id.is_not(None),
        )
        .join(
            CortexCanonicalTransformMaterialization,
            (CortexCanonicalTransformMaterialization.raw_record_id == CortexCanonicalMaterializationDeferral.parent_raw_record_id)
            & (CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
            & (CortexCanonicalTransformMaterialization.bundle_id == bundle_id),
        )
    )
    ids = [int(x) for x in db.scalars(subq).all()]
    if not ids:
        return 0
    res = db.execute(
        delete(CortexCanonicalMaterializationDeferral).where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.raw_record_id.in_(ids),
        )
    )
    db.flush()
    return int(getattr(res, "rowcount", 0) or 0)


def probe_deferral_releases_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> dict[str, Any]:
    """Run release paths and return before/after deferral counts (P2-E monitoring)."""
    before = count_deferrals(db, tenant_id=tenant_id, bundle_id=bundle_id)
    released_missing_parent = release_deferrals_when_missing_parent_ref_materialized_v1(
        db, tenant_id=tenant_id, bundle_id=bundle_id
    )
    released_materialized_parent = release_deferrals_with_materialized_parents(
        db, tenant_id=tenant_id, bundle_id=bundle_id
    )
    after = count_deferrals(db, tenant_id=tenant_id, bundle_id=bundle_id)
    return {
        "released_missing_parent_ref": int(released_missing_parent),
        "released_materialized_parent": int(released_materialized_parent),
        "released_total": int(released_missing_parent) + int(released_materialized_parent),
        "deferral_counts_before": before,
        "deferral_counts_after": after,
    }


def count_deferrals(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> dict[str, int]:
    now = _now()
    total = db.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
        )
    )
    waiting = db.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.retry_ready_at > now,
        )
    )
    retry_ready = db.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.retry_ready_at <= now,
        )
    )
    permanent = db.scalar(
        select(func.count())
        .select_from(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.detail_json["permanent_orphan"].astext == "true",
        )
    )
    return {
        "deferred_total": int(total or 0),
        "deferred_waiting_cooldown": int(waiting or 0),
        "deferred_retry_ready": int(retry_ready or 0),
        "deferred_permanent_orphan": int(permanent or 0),
    }


def summarize_topology_parent_gaps(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Group missing parent refs for operator truth (ingest gap vs runtime)."""
    rows = db.execute(
        select(
            CortexCanonicalMaterializationDeferral.missing_parent_ref,
            CortexCanonicalMaterializationDeferral.resource_type,
            func.count().label("n"),
        )
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.missing_parent_ref.is_not(None),
            CortexCanonicalMaterializationDeferral.missing_parent_ref != "",
        )
        .group_by(
            CortexCanonicalMaterializationDeferral.missing_parent_ref,
            CortexCanonicalMaterializationDeferral.resource_type,
        )
        .order_by(func.count().desc())
        .limit(max(1, min(limit, 50)))
    ).all()
    out: list[dict[str, Any]] = []
    for ref, rt, n in rows:
        ref_s = str(ref)
        prefix = ref_s.split(":", 1)[0] if ref_s else ""
        out.append(
            {
                "missing_parent_ref": ref_s,
                "parent_kind": prefix,
                "child_resource_type": str(rt),
                "count": int(n or 0),
                "likely_cause": _topology_gap_likely_cause(prefix, str(rt)),
            }
        )
    return out


def _topology_gap_likely_cause(parent_kind: str, child_resource_type: str) -> str:
    pk = parent_kind.strip()
    crt = child_resource_type.strip()
    if pk == "github.pull_request_review":
        return "ingest: PR review not in raw store (review page cap or sync error)"
    if pk == "github.commit":
        return "ingest: commit SHA not in raw store (commit page window)"
    if pk == "github.workflow_run":
        return "ingest: workflow run not ingested"
    if pk == "github.deployment":
        return "ingest: deployment object not ingested"
    if pk == "github.pull_request":
        return "ingest: pull request parent missing"
    if pk == "notion.database":
        return "ingest: Notion database parent missing"
    if crt == "github.pull_request_timeline_event":
        return "ingest/runtime: timeline parent not available in tenant raw graph"
    return "runtime: parent not materialized or not ingested"


def summarize_deferral_pressure(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    sample_limit: int = 12,
) -> list[dict[str, Any]]:
    """Operator-facing deferral breakdown by resource_type + reason."""
    rows = db.execute(
        select(
            CortexCanonicalMaterializationDeferral.resource_type,
            CortexCanonicalMaterializationDeferral.deferral_reason,
            CortexCanonicalMaterializationDeferral.queue,
            func.count().label("n"),
        )
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
        )
        .group_by(
            CortexCanonicalMaterializationDeferral.resource_type,
            CortexCanonicalMaterializationDeferral.deferral_reason,
            CortexCanonicalMaterializationDeferral.queue,
        )
        .order_by(func.count().desc())
        .limit(max(1, min(sample_limit, 50)))
    ).all()
    out: list[dict[str, Any]] = []
    for rt, reason, queue, n in rows:
        out.append(
            {
                "resource_type": str(rt),
                "deferral_reason": str(reason),
                "queue": str(queue),
                "count": int(n or 0),
            }
        )
    return out
