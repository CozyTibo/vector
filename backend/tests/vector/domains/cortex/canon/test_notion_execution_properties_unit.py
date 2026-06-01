"""Notion execution property and lifecycle substrate unit tests."""

from vector.domains.cortex.canon.lifecycle_substrate import (
    LIFECYCLE_PHASE_ACTIVE,
    LIFECYCLE_PHASE_ARCHIVED,
    LIFECYCLE_PHASE_COMPLETED,
    LIFECYCLE_PHASE_PLANNED,
    derive_lifecycle_phase,
)
from vector.domains.cortex.canon.mappers.notion_execution_properties import apply_notion_execution_properties
from vector.domains.cortex.canon.mappers.notion_mapper import NOTION_MAPPERS
from vector.domains.cortex.canon.mappers.notion_temporal import enrich_payload_with_notion_timestamps


def test_notion_row_execution_properties_and_lifecycle() -> None:
    attrs: dict = {"external_id": "row-1"}
    segment = {
        "id": "row-1",
        "created_time": "2026-05-20T15:45:00.000Z",
        "last_edited_time": "2026-05-20T15:51:00.000Z",
        "archived": False,
        "properties": {
            "Name": {"id": "title", "type": "title", "title": [{"plain_text": "Connexion via JWT"}]},
            "Status": {
                "id": "vLqW",
                "type": "status",
                "status": {"id": "s1", "name": "Shaped"},
            },
            "Due": {
                "id": "due1",
                "type": "date",
                "date": {"start": "2026-06-01", "end": None},
            },
            "Done": {"id": "cb1", "type": "checkbox", "checkbox": False},
            "Team": {
                "id": "tm1",
                "type": "multi_select",
                "multi_select": [{"id": "t1", "name": "Engineering"}],
            },
        },
    }
    apply_notion_execution_properties(segment, attrs)
    assert attrs["status_name"] == "Shaped"
    assert attrs["provider_dates"]["due1"]["start"] == "2026-06-01"
    assert attrs["checkboxes"]["cb1"] is False
    assert attrs["multi_selects"]["tm1"][0]["name"] == "Engineering"
    assert attrs["lifecycle_phase"] == LIFECYCLE_PHASE_PLANNED


def test_notion_archived_lifecycle() -> None:
    assert derive_lifecycle_phase({"archived": True, "status_name": "Active"}) == LIFECYCLE_PHASE_ARCHIVED


def test_notion_completed_status_lifecycle() -> None:
    assert derive_lifecycle_phase({"status_name": "Done"}) == LIFECYCLE_PHASE_COMPLETED


def test_notion_active_status_lifecycle() -> None:
    assert derive_lifecycle_phase({"status_name": "In Progress"}) == LIFECYCLE_PHASE_ACTIVE


def test_notion_mapper_promotes_timestamps_for_observed_at() -> None:
    mapper = next(m for m in NOTION_MAPPERS if m.resource_type == "notion.database_row")
    body = {
        "row": {
            "id": "row-1",
            "created_time": "2026-05-20T15:45:00.000Z",
            "last_edited_time": "2026-05-20T15:51:00.000Z",
            "properties": {},
        },
    }
    enriched = enrich_payload_with_notion_timestamps(body)
    assert enriched["provider_updated_at"] == "2026-05-20T15:51:00.000Z"
