"""Canon v1 resource_type disposition — aligned with ingestion exhaust matrix."""

from __future__ import annotations

from typing import Literal

Disposition = Literal["map", "skip", "defer"]

# entity_type used when disposition is map
_REGISTRY: dict[str, tuple[Disposition, str | None]] = {
    # Slack
    "slack.user": ("map", "actor"),
    "slack.conversation": ("map", "conversation"),
    "slack.channel_member": ("skip", None),
    "slack.message": ("map", "message"),
    "slack.message_changed": ("map", "message"),
    "slack.message_reply": ("map", "message"),
    "slack.thread": ("map", "conversation"),
    "slack.reaction": ("skip", None),
    "slack.file": ("defer", None),
    "slack.pin": ("skip", None),
    "slack.api_error": ("skip", None),
    # GitHub
    "github.user": ("map", "actor"),
    "github.team": ("skip", None),
    "github.team_membership": ("skip", None),
    "github.installation_repositories": ("skip", None),
    "github.repository": ("map", "project"),
    "github.pull_request": ("map", "pull_request"),
    "github.issue": ("map", "work_item"),
    "github.pull_request_review": ("map", "message"),
    "github.pull_request_review_comment": ("map", "message"),
    "github.issue_comment": ("map", "message"),
    "github.issue_timeline_event": ("defer", None),
    "github.pull_request_timeline_event": ("defer", None),
    "github.review_thread": ("map", "conversation"),
    "github.commit": ("map", "commit"),
    "github.commit_comment": ("map", "message"),
    "github.check_run": ("defer", None),
    "github.check_suite": ("skip", None),
    "github.workflow_run": ("map", "deployment"),
    "github.deployment": ("map", "deployment"),
    "github.deployment_status": ("defer", None),
    "github.branch": ("skip", None),
    "github.tag": ("skip", None),
    "github.release": ("map", "release"),
    "github.sync": ("skip", None),
    "commits": ("map", "commit"),
    # Linear
    "linear.user": ("map", "actor"),
    "linear.team": ("map", "team"),
    "linear.team_membership": ("skip", None),
    "linear.issue": ("map", "work_item"),
    "linear.comment": ("map", "message"),
    "linear.comment_thread": ("map", "conversation"),
    "linear.issue_attachment": ("defer", None),
    "linear.activity_history": ("defer", None),
    "linear.project": ("map", "project"),
    "linear.cycle": ("map", "cycle"),
    "linear.issue_relation": ("map", "issue_relation"),
    "linear.issue_label": ("map", "label"),
    "linear.initiative": ("map", "initiative"),
    "linear.project_update": ("defer", None),
    "linear.viewer_ping": ("skip", None),
    "linear.sync": ("skip", None),
    # Notion
    "notion.user": ("map", "actor"),
    "notion.search_result": ("skip", None),
    "notion.page": ("map", "document"),
    "notion.database": ("map", "project"),
    "notion.database_row": ("map", "document"),
    "notion.block": ("map", "document"),
    "notion.scope_ping": ("skip", None),
    # Calls
    "calls.meeting": ("defer", None),
    "calls.participant": ("skip", None),
    "calls.transcript": ("defer", None),
    "calls.transcript_segment": ("defer", None),
    "calls.recording": ("defer", None),
    "calls.scope_ping": ("skip", None),
    # Health aliases
    "scope_ping": ("skip", None),
    "viewer_ping": ("skip", None),
}


def disposition_by_resource_type() -> dict[str, str]:
    """Map resource_type → disposition string for inventory classification."""
    return {rt: entry[0] for rt, entry in _REGISTRY.items()}


def entity_type_for_resource_type(resource_type: str) -> str | None:
    entry = _REGISTRY.get(resource_type)
    if entry is None:
        return None
    disp, entity_type = entry
    if disp != "map":
        return None
    return entity_type


def should_materialize_resource_type(resource_type: str) -> bool:
    return _REGISTRY.get(resource_type, ("defer", None))[0] == "map"


def registry_rows() -> list[dict[str, str | None]]:
    return [
        {
            "resource_type": rt,
            "disposition": disp,
            "entity_type": et,
        }
        for rt, (disp, et) in sorted(_REGISTRY.items())
    ]
