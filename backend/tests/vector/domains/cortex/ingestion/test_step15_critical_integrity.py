"""Phase 02 Step 15 — reconstruction-critical pointer integrity (G15)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.raw_memory_critical_integrity import (
    verify_phase02_step15_critical_integrity,
)
from vector.domains.cortex.ingestion.raw_memory_verification_unified import (
    compute_phase02_gate_g15_critical_integrity,
)


def test_gate_g15_follows_step15_passed() -> None:
    g = compute_phase02_gate_g15_critical_integrity({"passed": True})
    assert g["decision"] == "pass"

    g_fail = compute_phase02_gate_g15_critical_integrity({"passed": False})
    assert g_fail["decision"] == "hard_fail"


@pytest.mark.integration
def test_step15_passes_when_indexes_empty(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"s15-{uuid.uuid4().hex[:8]}@example.com", full_name="Step15 User")
    tenant = Tenant(
        company_name="Step15Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s15-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()

    rep = verify_phase02_step15_critical_integrity(db_session, tenant.id)
    assert rep["passed"] is True
    assert rep["state"] == "integrity_sound"
