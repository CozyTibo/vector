"""Traversal replay equivalence verification."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.traversal.runtime.traversal_lineage_repository import (
    find_walks_by_replay_identity_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord


def verify_traversal_replay_equivalence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    replay_identity: str,
) -> dict[str, Any]:
    walks = find_walks_by_replay_identity_v1(
        session, tenant_id=tenant_id, replay_identity=replay_identity
    )
    hashes = sorted({w.walk_hash for w in walks if w.walk_hash})
    equivalent = len(hashes) <= 1
    receipt_body = {
        "replay_identity": replay_identity,
        "walk_count": len(walks),
        "distinct_walk_hashes": hashes,
        "equivalent": equivalent,
    }
    if not equivalent:
        receipt_body["divergence_source"] = "walk_hash_mismatch"
    return {
        **receipt_body,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(receipt_body),
    }


def build_replay_chaos_receipt_v1(
    *,
    scenario: str,
    equivalent: bool,
    detail: dict[str, Any],
) -> dict[str, Any]:
    body = {"scenario": scenario, "equivalent": equivalent, "detail": detail}
    return {**body, "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body)}
