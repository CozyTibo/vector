"""Notion display label enrichment unit tests."""

from vector.domains.cortex.canon.notion_display_labels import (
    enrich_notion_display_labels,
    notion_display_label_needs_enrichment,
    notion_title_from_payload,
)


def test_notion_display_label_needs_enrichment_for_uuid_label() -> None:
    class _Entity:
        connector = "notion"
        display_label = "3459fea5-206c-80f4-979e-d2f873e2e9c1"
        attrs_json = {"external_id": "3459fea5-206c-80f4-979e-d2f873e2e9c1"}

    assert notion_display_label_needs_enrichment(_Entity()) is True


def test_notion_page_title_from_payload() -> None:
    body = {
        "page": {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Fix image re-upload when content changes"}],
                },
            },
        },
    }
    assert (
        notion_title_from_payload(resource_type="notion.page", payload_body=body)
        == "Fix image re-upload when content changes"
    )


def test_resolve_notion_display_title_from_database_row_source() -> None:
    body = {
        "row": {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "Connexion via JWT"}],
                },
            },
        },
    }
    assert (
        notion_title_from_payload(resource_type="notion.database_row", payload_body=body)
        == "Connexion via JWT"
    )


def test_enrich_notion_display_labels_empty() -> None:
    class _Session:
        pass

    assert enrich_notion_display_labels(_Session(), []) == {}  # type: ignore[arg-type]
