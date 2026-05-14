"""P05-19 — walk replay resolution (**``phase-05-walk-replay-doctrine.md``**)."""

from __future__ import annotations

import json
import uuid

import pytest

from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    oct_walk_request_minimal_fixture_path,
    validate_oct_walk_request_v1,
)
from vector.domains.cortex.traversal.walk_api_contract import (
    OctsWalkApiMemoryStore,
    build_stub_completed_walk_payload_v1,
)
from vector.domains.cortex.traversal.walk_replay_contract import (
    WalkReplayResolutionError,
    prepare_effective_oct_walk_request_v1,
    verify_oct_walk_replay_stub_inherit_resolution_static,
)


def test_verify_oct_walk_replay_stub_inherit_resolution_static_passes() -> None:
    out = verify_oct_walk_replay_stub_inherit_resolution_static()
    assert out["passed"] is True


def test_prepare_inherit_rejects_unknown_parent() -> None:
    store = OctsWalkApiMemoryStore()
    tid = uuid.uuid4()
    body = {
        "inherit_walk_id": str(uuid.uuid4()),
        "walk_policy": {"max_hops": 1},
        "start_node_ids": ["00000000-0000-0000-0000-000000000001"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    with pytest.raises(WalkReplayResolutionError) as ei:
        prepare_effective_oct_walk_request_v1(body, tenant_id=tid, store=store)
    assert ei.value.error_code == "source_walk_not_found"
    assert ei.value.http_status == 404


def test_prepare_inherit_rejects_policy_mismatch() -> None:
    store = OctsWalkApiMemoryStore()
    inner = json.loads(oct_walk_request_minimal_fixture_path().read_text(encoding="utf-8"))
    tid = uuid.UUID(str(inner["temporal_anchor"]["tenant_id"]))
    wid = uuid.uuid4()
    first = build_stub_completed_walk_payload_v1(inner, tenant_id=tid)
    store.insert_completed_sync(
        tenant_id=tid,
        walk_id=wid,
        request_body=dict(inner),
        walk_payload=first,
        idempotency_key=None,
    )
    bad_policy = {**inner["walk_policy"], "max_hops": 99}
    child = {
        **{k: inner[k] for k in inner if k != "temporal_anchor"},
        "inherit_walk_id": str(wid),
        "walk_policy": bad_policy,
    }
    with pytest.raises(WalkReplayResolutionError) as ei:
        prepare_effective_oct_walk_request_v1(child, tenant_id=tid, store=store)
    assert ei.value.error_code == "replay_input_mismatch"
    assert ei.value.details.get("field") == "walk_policy"


def test_validate_oct_walk_request_with_expected_hash_field() -> None:
    inner = json.loads(oct_walk_request_minimal_fixture_path().read_text(encoding="utf-8"))
    inner["expected_walk_result_hash"] = "sha256:" + "aa" * 32
    validate_oct_walk_request_v1(inner)
