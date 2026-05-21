"""Admin recent ingestion runs listing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.admin_recent_raw import list_recent_ingestion_runs
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_runs(db_session: Session) -> uuid.UUID:
    user = User(email=f"runs-{uuid.uuid4().hex[:8]}@example.com", full_name="Runs User")
    tenant = Tenant(
        company_name="Runs Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"runs-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    now = datetime.now(UTC)
    for i, connector in enumerate(["slack", "notion", "slack"]):
        db_session.add(
            IngestionRun(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                connection_id=conn.id,
                connector=connector,
                status="COMPLETED",
                source_trigger="scheduled",
                sync_mode="incremental",
                replay_mode=False,
                replay_version=1,
                started_at=now.replace(second=i),
            ),
        )
    db_session.commit()
    return tenant.id


def test_list_recent_ingestion_runs_paginates_and_filters(db_session: Session) -> None:
    tenant_id = _seed_runs(db_session)

    page0, total = list_recent_ingestion_runs(db_session, tenant_id, limit=2, offset=0)
    assert total == 3
    assert len(page0) == 2

    slack_only, slack_total = list_recent_ingestion_runs(
        db_session,
        tenant_id,
        limit=10,
        connector="slack",
    )
    assert slack_total == 2
    assert all(r["connector"] == "slack" for r in slack_only)
