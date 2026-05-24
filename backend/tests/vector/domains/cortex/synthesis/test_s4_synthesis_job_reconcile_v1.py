"""S4.1 — synthesis job table reconciliation + terminal transition invariant."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    reconcile_all_stale_synthesis_jobs_v1,
    snapshot_synthesis_hygiene_v1,
    verify_synthesis_job_terminal_transition_invariant_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_s4_terminal_transition_invariant_static() -> None:
    inv = verify_synthesis_job_terminal_transition_invariant_v1()
    assert inv["invariant_ok"] is True
    assert inv["errors"] == []


@pytest.mark.integration
def test_s4_reconcile_all_stale_jobs_dry_run(db_session: Session) -> None:
    user = User(email=f"s4-{uuid.uuid4().hex[:10]}@example.com", full_name="S4 User")
    tenant = Tenant(
        company_name="S4SYN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"s4syn-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    tenant_id = tenant.id

    stale_at = datetime.now(UTC) - timedelta(hours=2)
    job = CortexSynthesisJob(
        tenant_id=tenant_id,
        status="running",
        envelope_digest=f"sha256:{'a' * 64}",
        envelope_json={"synthesis_workload_class": "degradation_brief"},
        created_at=stale_at,
        started_at=stale_at,
    )
    db_session.add(job)
    db_session.flush()

    out = reconcile_all_stale_synthesis_jobs_v1(
        db_session,
        tenant_id=tenant_id,
        dry_run=True,
    )
    assert out["dry_run"] is True
    assert out["receipt_code"] == "synthesis_job_failed_reconcile_receipt"
    assert int(out["running_reconcile"]["reconciled_count"]) >= 1
    db_session.refresh(job)
    assert job.status == "running"

    hygiene = snapshot_synthesis_hygiene_v1(db_session, tenant_id=tenant_id)
    assert hygiene["stale_running_count"] >= 1
    assert hygiene["hygiene_ok"] is False
