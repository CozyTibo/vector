"""Unit tests for scannable text collection."""

from __future__ import annotations

from vector.domains.cortex.graph.extractors.text_collect import collect_scannable_text


def test_collect_slack_message_and_reply() -> None:
    blobs = collect_scannable_text(
        {"message": {"text": "hello"}, "channel_id": "C1"},
        entity_type="message",
        connector="slack",
        resource_type="slack.message",
    )
    paths = [p for p, _ in blobs]
    assert "message.text" in paths

    reply_blobs = collect_scannable_text(
        {"reply": {"text": "thread reply"}, "thread_ts": "1.0"},
        entity_type="message",
        connector="slack",
        resource_type="slack.message_reply",
    )
    assert any(p == "reply.text" for p, _ in reply_blobs)


def test_collect_notion_page_url_and_properties() -> None:
    page_id = "a" * 32
    blobs = collect_scannable_text(
        {
            "page": {
                "url": f"https://notion.so/x-{page_id}",
                "properties": {
                    "Name": {
                        "title": [{"plain_text": "Spec doc"}],
                    },
                },
            },
        },
        entity_type="document",
        connector="notion",
        resource_type="notion.page",
    )
    texts = " ".join(t for _, t in blobs)
    assert "Spec doc" in texts
    assert page_id in texts


def test_collect_linear_and_github_work_items() -> None:
    linear = collect_scannable_text(
        {"issue": {"title": "Bug", "description": "See NEX-1"}},
        entity_type="work_item",
        connector="linear",
        resource_type="linear.issue",
    )
    assert any("issue.description" in p for p, _ in linear)

    gh = collect_scannable_text(
        {"pull_request": {"title": "Fix", "body": "closes #9"}},
        entity_type="pull_request",
        connector="github",
        resource_type="github.pull_request",
    )
    assert any(p == "pull_request.body" for p, _ in gh)
