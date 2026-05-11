"""Declarative canonical transform routing (replaces ad-hoc _STUB_ROUTING).

Each registration is the single source of truth for:
- which (connector, resource_type) pairs participate in deterministic materialization
- which ontology kind + rule namespace applies
- operator-visible maturity metadata (coverage matrix)

Bundle selection remains separate (pins / registry); routing does not load bundle artifacts yet — it
declares which transforms exist and which rule namespace they use (replay-safe, versioned IDs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind

TRANSFORM_ROUTING_REGISTRY_VERSION: Final[int] = 10


@dataclass(frozen=True, slots=True)
class TransformRouteRegistration:
    """One deterministic transform route."""

    connector: str
    resource_type: str
    canonical_object_kind: CanonicalObjectKind
    rule_base: str
    """Stable rule namespace id (prefix for lineage rule_ids)."""
    transform_impl: str
    """Implementation discriminator (e.g. deterministic_lineage_v1)."""
    matrix_maturity: str
    """Operator-facing coarse label: partially_canonicalized | canonicalized (honest, not 'production')."""
    oracle_fixture_id: str | None
    """Frozen oracle vector id when present; None if not yet covered."""
    notes: str | None = None


# Order: connector, then resource_type.
_ALL_ROUTES: tuple[TransformRouteRegistration, ...] = (
    TransformRouteRegistration(
        connector="calls",
        resource_type="calls.meeting",
        canonical_object_kind=CanonicalObjectKind.MEETING,
        rule_base="rule.registry.calls.calls.meeting",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Calls meeting event payload.",
    ),
    TransformRouteRegistration(
        connector="calls",
        resource_type="calls.participant",
        canonical_object_kind=CanonicalObjectKind.PERSON,
        rule_base="rule.registry.calls.calls.participant",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Calls participant payload mapped to PERSON identity object.",
    ),
    TransformRouteRegistration(
        connector="calls",
        resource_type="calls.recording",
        canonical_object_kind=CanonicalObjectKind.RECORDING,
        rule_base="rule.registry.calls.calls.recording",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Calls recording payload.",
    ),
    TransformRouteRegistration(
        connector="calls",
        resource_type="calls.transcript",
        canonical_object_kind=CanonicalObjectKind.TRANSCRIPT,
        rule_base="rule.registry.calls.calls.transcript",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Calls transcript envelope mapped to TRANSCRIPT artifact.",
    ),
    TransformRouteRegistration(
        connector="calls",
        resource_type="calls.transcript_segment",
        canonical_object_kind=CanonicalObjectKind.TRANSCRIPT_SEGMENT,
        rule_base="rule.registry.calls.calls.transcript_segment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Calls transcript segment payload with deterministic segment ordinal.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.check_run",
        canonical_object_kind=CanonicalObjectKind.EXECUTION_CHECK,
        rule_base="rule.registry.github.github.check_run",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes=(
            "GitHub check-run execution lifecycle object with deterministic identity by repository + check_run id."
        ),
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.workflow_run",
        canonical_object_kind=CanonicalObjectKind.WORKFLOW_RUN,
        rule_base="rule.registry.github.github.workflow_run",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub workflow-run execution lifecycle object.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.deployment",
        canonical_object_kind=CanonicalObjectKind.DEPLOYMENT,
        rule_base="rule.registry.github.github.deployment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub deployment lifecycle object.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.deployment_status",
        canonical_object_kind=CanonicalObjectKind.TIMELINE_MUTATION,
        rule_base="rule.registry.github.github.deployment_status",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub deployment status transition object.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.branch",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.github.github.branch",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub branch reference object.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.tag",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.github.github.tag",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub tag reference object.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.check_suite",
        canonical_object_kind=CanonicalObjectKind.WORKFLOW_RUN,
        rule_base="rule.registry.github.github.check_suite",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub check-suite object normalized as workflow-run semantics.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.release",
        canonical_object_kind=CanonicalObjectKind.DEPLOYMENT,
        rule_base="rule.registry.github.github.release",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub release object mapped to deployment artifact semantics.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.commit_comment",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.github.github.commit_comment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub commit comment represented as message artifact.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.review_thread",
        canonical_object_kind=CanonicalObjectKind.THREAD,
        rule_base="rule.registry.github.github.review_thread",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="GitHub review thread represented as first-class thread.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.commit",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.github.github.commit",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub commit payload retained as canonical reference keyed by repo+sha external id.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.issue",
        canonical_object_kind=CanonicalObjectKind.ISSUE,
        rule_base="rule.stub.github.github.issue",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Reserved for standalone GitHub issues when ingest emits this resource_type (sync currently emphasizes PRs).",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.issue_comment",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.github.github.issue_comment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub issue comment payload attached to issue/pull thread context.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.issue_timeline_event",
        canonical_object_kind=CanonicalObjectKind.TIMELINE_MUTATION,
        rule_base="rule.registry.github.github.issue_timeline_event",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Issue timeline row → TIMELINE_MUTATION with deterministic execution_mutations from explicit event fields.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.pull_request_timeline_event",
        canonical_object_kind=CanonicalObjectKind.TIMELINE_MUTATION,
        rule_base="rule.registry.github.github.pull_request_timeline_event",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="PR timeline row → TIMELINE_MUTATION with deterministic execution_mutations from explicit event fields.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.pull_request",
        canonical_object_kind=CanonicalObjectKind.PULL_REQUEST,
        rule_base="rule.registry.github.github.pull_request",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_github_pull_request_v1",
        notes="REST pulls list payload; payload_body.pull_request + base.repo.id + number.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.pull_request_review",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.github.github.pull_request_review",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub pull-request review payload represented as thread message-like artifact.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.pull_request_review_comment",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.github.github.pull_request_review_comment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub review comment payload represented as thread message-like artifact.",
    ),
    TransformRouteRegistration(
        connector="github",
        resource_type="github.repository",
        canonical_object_kind=CanonicalObjectKind.REPOSITORY,
        rule_base="rule.registry.github.github.repository",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="GitHub repository metadata payload.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.comment",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.linear.linear.comment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear comment stream item.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.cycle",
        canonical_object_kind=CanonicalObjectKind.CYCLE,
        rule_base="rule.registry.linear.linear.cycle",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear cycle stream item.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.initiative",
        canonical_object_kind=CanonicalObjectKind.INITIATIVE,
        rule_base="rule.registry.linear.linear.initiative",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear initiative stream item.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.issue",
        canonical_object_kind=CanonicalObjectKind.ISSUE,
        rule_base="rule.stub.linear.linear.issue",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear GraphQL issue payload.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.issue_label",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.linear.linear.issue_label",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear issue label stream item retained as reference.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.issue_relation",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.linear.linear.issue_relation",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear issue relation stream item retained as reference.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.project",
        canonical_object_kind=CanonicalObjectKind.PROJECT,
        rule_base="rule.registry.linear.linear.project",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear project stream item.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.issue_attachment",
        canonical_object_kind=CanonicalObjectKind.DOCUMENT,
        rule_base="rule.registry.linear.linear.issue_attachment",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear issue attachment as durable DOCUMENT artifact.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.activity_history",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_EVENT,
        rule_base="rule.registry.linear.linear.activity_history",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear issue activity history event.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.project_update",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_EVENT,
        rule_base="rule.registry.linear.linear.project_update",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="Linear project update event stream item.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.comment_thread",
        canonical_object_kind=CanonicalObjectKind.THREAD,
        rule_base="rule.registry.linear.linear.comment_thread",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="routable",
        oracle_fixture_id=None,
        notes="Linear comment thread container semantics.",
    ),
    TransformRouteRegistration(
        connector="linear",
        resource_type="linear.viewer_ping",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.linear.linear.viewer_ping",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Linear health snapshot retained as canonical reference.",
    ),
    TransformRouteRegistration(
        connector="notion",
        resource_type="notion.block",
        canonical_object_kind=CanonicalObjectKind.PAGE,
        rule_base="rule.registry.notion.notion.block",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_notion_block_v1",
        notes=(
            "Notion block node mapped to PAGE kind until dedicated block ontology kind exists; preserves parent "
            "hierarchy, block type, rich-text excerpt, and deterministic sibling cursor context."
        ),
    ),
    TransformRouteRegistration(
        connector="notion",
        resource_type="notion.database",
        canonical_object_kind=CanonicalObjectKind.PAGE,
        rule_base="rule.registry.notion.notion.database",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_notion_database_v1",
        notes=(
            "Notion database container mapped to existing PAGE kind; captures schema/relation property lineage "
            "until dedicated database-container ontology kind is introduced."
        ),
    ),
    TransformRouteRegistration(
        connector="notion",
        resource_type="notion.database_row",
        canonical_object_kind=CanonicalObjectKind.DATABASE_ROW,
        rule_base="rule.registry.notion.notion.database_row",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_notion_database_row_v1",
        notes="Notion database query row payload; preserves database containment and relation refs.",
    ),
    TransformRouteRegistration(
        connector="notion",
        resource_type="notion.page",
        canonical_object_kind=CanonicalObjectKind.DOCUMENT,
        rule_base="rule.registry.notion.notion.page",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_notion_page_v1",
        notes="Notion page payload from /search results; preserves parent/workspace/title/url lineage.",
    ),
    TransformRouteRegistration(
        connector="notion",
        resource_type="notion.search_result",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.notion.notion.search_result",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Notion search result envelope retained as canonical reference for exhaust visibility.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.conversation",
        canonical_object_kind=CanonicalObjectKind.CONVERSATION,
        rule_base="rule.registry.slack.slack.conversation",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack conversation/channel metadata.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.message",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.stub.slack.slack.message",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id="p03_oracle_temporal_message_order",
        notes="Slack conversations.history payload; thread ts in payload.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.message_reply",
        canonical_object_kind=CanonicalObjectKind.MESSAGE,
        rule_base="rule.registry.slack.slack.message_reply",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack thread reply payload from conversations.replies.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.thread",
        canonical_object_kind=CanonicalObjectKind.THREAD,
        rule_base="rule.registry.slack.slack.thread",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack thread container derived from thread root identity.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.reaction",
        canonical_object_kind=CanonicalObjectKind.CANONICAL_REFERENCE,
        rule_base="rule.registry.slack.slack.reaction",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack reaction artifact retained as canonical reference.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.file",
        canonical_object_kind=CanonicalObjectKind.DOCUMENT,
        rule_base="rule.registry.slack.slack.file",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack file object as durable DOCUMENT artifact.",
    ),
    TransformRouteRegistration(
        connector="slack",
        resource_type="slack.user",
        canonical_object_kind=CanonicalObjectKind.PERSON,
        rule_base="rule.registry.slack.slack.user",
        transform_impl="deterministic_lineage_v1",
        matrix_maturity="partially_canonicalized",
        oracle_fixture_id=None,
        notes="Slack user/member payload.",
    ),
)


def all_transform_route_registrations() -> tuple[TransformRouteRegistration, ...]:
    return _ALL_ROUTES


def transform_routing_table() -> dict[tuple[str, str], tuple[CanonicalObjectKind, str]]:
    """Map (connector, resource_type) → (kind, rule_base) for materialization resolution."""
    return {(r.connector, r.resource_type): (r.canonical_object_kind, r.rule_base) for r in _ALL_ROUTES}


def transform_route_keys() -> list[tuple[str, str]]:
    return [(r.connector, r.resource_type) for r in _ALL_ROUTES]


def registration_for_pair(connector: str, resource_type: str) -> TransformRouteRegistration | None:
    c, rt = connector.strip(), resource_type.strip()
    for r in _ALL_ROUTES:
        if r.connector == c and r.resource_type == rt:
            return r
    return None
