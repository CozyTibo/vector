"""Replay chaos — durable walk replay identity survives re-insert."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.traversal.runtime.durable_walk_store import (
    OctsWalkApiDurableStore,
    extract_walk_replay_metadata_v1,
)
def _minimal_walk_payload(*, walk_hash: str = "deadbeef") -> dict:
    return {
        "walk_result": {
            "walk_result_hash": walk_hash,
            "hash_body": {"termination_reason": "completed", "hop_receipts": [], "traversal_epoch": "e1"},
        },
        "telemetry": {"engine_build_id": "phase07-test"},
    }


def test_extract_walk_replay_metadata_deterministic() -> None:
    tid = uuid.uuid4()
    req = {
        "walk_policy": {"max_depth": 4, "max_frontier": 10},
        "temporal_anchor": {"tenant_id": str(tid), "snapshot_unix_ns": 1},
        "exploration_mode": False,
    }
    payload = _minimal_walk_payload()
    a = extract_walk_replay_metadata_v1(request_body=req, walk_payload=payload, replay_lineage=None)
    b = extract_walk_replay_metadata_v1(request_body=req, walk_payload=payload, replay_lineage=None)
    assert a["replay_identity"] == b["replay_identity"]
    assert a["walk_hash"] == b["walk_hash"]


def test_resolve_octs_walk_store_prefers_durable_with_session() -> None:
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
    from vector.domains.cortex.traversal.walk_api_contract import octs_walk_api_memory_store_v1

    session = MagicMock()
    assert resolve_octs_walk_store_v1(session).__class__.__name__ == "OctsWalkApiDurableStore"
    assert resolve_octs_walk_store_v1(None) is octs_walk_api_memory_store_v1()
