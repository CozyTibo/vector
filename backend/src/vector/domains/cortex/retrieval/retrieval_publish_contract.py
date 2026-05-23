"""Phase B step B1 — single publish contract for pipeline retrieval materialization.

Law R-REC-1 (binding): materialize all entries under one ``BUILDING`` epoch, then publish once;
every entry in that pass must share ``index_epoch`` with ``get_published_index_epoch_v1``.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

_ISLAND_SCOPE_KEY_V1: Final[str] = "island_scope_id"
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_index_epoch_row_v1,
    get_published_index_epoch_v1,
    publish_retrieval_index_epoch_v1,
    start_retrieval_index_build_v1,
    transition_retrieval_index_build_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch

RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION: Final[int] = 1
P0_B1_STEP: Final[str] = "step_b1_retrieval_publish_contract"


def begin_pipeline_retrieval_index_build_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None = None,
) -> tuple[CortexRetrievalIndexEpoch, str]:
    """Start epoch in ``BUILDING`` — entries must not publish until finalize."""
    row = start_retrieval_index_build_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    row = transition_retrieval_index_build_v1(session, epoch_row=row, to_state="BUILDING")
    return row, str(row.index_epoch)


def audit_published_epoch_entry_alignment_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
) -> dict[str, Any]:
    """Verify all rows for ``index_epoch`` align with the published epoch getter."""
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    epoch = index_epoch.strip()
    entries_in_epoch = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == epoch,
            )
        )
        or 0
    )
    entries_off_epoch = int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch != epoch,
                CortexRetrievalIndexEntry.index_epoch.isnot(None),
            )
        )
        or 0
    )
    tagged_in_epoch = 0
    if entries_in_epoch > 0:
        rows = list(
            session.scalars(
                select(CortexRetrievalIndexEntry.omission_summary).where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.index_epoch == epoch,
                )
            ).all()
        )
        tagged_in_epoch = sum(
            1
            for summary in rows
            if isinstance(summary, dict) and bool(summary.get(_ISLAND_SCOPE_KEY_V1))
        )
    epoch_row = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=epoch)
    return {
        "published_index_epoch": published,
        "materialized_index_epoch": epoch,
        "epochs_align": bool(published) and published == epoch,
        "build_state": epoch_row.build_state if epoch_row else None,
        "entries_in_materialized_epoch": entries_in_epoch,
        "entries_off_materialized_epoch": entries_off_epoch,
        "entries_with_island_scope_in_epoch": tagged_in_epoch,
        "all_entries_share_published_epoch": bool(published)
        and published == epoch
        and entries_in_epoch > 0,
    }


def finalize_pipeline_retrieval_index_build_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
    pipeline_run_id: uuid.UUID | None = None,
    sync_island_registry: bool = True,
) -> dict[str, Any]:
    """Publish barrier after materialization; validate epoch alignment (R-REC-1)."""
    published = publish_retrieval_index_epoch_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
    )
    audit = audit_published_epoch_entry_alignment_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
    )
    out: dict[str, Any] = {
        "publish_contract_schema_version": RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
        "build_state": published.build_state,
        "entry_count": int(published.entry_count or 0),
        "output_index_hash": published.output_index_hash,
        "published_index_epoch": get_published_index_epoch_v1(session, tenant_id=tenant_id),
        "index_epoch": index_epoch,
        "publish_contract_audit": audit,
        "ok": published.build_state == "PUBLISHED" and bool(audit.get("epochs_align")),
    }
    if sync_island_registry and pipeline_run_id is not None:
        try:
            from vector.domains.cortex.operational_runtime.execution_island_registry import (
                is_execution_island_registry_enabled_v1,
                sync_execution_island_registry_v1,
            )

            if is_execution_island_registry_enabled_v1():
                out["island_registry_sync"] = sync_execution_island_registry_v1(
                    session,
                    tenant_id=tenant_id,
                )
        except Exception as exc:  # noqa: BLE001
            out["island_registry_sync"] = {"synced": False, "error": str(exc)[:500]}
    return out


def materialize_entry_respecting_publish_contract_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str,
    auto_publish: bool,
    **kwargs: Any,
) -> Any:
    """Delegate to entry materializer without publishing while epoch is ``BUILDING``."""
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        materialize_retrieval_index_entry_v1,
    )

    epoch_row = get_index_epoch_row_v1(session, tenant_id=tenant_id, index_epoch=index_epoch)
    defer_publish = bool(
        epoch_row is not None and epoch_row.build_state == "BUILDING"
    )
    return materialize_retrieval_index_entry_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
        auto_publish=auto_publish and not defer_publish,
        **kwargs,
    )
