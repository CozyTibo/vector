"""P06-RUNTIME-01 — live reconstruction slice (in-memory pipeline)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.runtime.causal_edge_runtime_reducer import (
    reduce_causal_edges_v1,
)
from vector.domains.cortex.reasoning.runtime.chronology_runtime_reducer import (
    chronology_snapshot_from_materialization_v1,
    reduce_chronology_rows_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    _compare_in_memory_replay_twin_v1,
)
from vector.domains.cortex.reasoning.runtime.receipt_materialization import (
    aggregate_artifact_digest_v1,
)
from vector.domains.cortex.reasoning.runtime.runtime_scope import normalize_reconstruction_scope_v1


def _mat(mid: str, *, tok: str | None = "a|b") -> MagicMock:
    m = MagicMock()
    m.id = uuid.UUID(mid)
    m.bundle_id = "bundle.test"
    m.temporal_ordering_key = tok
    m.observed_at = None
    m.occurred_at = None
    return m


def test_normalize_scope_caps_limit() -> None:
    s = normalize_reconstruction_scope_v1({"materialization_limit": 9999})
    assert s["materialization_limit"] == 200


def test_chronology_and_edges_deterministic() -> None:
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    mats = [_mat("00000000-0000-4000-8000-000000000001"), _mat("00000000-0000-4000-8000-000000000002")]
    rows = reduce_chronology_rows_v1(mats, policy=policy, tcre_policy_bundle_digest=digest)
    assert len(rows) == 2
    snap = chronology_snapshot_from_materialization_v1(mats[0])
    assert snap["replay_safe_ordering"] == "strict"
    edges = reduce_causal_edges_v1(mats, tcre_policy_bundle_digest=digest)
    assert len(edges) == 1
    d1 = aggregate_artifact_digest_v1([r["receipt_digest"] for r in rows] + [edges[0]["tcre_causal_edge_id"]])
    d2 = aggregate_artifact_digest_v1([r["receipt_digest"] for r in rows] + [edges[0]["tcre_causal_edge_id"]])
    assert d1 == d2


def test_replay_twin_in_memory_passes() -> None:
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    db = MagicMock()
    db.scalars.return_value.all.return_value = [
        _mat("00000000-0000-4000-8000-000000000001"),
        _mat("00000000-0000-4000-8000-000000000002"),
    ]
    job = MagicMock()
    job.tenant_id = uuid.uuid4()
    job.scope_json = {"materialization_limit": 10}
    job.tcre_policy_bundle_digest = digest
    job.reasoning_rule_pack_id = str(policy["tcre_policy_pack_id"])
    out = _compare_in_memory_replay_twin_v1(db, job=job)
    assert out["replay_equivalence_passed"] is True
    assert out["replay_diff"]["identical"] is True
