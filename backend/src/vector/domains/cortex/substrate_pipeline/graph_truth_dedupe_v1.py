"""Wave S1 — revoke duplicate active authoritative org links (operator + dry-run)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
    snapshot_authoritative_link_topology_v1,
)

GRAPH_TRUTH_DEDUPE_SCHEMA_VERSION = 1


def plan_revoke_duplicate_authoritative_links_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """List active authoritative rows that would be revoked (keep newest per endpoint triple)."""
    tid = str(tenant_id)
    rows = session.execute(
        text(
            """
            SELECT id, source_entity_id, target_entity_id, link_type, created_at
            FROM (
              SELECT
                id,
                source_entity_id,
                target_entity_id,
                link_type,
                created_at,
                ROW_NUMBER() OVER (
                  PARTITION BY tenant_id, source_entity_id, target_entity_id, link_type
                  ORDER BY created_at DESC, id DESC
                ) AS rn
              FROM cortex_org_links
              WHERE tenant_id = :tenant
                AND revoked_at IS NULL
                AND link_authority = 'authoritative'
            ) AS ranked
            WHERE ranked.rn > 1
            ORDER BY created_at ASC, id ASC
            """
        ),
        {"tenant": tid},
    ).mappings().all()
    revoke_ids = [str(r["id"]) for r in rows]
    return {
        "schema_version": GRAPH_TRUTH_DEDUPE_SCHEMA_VERSION,
        "tenant_id": tid,
        "revoke_link_ids": revoke_ids,
        "revoke_count": len(revoke_ids),
    }


def revoke_duplicate_authoritative_links_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    apply: bool,
) -> dict[str, Any]:
    """Dry-run or apply duplicate revoke for one tenant; returns before/after topology receipt."""
    before = snapshot_authoritative_link_topology_v1(session, tenant_id=tenant_id)
    plan = plan_revoke_duplicate_authoritative_links_v1(session, tenant_id=tenant_id)
    revoked_count = 0
    if apply and plan["revoke_count"] > 0:
        tid = str(tenant_id)
        result = session.execute(
            text(
                """
                UPDATE cortex_org_links AS l
                SET revoked_at = NOW(),
                    updated_at = NOW()
                WHERE l.tenant_id = :tenant
                  AND l.id IN (
                    SELECT id FROM (
                      SELECT id,
                        ROW_NUMBER() OVER (
                          PARTITION BY tenant_id, source_entity_id, target_entity_id, link_type
                          ORDER BY created_at DESC, id DESC
                        ) AS rn
                      FROM cortex_org_links
                      WHERE tenant_id = :tenant
                        AND revoked_at IS NULL
                        AND link_authority = 'authoritative'
                    ) AS ranked
                    WHERE ranked.rn > 1
                  )
                """
            ),
            {"tenant": tid},
        )
        revoked_count = int(result.rowcount or 0)
        session.flush()
    after = snapshot_authoritative_link_topology_v1(session, tenant_id=tenant_id)
    return {
        "schema_version": GRAPH_TRUTH_DEDUPE_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "apply": apply,
        "revoked_count": revoked_count,
        "planned_revoke_count": int(plan["revoke_count"]),
        "revoke_link_ids_sample": list(plan["revoke_link_ids"])[:20],
        "topology_before": before,
        "topology_after": after,
        "unique_auth_pairs_delta": int(after.get("unique_auth_pairs") or 0)
        - int(before.get("unique_auth_pairs") or 0),
        "auth_edge_rows_delta": int(after.get("auth_edge_rows") or 0)
        - int(before.get("auth_edge_rows") or 0),
        "completed_at": datetime.now(tz=UTC).isoformat(),
    }
