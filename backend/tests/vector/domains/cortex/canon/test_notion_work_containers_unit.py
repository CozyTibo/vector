"""Notion work container allowlist unit tests."""

from vector.domains.cortex.canon.declared_container_registry import (
    apply_declared_container_attrs,
    declared_container_kind_for_materialize,
    member_attrs_match_container,
)
from vector.domains.cortex.canon.notion_work_containers import (
    MAX_NOTION_WORK_CONTAINER_PINS,
    normalize_work_container_pins,
    pinned_database_ids,
)


def test_notion_database_not_seed_without_allowlist() -> None:
    assert (
        declared_container_kind_for_materialize(
            resource_type="notion.database",
            external_id="db-1",
            notion_work_db_allowlist=None,
        )
        is None
    )


def test_notion_database_seed_when_pinned() -> None:
    assert (
        declared_container_kind_for_materialize(
            resource_type="notion.database",
            external_id="db-1",
            notion_work_db_allowlist=frozenset({"db-1"}),
        )
        == "work_database"
    )


def test_apply_attrs_clears_unpinned_notion_database() -> None:
    attrs = {
        "declared_container_kind": "work_database",
        "declared_container_external_id": "db-1",
    }
    apply_declared_container_attrs(
        resource_type="notion.database",
        attrs_json=attrs,
        external_id="db-1",
        notion_work_db_allowlist=frozenset(),
    )
    assert "declared_container_kind" not in attrs


def test_member_matches_work_database() -> None:
    assert member_attrs_match_container(
        {"database_id": "db-1"},
        container_kind="work_database",
        container_external_id="db-1",
    )


def test_normalize_pins_dedupes_and_caps() -> None:
    pins = normalize_work_container_pins(
        database_ids=["a", "a", "b"],
        labels_by_id={"a": "Roadmap", "b": "Bugs"},
    )
    assert len(pins) == 2
    assert pinned_database_ids(pins) == frozenset({"a", "b"})


def test_normalize_pins_enforces_max() -> None:
    try:
        normalize_work_container_pins(database_ids=[f"id-{i}" for i in range(MAX_NOTION_WORK_CONTAINER_PINS + 1)])
    except ValueError as exc:
        assert "max_pins_exceeded" in str(exc)
    else:
        raise AssertionError("expected ValueError")
