"""Persist OCTS traversal receipts (durable, hash-addressed)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_octs_traversal_receipt import CortexOctsTraversalReceipt


def persist_traversal_receipt_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
    receipt_kind: str,
    body: dict[str, Any],
) -> CortexOctsTraversalReceipt:
    digest = hash_reasoning_canonical_json_sha256_v1(body)
    existing = session.scalar(
        select(CortexOctsTraversalReceipt).where(
            CortexOctsTraversalReceipt.walk_id == walk_id,
            CortexOctsTraversalReceipt.receipt_kind == receipt_kind,
        )
    )
    if existing is not None:
        if existing.receipt_digest != digest:
            raise ValueError("traversal_receipt_digest_mismatch")
        return existing
    row = CortexOctsTraversalReceipt(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        walk_id=walk_id,
        receipt_digest=digest,
        receipt_kind=receipt_kind,
        body_json=dict(body),
    )
    session.add(row)
    session.flush()
    return row
