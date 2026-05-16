"""P06-08 — Interval continuity + half-open closure + chronology receipt binding."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.interval_continuity import (
    PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION,
    REASONING_CHRONOLOGY_RECEIPT_TYPE,
    IntervalContinuityError,
    reasoning_chronology_receipt_body_v1,
    validate_chronology_snapshot_read_only_replay_safe_ordering_v1,
    validate_half_open_interval_chain_continuity_v1,
    validate_interval_graph_and_emit_chronology_receipt_v1,
    validate_reasoning_interval_slice_half_open_v1,
    verify_gp06_int01_half_open_chain_continuity_static,
    verify_gp06_int02_chronology_receipt_projection_static,
)


def _two_segment_chain() -> list[dict[str, object]]:
    return [
        {
            "derivation_rule_id": "SEG_v1",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "anchor_ids": ["a1"],
        },
        {
            "derivation_rule_id": "SEG_v1",
            "start_iso": "2025-01-02T00:00:00Z",
            "end_iso": "2025-01-03T00:00:00Z",
            "anchor_ids": ["a2"],
        },
    ]


def test_runtime_schema_version() -> None:
    assert PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp06_int01_static() -> None:
    assert verify_gp06_int01_half_open_chain_continuity_static()["passed"] is True


def test_verify_gp06_int02_static() -> None:
    assert verify_gp06_int02_chronology_receipt_projection_static()["passed"] is True


def test_slice_half_open_and_lineage() -> None:
    validate_reasoning_interval_slice_half_open_v1(
        {
            "derivation_rule_id": "x",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "anchor_ids": ["z"],
        }
    )


def test_chain_reorders_out_of_order_starts() -> None:
    a, b = _two_segment_chain()
    out = validate_half_open_interval_chain_continuity_v1([b, a])
    assert out[0]["start_iso"] == "2025-01-01T00:00:00Z"


def test_chain_open_tail_last_end_optional() -> None:
    out = validate_half_open_interval_chain_continuity_v1(
        [
            {
                "derivation_rule_id": "SEG_v1",
                "start_iso": "2025-01-01T00:00:00Z",
                "end_iso": "2025-01-02T00:00:00Z",
                "anchor_ids": ["a1"],
            },
            {
                "derivation_rule_id": "SEG_v1",
                "start_iso": "2025-01-02T00:00:00Z",
                "anchor_ids": ["a2"],
            },
        ]
    )
    assert len(out) == 2
    assert out[1].get("end_iso") is None


def test_chain_rejects_interior_missing_end() -> None:
    with pytest.raises(IntervalContinuityError, match="interior interval must not omit end_iso"):
        validate_half_open_interval_chain_continuity_v1(
            [
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-01T00:00:00Z",
                    "anchor_ids": ["a1"],
                },
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-02T00:00:00Z",
                    "end_iso": "2025-01-03T00:00:00Z",
                    "anchor_ids": ["a2"],
                },
            ]
        )


def test_read_only_replay_safe_ordering_rejects_mutation_claim() -> None:
    with pytest.raises(IntervalContinuityError):
        validate_chronology_snapshot_read_only_replay_safe_ordering_v1(
            {
                "replay_safe_ordering": "strict",
                "mutated_replay_safe_ordering": True,
            }
        )


def test_reasoning_chronology_receipt_end_to_end() -> None:
    pack = load_default_reasoning_policy_pack()
    body, digest, idx, part = reasoning_chronology_receipt_body_v1(
        anchor_chain_digest="sha256:" + "0" * 64,
        chronology_projection_snapshot={
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        },
        policy=pack,
        intervals_chain_digest="sha256:" + "1" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    )
    assert body["receipt_type"] == REASONING_CHRONOLOGY_RECEIPT_TYPE
    assert body["chronology_legality_class"] == "chronology_strict"
    assert isinstance(idx, int)
    assert part is False
    assert len(digest) == 64


def test_validate_interval_graph_and_emit_combined() -> None:
    pack = load_default_reasoning_policy_pack()
    ordered, body, digest, int_dig, idx, part = validate_interval_graph_and_emit_chronology_receipt_v1(
        _two_segment_chain(),
        chronology_projection_snapshot={
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        },
        policy=pack,
        anchor_chain_digest="sha256:" + "a" * 64,
        reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
        tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    )
    assert len(ordered) == 2
    assert body["intervals_chain_digest"] == int_dig
    assert body["chronology_skew_projection_matched_row_canonical_index"] == idx
    assert len(digest) == 64


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "temporal-reasoning-doctrine.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "chronology-replay-legality-state-machine.md"
        if p1.is_file() and p2.is_file():
            assert "half" in p1.read_text(encoding="utf-8").lower()
            assert "ChronologyLegalityProjectionV1" in p2.read_text(encoding="utf-8")
            return
    pytest.fail("doctrine files not found")


def test_package_reexports() -> None:
    from vector.domains.cortex.reasoning import (
        PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION as v,
        validate_half_open_interval_chain_continuity_v1 as f,
    )

    assert v >= 1
    assert len(f(_two_segment_chain())) == 2
