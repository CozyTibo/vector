"""Notion people property parsing for assignees."""

from __future__ import annotations

from vector.domains.cortex.canon.mappers.notion_people import (
    iter_notion_people_assignments,
    primary_notion_assignee_user_id,
)


def test_iter_notion_people_assignments_sorted_and_filtered() -> None:
    props = {
        "Owner": {
            "type": "people",
            "people": [{"id": "user-b"}, {"id": "user-a"}],
        },
        "Status": {"type": "select", "select": {"name": "Done"}},
        "Notes": {
            "type": "people",
            "people": [{"id": "user-z"}],
        },
    }
    pairs = iter_notion_people_assignments(props)
    assert pairs == [("Owner", "user-a"), ("Owner", "user-b")]


def test_primary_assignee_is_first_deterministic_pair() -> None:
    segment = {
        "properties": {
            "Assignee": {
                "type": "people",
                "people": [{"id": "zzz"}, {"id": "aaa"}],
            },
        },
    }
    assert primary_notion_assignee_user_id(segment) == "aaa"


def test_non_allowlisted_people_property_ignored() -> None:
    props = {
        "Collaborators": {
            "type": "people",
            "people": [{"id": "user-1"}],
        },
        "Vote de priorité": {
            "type": "people",
            "people": [{"id": "user-2"}],
        },
    }
    assert iter_notion_people_assignments(props) == []


def test_product_owner_suffix_matches_assignee_property() -> None:
    props = {
        "Product owner": {
            "type": "people",
            "people": [{"id": "user-po"}],
        },
    }
    assert iter_notion_people_assignments(props) == [("Product owner", "user-po")]
