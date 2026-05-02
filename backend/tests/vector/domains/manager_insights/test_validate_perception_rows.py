"""§6 Step 8 — validate_perception_rows."""

from __future__ import annotations

import pytest

from vector.contracts.manager_insights_activity import PerceptionRow, WorkItem
from vector.domains.manager_insights.validate_perception_rows import (
    build_perception_validation_demo_debug,
    parent_text_for_grounding,
    validate_perception_rows,
)


@pytest.fixture
def sample_work_item() -> WorkItem:
    return WorkItem(
        id="wi-1",
        source="linear",
        type="issue",
        title="Rollout",
        summary="blocked on the auth layer. Alice owns the timeline.",
    )


def test_parent_text_joins_title_and_summary(sample_work_item: WorkItem) -> None:
    t = parent_text_for_grounding(sample_work_item)
    assert "Rollout" in t
    assert "auth layer" in t


def test_accepts_grounded_row(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="blocker",
        statement="Blocked on auth.",
        quote="blocked on the auth layer",
        waits_on=["Alice"],
        blocked_by=[],
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert len(accepted) == 1
    assert rejected == []


def test_rejects_quote_not_in_parent(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="risk",
        statement="x",
        quote="not present in parent body at all",
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert accepted == []
    assert len(rejected) == 1
    assert rejected[0].reason == "quote_not_grounded"


def test_case_insensitive_and_whitespace_normalized_match(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="blocker",
        statement="s",
        quote="BLOCKED   ON\n\tTHE auth layer",
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert len(accepted) == 1
    assert rejected == []


def test_dedupe_second_identical_row_rejected(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="blocker",
        statement="s",
        quote="blocked on the auth layer",
    )
    dup = PerceptionRow.model_validate({**row.model_dump(mode="python"), "id": "r2"})
    accepted, rejected = validate_perception_rows(
        [row, dup],
        work_items_by_id={"wi-1": sample_work_item},
    )
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert rejected[0].reason == "duplicate_row"


def test_unknown_work_item(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="missing",
        kind="blocker",
        statement="s",
        quote="blocked on the auth layer",
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert accepted == []
    assert rejected[0].reason == "unknown_work_item"


def test_schema_invalid_dict() -> None:
    accepted, rejected = validate_perception_rows(
        [{"id": "only"}],
        work_items_by_id={},
    )
    assert accepted == []
    assert rejected[0].reason == "schema_invalid"


def test_state_transition_quote_must_be_grounded(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="blocker",
        statement="s",
        quote="blocked on the auth layer",
        state_transition={
            "from_state": "blocked",
            "to_state": "in_progress",
            "quote": "phantom transition phrase",
        },
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert accepted == []
    assert rejected[0].reason == "state_transition_quote_not_grounded"


def test_waits_on_must_be_grounded(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="blocker",
        statement="s",
        quote="blocked on the auth layer",
        waits_on=["@ghost"],
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert accepted == []
    assert rejected[0].reason == "waits_on_not_grounded"


def test_ownership_span_must_be_grounded(sample_work_item: WorkItem) -> None:
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-1",
        kind="ownership_hint",
        statement="s",
        quote="Alice owns the timeline",
        ownership_inferred={"text_span": "Bob", "role_guess": "owner"},
    )
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-1": sample_work_item})
    assert accepted == []
    assert rejected[0].reason == "ownership_span_not_grounded"


def test_build_demo_fixture_stable() -> None:
    d = build_perception_validation_demo_debug()
    assert d.input_row_count == 5
    assert len(d.accepted) == 1
    assert len(d.rejected) == 4
    reasons = [r.reason for r in d.rejected]
    assert reasons == ["duplicate_row", "quote_not_grounded", "unknown_work_item", "schema_invalid"]


def test_empty_parent_text_rejected() -> None:
    wi = WorkItem(
        id="wi-empty",
        source="github",
        type="issue",
        title="   ",
        summary=None,
    )
    row = PerceptionRow(
        id="r1",
        work_item_id="wi-empty",
        kind="blocker",
        statement="s",
        quote="x",
    )
    # quote cannot match empty parent — but we hit empty_parent_text first only if parent strips to empty
    accepted, rejected = validate_perception_rows([row], work_items_by_id={"wi-empty": wi})
    assert accepted == []
    assert rejected[0].reason == "empty_parent_text"
