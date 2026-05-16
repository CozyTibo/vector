"""P06-10 — Temporal conflict resolution law (late arrival + skew / export vs observed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_legality import (
    load_default_reasoning_policy_pack,
    project_chronology_legality_class_v1,
)
from vector.domains.cortex.reasoning.temporal_conflict_resolution import (
    PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION,
    TEMPORAL_CONFLICT_CLASS_IDS,
    TemporalConflictResolutionError,
    chronology_projection_snapshot_from_temporal_conflict_v1,
    temporal_conflict_precedence_rank_v1,
    validate_chronology_strict_requires_resolved_pairs_v1,
    validate_export_vs_observed_conflict_flags_v1,
    validate_temporal_active_conflict_classes_v1,
    validate_temporal_conflict_no_history_rewrite_v1,
    verify_gp06_tcr01_precedence_oracle_static,
    verify_gp06_tcr02_chronology_strict_pairwise_static,
    verify_gp06_tcr03_conflict_class_registry_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_static_gates() -> None:
    assert verify_gp06_tcr01_precedence_oracle_static()["passed"] is True
    assert verify_gp06_tcr02_chronology_strict_pairwise_static()["passed"] is True
    assert verify_gp06_tcr03_conflict_class_registry_static()["passed"] is True


def test_active_conflict_classes_sorted_unique() -> None:
    assert validate_temporal_active_conflict_classes_v1(["anchor_skew", "chronology_conflict", "anchor_skew"]) == [
        "anchor_skew",
        "chronology_conflict",
    ]


def test_active_conflict_classes_rejects_unknown() -> None:
    with pytest.raises(TemporalConflictResolutionError, match="unknown"):
        validate_temporal_active_conflict_classes_v1(["not_a_real_conflict"])


def test_snapshot_builder_round_trip_projection() -> None:
    pack = load_default_reasoning_policy_pack()
    snap = chronology_projection_snapshot_from_temporal_conflict_v1(
        replay_safe_ordering="strict",
        evidence={
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        },
    )
    c, _, _ = project_chronology_legality_class_v1(snap, pack)
    assert c == "chronology_strict"


def test_export_flag_snapshot_projects() -> None:
    pack = load_default_reasoning_policy_pack()
    snap = chronology_projection_snapshot_from_temporal_conflict_v1(
        replay_safe_ordering="strict",
        evidence={
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": True,
        },
    )
    c, _, _ = project_chronology_legality_class_v1(snap, pack)
    assert c == "chronology_partial"


def test_validate_export_flags_type() -> None:
    with pytest.raises(TemporalConflictResolutionError):
        validate_export_vs_observed_conflict_flags_v1({"skew_detected": "no"})


def test_no_history_rewrite_guard() -> None:
    validate_temporal_conflict_no_history_rewrite_v1({})
    with pytest.raises(TemporalConflictResolutionError):
        validate_temporal_conflict_no_history_rewrite_v1({"rewrites_historical_labels": True})


def test_doctrine_file_exists() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "temporal-conflict-resolution-law.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "chronology_conflict" in text
            assert "export_sequence_conflict" in text
            return
    pytest.fail("temporal-conflict-resolution-law.md not found")


def test_package_reexports() -> None:
    from vector.domains.cortex.reasoning import (
        TEMPORAL_CONFLICT_CLASS_IDS as ids,
        temporal_conflict_precedence_rank_v1 as rank,
    )

    assert "anchor_skew" in ids
    assert rank({})["precedence_rank"] == 4
