"""P2-C — execution island registry (component scope persisted per tenant)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density import count_active_org_entities_v1
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    evaluate_traversal_propagation_v1,
    get_traversal_min_component_entities_v1,
    is_component_traversal_schedule_enabled_v1,
    list_eligible_traversal_components_v1,
    stable_component_scope_id_v1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    classify_tenant_graph_orphans_v1,
)
from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    P1_C_ISLAND_SCOPE_KEY_V1,
    walk_record_intersects_island_v1,
)
from vector.infrastructure.db.models.cortex_execution_island_registry import (
    CortexExecutionIslandRegistry,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord

P2_C_REGISTRY_SCHEMA_VERSION_V1: Final[int] = 1
DEFAULT_MAX_ENTITY_IDS_PERSISTED_V1: Final[int] = 512


def is_execution_island_registry_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_execution_island_registry_enabled)
    except Exception:  # noqa: BLE001
        return True


def get_island_registry_max_entity_ids_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(
            1,
            int(get_settings().cortex_execution_island_registry_max_entity_ids),
        )
    except Exception:  # noqa: BLE001
        return DEFAULT_MAX_ENTITY_IDS_PERSISTED_V1


def count_authoritative_edges_in_component_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    component: frozenset[uuid.UUID],
) -> int:
    if len(component) < 2:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
                CortexOrgLink.source_entity_id.in_(component),
                CortexOrgLink.target_entity_id.in_(component),
            )
        )
        or 0
    )


def _last_walk_at_for_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island: frozenset[uuid.UUID],
) -> datetime | None:
    latest: datetime | None = None
    for record in session.scalars(
        select(CortexOctsDurableWalkRecord).where(
            CortexOctsDurableWalkRecord.tenant_id == tenant_id,
            CortexOctsDurableWalkRecord.status == "completed",
        )
    ).all():
        if not record.walk_payload or not walk_record_intersects_island_v1(record, island):
            continue
        ts = record.updated_at or record.created_at
        if ts is None:
            continue
        if latest is None or ts > latest:
            latest = ts
    return latest


def _last_retrieval_epoch_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str,
) -> str | None:
    epochs: list[str] = []
    for row in session.scalars(
        select(CortexRetrievalIndexEntry).where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
    ).all():
        scope = str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "")
        if scope == island_scope_id and row.index_epoch:
            epochs.append(str(row.index_epoch))
    if not epochs:
        return None
    return max(epochs)


def _entity_ids_payload_v1(
    component: frozenset[uuid.UUID],
    *,
    max_ids: int,
) -> tuple[list[str], bool]:
    sorted_ids = sorted(str(e) for e in component)
    truncated = len(sorted_ids) > max_ids
    return sorted_ids[:max_ids], truncated


def sync_execution_island_registry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Rebuild persisted island rows from authoritative graph components (P2-C)."""
    if not is_execution_island_registry_enabled_v1():
        return {"synced": False, "reason": "registry_disabled"}

    min_entities = get_traversal_min_component_entities_v1()
    eligible = list_eligible_traversal_components_v1(
        session,
        tenant_id=tenant_id,
        min_entities=min_entities,
    )
    snapshot_at = datetime.now(UTC)
    max_ids = get_island_registry_max_entity_ids_v1()

    session.execute(
        delete(CortexExecutionIslandRegistry).where(
            CortexExecutionIslandRegistry.tenant_id == tenant_id
        )
    )

    rows: list[CortexExecutionIslandRegistry] = []
    for component in eligible:
        scope_id = stable_component_scope_id_v1(component)
        entity_ids, truncated = _entity_ids_payload_v1(component, max_ids=max_ids)
        rows.append(
            CortexExecutionIslandRegistry(
                tenant_id=tenant_id,
                island_scope_id=scope_id,
                entity_count=len(component),
                authoritative_edge_count=count_authoritative_edges_in_component_v1(
                    session,
                    tenant_id=tenant_id,
                    component=component,
                ),
                entity_ids=entity_ids,
                last_walk_at=_last_walk_at_for_island_v1(
                    session, tenant_id=tenant_id, island=component
                ),
                last_retrieval_epoch=_last_retrieval_epoch_for_scope_v1(
                    session,
                    tenant_id=tenant_id,
                    island_scope_id=scope_id,
                ),
                registry_snapshot_at=snapshot_at,
                detail_json={
                    "entity_ids_truncated": truncated,
                    "min_component_entities": min_entities,
                },
            )
        )

    if rows:
        session.add_all(rows)
    session.flush()

    return {
        "synced": True,
        "registry_schema_version": P2_C_REGISTRY_SCHEMA_VERSION_V1,
        "island_count": len(rows),
        "islands_eligible_count": len(eligible),
        "registry_snapshot_at": snapshot_at.isoformat(),
    }


def list_execution_island_registry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Read persisted registry rows for admin / proof surfaces."""
    rows = list(
        session.scalars(
            select(CortexExecutionIslandRegistry)
            .where(CortexExecutionIslandRegistry.tenant_id == tenant_id)
            .order_by(CortexExecutionIslandRegistry.entity_count.desc())
        ).all()
    )
    return [
        {
            "island_scope_id": row.island_scope_id,
            "entity_count": int(row.entity_count),
            "authoritative_edge_count": int(row.authoritative_edge_count),
            "entity_ids": list(row.entity_ids or []),
            "entity_ids_count": len(row.entity_ids or []),
            "last_walk_at": row.last_walk_at.isoformat() if row.last_walk_at else None,
            "last_retrieval_epoch": row.last_retrieval_epoch,
            "registry_snapshot_at": row.registry_snapshot_at.isoformat()
            if row.registry_snapshot_at
            else None,
            "detail_json": dict(row.detail_json or {}),
        }
        for row in rows
    ]


def build_island_registry_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    sync: bool = True,
) -> dict[str, Any]:
    """Admin inspect block: propagation schedule + persisted islands."""
    orphans = classify_tenant_graph_orphans_v1(session, tenant_id=tenant_id)
    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    propagation = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tenant_id,
        linked_entity_count=int(orphans.get("linked_entity_count") or 0),
        entity_count=entity_count,
        orphan_disconnected_count=int(orphans.get("orphan_disconnected_count") or 0),
        orphan_identity_unresolved_count=int(
            orphans.get("orphan_identity_unresolved_count") or 0
        ),
    )
    sync_result: dict[str, Any] = {"synced": False}
    if sync and is_execution_island_registry_enabled_v1():
        sync_result = sync_execution_island_registry_v1(session, tenant_id=tenant_id)

    islands = list_execution_island_registry_v1(session, tenant_id=tenant_id)
    return {
        "surface_kind": "execution_island_registry",
        "registry_enabled": is_execution_island_registry_enabled_v1(),
        "component_schedule_enabled": is_component_traversal_schedule_enabled_v1(),
        "traversal_propagation": propagation,
        "sync": sync_result,
        "island_count": len(islands),
        "islands": islands,
    }
