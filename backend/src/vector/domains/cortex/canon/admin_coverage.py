"""Admin canon coverage — per-connector gaps between raw exhaust and materialized entities."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.resource_type_registry import (
    disposition_by_resource_type,
    entity_type_for_resource_type,
    registry_rows,
)
from vector.domains.cortex.ingestion.admin_recent_raw import aggregate_raw_ingestion_stats
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource

_CONNECTORS = ("slack", "github", "linear", "notion", "calls")


def _connector_from_resource_type(resource_type: str) -> str:
    if "." in resource_type:
        return resource_type.split(".", 1)[0]
    return "unknown"


def build_canon_coverage_payload(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Per-connector resource_type rows with raw counts, entity counts, and gap hints."""
    disposition = disposition_by_resource_type()
    raw_rows = aggregate_raw_ingestion_stats(session, tenant_id, include_health_rows=False)
    raw_by_type = {r["resource_type"]: int(r["row_count"]) for r in raw_rows}

    entity_by_resource_type = {
        str(rt): int(n)
        for rt, n in session.execute(
            select(
                CanonEntitySource.resource_type,
                func.count(func.distinct(CanonEntitySource.canon_entity_id)),
            )
            .join(CanonEntity, CanonEntity.id == CanonEntitySource.canon_entity_id)
            .where(CanonEntity.tenant_id == tenant_id)
            .group_by(CanonEntitySource.resource_type),
        ).all()
    }

    entities_total_by_connector = {
        str(conn): int(n)
        for conn, n in session.execute(
            select(CanonEntity.connector, func.count())
            .where(CanonEntity.tenant_id == tenant_id)
            .group_by(CanonEntity.connector),
        ).all()
    }

    all_types = set(raw_by_type) | set(disposition)
    connectors_out: list[dict[str, Any]] = []

    for connector in _CONNECTORS:
        resource_types: list[dict[str, Any]] = []
        raw_total = 0
        entity_total = entities_total_by_connector.get(connector, 0)
        gap_unmaterialized = 0
        gap_unknown = 0

        for rt in sorted(all_types):
            if _connector_from_resource_type(rt) != connector:
                continue
            raw_n = raw_by_type.get(rt, 0)
            if raw_n == 0 and rt not in disposition:
                continue
            disp = disposition.get(rt, "unknown")
            et = entity_type_for_resource_type(rt)
            ent_n = entity_by_resource_type.get(rt, 0)
            gap: str | None = None
            if disp == "map":
                if raw_n > 0 and ent_n == 0:
                    gap = "unmaterialized"
                    gap_unmaterialized += raw_n
                elif raw_n == 0:
                    gap = "no_raw"
            elif disp == "unknown" and raw_n > 0:
                gap = "unknown_type"
                gap_unknown += raw_n
            elif disp == "defer" and raw_n > 0:
                gap = "deferred"
            elif disp == "skip" and raw_n > 0:
                gap = "skipped"

            raw_total += raw_n
            resource_types.append(
                {
                    "resource_type": rt,
                    "disposition": disp,
                    "entity_type": et,
                    "raw_row_count": raw_n,
                    "canon_entity_count": ent_n if disp == "map" else 0,
                    "gap": gap,
                },
            )

        connectors_out.append(
            {
                "connector": connector,
                "raw_row_count": raw_total,
                "canon_entity_count": entity_total,
                "unmaterialized_raw_rows": gap_unmaterialized,
                "unknown_type_raw_rows": gap_unknown,
                "resource_types": resource_types,
            },
        )

    return {
        "tenant_id": str(tenant_id),
        "connectors": connectors_out,
        "registry_row_count": len(registry_rows()),
    }


def aggregate_canon_entity_stats(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    connector: str | None = None,
    entity_type: str | None = None,
) -> list[dict[str, Any]]:
    """Counts by entity_type (and connector) for listing filters."""
    stmt = (
        select(
            CanonEntity.connector,
            CanonEntity.entity_type,
            func.count().label("row_count"),
            func.max(CanonEntity.materialized_at).label("newest"),
            func.min(CanonEntity.materialized_at).label("oldest"),
        )
        .where(CanonEntity.tenant_id == tenant_id)
        .group_by(CanonEntity.connector, CanonEntity.entity_type)
    )
    if connector:
        stmt = stmt.where(CanonEntity.connector == connector)
    if entity_type:
        stmt = stmt.where(CanonEntity.entity_type == entity_type)

    out: list[dict[str, Any]] = []
    for conn, et, n, newest, oldest in session.execute(stmt).all():
        out.append(
            {
                "connector": str(conn),
                "entity_type": str(et),
                "row_count": int(n),
                "newest_materialized_at": newest.isoformat() if newest else None,
                "oldest_materialized_at": oldest.isoformat() if oldest else None,
            },
        )
    out.sort(key=lambda r: (-r["row_count"], r["connector"], r["entity_type"]))
    return out
