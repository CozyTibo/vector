"""S3.6 — retrieval index row inspector (good vs useless org_link mirrors)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import EXECUTION_INDEX_KINDS_V1
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

RETRIEVAL_INDEX_ROW_INSPECTOR_SCHEMA_VERSION: Final[int] = 1

ROW_CLASS_GOOD_EXECUTION_V1: Final[str] = "good_execution_row"
ROW_CLASS_GOOD_SUPPORTING_V1: Final[str] = "good_supporting_link"
ROW_CLASS_USELESS_MIRROR_V1: Final[str] = "useless_mirror"
ROW_CLASS_NEUTRAL_V1: Final[str] = "neutral"


def _execution_context_for_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> dict[str, Any]:
    epoch = index_epoch.strip()
    execution_rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry).where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == epoch,
                CortexRetrievalIndexEntry.index_kind.in_(sorted(EXECUTION_INDEX_KINDS_V1)),
            )
        ).all()
    )
    traversal_epochs: set[str] = set()
    for row in execution_rows:
        te = str(row.traversal_epoch or "").strip()
        if te:
            traversal_epochs.add(te)
    return {
        "execution_row_count": len(execution_rows),
        "execution_traversal_epochs": sorted(traversal_epochs),
        "has_execution_rows": len(execution_rows) > 0,
    }


def classify_retrieval_index_row_v1(
    row: CortexRetrievalIndexEntry,
    *,
    execution_context: dict[str, Any],
) -> str:
    """Classify one index row for operator inspection."""
    kind = str(row.index_kind or "")
    if kind in EXECUTION_INDEX_KINDS_V1:
        return ROW_CLASS_GOOD_EXECUTION_V1
    if kind != "org_link":
        return ROW_CLASS_NEUTRAL_V1

    if not execution_context.get("has_execution_rows"):
        return ROW_CLASS_USELESS_MIRROR_V1

    traversal_epochs = set(execution_context.get("execution_traversal_epochs") or [])
    row_te = str(row.traversal_epoch or "").strip()
    if row_te:
        if row_te in traversal_epochs:
            return ROW_CLASS_GOOD_SUPPORTING_V1
        return ROW_CLASS_USELESS_MIRROR_V1

    # org_link without traversal_epoch but execution exists in epoch — supporting context
    return ROW_CLASS_GOOD_SUPPORTING_V1


def build_retrieval_index_row_inspector_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
    index_kind: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Sample index rows with good vs useless classification (S3.6)."""
    epoch = index_epoch.strip()
    lim = max(1, min(int(limit), 200))
    execution_context = _execution_context_for_epoch_v1(
        session, tenant_id=tenant_id, index_epoch=epoch
    )

    q = select(CortexRetrievalIndexEntry).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
        CortexRetrievalIndexEntry.index_epoch == epoch,
    )
    if index_kind:
        q = q.where(CortexRetrievalIndexEntry.index_kind == str(index_kind).strip())
    q = q.order_by(CortexRetrievalIndexEntry.created_at.desc()).limit(lim)

    samples: list[dict[str, Any]] = []
    counts: dict[str, int] = {
        ROW_CLASS_GOOD_EXECUTION_V1: 0,
        ROW_CLASS_GOOD_SUPPORTING_V1: 0,
        ROW_CLASS_USELESS_MIRROR_V1: 0,
        ROW_CLASS_NEUTRAL_V1: 0,
    }
    for row in session.scalars(q).all():
        row_class = classify_retrieval_index_row_v1(row, execution_context=execution_context)
        counts[row_class] = int(counts.get(row_class, 0)) + 1
        samples.append(
            {
                "retrieval_lookup_id": row.retrieval_lookup_id,
                "index_kind": row.index_kind,
                "index_key": row.index_key,
                "traversal_epoch": row.traversal_epoch,
                "row_class": row_class,
                "useless_mirror": row_class == ROW_CLASS_USELESS_MIRROR_V1,
                "artifact_ref": dict(row.artifact_ref_json or {}),
            }
        )

    return {
        "schema_version": RETRIEVAL_INDEX_ROW_INSPECTOR_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "index_epoch": epoch,
        "index_kind_filter": index_kind,
        "sample_limit": lim,
        "execution_context": execution_context,
        "row_class_counts": counts,
        "samples": samples,
        "useless_mirror_count": counts[ROW_CLASS_USELESS_MIRROR_V1],
        "good_execution_count": counts[ROW_CLASS_GOOD_EXECUTION_V1],
    }
