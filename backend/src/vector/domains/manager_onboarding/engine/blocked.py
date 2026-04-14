"""Minimal onboarding blocked state in ``context_json``."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

BLOCK_REASON_CHANNEL = "channel_inaccessible"
BLOCK_REASON_ENTITY = "entity_unresolvable"
BLOCK_REASON_REFUSED = "user_refused"


def clear_onboarding_blocked(ctx: dict[str, Any]) -> None:
    ctx.pop("onboarding_blocked", None)


def set_onboarding_blocked(
    ctx: dict[str, Any],
    *,
    reason: str,
    detail: str,
    requirement_id: str | None,
) -> None:
    ctx["onboarding_blocked"] = {
        "active": True,
        "reason": reason,
        "detail": (detail or "")[:500],
        "requirement_id": requirement_id or "",
        "since": datetime.now(UTC).isoformat(),
    }


def refresh_blocked_after_turn(
    ctx: dict[str, Any],
    *,
    merged_something: bool,
    channels_inaccessible: bool,
    entity_unresolved: bool,
    primary_requirement: str | None,
) -> None:
    if merged_something:
        clear_onboarding_blocked(ctx)
        return
    if channels_inaccessible:
        set_onboarding_blocked(
            ctx,
            reason=BLOCK_REASON_CHANNEL,
            detail="One or more channels could not be accessed or joined.",
            requirement_id=primary_requirement,
        )
        return
    if entity_unresolved:
        set_onboarding_blocked(
            ctx,
            reason=BLOCK_REASON_ENTITY,
            detail="Could not resolve one or more Slack people or groups.",
            requirement_id=primary_requirement,
        )
