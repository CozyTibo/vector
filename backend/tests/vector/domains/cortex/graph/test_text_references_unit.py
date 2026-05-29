"""Unit tests for shared text reference extraction (GitHub, Linear, Notion)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.text_references import extract_reference_edges_from_text
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _message_entity() -> CanonEntity:
    now = datetime.now(UTC)
    return CanonEntity(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="slack",
        entity_type="message",
        entity_key="k",
        display_label="msg",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )


def test_linear_identifier_creates_references_edge() -> None:
    entity = _message_entity()
    linear_id = uuid.uuid4()
    session = MagicMock()
    with patch(
        "vector.domains.cortex.graph.extractors.text_references._resolve_linear_identifier",
        return_value=linear_id,
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text="Please fix NEX-105 before deploy",
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    assert len(edges) == 1
    assert edges[0].relationship_kind == "references"
    assert edges[0].to_entity_id == linear_id
    assert edges[0].extractor_rule == "text.linear_identifier"
    assert unresolved == []


def test_linear_duplicate_tokens_deduped_to_one_edge() -> None:
    entity = _message_entity()
    linear_id = uuid.uuid4()
    session = MagicMock()
    text = (
        "https://linear.app/nexora/issue/NEX-105 "
        "https://linear.app/nexora/NEX-105"
    )
    with patch(
        "vector.domains.cortex.graph.extractors.text_references._resolve_linear_identifier",
        return_value=linear_id,
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text=text,
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    assert len(edges) == 1
    assert edges[0].to_entity_id == linear_id
    assert unresolved == []


def test_linear_unresolved_when_issue_missing() -> None:
    entity = _message_entity()
    session = MagicMock()
    with patch(
        "vector.domains.cortex.graph.extractors.text_references._resolve_linear_identifier",
        return_value=None,
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text="Blocked on LIN-99",
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    assert edges == []
    assert len(unresolved) == 1
    assert unresolved[0].reference_kind == "linear_issue"
    assert unresolved[0].extractor_rule == "text.linear_identifier"


def test_notion_so_and_site_urls_resolve() -> None:
    entity = _message_entity()
    doc_a = uuid.uuid4()
    doc_b = uuid.uuid4()
    notion_a = "c" * 32
    notion_b = "d" * 32
    text = (
        f"Doc https://www.notion.so/w/Title-{notion_a} "
        f"and https://team.notion.site/Page-{notion_b}"
    )

    def resolve_notion(_session, *, tenant_id, page_id):  # noqa: ANN001
        if page_id == notion_a:
            return doc_a
        if page_id == notion_b:
            return doc_b
        return None

    session = MagicMock()
    with patch(
        "vector.domains.cortex.graph.extractors.text_references._resolve_notion_page",
        side_effect=resolve_notion,
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text=text,
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    rules = {e.extractor_rule for e in edges}
    assert edges[0].to_entity_id == doc_a
    assert edges[1].to_entity_id == doc_b
    assert "text.notion_page_url" in rules
    assert "text.notion_site_url" in rules
    assert unresolved == []


def test_github_shorthand_repo_number() -> None:
    entity = _message_entity()
    pr_id = uuid.uuid4()
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.graph.extractors.text_references._resolve_repo_project_id",
            return_value=uuid.uuid4(),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.text_references._resolve_github_number",
            return_value=pr_id,
        ),
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text="Please review acme/api#42",
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    assert len(edges) == 1
    assert edges[0].extractor_rule == "text.github_shorthand"
    assert unresolved == []


def test_github_pr_url_in_slack_message_text() -> None:
    entity = _message_entity()
    pr_id = uuid.uuid4()
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.graph.extractors.text_references._resolve_repo_project_id",
            return_value=uuid.uuid4(),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.text_references._resolve_github_number",
            return_value=pr_id,
        ),
    ):
        edges, unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=entity.tenant_id,
            entity=entity,
            field_path="message.text",
            text="Merged https://github.com/fizzer/api/pull/1822 thanks",
            repo_fn=None,
            source_raw_id=1,
            source_canon_source_id=2,
            observed_at=datetime.now(UTC),
        )
    assert len(edges) == 1
    assert edges[0].relationship_kind == "references"
    assert edges[0].to_entity_id == pr_id
    assert edges[0].extractor_rule == "text.github_pr_url"
    assert unresolved == []
