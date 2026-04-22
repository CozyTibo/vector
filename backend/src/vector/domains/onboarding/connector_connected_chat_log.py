"""Append onboarding transcript lines when a connector OAuth completes (product onboarding)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import STATUS_COMPLETED
from vector.infrastructure.db.repositories import onboarding as ob_repo


def _return_targets_product_onboarding(return_to: str | None) -> bool:
    if not return_to or not isinstance(return_to, str):
        return False
    normalized = return_to.replace("\\", "/")
    return "/app/onboarding" in normalized


def append_connector_connected_user_line(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    return_to: str | None,
    tool_label: str,
) -> None:
    """Persist a user-role chat line (e.g. ``Linear connected``) when OAuth lands on onboarding."""
    if not _return_targets_product_onboarding(return_to):
        return
    if not ob_repo.onboarding_messages_table_exists(session):
        return
    row = ob_repo.get_onboarding_for_tenant(session, tenant_id)
    if row is None or row.status == STATUS_COMPLETED:
        return
    line = f"{tool_label.strip()} connected"
    prior = ob_repo.list_onboarding_messages_chronological(session, tenant_id, limit=200)
    last = prior[-1] if prior else None
    if last is not None and last.role == "user" and (last.content or "").strip() == line:
        return
    ob_repo.append_onboarding_message(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        role="user",
        content=line,
    )
