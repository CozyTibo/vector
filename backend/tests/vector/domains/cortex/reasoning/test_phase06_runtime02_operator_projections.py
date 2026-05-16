"""P06-RUNTIME-02 — operator projection determinism."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.runtime.causal_edge_explanation_projection import (
    project_causal_edge_explanation_v1,
)
from vector.domains.cortex.reasoning.runtime.chronology_explanation_projection import (
    project_chronology_explanation_v1,
)
from vector.domains.cortex.reasoning.runtime.chronology_runtime_reducer import reduce_chronology_rows_v1
from vector.domains.cortex.reasoning.runtime.replay_diff_projection import build_replay_diff_v1


def _mat(mid: str) -> MagicMock:
    m = MagicMock()
    m.id = uuid.UUID(mid)
    m.bundle_id = "bundle.test"
    m.temporal_ordering_key = "a|b"
    m.canonical_object_kind = "meeting"
    m.observed_at = None
    m.occurred_at = None
    return m


def test_chronology_explanation_stable_digest() -> None:
    policy = load_default_reasoning_policy_pack()
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    mats = [_mat("00000000-0000-4000-8000-000000000001")]
    rows = reduce_chronology_rows_v1(mats, policy=policy, tcre_policy_bundle_digest=digest)
    e1 = project_chronology_explanation_v1(
        materialization_id=str(mats[0].id),
        canonical_object_kind="meeting",
        bundle_id="bundle.test",
        occurred_at_iso=None,
        observed_at_iso=None,
        chronology_row=rows[0],
        tcre_policy_bundle_digest=digest,
        replay_posture="replay_safe_reasoning_posture_v1",
    )
    e2 = project_chronology_explanation_v1(
        materialization_id=str(mats[0].id),
        canonical_object_kind="meeting",
        bundle_id="bundle.test",
        occurred_at_iso=None,
        observed_at_iso=None,
        chronology_row=rows[0],
        tcre_policy_bundle_digest=digest,
        replay_posture="replay_safe_reasoning_posture_v1",
    )
    assert e1["explanation_digest"] == e2["explanation_digest"]
    assert "CHRON-PROJ" in e1["chronology_projection_rule_id"]
    assert e1["explanation_summary"]


def test_replay_diff_identical_runs() -> None:
    run = {
        "materialization_count": 2,
        "chronology_rows": [
            {"materialization_id": "a", "receipt_digest": "d1"},
            {"materialization_id": "b", "receipt_digest": "d2"},
        ],
        "edge_rows": [{"tcre_causal_edge_id": "e1"}],
        "chain": {"causal_chain_id": "c1"},
        "aggregate_digest": "agg",
    }
    diff = build_replay_diff_v1(run, run, policy_digest_a="p", policy_digest_b="p")
    assert diff["identical"] is True
    assert diff["chronology_divergence"] == []
    assert diff["edge_divergence"] == []


def test_replay_diff_detects_chronology_change() -> None:
    run_a = {
        "chronology_rows": [{"materialization_id": "a", "receipt_digest": "d1"}],
        "edge_rows": [],
        "chain": None,
        "aggregate_digest": "x",
        "materialization_count": 1,
    }
    run_b = {
        "chronology_rows": [{"materialization_id": "a", "receipt_digest": "d2"}],
        "edge_rows": [],
        "chain": None,
        "aggregate_digest": "y",
        "materialization_count": 1,
    }
    diff = build_replay_diff_v1(run_a, run_b, policy_digest_a="p", policy_digest_b="p")
    assert diff["identical"] is False
    assert len(diff["chronology_divergence"]) == 1


def test_edge_explanation_template() -> None:
    edge_row = {
        "tcre_causal_edge_id": "edgehash",
        "from_materialization_id": "a",
        "to_materialization_id": "b",
        "edge_body": {
            "tcre_causal_edge_kind": "tcre_coordination_temporal_order",
            "derivation_rule_id": "p06.runtime01.canonical_temporal_order.v1",
            "causal_legality_class": "causal_replay_equivalent",
            "parent_artifact_ids": [],
        },
    }
    expl = project_causal_edge_explanation_v1(
        edge_row=edge_row,
        from_kind="meeting",
        to_kind="meeting",
        from_chronology_class="chronology_strict",
        to_chronology_class="chronology_strict",
        tcre_policy_bundle_digest="digest",
        replay_posture="replay_safe_reasoning_posture_v1",
    )
    assert "TCRE-EDGE-TEMPORAL-01" in expl["explanation_summary"]
