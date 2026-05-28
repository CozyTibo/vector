from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.tasks.cortex_identity_scheduler import _should_skip_scheduled_identity_pass
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.tenant import Tenant

pytestmark = pytest.mark.integration


def test_skip_when_scheduled_pass_ran_recently(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Sched Co",
        primary_email="sched@example.com",
        email_domain="example.com",
        slug=f"sched-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    db_session.add(
        IdentityPassRun(
            tenant_id=tenant.id,
            source_trigger="scheduled",
            status="COMPLETED",
            started_at=utc_now() - timedelta(seconds=30),
            finished_at=utc_now(),
        ),
    )
    db_session.commit()
    assert _should_skip_scheduled_identity_pass(
        db_session,
        tenant_id=tenant.id,
        interval_seconds=300,
    )


def test_no_skip_when_last_scheduled_pass_is_stale(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Sched2 Co",
        primary_email="sched2@example.com",
        email_domain="example.com",
        slug=f"sched2-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    db_session.add(
        IdentityPassRun(
            tenant_id=tenant.id,
            source_trigger="scheduled",
            status="COMPLETED",
            started_at=utc_now() - timedelta(seconds=400),
            finished_at=utc_now() - timedelta(seconds=390),
        ),
    )
    db_session.commit()
    assert not _should_skip_scheduled_identity_pass(
        db_session,
        tenant_id=tenant.id,
        interval_seconds=300,
    )
