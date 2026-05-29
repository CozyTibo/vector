"""Canon mapper refs that feed graph phase-0 edges."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.cortex.canon.mappers.github_mapper import GITHUB_MAPPERS
from vector.domains.cortex.canon.mappers.linear_mapper import LINEAR_MAPPERS
from vector.domains.cortex.canon.mappers.notion_mapper import NOTION_MAPPERS
from vector.domains.cortex.canon.mappers.slack_mapper import SLACK_MAPPERS


def _mapper(mappers, resource_type: str):
    for m in mappers:
        if m.resource_type == resource_type:
            return m
    raise AssertionError(resource_type)


def test_slack_thread_reply_uses_thread_conversation_and_parent() -> None:
    mapper = _mapper(SLACK_MAPPERS, "slack.message_reply")
    tenant_id = uuid.uuid4()
    result = mapper.map_row(
        tenant_id=tenant_id,
        connection_id=uuid.uuid4(),
        connector="slack",
        resource_type="slack.message_reply",
        external_id="C1:100.0:100.1",
        payload_body={
            "channel_id": "C1",
            "thread_ts": "100.0",
            "reply": {"ts": "100.1", "user": "U1", "text": "ok"},
        },
        raw_id=1,
        source_identity_key="slack:slack.message_reply:C1:100.0:100.1",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.conversation_ref is not None
    assert "slack.thread" in (result.draft.conversation_ref or "")
    assert result.draft.parent_message_ref is not None
    assert result.draft.parent_message_ref.endswith("slack.message:C1:100.0")


def test_github_issue_comment_targets_pull_request() -> None:
    mapper = _mapper(GITHUB_MAPPERS, "github.issue_comment")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="github",
        resource_type="github.issue_comment",
        external_id="acme/api#42:issue_comment:99",
        payload_body={"pull_request_number": 42, "comment": {"id": 99, "user": {"login": "bob"}}},
        raw_id=2,
        source_identity_key="github:github.issue_comment:acme/api#42:issue_comment:99",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.work_item_ref is not None
    assert "github.pull_request" in (result.draft.work_item_ref or "")
    assert result.draft.work_item_ref.endswith("acme/api#42")


def test_github_issue_has_creator_and_repo_refs() -> None:
    mapper = _mapper(GITHUB_MAPPERS, "github.issue")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="github",
        resource_type="github.issue",
        external_id="acme/api#7",
        payload_body={
            "issue": {
                "number": 7,
                "user": {"login": "alice"},
                "repository": {"full_name": "acme/api"},
            },
        },
        raw_id=3,
        source_identity_key="github:github.issue:acme/api#7",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.author_ref is not None
    assert result.draft.repository_ref is not None


def test_linear_issue_has_creator_ref() -> None:
    mapper = _mapper(LINEAR_MAPPERS, "linear.issue")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="linear",
        resource_type="linear.issue",
        external_id="issue-uuid",
        payload_body={
            "issue": {
                "identifier": "NEX-1",
                "creator": {"id": "user-1"},
                "assignee": {"id": "user-2"},
            },
        },
        raw_id=4,
        source_identity_key="linear:linear.issue:issue-uuid",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.author_ref is not None
    assert result.draft.assignee_ref is not None


def test_notion_page_has_created_by_author_ref() -> None:
    mapper = _mapper(NOTION_MAPPERS, "notion.page")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="notion",
        resource_type="notion.page",
        external_id="page-1",
        payload_body={"page": {"id": "page-1", "created_by": {"id": "user-abc"}}},
        raw_id=5,
        source_identity_key="notion:notion.page:page-1",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.author_ref is not None
    assert "notion.user" in (result.draft.author_ref or "")


def test_notion_database_row_maps_owner_people_property_to_assignee_ref() -> None:
    mapper = _mapper(NOTION_MAPPERS, "notion.database_row")
    result = mapper.map_row(
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        connector="notion",
        resource_type="notion.database_row",
        external_id="row-1",
        payload_body={
            "row": {
                "id": "row-1",
                "properties": {
                    "Product owner": {
                        "type": "people",
                        "people": [{"id": "user-owner"}],
                    },
                },
            },
        },
        raw_id=6,
        source_identity_key="notion:notion.database_row:row-1",
        source_revision_key="h",
        fetched_at_iso=datetime.now(UTC).isoformat(),
    )
    assert result.draft is not None
    assert result.draft.assignee_ref is not None
    assert result.draft.assignee_ref.endswith("user-owner")
