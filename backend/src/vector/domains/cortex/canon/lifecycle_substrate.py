"""Shared deterministic temporal / lifecycle attrs for canon entities."""

from __future__ import annotations

from typing import Any

# Normalized lifecycle phase stored on qualified execution entities.
LIFECYCLE_PHASE_PLANNED = "planned"
LIFECYCLE_PHASE_ACTIVE = "active"
LIFECYCLE_PHASE_COMPLETED = "completed"
LIFECYCLE_PHASE_ARCHIVED = "archived"
LIFECYCLE_PHASE_CANCELLED = "cancelled"
LIFECYCLE_PHASE_UNKNOWN = "unknown"
# Observation-only bucket (declared domains); not set on entity attrs by mappers.
LIFECYCLE_PHASE_DORMANT = "dormant"

# Status name sets (normalized lowercase) — extend per connector in registry later.
COMPLETED_STATUS_NAMES = frozenset(
    {
        "completed",
        "done",
        "canceled",
        "cancelled",
        "closed",
        "shipped",
        "resolved",
    },
)
PLANNED_STATUS_NAMES = frozenset(
    {
        "planned",
        "backlog",
        "triage",
        "unstarted",
        "idea",
        "shaped",
        "not started",
        "todo",
        "to do",
    },
)
ACTIVE_STATUS_NAMES = frozenset(
    {
        "started",
        "in progress",
        "in_progress",
        "active",
        "building",
        "in review",
        "in_review",
    },
)


def _norm_status(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def apply_temporal_attrs(
    attrs: dict[str, Any],
    *,
    provider_created_at: str | None = None,
    provider_updated_at: str | None = None,
    archived: bool | None = None,
    in_trash: bool | None = None,
) -> None:
    if provider_created_at:
        attrs["provider_created_at"] = provider_created_at
    if provider_updated_at:
        attrs["provider_updated_at"] = provider_updated_at
    if archived is not None:
        attrs["archived"] = archived
    if in_trash is not None:
        attrs["in_trash"] = in_trash


def apply_status_attrs(
    attrs: dict[str, Any],
    *,
    status_name: str | None = None,
    status_id: str | None = None,
    workflow_state: str | None = None,
) -> None:
    if status_name:
        attrs["status_name"] = status_name
    if status_id:
        attrs["status_id"] = status_id
    if workflow_state:
        attrs["workflow_state"] = workflow_state


def derive_lifecycle_phase(
    attrs: dict[str, Any],
) -> str:
    """Deterministic lifecycle phase from canon attrs (no inference beyond explicit fields)."""
    if attrs.get("archived") is True or attrs.get("in_trash") is True:
        return LIFECYCLE_PHASE_ARCHIVED

    status = _norm_status(
        attrs.get("status_name")
        or attrs.get("state")
        or attrs.get("status")
        or attrs.get("workflow_state"),
    )
    if status in COMPLETED_STATUS_NAMES:
        return LIFECYCLE_PHASE_COMPLETED
    if status in {"canceled", "cancelled", "wont fix", "won't fix", "dropped"}:
        return LIFECYCLE_PHASE_CANCELLED
    if status in ACTIVE_STATUS_NAMES:
        return LIFECYCLE_PHASE_ACTIVE
    if status in PLANNED_STATUS_NAMES:
        return LIFECYCLE_PHASE_PLANNED
    return LIFECYCLE_PHASE_UNKNOWN


def finalize_execution_attrs(attrs: dict[str, Any]) -> None:
    """Set lifecycle_phase when enough substrate fields are present."""
    phase = derive_lifecycle_phase(attrs)
    if phase != LIFECYCLE_PHASE_UNKNOWN or any(
        key in attrs for key in ("status_name", "state", "archived", "in_trash")
    ):
        attrs["lifecycle_phase"] = phase
