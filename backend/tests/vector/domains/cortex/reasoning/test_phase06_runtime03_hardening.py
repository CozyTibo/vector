"""P06-RUNTIME-03 — OCTS binding, edge expansion, hostile replay."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.runtime.chronology_runtime_reducer import reduce_chronology_rows_v1
from vector.domains.cortex.reasoning.runtime.octs_binding_projection import (
    OctsBindingError,
    TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH,
    TRAVERSAL_BINDING_STATUS_UNBOUND,
    assert_replay_identity_stable_v1,
    build_octs_replay_identity_envelope_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    _compare_in_memory_replay_twin_v1,
)
from vector.domains.cortex.reasoning.runtime.runtime_scope import normalize_reconstruction_scope_v1
from vector.domains.cortex.reasoning.runtime.edge_expansion_runtime import (
    reduce_all_expanded_edges_v1,
    reduce_degradation_propagation_edges_v1,
)

from tests.vector.domains.cortex.reasoning.runtime.hostile.hostile_generators import (
    hostile_materialization,
    seed_octs_walk_v1,
)


def test_octs_unbound_non_strict() -> None:
    tid = uuid.uuid4()
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    mats = [hostile_materialization("00000000-0000-4000-8000-000000000099")]
    rows = reduce_chronology_rows_v1(mats, policy=policy, tcre_policy_bundle_digest=digest)
    env = build_octs_replay_identity_envelope_v1(
        tenant_id=tid,
        scope=normalize_reconstruction_scope_v1({}),
        chronology_rows=rows,
        tcre_policy_bundle_digest=digest,
        reasoning_rule_pack_id=str(policy["tcre_policy_pack_id"]),
        strict_binding=False,
    )
    assert env["binding_legality_class"] == TRAVERSAL_BINDING_STATUS_UNBOUND


def test_octs_strict_requires_walk() -> None:
    tid = uuid.uuid4()
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    with pytest.raises(OctsBindingError):
        build_octs_replay_identity_envelope_v1(
            tenant_id=tid,
            scope=normalize_reconstruction_scope_v1(
                {"octs_walk_id": str(uuid.uuid4()), "octs_strict_binding": True}
            ),
            chronology_rows=[],
            tcre_policy_bundle_digest=digest,
            reasoning_rule_pack_id=str(policy["tcre_policy_pack_id"]),
            strict_binding=True,
        )


def test_octs_epoch_mismatch_hostile() -> None:
    tid = uuid.uuid4()
    wid, wh = seed_octs_walk_v1(tid)
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    scope = normalize_reconstruction_scope_v1(
        {
            "octs_walk_id": str(wid),
            "expected_walk_result_hash": "sha256:" + "ff" * 32,
        }
    )
    env = build_octs_replay_identity_envelope_v1(
        tenant_id=tid,
        scope=scope,
        chronology_rows=[],
        tcre_policy_bundle_digest=digest,
        reasoning_rule_pack_id=str(policy["tcre_policy_pack_id"]),
        strict_binding=False,
    )
    assert env["binding_legality_class"] == TRAVERSAL_BINDING_STATUS_EPOCH_MISMATCH
    assert wh != scope["expected_walk_result_hash"]


def test_replay_identity_drift_assertion() -> None:
    with pytest.raises(OctsBindingError):
        assert_replay_identity_stable_v1(
            {"ingestion_replay_identity": "a"},
            {"ingestion_replay_identity": "b"},
        )


def test_degradation_propagation_edges() -> None:
    rows = [
        {"materialization_id": "m1", "chronology_legality_class": "chronology_degraded"},
        {"materialization_id": "m2", "chronology_legality_class": "chronology_degraded"},
    ]
    edges = reduce_degradation_propagation_edges_v1(
        rows, tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    )
    assert len(edges) == 1
    assert edges[0]["edge_body"]["tcre_causal_edge_kind"] == "tcre_follow_through_gap"


def test_expanded_edges_from_explicit_refs() -> None:
    m1 = hostile_materialization(
        "00000000-0000-4000-8000-000000000001",
        snapshot_extra={"depends_on_issue_id": "ISSUE-42", "workflow_run_id": "wf-1"},
    )
    m2 = hostile_materialization(
        "00000000-0000-4000-8000-000000000002",
        snapshot_extra={"workflow_run_id": "wf-1"},
    )
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    rows = reduce_chronology_rows_v1([m1, m2], policy=policy, tcre_policy_bundle_digest=digest)
    edges = reduce_all_expanded_edges_v1([m1, m2], rows, tcre_policy_bundle_digest=digest)
    kinds = {e["edge_body"]["tcre_causal_edge_kind"] for e in edges}
    assert "tcre_coordination_dependency" in kinds
    assert "tcre_coordination_thread_context" in kinds


def test_replay_twin_with_octs_walk() -> None:
    tid = uuid.uuid4()
    wid, _ = seed_octs_walk_v1(tid)
    db = MagicMock()
    db.scalars.return_value.all.return_value = [
        hostile_materialization("00000000-0000-4000-8000-000000000001"),
        hostile_materialization("00000000-0000-4000-8000-000000000002"),
    ]
    job = MagicMock()
    job.tenant_id = tid
    job.scope_json = normalize_reconstruction_scope_v1({"octs_walk_id": str(wid)})
    job.tcre_policy_bundle_digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    job.reasoning_rule_pack_id = "ReasoningPolicyPackV1_Default"
    out = _compare_in_memory_replay_twin_v1(db, job=job)
    assert out["replay_equivalence_passed"] is True
