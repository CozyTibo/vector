"""P06-05 — Temporal reasoning substrate (``temporal_reasoning``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.temporal_reasoning import (
    PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION,
    REPLAY_SAFE_ORDERING_LITERALS,
    TemporalReasoningInvariantError,
    validate_cross_source_temporal_reference_contract,
    validate_half_open_interval_iso,
    validate_late_arrival_append_only,
    validate_no_replay_safe_ordering_mutation_claim,
    validate_reasoning_interval_has_anchor_or_raw_lineage,
    validate_replay_safe_ordering_read_only_value,
    verify_gp06_tr01_interval_lineage_static,
    verify_gp06_tr02_late_arrival_append_static,
    verify_gp06_tr03_cross_source_reference_static,
    verify_gp06_tr04_half_open_interval_static,
)


def test_temporal_reasoning_runtime_schema_version() -> None:
    assert PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION >= 1


def test_replay_safe_ordering_literals() -> None:
    assert REPLAY_SAFE_ORDERING_LITERALS == frozenset({"strict", "partial", "unresolved"})


def test_validate_replay_safe_ordering_read_only_value() -> None:
    validate_replay_safe_ordering_read_only_value("strict")
    with pytest.raises(TemporalReasoningInvariantError):
        validate_replay_safe_ordering_read_only_value("magic")


def test_validate_no_mutation_claim() -> None:
    validate_no_replay_safe_ordering_mutation_claim({})
    with pytest.raises(TemporalReasoningInvariantError):
        validate_no_replay_safe_ordering_mutation_claim({"mutated_replay_safe_ordering": True})


def test_interval_accepts_raw_ids() -> None:
    validate_reasoning_interval_has_anchor_or_raw_lineage(
        {
            "derivation_rule_id": "SIL_v1",
            "source_raw_record_ids": [101, 102],
        }
    )


def test_interval_accepts_anchor_ids() -> None:
    validate_reasoning_interval_has_anchor_or_raw_lineage(
        {
            "derivation_rule_id": "WIN_v1",
            "anchor_ids": ["anch-1"],
        }
    )


def test_half_open_accepts_open_end() -> None:
    validate_half_open_interval_iso(start_iso="2025-01-01T00:00:00Z", end_iso=None)


def test_half_open_rejects_equal_bounds() -> None:
    with pytest.raises(TemporalReasoningInvariantError, match="start_iso"):
        validate_half_open_interval_iso(
            start_iso="2025-01-01T12:00:00Z",
            end_iso="2025-01-01T12:00:00Z",
        )


def test_verify_gp06_tr01_static_passes() -> None:
    assert verify_gp06_tr01_interval_lineage_static()["passed"] is True


def test_verify_gp06_tr02_static_passes() -> None:
    assert verify_gp06_tr02_late_arrival_append_static()["passed"] is True


def test_verify_gp06_tr03_static_passes() -> None:
    assert verify_gp06_tr03_cross_source_reference_static()["passed"] is True


def test_verify_gp06_tr04_static_passes() -> None:
    assert verify_gp06_tr04_half_open_interval_static()["passed"] is True


def test_temporal_reasoning_doctrine_contract() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "temporal-reasoning-doctrine.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "\u2011TEMP\u201101" in text  # T‑TEMP‑01
            assert "\u2011TEMP\u201102" in text
            assert "\u2011TEMP\u201103" in text
            assert "TemporalAnchorChain" in text
            assert "replay_safe_ordering" in text
            return
    pytest.fail("temporal-reasoning-doctrine.md not found")


def test_cross_system_continuity_law_exists() -> None:
    """T‑TEMP‑03 cites continuity law — file must remain present for linkage discipline."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "continuity" / "cross-system-continuity-law.md"
        if p.is_file():
            assert "cross" in p.read_text(encoding="utf-8").lower()
            return
    pytest.fail("cross-system-continuity-law.md not found")
