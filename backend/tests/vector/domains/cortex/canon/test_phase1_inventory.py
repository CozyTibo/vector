"""Phase 1 — canon inventory and readiness."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.admin_readiness import build_canon_admin_readiness
from vector.domains.cortex.canon.inventory import (
    build_tenant_canon_readiness,
    scan_materialization_lag,
    scan_tenant_raw_inventory,
)
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _seed_tenant_with_raw(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"canon-{uuid.uuid4().hex[:8]}@example.com", full_name="Canon User")
    tenant = Tenant(
        company_name="Canon Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"canon-{uuid.uuid4().hex[:10]}",
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
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    ctx = IngestionSyncContext.live_incremental()
    append_raw(
        db_session,
        ctx=ctx,
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        run_id=run.id,
        source_trigger="test",
        resource_type="github.pull_request",
        external_id="acme/repo#1",
        api_endpoint="https://api.github.com/repos/acme/repo/pulls",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="github",
                connection_id=conn.id,
                source_object_type="github.pull_request",
                source_object_id="acme/repo#1",
            ),
            "pull_request": {"number": 1, "title": "Test PR", "updated_at": "2026-01-01T00:00:00Z"},
        },
        http_status=200,
        idempotency_key="test:pr:1",
    )
    db_session.commit()
    return tenant.id, conn.id


def test_scan_tenant_raw_inventory(db_session: Session) -> None:
    tenant_id, _ = _seed_tenant_with_raw(db_session)
    inv = scan_tenant_raw_inventory(db_session, tenant_id)
    assert inv["total_live_rows"] >= 1
    assert "github.pull_request" in inv["resource_type_counts"]
    assert inv["max_live_raw_id"] > 0


def test_materialization_lag_without_cursor(db_session: Session) -> None:
    tenant_id, _ = _seed_tenant_with_raw(db_session)
    lag = scan_materialization_lag(db_session, tenant_id)
    assert lag["last_raw_id"] == 0
    assert lag["pending_raw_rows_estimate"] >= 1


def test_build_canon_admin_readiness(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    tenant_id, _ = _seed_tenant_with_raw(db_session)
    payload = build_canon_admin_readiness(db_session, get_settings(), tenant_id)
    assert payload["company_name"] == "Canon Co"
    assert payload["raw_inventory"]["total_live_rows"] >= 1
    assert "scheduler" in payload
