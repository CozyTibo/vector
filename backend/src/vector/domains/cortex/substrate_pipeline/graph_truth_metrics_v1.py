"""Authoritative link topology metrics (unique pairs, dup factor) — Wave S1 graph truth."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

GRAPH_TRUTH_METRICS_SCHEMA_VERSION = 1


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return int(value)


def snapshot_authoritative_link_topology_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Count active authoritative links using unique endpoint pairs (not projection edge lists)."""
    tid = str(tenant_id)
    row = session.execute(
        text(
            """
            SELECT
              COUNT(*)::bigint AS auth_edge_rows,
              COUNT(DISTINCT (source_entity_id, target_entity_id, link_type))::bigint
                AS unique_auth_pairs
            FROM cortex_org_links
            WHERE tenant_id = :tenant
              AND link_authority = 'authoritative'
              AND revoked_at IS NULL
            """
        ),
        {"tenant": tid},
    ).mappings().first()
    auth_edge_rows = _to_int(row["auth_edge_rows"]) if row else 0
    unique_auth_pairs = _to_int(row["unique_auth_pairs"]) if row else 0
    dup_factor: float | None = None
    if unique_auth_pairs > 0:
        dup_factor = round(auth_edge_rows / unique_auth_pairs, 3)
    return {
        "schema_version": GRAPH_TRUTH_METRICS_SCHEMA_VERSION,
        "tenant_id": tid,
        "auth_edge_rows": auth_edge_rows,
        "unique_auth_pairs": unique_auth_pairs,
        "dup_factor": dup_factor,
        "primary_metric_key": "unique_auth_pairs",
    }
