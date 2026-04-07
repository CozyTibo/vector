"""Hard-delete a tenant and all product data scoped by tenant_id."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from vector.domains.ingestion.step1_reset import wipe_step1_raw_for_tenant
from vector.domains.ingestion.step2_step3_reset import (
    wipe_step2_projections_for_tenant,
    wipe_step3_canonical_for_tenant,
)
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

# Typed in the admin UI before delete (must match exactly, case-sensitive).
HARD_DELETE_TENANT_CONFIRMATION_PHRASE = "DELETE TENANT AND ALL DATA"


def hard_delete_tenant(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Wipe Step 3 → Step 1, then delete the tenant row.

    CASCADE removes memberships, connector rows, onboarding, and messages.
    User rows are kept; only memberships for this tenant are removed.
    """
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        msg = f"Tenant not found: {tenant_id}"
        raise ValueError(msg)

    company_name = tenant.company_name
    step3 = wipe_step3_canonical_for_tenant(session, tenant_id=tenant_id)
    step2 = wipe_step2_projections_for_tenant(session, tenant_id=tenant_id)
    step1 = wipe_step1_raw_for_tenant(session, tenant_id=tenant_id)

    session.execute(delete(Tenant).where(Tenant.id == tenant_id))

    return {
        "deleted_tenant_id": str(tenant_id),
        "deleted_company_name": company_name,
        "step3": step3,
        "step2": step2,
        "step1": step1,
    }
