"""Unit tests for phase 2 patterns."""

from __future__ import annotations

from vector.domains.cortex.graph.extractors.patterns import NOTION_PAGE_URL_RE, SLACK_USER_MENTION_RE


def test_notion_url_pattern() -> None:
    url = "https://www.notion.so/Team-abc123def4567890abcdef1234567890"
    assert NOTION_PAGE_URL_RE.search(url) is not None


def test_slack_mention_pattern() -> None:
    assert SLACK_USER_MENTION_RE.findall("hey <@U123ABC>") == ["U123ABC"]
