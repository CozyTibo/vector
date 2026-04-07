"""Tests for answers_json.slack_stakeholders normalization."""

from __future__ import annotations

from vector.infrastructure.db.repositories.onboarding import normalize_slack_stakeholders_in_place


def test_normalize_dedupes_ids_and_keeps_first_labels() -> None:
    answers = {
        "slack_stakeholders": {
            "slack_user_ids": ["U1", "U2", "U1"],
            "mention_labels": ["Ada", "Bob", "Ada-dup"],
        }
    }
    normalize_slack_stakeholders_in_place(answers)
    assert answers["slack_stakeholders"]["slack_user_ids"] == ["U1", "U2"]
    assert answers["slack_stakeholders"]["mention_labels"] == ["Ada", "Bob"]


def test_normalize_ids_only_when_labels_mismatched_length() -> None:
    answers = {
        "slack_stakeholders": {
            "slack_user_ids": ["U1", "U1"],
            "mention_labels": ["Only"],
        }
    }
    normalize_slack_stakeholders_in_place(answers)
    assert answers["slack_stakeholders"]["slack_user_ids"] == ["U1"]
    assert "mention_labels" not in answers["slack_stakeholders"]
