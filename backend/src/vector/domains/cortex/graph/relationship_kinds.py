"""Relationship kind labels for admin display."""

from __future__ import annotations

RELATIONSHIP_KIND_LABELS: dict[str, str] = {
    "authored_by": "Authored by",
    "assigned_to": "Assigned to",
    "reviewed_by": "Reviewed by",
    "comments_on": "Comments on",
    "attached_to": "Attached to",
    "replies_to": "Replies to",
    "belongs_to_repo": "Belongs to repo",
    "parent_of": "Parent of",
    "relates_to": "Relates to",
    "references": "References",
    "merged_as_commit": "Merged as commit",
    "deploys": "Deploys",
    "mentions": "Mentions",
    "contains_commit": "Contains commit",
}


def label_for_kind(kind: str) -> str:
    return RELATIONSHIP_KIND_LABELS.get(kind, kind.replace("_", " ").title())
