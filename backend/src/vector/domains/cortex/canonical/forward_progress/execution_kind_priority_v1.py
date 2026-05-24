"""Phase S2.2 — priority boost for execution-bearing canonical materializations."""

from __future__ import annotations

import os
from typing import Final

from sqlalchemy import case
from sqlalchemy.sql.elements import Case

from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

EXECUTION_BEARING_RESOURCE_TYPES_V1: Final[frozenset[str]] = frozenset(
    {
        "github.pull_request",
        "github.pull_request_review",
        "github.deployment",
        "github.deployment_status",
        "github.pull_request_timeline_event",
        "github.issue_timeline_event",
        "github.workflow_run",
        "slack.message",
        "slack.message_reply",
    }
)

LOW_VALUE_GITHUB_RESOURCE_TYPES_V1: Final[frozenset[str]] = frozenset(
    {
        "github.branch",
        "github.tag",
        "github.check_run",
        "github.check_suite",
        "github.review_thread",
        "github.commit_comment",
    }
)

LOW_VALUE_GITHUB_ORPHAN_THRESHOLD_V1: Final[int] = 2


def canonical_execution_kind_priority_enabled_v1() -> bool:
    raw = os.environ.get("CORTEX_CANONICAL_EXECUTION_KIND_PRIORITY", "1")
    return raw.strip().lower() not in ("0", "false", "no", "off")


def raw_record_drain_priority_rank_v1(resource_type: str) -> int:
    rt = (resource_type or "").strip().lower()
    if rt in EXECUTION_BEARING_RESOURCE_TYPES_V1:
        return 0
    if rt in LOW_VALUE_GITHUB_RESOURCE_TYPES_V1:
        return 2
    return 1


def drain_priority_order_clause_v1() -> Case[int] | None:
    """SQL CASE for candidate ordering (lower rank = drained first). None when disabled."""
    if not canonical_execution_kind_priority_enabled_v1():
        return None
    return case(
        (RawIngestionRecord.resource_type.in_(tuple(EXECUTION_BEARING_RESOURCE_TYPES_V1)), 0),
        (RawIngestionRecord.resource_type.in_(tuple(LOW_VALUE_GITHUB_RESOURCE_TYPES_V1)), 2),
        else_=1,
    )


def permanent_orphan_threshold_for_resource_type_v1(
    resource_type: str,
    *,
    default_threshold: int,
) -> int:
    """Low-value GitHub refs reach permanent_orphan faster to reduce deferral churn."""
    if not canonical_execution_kind_priority_enabled_v1():
        return default_threshold
    rt = (resource_type or "").strip().lower()
    if rt in LOW_VALUE_GITHUB_RESOURCE_TYPES_V1:
        return min(default_threshold, LOW_VALUE_GITHUB_ORPHAN_THRESHOLD_V1)
    return default_threshold
