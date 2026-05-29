"""Declared domains V1 integration tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.declared_container_registry import (
    ATTR_DECLARED_CONTAINER_KIND,
    ATTR_DECLARED_CONTAINER_EXTERNAL_ID,
)
from vector.domains.cortex.canon.materialize import materialize_raw_row
from vector.domains.cortex.declared_domains.materialize import execute_declared_domain_pass_for_tenant
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.declared_domain import DeclaredDomain
from vector.infrastructure.db.models.declared_domain_membership import (
    DeclaredDomainMembership,
    STATUS_ACTIVE,
)
from vector.infrastructure.db.models.declared_domain_stats import DeclaredDomainStats
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _linear_tenant(db_session: Session) -> tuple[Tenant, TenantConnection, IngestionRun]:
    user = User(email=f"dd-{uuid.uuid4().hex[:8]}@example.com", full_name="DD test")
    tenant = Tenant(
        company_name="DD Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"dd-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="linear",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="linear",
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


def test_level0_project_domain_and_work_item_membership(db_session: Session) -> None:
    tenant, conn, run = _linear_tenant(db_session)
    now = datetime.now(UTC)
    project_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="linear",
        resource_type="linear.project",
        external_id="proj-1",
        api_endpoint="https://api.linear.app/graphql",
        query_params={},
        source_identity_key="linear:linear.project:proj-1",
        source_revision_key="hash:proj1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h1",
        http_status=200,
        run_id=run.id,
        source_trigger="test",
        payload_body={
            "schema_version": 1,
            "connector_type": "linear",
            "connector_instance_id": str(conn.id),
            "source_object_type": "linear.project",
            "source_object_id": "proj-1",
            "ingestion_version": 1,
            "project": {"id": "proj-1", "name": "Alpha"},
        },
        fetched_at=now,
    )
    issue_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="linear",
        resource_type="linear.issue",
        external_id="issue-1",
        api_endpoint="https://api.linear.app/graphql",
        query_params={},
        source_identity_key="linear:linear.issue:issue-1",
        source_revision_key="hash:issue1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h2",
        http_status=200,
        run_id=run.id,
        source_trigger="test",
        payload_body={
            "schema_version": 1,
            "connector_type": "linear",
            "connector_instance_id": str(conn.id),
            "source_object_type": "linear.issue",
            "source_object_id": "issue-1",
            "ingestion_version": 1,
            "issue": {
                "id": "issue-1",
                "identifier": "ENG-1",
                "title": "Ship it",
                "project": {"id": "proj-1", "name": "Alpha"},
            },
        },
        fetched_at=now,
    )
    db_session.add_all([project_raw, issue_raw])
    db_session.flush()
    materialize_raw_row(db_session, project_raw)
    materialize_raw_row(db_session, issue_raw)
    db_session.commit()

    seed = db_session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant.id,
            CanonEntity.entity_type == "project",
        ),
    )
    assert seed is not None
    assert seed.attrs_json.get(ATTR_DECLARED_CONTAINER_KIND) == "project"
    assert seed.attrs_json.get(ATTR_DECLARED_CONTAINER_EXTERNAL_ID) == "proj-1"

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
    assert domain.declared_container_kind == "project"
    assert domain.display_name == "Alpha"

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

    stats = db_session.get(DeclaredDomainStats, domain.id)
    assert stats is not None
    assert stats.mass_total >= 10
    assert stats.events_7d >= 1
