"""Hard-delete a user account with no workspace ties (admin-only safety valve)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.infrastructure.db.repositories import tenancy as tenancy_repo

# Typed in the admin UI before delete (must match exactly, case-sensitive).
HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE = "DELETE USER ACCOUNT"


def hard_delete_orphan_user(session: Session, *, user_id: uuid.UUID) -> str:
    """Delete user row if they have no memberships and no tenant_connections as connector.

    CASCADE removes identities and onboarding messages tied to this user.
    """
    user = tenancy_repo.get_user_by_id(session, user_id)
    if user is None:
        msg = f"User not found: {user_id}"
        raise ValueError(msg)

    if tenancy_repo.count_memberships_for_user(session, user_id) > 0:
        msg = "User still belongs to one or more workspaces."
        raise ValueError(msg)

    if tenancy_repo.count_tenant_connections_for_connected_user(session, user_id) > 0:
        msg = "User still has tenant connection records (connected_by)."
        raise ValueError(msg)

    email = user.email
    session.delete(user)
    return email
