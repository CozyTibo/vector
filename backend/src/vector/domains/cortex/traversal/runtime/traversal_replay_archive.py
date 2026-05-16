"""Archive completed OCTS walks for deterministic replay resurrection."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord
from vector.infrastructure.db.models.cortex_octs_traversal_replay_archive import CortexOctsTraversalReplayArchive


def archive_completed_walk_v1(
    session: Session,
    *,
    row: CortexOctsDurableWalkRecord,
) -> CortexOctsTraversalReplayArchive:
    snapshot: dict[str, Any] = {
        "walk_id": str(row.walk_id),
        "tenant_id": str(row.tenant_id),
        "walk_hash": row.walk_hash,
        "replay_identity": row.replay_identity,
        "traversal_epoch": row.traversal_epoch,
        "traversal_receipt_digest": row.traversal_receipt_digest,
        "request_body": dict(row.request_body or {}),
        "walk_payload": dict(row.walk_payload or {}) if row.walk_payload else None,
    }
    digest = hash_reasoning_canonical_json_sha256_v1(snapshot)
    archive = CortexOctsTraversalReplayArchive(
        id=uuid.uuid4(),
        tenant_id=row.tenant_id,
        walk_id=row.walk_id,
        archive_digest=digest,
        snapshot_json=snapshot,
    )
    session.add(archive)
    row.archived_at = archive.archived_at
    session.flush()
    return archive
