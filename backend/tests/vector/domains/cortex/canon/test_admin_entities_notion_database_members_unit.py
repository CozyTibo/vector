"""Notion database member listing unit tests."""

from vector.domains.cortex.canon.admin_entities import notion_database_id_from_entity


def test_notion_database_id_from_entity() -> None:
    class _Entity:
        connector = "notion"
        entity_key = "tenant:notion:notion.database:6320c3e7-1777-4077-905b-20ca7886bb5f"
        attrs_json = {
            "notion_id": "6320c3e7-1777-4077-905b-20ca7886bb5f",
            "declared_container_kind": "work_database",
        }

    assert (
        notion_database_id_from_entity(_Entity())  # type: ignore[arg-type]
        == "6320c3e7-1777-4077-905b-20ca7886bb5f"
    )


def test_notion_database_id_from_entity_rejects_row() -> None:
    class _Entity:
        connector = "notion"
        entity_key = "tenant:notion:notion.database_row:3669fea5-206c-800a-8776-cd500126f36e"
        attrs_json = {"database_id": "6320c3e7-1777-4077-905b-20ca7886bb5f"}

    assert notion_database_id_from_entity(_Entity()) is None  # type: ignore[arg-type]
