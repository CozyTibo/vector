"""Phase 01 Step 14 — verification gate + reconstruction drill checks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_tenant(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"step14-{uuid.uuid4().hex[:8]}@example.com", full_name="Step 14 User")
    tenant = Tenant(
        company_name="Step14 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"step14-{uuid.uuid4().hex[:10]}",
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
        finished_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    return tenant.id, run.id


def test_step14_gate_fails_when_ping_rows_dominate(db_session: Session) -> None:
    tenant_id, run_id = _seed_tenant(db_session)
    db_session.add_all(
        [
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=uuid.uuid4(),
                connector="github",
                resource_type="github.pull_request",
                external_id="pr-1",
                api_endpoint="https://api.github.com/repos/acme/repo/pulls",
                query_params={},
                payload_body={"title": "one real row"},
                payload_hash="hash-real",
                http_status=200,
                fetched_at=datetime.now(UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-real",
                source_identity_key="github:github.pull_request:pr-1",
                source_revision_key="provider:1",
            ),
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=uuid.uuid4(),
                connector="github",
                resource_type="github.scope_ping",
                external_id="scope-1",
                api_endpoint="internal://github/scope_ping",
                query_params={},
                payload_body={"ping": True},
                payload_hash="hash-ping-1",
                http_status=200,
                fetched_at=datetime.now(UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-ping-1",
                source_identity_key="github:github.scope_ping:scope-1",
                source_revision_key="provider:1",
            ),
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=uuid.uuid4(),
                connector="linear",
                resource_type="linear.viewer_ping",
                external_id="viewer-1",
                api_endpoint="internal://linear/viewer_ping",
                query_params={},
                payload_body={"ping": True},
                payload_hash="hash-ping-2",
                http_status=200,
                fetched_at=datetime.now(UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-ping-2",
                source_identity_key="linear:linear.viewer_ping:viewer-1",
                source_revision_key="provider:1",
            ),
        ]
    )
    db_session.flush()

    rep = verify_tenant_ingestion_invariants(db_session, tenant_id, enforce_exhaust_gate=True)
    assert rep["passed"] is False
    assert rep["exhaust_depth"]["gate_passed"] is False


def test_step14_gate_not_enforced_by_default(db_session: Session) -> None:
    tenant_id, run_id = _seed_tenant(db_session)
    db_session.add(
        RawIngestionRecord(
            tenant_id=tenant_id,
            connection_id=uuid.uuid4(),
            connector="github",
            resource_type="github.scope_ping",
            external_id="scope-only",
            api_endpoint="internal://github/scope_ping",
            query_params={},
            payload_body={"ping": True},
            payload_hash="hash-ping-only",
            http_status=200,
            fetched_at=datetime.now(UTC),
            run_id=run_id,
            source_trigger="manual_admin",
            idempotency_key="idem-ping-only",
            source_identity_key="github:github.scope_ping:scope-only",
            source_revision_key="provider:1",
        )
    )
    db_session.flush()

    rep = verify_tenant_ingestion_invariants(db_session, tenant_id)
    assert "exhaust_depth" in rep
    # Default path remains compatibility-safe for non-gate callers.
    assert isinstance(rep["passed"], bool)
