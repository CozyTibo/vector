"""Hard-delete a tenant and all product data scoped by tenant_id."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

# Typed in the admin UI before delete (must match exactly, case-sensitive).
HARD_DELETE_TENANT_CONFIRMATION_PHRASE = "DELETE TENANT AND ALL DATA"


def hard_delete_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Delete tenant row and keep only non-legacy delete stats.

    CASCADE removes memberships, connector rows, onboarding, and messages.
    User rows are kept; only memberships for this tenant are removed.
    """
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        msg = f"Tenant not found: {tenant_id}"
        raise ValueError(msg)

    company_name = tenant.company_name
    session.execute(delete(Tenant).where(Tenant.id == tenant_id))

    return {
        "deleted_tenant_id": str(tenant_id),
        "deleted_company_name": company_name,
        # Legacy ingestion/projection/canonical stack was removed.
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
    }
