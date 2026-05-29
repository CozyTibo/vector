"""Unit tests for Slack cross-tool reference extraction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from vector.domains.cortex.graph.extractors.patterns import (
    GITHUB_PR_URL_RE,
    LINEAR_ISSUE_URL_RE,
    NOTION_PAGE_URL_RE,
    NOTION_SITE_URL_RE,
    SLACK_ARCHIVE_URL_RE,
)
from vector.domains.cortex.graph.extractors.phase2_cross_tool import (
    _slack_ts_from_permalink_token,
    extract_cross_tool_edges,
)
from vector.infrastructure.db.models.canon_entity import CanonEntity


def test_slack_archive_url_pattern_matches_slack_markup() -> None:
    text = (
        "voir <https://fizzer.slack.com/archives/C9P1C9K8X/p1673610318400629|ce thread> "
        "et <https://github.com/fizzer/api/pull/1822>"
    )
    slack = list(SLACK_ARCHIVE_URL_RE.finditer(text))
    assert len(slack) == 1
    assert slack[0].group(1) == "C9P1C9K8X"
    assert slack[0].group(2) == "1673610318400629"
    gh = list(GITHUB_PR_URL_RE.finditer(text))
    assert len(gh) == 1
    assert gh[0].groups() == ("fizzer", "api", "1822")


def test_linear_and_notion_url_patterns_in_message_text() -> None:
    notion_a = "a" * 32
    notion_b = "b" * 32
    text = (
        f"Fix NEX-105 — https://linear.app/nexora/issue/NEX-105 "
        f"spec https://www.notion.so/workspace/Spec-{notion_a} "
        f"pub https://acme.notion.site/Roadmap-{notion_b}"
    )
    linear = list(LINEAR_ISSUE_URL_RE.finditer(text))
    assert len(linear) == 1
    assert linear[0].group(1).upper() == "NEX-105"
    notion_so = list(NOTION_PAGE_URL_RE.finditer(text))
    assert len(notion_so) == 1
    assert notion_so[0].group(1) == notion_a
    notion_site = list(NOTION_SITE_URL_RE.finditer(text))
    assert len(notion_site) == 1
    assert notion_site[0].group(1) == notion_b


def test_slack_ts_from_permalink_token() -> None:
    assert _slack_ts_from_permalink_token("1673610318400629") == "1673610318.400629"
    assert _slack_ts_from_permalink_token("1673620123") == "1673620123"


def test_extract_cross_tool_edges_wires_slack_text_to_reference_extractors() -> None:
    from vector.domains.cortex.graph.edges import EdgeDraft

    tenant_id = uuid.uuid4()
    message_id = uuid.uuid4()
    pr_id = uuid.uuid4()
    thread_id = uuid.uuid4()
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=message_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="slack",
        entity_type="message",
        entity_key=f"{tenant_id}:slack:slack.message:C92:1673620123.063889",
        display_label="PR thread",
        attrs_json={"external_id": "C92CP2A4A:1673620123.063889"},
        mapper_version=1,
        materialized_at=now,
    )

    text = (
        "PR : fix <https://fizzer.slack.com/archives/C9P1C9K8X/p1673610318400629|thread> "
        "• <https://github.com/fizzer/api/pull/1822>"
    )
    raw = MagicMock()
    raw.id = 99
    raw.payload_body = {"message": {"text": text}}
    raw.fetched_at = now
    source = MagicMock()
    source.id = 1

    pr_edge = EdgeDraft(
        relationship_kind="references",
        from_entity_id=message_id,
        to_entity_id=pr_id,
        extractor_rule="text.github_pr_url",
        evidence_kind="text_pattern",
        evidence_ref="github_pr_url_v1",
        evidence_snapshot={},
        confidence="high",
    )

    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.graph.extractors.phase2_cross_tool._latest_raw",
            return_value=(source, raw),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.phase2_cross_tool.extract_reference_edges_from_text",
            return_value=([pr_edge], []),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.phase2_cross_tool._resolve_slack_archive_message",
            return_value=thread_id,
        ),
    ):
        edges, unresolved = extract_cross_tool_edges(
            session,
            tenant_id=tenant_id,
            entity=entity,
        )

    rules = {e.extractor_rule for e in edges}
    assert "text.github_pr_url" in rules
    assert "text.slack_archive_url" in rules
    assert any(e.to_entity_id == pr_id for e in edges)
    assert any(e.to_entity_id == thread_id for e in edges)
    assert unresolved == []


def test_extract_cross_tool_collects_linear_comment_body() -> None:
    """Linear comments use comment.body; shared reference extractors must see that text."""
    from vector.domains.cortex.graph.edges import EdgeDraft

    tenant_id = uuid.uuid4()
    message_id = uuid.uuid4()
    linear_id = uuid.uuid4()
    now = datetime.now(UTC)

    entity = CanonEntity(
        id=message_id,
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="linear",
        entity_type="message",
        entity_key=f"{tenant_id}:linear:linear.comment:c1",
        display_label="comment",
        attrs_json={},
        mapper_version=1,
        materialized_at=now,
    )

    raw = MagicMock()
    raw.id = 5
    raw.payload_body = {"comment": {"body": "See https://linear.app/team/LIN-7"}}
    raw.fetched_at = now
    source = MagicMock()
    source.id = 1

    linear_edge = EdgeDraft(
        relationship_kind="references",
        from_entity_id=message_id,
        to_entity_id=linear_id,
        extractor_rule="text.linear_issue_url",
        evidence_kind="text_pattern",
        evidence_ref="linear_issue_url_v1",
        evidence_snapshot={},
        confidence="high",
    )

    session = MagicMock()
    captured_text: list[str] = []

    def capture_extract(*_args, text: str, **_kwargs):  # noqa: ANN001
        captured_text.append(text)
        return [linear_edge], []

    with (
        patch(
            "vector.domains.cortex.graph.extractors.phase2_cross_tool._latest_raw",
            return_value=(source, raw),
        ),
        patch(
            "vector.domains.cortex.graph.extractors.phase2_cross_tool.extract_reference_edges_from_text",
            side_effect=capture_extract,
        ),
    ):
        edges, _unresolved = extract_cross_tool_edges(
            session,
            tenant_id=tenant_id,
            entity=entity,
        )

    assert captured_text == ["See https://linear.app/team/LIN-7"]
    assert edges[0].to_entity_id == linear_id
