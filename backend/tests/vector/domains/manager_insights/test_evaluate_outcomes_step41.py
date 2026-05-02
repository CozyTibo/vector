"""§6 Step 41 — deterministic ground_truth rules (unit)."""

from __future__ import annotations

from unittest.mock import MagicMock

from vector.domains.manager_insights.evaluate_outcomes import (
    RULE_VERSION,
    compute_ground_truth_patch,
)


def test_compute_patch_dismissed_coherent() -> None:
    d = MagicMock()
    d.status = "dismissed"
    d.receipt = None
    patch, rules = compute_ground_truth_patch(
        decision=d,
        outcome_type="dismissed",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch["decision_outcome_coherent"] is True
    assert "coherence_dismissed" in rules
    assert patch["rule_version"] == RULE_VERSION
    assert "evaluated_at" in patch


def test_compute_patch_dismissed_incoherent() -> None:
    d = MagicMock()
    d.status = "proposed"
    d.receipt = None
    patch, rules = compute_ground_truth_patch(
        decision=d,
        outcome_type="dismissed",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch["decision_outcome_coherent"] is False
    assert "coherence_dismissed" in rules


def test_compute_patch_apply_success_matches() -> None:
    d = MagicMock()
    d.status = "completed"
    d.receipt = {"ok": True, "connector": "slack"}
    patch, _ = compute_ground_truth_patch(
        decision=d,
        outcome_type="applied_success",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch["apply_outcome_matches_lifecycle"] is True


def test_compute_patch_apply_success_mismatch() -> None:
    d = MagicMock()
    d.status = "proposed"
    d.receipt = {"ok": True}
    patch, _ = compute_ground_truth_patch(
        decision=d,
        outcome_type="applied_success",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch["apply_outcome_matches_lifecycle"] is False


def test_compute_patch_partial_suggests_review() -> None:
    d = MagicMock()
    d.status = "completed"
    d.receipt = {"ok": True}
    patch, rules = compute_ground_truth_patch(
        decision=d,
        outcome_type="applied_partial",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch.get("apply_terminal_review") == "suggested"
    assert "apply_non_terminal_note" in rules


def test_compute_patch_orphan() -> None:
    patch, rules = compute_ground_truth_patch(
        decision=None,
        outcome_type="ignored",
        false_positive=None,
        existing_ground_truth={},
    )
    assert patch["decision_row_missing"] is True
    assert "orphan_outcome" in rules


def test_compute_patch_false_positive() -> None:
    d = MagicMock()
    d.status = "proposed"
    d.receipt = None
    patch, rules = compute_ground_truth_patch(
        decision=d,
        outcome_type="ignored",
        false_positive=True,
        existing_ground_truth={},
    )
    assert patch["flagged_false_positive_recorded"] is True
    assert "false_positive_note" in rules


def test_rules_applied_cumulative() -> None:
    d = MagicMock()
    d.status = "dismissed"
    d.receipt = None
    existing = {"rules_applied": ["legacy"]}
    patch, _ = compute_ground_truth_patch(
        decision=d,
        outcome_type="dismissed",
        false_positive=None,
        existing_ground_truth=existing,
    )
    assert patch["rules_applied"][0] == "legacy"
    assert "stamp" in patch["rules_applied"]
