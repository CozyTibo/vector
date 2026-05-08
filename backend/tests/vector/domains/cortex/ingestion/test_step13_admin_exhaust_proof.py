"""Phase 01 Step 13 — admin exhaust proof filters and health-row defaults."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.admin_recent_raw import (
    aggregate_raw_ingestion_stats,
    list_raw_records_for_connector,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_rows(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"step13-{uuid.uuid4().hex[:8]}@example.com", full_name="Step 13 User")
    tenant = Tenant(
        company_name="Step13 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"step13-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()

    base_t = datetime.now(UTC)
    db_session.add_all(
        [
            RawIngestionRecord(
                tenant_id=tenant.id,
                connection_id=conn.id,
                connector="github",
                resource_type="github.pull_request",
                external_id="pr-1",
                api_endpoint="https://api.github.com/repos/acme/repo/pulls",
                query_params={"page": 1},
                payload_body={"title": "alpha token"},
                payload_hash="hash-1",
                http_status=200,
                fetched_at=base_t - timedelta(hours=2),
                run_id=run.id,
                source_trigger="manual_admin",
                idempotency_key="idem-1",
                source_identity_key="github:github.pull_request:pr-1",
                source_revision_key="provider:1",
            ),
            RawIngestionRecord(
                tenant_id=tenant.id,
                connection_id=conn.id,
                connector="github",
                resource_type="github.scope_ping",
                external_id="scope",
                api_endpoint="internal://github/scope_ping",
                query_params={},
                payload_body={"ping": True},
                payload_hash="hash-2",
                http_status=200,
                fetched_at=base_t - timedelta(hours=1),
                run_id=run.id,
                source_trigger="manual_admin",
                idempotency_key="idem-2",
                source_identity_key="github:github.scope_ping:scope",
                source_revision_key="provider:1",
            ),
            RawIngestionRecord(
                tenant_id=tenant.id,
                connection_id=conn.id,
                connector="github",
                resource_type="github.pull_request",
                external_id="pr-2",
                api_endpoint="https://api.github.com/repos/acme/repo/pulls",
                query_params={"page": 2},
                payload_body={"title": "beta token payload-needle"},
                payload_hash="hash-3",
                http_status=200,
                fetched_at=base_t,
                run_id=run.id,
                source_trigger="manual_admin",
                idempotency_key="idem-3",
                source_identity_key="github:github.pull_request:pr-2",
                source_revision_key="provider:2",
            ),
        ]
    )
    db_session.flush()
    return tenant.id, conn.id


def test_step13_aggregate_raw_stats_hides_health_rows_by_default(db_session: Session) -> None:
    tenant_id, _ = _seed_rows(db_session)
    rows = aggregate_raw_ingestion_stats(db_session, tenant_id)
    assert all(r["resource_type"] != "github.scope_ping" for r in rows)

    with_health = aggregate_raw_ingestion_stats(db_session, tenant_id, include_health_rows=True)
    assert any(r["resource_type"] == "github.scope_ping" for r in with_health)


def test_step13_raw_records_payload_search_and_health_toggle(db_session: Session) -> None:
    tenant_id, _ = _seed_rows(db_session)
    items_default, _, _ = list_raw_records_for_connector(db_session, tenant_id, "github")
    assert len(items_default) == 2
    assert all(r["resource_type"] != "github.scope_ping" for r in items_default)

    items_search, _, _ = list_raw_records_for_connector(
        db_session, tenant_id, "github", search_query="payload-needle"
    )
    assert len(items_search) == 1
    assert items_search[0]["external_id"] == "pr-2"

    items_health, _, _ = list_raw_records_for_connector(
        db_session,
        tenant_id,
        "github",
        include_health_rows=True,
        resource_type="github.scope_ping",
    )
    assert len(items_health) == 1
    assert items_health[0]["resource_type"] == "github.scope_ping"
