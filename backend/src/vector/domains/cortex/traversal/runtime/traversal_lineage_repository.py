"""Walk replay lineage (walk → replay → replay-of-replay)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord


def list_walk_replay_lineage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
    max_depth: int = 16,
) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    current_id: uuid.UUID | None = walk_id
    depth = 0
    while current_id is not None and depth < max_depth:
        row = session.get(CortexOctsDurableWalkRecord, current_id)
        if row is None or row.tenant_id != tenant_id:
            break
        chain.append(
            {
                "walk_id": str(row.walk_id),
                "replay_identity": row.replay_identity,
                "walk_hash": row.walk_hash,
                "parent_walk_id": str(row.parent_walk_id) if row.parent_walk_id else None,
                "depth": depth,
            }
        )
        current_id = row.parent_walk_id
        depth += 1
    return list(reversed(chain))


def find_walks_by_replay_identity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    replay_identity: str,
) -> list[CortexOctsDurableWalkRecord]:
    return list(
        session.scalars(
            select(CortexOctsDurableWalkRecord)
            .where(
                CortexOctsDurableWalkRecord.tenant_id == tenant_id,
                CortexOctsDurableWalkRecord.replay_identity == replay_identity,
            )
            .order_by(CortexOctsDurableWalkRecord.created_at.asc())
        ).all()
    )
