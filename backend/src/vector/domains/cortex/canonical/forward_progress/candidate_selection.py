"""Forward-progress-aware candidate selection for canonical backlog drains."""

from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.pass_registry import (
    all_canonical_passes,
    pass_key_label,
)
from vector.domains.cortex.canonical.transform_runtime import stub_routing_pairs
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _now_utc():
    from datetime import UTC, datetime

    return datetime.now(UTC)


def resolve_pass_cursor(pass_index: int) -> tuple[str, str, str, int]:
    """Return (connector, resource_type, pass_key, next_index)."""
    passes = all_canonical_passes()
    if not passes:
        return "", "", "", 0
    idx = int(pass_index) % len(passes)
    c, rt = passes[idx]
    return c, rt, pass_key_label(c, rt), (idx + 1) % len(passes)


def list_forward_progress_candidate_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    connector: str | None,
    resource_type: str | None,
    pass_index: int,
    fetch_limit: int,
) -> tuple[list[int], bool, dict[str, object]]:
    """Select untreated routable raw ids with pass rotation and deferral exclusion."""
    lim = max(1, fetch_limit)
    meta: dict[str, object] = {}

    pass_key: str | None = None
    next_index = pass_index
    if connector and resource_type:
        pairs = [(connector.strip(), resource_type.strip())]
        pass_key = pass_key_label(connector, resource_type)
    elif connector:
        pairs = stub_routing_pairs(connector=connector, resource_type=None)
        pass_key = connector.strip()
    else:
        c, rt, pass_key, next_index = resolve_pass_cursor(pass_index)
        meta["pass_index_used"] = pass_index
        meta["pass_index_next"] = next_index
        meta["pass_key"] = pass_key
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
    now = _now_utc()
    deferral_block = (
        select(CortexCanonicalMaterializationDeferral.raw_record_id)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bundle_id,
            CortexCanonicalMaterializationDeferral.retry_ready_at > now,
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
            ~deferral_block,
        )
        .order_by(RawIngestionRecord.id.asc())
        .limit(lim + 1)
    )
    rows = [int(x) for x in db.scalars(stmt).all()]
    more_remain = len(rows) > lim
    meta.setdefault("pass_key", pass_key)
    meta.setdefault("pass_index_next", next_index)
    return rows[:lim], more_remain, meta


def list_untreated_routable_count_estimate(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> int:
    pairs = stub_routing_pairs(connector=None, resource_type=None)
    if not pairs:
        return 0
    type_or = or_(
        *[
            and_(RawIngestionRecord.connector == p[0], RawIngestionRecord.resource_type == p[1])
            for p in pairs
        ]
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
        )
    )
    return len(db.scalars(stmt).all())
