"""Forward-progress-aware candidate selection for canonical backlog drains."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.pass_fairness import resolve_fair_pass_cursor
from vector.domains.cortex.canonical.forward_progress.pass_registry import pass_key_label
from vector.domains.cortex.canonical.transform_runtime import stub_routing_pairs
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _now_utc() -> datetime:
    from datetime import UTC, datetime

    return datetime.now(UTC)


def resolve_pass_cursor(
    pass_index: int,
    *,
    pass_cooldowns: dict[str, datetime] | None = None,
    pass_stall_counts: dict[str, int] | None = None,
    now: datetime | None = None,
) -> tuple[str, str, str, int]:
    """Return (connector, resource_type, pass_key, next_index)."""
    c, rt, pk, nxt, _skipped = resolve_fair_pass_cursor(
        pass_index,
        pass_cooldowns=pass_cooldowns,
        pass_stall_counts=pass_stall_counts,
        now=now,
    )
    return c, rt, pk, nxt


def list_forward_progress_candidate_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None,
    resource_type: str | None,
    pass_index: int,
    fetch_limit: int,
    pass_cooldowns: dict[str, datetime] | None = None,
    pass_stall_counts: dict[str, int] | None = None,
) -> tuple[list[int], bool, dict[str, object]]:
    """Select untreated routable raw ids with pass rotation and deferral exclusion."""
    lim = max(1, fetch_limit)
    meta: dict[str, object] = {}
    now = _now_utc()

    pass_key: str | None = None
    next_index = pass_index
    if connector and resource_type:
        pairs = [(connector.strip(), resource_type.strip())]
        pass_key = pass_key_label(connector, resource_type)
    elif connector:
        pairs = stub_routing_pairs(connector=connector, resource_type=None)
        pass_key = connector.strip()
    else:
        c, rt, pass_key, next_index, skipped_cooled = resolve_fair_pass_cursor(
            pass_index,
            pass_cooldowns=pass_cooldowns,
            pass_stall_counts=pass_stall_counts,
            now=now,
        )
        meta["pass_index_used"] = pass_index
        meta["pass_index_next"] = next_index
        meta["pass_key"] = pass_key
        meta["skipped_pass_on_cooldown"] = skipped_cooled
        if c and rt:
            pairs = [(c, rt)]
        else:
            pairs = stub_routing_pairs(connector=None, resource_type=None)

    if not pairs:
        return [], False, meta

    type_or = or_(
        *[
            and_(RawIngestionRecord.connector == p[0], RawIngestionRecord.resource_type == p[1])
            for p in pairs
        ]
    )
    deferral_tbl = CortexCanonicalMaterializationDeferral
    cooldown_deferral_block = (
        select(deferral_tbl.raw_record_id)
        .where(
            deferral_tbl.tenant_id == tenant_id,
            deferral_tbl.bundle_id == bundle_id,
            deferral_tbl.raw_record_id == RawIngestionRecord.id,
            deferral_tbl.retry_ready_at > now,
            deferral_tbl.detail_json["permanent_orphan"].astext.is_distinct_from("true"),
        )
        .correlate(RawIngestionRecord)
        .exists()
    )
    permanent_deferral_block = (
        select(deferral_tbl.raw_record_id)
        .where(
            deferral_tbl.tenant_id == tenant_id,
            deferral_tbl.bundle_id == bundle_id,
            deferral_tbl.raw_record_id == RawIngestionRecord.id,
            deferral_tbl.detail_json["permanent_orphan"].astext == "true",
        )
        .correlate(RawIngestionRecord)
        .exists()
    )

    stmt = (
        select(RawIngestionRecord.id)
        .outerjoin(
            CortexCanonicalTransformMaterialization,
            and_(
                CortexCanonicalTransformMaterialization.raw_record_id == RawIngestionRecord.id,
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.bundle_id == bundle_id,
            ),
        )
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            type_or,
            CortexCanonicalTransformMaterialization.id.is_(None),
            ~cooldown_deferral_block,
            ~permanent_deferral_block,
        )
        .order_by(RawIngestionRecord.id.asc())
        .limit(lim + 1)
    )
    rows = [int(x) for x in db.scalars(stmt).all()]
    more_remain = len(rows) > lim
    meta.setdefault("pass_key", pass_key)
    meta.setdefault("pass_index_next", next_index)
    return rows[:lim], more_remain, meta
