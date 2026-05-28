from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.pass_run_ops import abandon_stuck_running_canon_passes
from vector.domains.cortex.canon.scheduler_dedup import should_skip_scheduled_canon_pass
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.tenant import Tenant

pytestmark = pytest.mark.integration


def test_skip_when_scheduled_canon_pass_ran_recently(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Canon Sched Co",
        primary_email="canon-sched@example.com",
        email_domain="example.com",
        slug=f"canon-sched-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    db_session.add(
        CanonPassRun(
            tenant_id=tenant.id,
            source_trigger="scheduled",
            status="COMPLETED",
            started_at=utc_now() - timedelta(seconds=30),
            finished_at=utc_now(),
        ),
    )
    db_session.commit()
    assert should_skip_scheduled_canon_pass(
        db_session,
        tenant_id=tenant.id,
        interval_seconds=300,
    )


def test_stuck_running_canon_pass_is_abandoned(db_session: Session) -> None:
    tenant = Tenant(
        company_name="Canon Stuck Co",
        primary_email="canon-stuck@example.com",
        email_domain="example.com",
        slug=f"canon-stuck-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    stuck_run = CanonPassRun(
        tenant_id=tenant.id,
        source_trigger="scheduled",
        status="RUNNING",
        started_at=utc_now() - timedelta(hours=2),
    )
    db_session.add(stuck_run)
    db_session.commit()
    abandoned = abandon_stuck_running_canon_passes(
        db_session,
        tenant_id=tenant.id,
        interval_seconds=300,
    )
    db_session.commit()
    assert abandoned == 1
    db_session.refresh(stuck_run)
    assert stuck_run.status == "FAILED"
    assert stuck_run.error_summary == "stale_running_pass_abandoned"
