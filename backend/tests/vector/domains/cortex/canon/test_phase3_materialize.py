"""Phase 3 — canon entity materialization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant, materialize_raw_row
from vector.domains.cortex.ingestion.raw_envelope_contract import core_envelope_fields
from vector.domains.cortex.ingestion.sync_shared import append_raw
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _seed_pr(db_session: Session) -> uuid.UUID:
    user = User(email=f"canon3-{uuid.uuid4().hex[:8]}@example.com", full_name="Canon3")
    tenant = Tenant(
        company_name="Canon3 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"canon3-{uuid.uuid4().hex[:10]}",
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
        external_id="acme/app#99",
        api_endpoint="https://api.github.com/repos/acme/app/pulls",
        query_params={},
        payload_body={
            **core_envelope_fields(
                connector="github",
                connection_id=conn.id,
                source_object_type="github.pull_request",
                source_object_id="acme/app#99",
            ),
            "pull_request": {
                "number": 99,
                "title": "Canon PR",
                "state": "open",
                "updated_at": "2026-02-01T12:00:00Z",
                "user": {"login": "dev1", "id": 1},
                "head": {"sha": "abc", "repo": {"full_name": "acme/app"}},
            },
        },
        http_status=200,
        idempotency_key="test:pr:99",
    )
    db_session.commit()
    return tenant.id


def test_materialize_github_pull_request(db_session: Session) -> None:
    tenant_id = _seed_pr(db_session)
    from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

    row = db_session.scalar(
        select(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id).limit(1),
    )
    assert row is not None
    out = materialize_raw_row(db_session, row)
    assert out["outcome"] == "materialized"
    db_session.commit()
    entity = db_session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_type == "pull_request",
        ),
    )
    assert entity is not None
    assert "Canon PR" in entity.display_label
    sources = list(
        db_session.scalars(
            select(CanonEntitySource).where(CanonEntitySource.canon_entity_id == entity.id),
        ).all(),
    )
    assert len(sources) >= 1
    assert any(s.is_latest for s in sources)


def test_execute_canon_pass_idempotent(db_session: Session) -> None:
    tenant_id = _seed_pr(db_session)
    r1 = execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert r1["status"] == "completed"
    assert r1["stats"]["materialized"] >= 1
    r2 = execute_canon_pass_for_tenant(
        db_session,
        tenant_id=tenant_id,
        source_trigger="test",
        batch_limit=100,
    )
    db_session.commit()
    assert r2["stats"]["scanned"] == 0 or r2["stats"]["materialized"] == 0
