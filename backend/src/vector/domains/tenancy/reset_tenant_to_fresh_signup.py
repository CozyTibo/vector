"""Reset a tenant to a post-signup empty state while keeping the tenant row and memberships."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.orm import Session

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

    - Legacy Step 1/2/3 ingestion data is already removed from this codebase.
    - All ``tenant_connections`` (OAuth tokens / connector links).
    - Website onboarding state + chat transcript rows.
    - Legacy manager-onboarding session rows when those tables still exist (no-op after they are dropped).
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

    session.execute(delete(TenantConnection).where(TenantConnection.tenant_id == tenant_id))
    session.execute(delete(OnboardingMessage).where(OnboardingMessage.tenant_id == tenant_id))
    session.execute(delete(OnboardingState).where(OnboardingState.tenant_id == tenant_id))

    bind = session.get_bind()
    if bind is not None and inspect(bind).has_table("manager_onboarding_sessions"):
        session.execute(
            text(
                "UPDATE manager_onboarding_sessions SET parent_session_id = NULL "
                "WHERE tenant_id = CAST(:tid AS uuid)",
            ).bindparams(tid=str(tenant_id)),
        )
        session.execute(
            text(
                "DELETE FROM manager_onboarding_sessions WHERE tenant_id = CAST(:tid AS uuid)",
            ).bindparams(tid=str(tenant_id)),
        )

    tenant.workspace_access_enabled = False
    tenant.slack_vector_paused = False
    tenant.status = "active"

    onboarding_repo.get_or_create_onboarding(session, tenant_id)

    return {
        "tenant_id": tenant_id,
        "company_name": tenant.company_name,
        "step3": {
            "deleted_relationships": 0,
            "deleted_mapping_events": 0,
            "deleted_current_mappings": 0,
            "deleted_external_references": 0,
            "deleted_actor_external_identities": 0,
            "deleted_artifacts": 0,
            "deleted_actors": 0,
            "deleted_step3_canonical_cursors": 0,
        },
        "step2": {
            "deleted_github_projection_rows": 0,
            "deleted_linear_projection_rows": 0,
            "deleted_connector_projection_progress_rows": 0,
        },
        "step1": {
            "deleted_raw_records": 0,
            "deleted_ingestion_runs": 0,
            "deleted_sync_state_rows": 0,
        },
        "deleted_tenant_connections": n_conn,
    }
