"""Graph projection phase 0 — canon ref edges."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.materialize import materialize_raw_row
from vector.domains.cortex.graph.materialize import execute_graph_projection_pass_for_tenant
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.graph_relationship import GraphRelationship, STATUS_ACTIVE
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection

pytestmark = pytest.mark.integration


def _tenant_conn(db_session: Session) -> tuple[Tenant, TenantConnection]:
    tenant = Tenant(
        company_name="Graph Co",
        primary_email="graph@example.com",
        email_domain="example.com",
        slug=f"graph-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        external_id=f"gh-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(conn)
    db_session.flush()
    return tenant, conn


def test_phase0_projects_authored_by_from_canon_ref(db_session: Session) -> None:
    tenant, conn = _tenant_conn(db_session)
    actor_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.user",
        external_id="alice",
        source_identity_key="github:github.user:alice",
        source_revision_key="hash:actor1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h1",
        payload_body={
            "schema_version": 1,
            "connector_type": "github",
            "connector_instance_id": str(conn.id),
            "source_object_type": "github.user",
            "source_object_id": "alice",
            "ingestion_version": 1,
            "user": {"login": "alice", "id": 1},
        },
        fetched_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    msg_raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.issue_comment",
        external_id="issue-1:comment-1",
        source_identity_key="github:github.issue_comment:issue-1:comment-1",
        source_revision_key="hash:msg1",
        idempotency_key=f"idemp-{uuid.uuid4().hex}",
        payload_hash="h2",
        payload_body={
            "schema_version": 1,
            "connector_type": "github",
            "connector_instance_id": str(conn.id),
            "source_object_type": "github.issue_comment",
            "source_object_id": "issue-1:comment-1",
            "ingestion_version": 1,
            "comment": {"id": 1, "user": {"login": "alice", "id": 1}},
        },
        fetched_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    db_session.add(actor_raw)
    db_session.add(msg_raw)
    db_session.flush()
    materialize_raw_row(db_session, actor_raw)
    materialize_raw_row(db_session, msg_raw)
    db_session.commit()

    out = execute_graph_projection_pass_for_tenant(
        db_session,
        tenant_id=tenant.id,
        source_trigger="test",
        batch_limit=50,
        drain=True,
    )
    db_session.commit()
    assert out["status"] == "completed"
    edges = list(
        db_session.scalars(
            select(GraphRelationship).where(
                GraphRelationship.tenant_id == tenant.id,
                GraphRelationship.status == STATUS_ACTIVE,
            ),
        ).all(),
    )
    kinds = {e.relationship_kind for e in edges}
    assert "authored_by" in kinds

    msg = db_session.scalar(
        select(CanonEntity).where(
            CanonEntity.tenant_id == tenant.id,
            CanonEntity.entity_type == "message",
        ),
    )
    assert msg is not None
    authored = [
        e
        for e in edges
        if e.relationship_kind == "authored_by" and e.from_entity_id == msg.id
    ]
    assert len(authored) >= 1
