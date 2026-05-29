"""Declared container registry unit tests."""

from vector.domains.cortex.canon.declared_container_registry import (
    apply_declared_container_attrs,
    declared_container_kind_for_resource_type,
    work_item_matches_container,
)


def test_linear_project_is_declared_seed() -> None:
    assert declared_container_kind_for_resource_type("linear.project") == "project"


def test_notion_database_is_not_seed() -> None:
    assert declared_container_kind_for_resource_type("notion.database") is None


def test_apply_declared_container_attrs_on_project() -> None:
    attrs: dict = {}
    apply_declared_container_attrs(
        resource_type="linear.project",
        attrs_json=attrs,
        external_id="p-1",
    )
    assert attrs["declared_container_kind"] == "project"
    assert attrs["declared_container_external_id"] == "p-1"


def test_work_item_matches_project_container() -> None:
    assert work_item_matches_container(
        {"project_id": "p-1"},
        container_kind="project",
        container_external_id="p-1",
    )
