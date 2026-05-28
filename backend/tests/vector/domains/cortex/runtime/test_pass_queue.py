"""cortex_passes queue helpers."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.runtime.pass_types import CANON_PASS, STATUS_PENDING
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.infrastructure.db.models.tenant import Tenant

pytestmark = pytest.mark.integration


def test_upsert_pending_pass_dedupes_active_row(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Pass Co",
        primary_email="pass@example.com",
        email_domain="example.com",
        slug=f"pass-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    first = upsert_pending_pass_v1(
        db_session,
        tenant_id=tenant.id,
        pass_type=CANON_PASS,
        source_trigger="scheduled",
    )
    second = upsert_pending_pass_v1(
        db_session,
        tenant_id=tenant.id,
        pass_type=CANON_PASS,
        source_trigger="ingestion_complete",
    )
    db_session.commit()
    assert first == second
    count = db_session.scalar(
        select(CortexPass).where(
            CortexPass.tenant_id == tenant.id,
            CortexPass.pass_type == CANON_PASS,
            CortexPass.status == STATUS_PENDING,
        ),
    )
    rows = list(db_session.scalars(select(CortexPass).where(CortexPass.tenant_id == tenant.id)).all())
    assert len(rows) == 1
    assert rows[0].source_trigger == "ingestion_complete"
