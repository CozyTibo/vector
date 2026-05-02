"""§6 Step 7 — PerceptionRow contract (coordination §2.1)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from vector.contracts.manager_insights_activity import (
    PerceptionOwnershipInferred,
    PerceptionRow,
    PerceptionStateTransition,
)


def test_perception_row_minimal_valid() -> None:
    r = PerceptionRow(
        id="p1",
        work_item_id="wi-1",
        kind="blocker",
        statement="Blocked on dependency.",
        quote="blocked on the auth service",
        execution_state="blocked",
    )
    assert r.waits_on == []
    assert r.ambiguity_class is None


def test_perception_row_full_round_trip_json() -> None:
    r = PerceptionRow(
        id="p2",
        work_item_id="wi-2",
        kind="ambiguity",
        statement="Conflicting ship dates.",
        quote="ships Friday",
        execution_state="in_progress",
        state_transition=PerceptionStateTransition(
            from_state="blocked",
            to_state="in_progress",
            quote="unblocked now — merging",
        ),
        waits_on=["@infra"],
        blocked_by=["missing env"],
        commitment_strength="weak",
        ambiguity_class="contradiction",
        ambiguity_quote="next month is safer",
        contradiction_pair_id="pair-abc",
    )
    dumped = r.model_dump(mode="json")
    again = PerceptionRow.model_validate(json.loads(json.dumps(dumped)))
    assert again == r


def test_perception_row_contradiction_requires_second_quote_and_pair_id() -> None:
    with pytest.raises(ValidationError, match="ambiguity_quote"):
        PerceptionRow(
            id="p3",
            work_item_id="wi-3",
            kind="ambiguity",
            statement="Conflict.",
            quote="yes",
            ambiguity_class="contradiction",
            contradiction_pair_id="pair-x",
        )
    with pytest.raises(ValidationError, match="contradiction_pair_id"):
        PerceptionRow(
            id="p4",
            work_item_id="wi-4",
            kind="ambiguity",
            statement="Conflict.",
            quote="yes",
            ambiguity_class="contradiction",
            ambiguity_quote="no",
        )


def test_perception_row_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        PerceptionRow.model_validate(
            {
                "id": "p",
                "work_item_id": "w",
                "kind": "risk",
                "statement": "s",
                "quote": "q",
                "model_confidence": 0.9,
            }
        )


def test_perception_row_empty_quote_rejected() -> None:
    with pytest.raises(ValidationError):
        PerceptionRow(
            id="p",
            work_item_id="w",
            kind="decision",
            statement="s",
            quote="",
        )


def test_perception_row_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        PerceptionRow.model_validate(
            {
                "id": "p",
                "work_item_id": "w",
                "kind": "not_a_kind",
                "statement": "s",
                "quote": "x",
            }
        )


def test_perception_ownership_nested_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        PerceptionOwnershipInferred.model_validate({"text_span": "Bob", "extra": 1})
