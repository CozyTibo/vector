"""Relationship kind labels for admin display."""

from __future__ import annotations

RELATIONSHIP_KIND_LABELS: dict[str, str] = {
    "authored_by": "Authored by",
    "assigned_to": "Assigned to",
    "involves": "Involves",
    "reviewed_by": "Reviewed by",
    "comments_on": "Comments on",
    "attached_to": "Attached to",
    "replies_to": "Replies to",
    "belongs_to_repo": "Belongs to repo",
    "parent_of": "Parent of",
    "blocks": "Blocks",
    "duplicates": "Duplicates",
    "relates_to": "Relates to",
    "references": "References",
    "head_commit": "Head commit",
    "merged_as_commit": "Merged as commit",
    "deploys": "Deploys",
    "mentions": "Mentions",
    "contains_commit": "Contains commit",
}

# Kinds current extractors may materialize; admin stats always include these (count may be 0).
EXTRACTABLE_RELATIONSHIP_KINDS: tuple[str, ...] = (
    "authored_by",
    "assigned_to",
    "involves",
    "attached_to",
    "replies_to",
    "comments_on",
    "belongs_to_repo",
    "parent_of",
    "blocks",
    "duplicates",
    "relates_to",
    "references",
    "mentions",
    "head_commit",
    "merged_as_commit",
    "deploys",
)


def label_for_kind(kind: str) -> str:
    return RELATIONSHIP_KIND_LABELS.get(kind, kind.replace("_", " ").title())
