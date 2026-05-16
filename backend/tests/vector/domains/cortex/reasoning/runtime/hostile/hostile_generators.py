"""Deterministic hostile scenario builders (no probabilistic inference)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

from vector.domains.cortex.traversal.walk_api_contract import (
    build_stub_completed_walk_payload_v1,
    octs_walk_api_memory_store_v1,
)


def hostile_materialization(
    mid: str,
    *,
    temporal_key: str | None = "a|1",
    occurred_after_observed: bool = False,
    snapshot_extra: dict[str, Any] | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = uuid.UUID(mid)
    m.bundle_id = "bundle.hostile"
    m.temporal_ordering_key = temporal_key
    m.canonical_object_kind = "meeting"
    m.observed_at = None
    m.occurred_at = None
    if occurred_after_observed:
        from datetime import UTC, datetime

        m.occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
        m.observed_at = datetime(2026, 1, 2, tzinfo=UTC)
    snap = dict(snapshot_extra or {})
    m.emitted_snapshot_json = snap
    return m


def seed_octs_walk_v1(
    tenant_id: uuid.UUID,
    *,
    walk_id: uuid.UUID | None = None,
    hop_count: int = 2,
) -> tuple[uuid.UUID, str]:
    """Insert completed OCTS walk; return (walk_id, walk_result_hash)."""
    wid = walk_id or uuid.uuid4()
    request = {
        "temporal_anchor": {
            "tenant_id": str(tenant_id),
            "export_id": "00000000-0000-4000-8000-000000000099",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "aa" * 32,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "walk_policy": {
            "max_hops": hop_count,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    payload = build_stub_completed_walk_payload_v1(request, tenant_id=tenant_id)
    octs_walk_api_memory_store_v1().insert_completed_sync(
        tenant_id=tenant_id,
        walk_id=wid,
        request_body={"mode": "hostile_fixture"},
        walk_payload=payload,
        idempotency_key=None,
    )
    wh = str((payload.get("walk_result") or {}).get("walk_result_hash") or "")
    return wid, wh
