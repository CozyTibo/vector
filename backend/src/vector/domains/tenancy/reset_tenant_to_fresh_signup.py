"""Reset a tenant to a post-signup empty state while keeping the tenant row and memberships."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from vector.domains.ingestion.step1_reset import wipe_step1_raw_for_tenant
from vector.domains.ingestion.step2_step3_reset import (
    wipe_step2_projections_for_tenant,
    wipe_step3_canonical_for_tenant,
)
from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import onboarding as onboarding_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

# Typed in the admin UI before reset (must match exactly, case-sensitive).
RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE = "RESET WORKSPACE TO FRESH SIGNUP"


def reset_tenant_to_fresh_signup(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Wipe product data and integrations; keep tenant id, company profile fields, and memberships.

    - Step 3 → 1 ingestion/canonical data (same wipes as hard delete, without removing the tenant).
    - All ``tenant_connections`` (OAuth tokens / connector links).
    - Website onboarding state + chat transcript rows.
    - Manager Slack onboarding sessions (and dependent rows via FK / CASCADE).
    - Tenant flags: ``workspace_access_enabled=False``, ``slack_vector_paused=False``, ``status=active``.
    - Seeds a fresh ``onboarding_state`` row (day-one chat profile step).

    Does not remove ``tenant_memberships`` or user accounts.
    """
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        msg = f"Tenant not found: {tenant_id}"
        raise ValueError(msg)

    n_conn = int(
        session.scalar(
            select(func.count()).select_from(TenantConnection).where(TenantConnection.tenant_id == tenant_id),
        )
        or 0,
    )
    n_mo = int(
        session.scalar(
            select(func.count())
            .select_from(ManagerOnboardingSession)
            .where(ManagerOnboardingSession.tenant_id == tenant_id),
        )
        or 0,
    )

    step3 = wipe_step3_canonical_for_tenant(session, tenant_id=tenant_id)
    step2 = wipe_step2_projections_for_tenant(session, tenant_id=tenant_id)
    step1 = wipe_step1_raw_for_tenant(session, tenant_id=tenant_id)

    session.execute(delete(TenantConnection).where(TenantConnection.tenant_id == tenant_id))
    session.execute(delete(OnboardingMessage).where(OnboardingMessage.tenant_id == tenant_id))
    session.execute(delete(OnboardingState).where(OnboardingState.tenant_id == tenant_id))

    session.execute(
        update(ManagerOnboardingSession)
        .where(ManagerOnboardingSession.tenant_id == tenant_id)
        .values(parent_session_id=None),
    )
    session.execute(delete(ManagerOnboardingSession).where(ManagerOnboardingSession.tenant_id == tenant_id))

    tenant.workspace_access_enabled = False
    tenant.slack_vector_paused = False
    tenant.status = "active"

    onboarding_repo.get_or_create_onboarding(session, tenant_id)

    return {
        "tenant_id": tenant_id,
        "company_name": tenant.company_name,
        "step3": step3,
        "step2": step2,
        "step1": step1,
        "deleted_tenant_connections": n_conn,
        "deleted_manager_onboarding_sessions": n_mo,
    }
