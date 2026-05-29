"""Notion declared domains integration test."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
    ATTR_DECLARED_CONTAINER_KIND,
)
from vector.domains.cortex.canon.materialize import materialize_raw_row
from vector.domains.cortex.canon.notion_work_containers import update_notion_work_container_pins
from vector.domains.cortex.declared_domains.materialize import execute_declared_domain_pass_for_tenant
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _notion_tenant(db_session: Session) -> tuple[Tenant, TenantConnection, IngestionRun]:
    user = User(email=f"notion-dd-{uuid.uuid4().hex[:8]}@example.com", full_name="Notion DD")
    tenant = Tenant(
        company_name="Notion DD Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"notion-dd-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="notion",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    db_session.add(
        NotionConnectionDetail(
            connection_id=conn.id,
            access_token="test-token",
            work_container_pins=[],
        ),
    )
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="notion",
        status="COMPLETED",
        source_trigger="test",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    return tenant, conn, run


def test_pinned_notion_database_creates_domain_and_row_membership(db_session: Session) -> None:
    tenant, conn, run = _notion_tenant(db_session)
    now = datetime.now(UTC)
    db_id = "db-roadmap"
    db_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="notion",
        resource_type="notion.database",
        external_id=db_id,
        api_endpoint="https://api.notion.com/v1/databases/db-roadmap",
        query_params={},
        source_identity_key=f"notion:notion.database:{db_id}",
        source_revision_key="hash:db1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h1",
        http_status=200,
        run_id=run.id,
        source_trigger="test",
        payload_body={
            "schema_version": 1,
            "connector_type": "notion",
            "connector_instance_id": str(conn.id),
            "source_object_type": "notion.database",
            "source_object_id": db_id,
            "ingestion_version": 1,
            "database": {"id": db_id, "title": [{"plain_text": "Roadmap"}]},
        },
        fetched_at=now,
    )
    row_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="notion",
        resource_type="notion.database_row",
        external_id="row-1",
        api_endpoint="https://api.notion.com/v1/databases/db-roadmap",
        query_params={"database_id": db_id},
        source_identity_key="notion:notion.database_row:row-1",
        source_revision_key="hash:row1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h2",
        http_status=200,
        run_id=run.id,
        source_trigger="test",
        payload_body={
            "schema_version": 1,
            "connector_type": "notion",
            "connector_instance_id": str(conn.id),
            "source_object_type": "notion.database_row",
            "source_object_id": "row-1",
            "ingestion_version": 1,
            "row": {
                "id": "row-1",
                "database_id": db_id,
                "parent": {"type": "database_id", "database_id": db_id},
            },
        },
        fetched_at=now,
    )
    db_session.add_all([db_raw, row_raw])
    db_session.flush()
    materialize_raw_row(db_session, db_raw)
    materialize_raw_row(db_session, row_raw)
    db_session.commit()

    seed = db_session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant.id,
            CanonEntity.entity_type == "project",
        ),
    )
    assert seed is not None
    assert seed.attrs_json.get(ATTR_DECLARED_CONTAINER_KIND) is None

    update_notion_work_container_backfill = update_notion_work_container_pins(
        db_session,
        tenant_id=tenant.id,
        database_ids=[db_id],
        labels_by_id={db_id: "Roadmap"},
    )
    db_session.commit()
    assert update_notion_work_container_backfill["pinned_count"] == 1

    seed = db_session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant.id,
            CanonEntity.entity_type == "project",
        ),
    )
    assert seed is not None
    assert seed.attrs_json.get(ATTR_DECLARED_CONTAINER_KIND) == "work_database"
    assert seed.attrs_json.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID) == db_id

    out = execute_declared_domain_pass_for_tenant(
        db_session,
        tenant_id=tenant.id,
        source_trigger="test",
        batch_limit=50,
        drain=True,
    )
    db_session.commit()
    assert out["status"] == "completed"

    domain = db_session.scalar(
        select(DeclaredDomain).where(DeclaredDomain.tenant_id == tenant.id),
    )
    assert domain is not None
    assert domain.declared_container_kind == "work_database"

    memberships = list(
        db_session.scalars(
            select(DeclaredDomainMembership).where(
                DeclaredDomainMembership.tenant_id == tenant.id,
                DeclaredDomainMembership.status == STATUS_ACTIVE,
            ),
        ).all(),
    )
    assert len(memberships) == 1
    assert memberships[0].extractor_rule == "direct.container_ref"
