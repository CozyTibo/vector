"""Registry-driven canonical materialization pass ordering (parent-before-child)."""

from __future__ import annotations

from typing import Final

from vector.domains.cortex.canonical.transform_routing_registry import transform_routing_table

# Policy: ordered resource-type passes per connector (earlier passes materialize first).
# Derived from replay topology tiers; extend when new routes register.
_CANONICAL_PASS_POLICY: Final[dict[str, tuple[str, ...]]] = {
    "github": (
        "github.repository",
        "github.organization",
        "github.user",
        "github.team",
        "github.commit",
        "github.issue",
        "github.pull_request",
        "github.pull_request_review",
        "github.pull_request_review_comment",
        "github.review_thread",
        "github.issue_comment",
        "github.deployment",
        "github.deployment_status",
        "github.workflow_run",
        "github.workflow_job",
        "github.workflow_job_step",
        "github.check_run",
        "github.pull_request_timeline_event",
        "github.issue_timeline_event",
    ),
    "notion": (
        "notion.database",
        "notion.page",
        "notion.block",
        "notion.database_row",
        "notion.search_result",
    ),
    "slack": (
        "slack.channel",
        "slack.user",
        "slack.message",
        "slack.thread",
        "slack.message_reply",
        "slack.file",
        "slack.reaction",
    ),
    "linear": (
        "linear.team",
        "linear.project",
        "linear.cycle",
        "linear.issue",
        "linear.comment",
        "linear.comment_thread",
        "linear.issue_attachment",
        "linear.activity_history",
        "linear.issue_relation",
        "linear.issue_label",
        "linear.initiative",
        "linear.project_update",
    ),
    "calls": (
        "calls.meeting",
        "calls.participant",
        "calls.recording",
        "calls.transcript",
        "calls.transcript_segment",
    ),
}


def canonical_pass_keys_for_connector(connector: str) -> list[str]:
    """Ordered pass keys (resource types) for a connector."""
    c = connector.strip()
    policy = _CANONICAL_PASS_POLICY.get(c)
    if policy is None:
        return []
    routable = {rt for conn, rt in transform_routing_table() if conn == c}
    return [rt for rt in policy if rt in routable]


def all_canonical_passes() -> list[tuple[str, str]]:
    """Global ordered (connector, resource_type) passes for fair rotation."""
    out: list[tuple[str, str]] = []
    for connector in sorted(_CANONICAL_PASS_POLICY):
        for rt in canonical_pass_keys_for_connector(connector):
            if (connector, rt) in transform_routing_table():
                out.append((connector, rt))
    # Any routable pairs missing from policy append at end (deterministic).
    known = set(out)
    for pair in sorted(transform_routing_table()):
        if pair not in known:
            out.append(pair)
    return out


def all_canonical_passes_fair_rotation() -> list[tuple[str, str]]:
    """Round-robin across connectors so one connector's topology blocks do not starve others."""
    by_connector: dict[str, list[tuple[str, str]]] = {}
    for connector, resource_type in all_canonical_passes():
        by_connector.setdefault(connector, []).append((connector, resource_type))

    connectors = sorted(by_connector)
    if not connectors:
        return []
    max_len = max(len(by_connector[c]) for c in connectors)
    out: list[tuple[str, str]] = []
    for i in range(max_len):
        for c in connectors:
            rows = by_connector[c]
            if i < len(rows):
                out.append(rows[i])
    return out


def pass_key_label(connector: str, resource_type: str) -> str:
    return f"{connector.strip()}/{resource_type.strip()}"


def parse_pass_key(pass_key: str) -> tuple[str, str] | None:
    parts = pass_key.split("/", 1)
    if len(parts) != 2:
        return None
    c, rt = parts[0].strip(), parts[1].strip()
    if not c or not rt:
        return None
    return c, rt
