"""Graph admin readiness helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.admin import (
    build_graph_readiness,
    count_unlinked_scoped_entities,
    graph_stats_by_kind,
)
from vector.domains.cortex.graph.materialize import (
    prepare_graph_rebuild_for_tenant,
    rebuild_graph_links_for_entity,
)
from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue
from vector.infrastructure.db.models.graph_relationship import STATUS_SUPERSEDED
from vector.domains.cortex.graph.relationship_kinds import EXTRACTABLE_RELATIONSHIP_KINDS
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.graph_relationship import GraphRelationship
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> tuple[Tenant, TenantConnection]:
    user = User(email=f"graph-admin-{uuid.uuid4().hex[:8]}@example.com", full_name="Admin")
    tenant = Tenant(
        company_name="Graph Admin Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"graph-admin-{uuid.uuid4().hex[:8]}",
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
    return tenant, conn


def _canon_entity(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    entity_type: str,
    entity_key: str,
    display_label: str,
    materialized_at: datetime,
    **refs: uuid.UUID | None,
) -> CanonEntity:
    return CanonEntity(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector="github",
        entity_type=entity_type,
        entity_key=entity_key,
        display_label=display_label,
        attrs_json={},
        mapper_version=1,
        materialized_at=materialized_at,
        **refs,
    )


def test_count_unlinked_scoped_entities_excludes_linked_endpoints(db_session: Session) -> None:
    tenant, conn = _tenant(db_session)
    now = datetime.now(UTC)
    actor = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="actor",
        entity_key="actor:1",
        display_label="Alice",
        materialized_at=now,
    )
    message = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="message",
        entity_key="msg:1",
        display_label="Hello",
        materialized_at=now,
    )
    orphan = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="message",
        entity_key="msg:2",
        display_label="Orphan",
        materialized_at=now,
    )
    db_session.add_all([actor, message, orphan])
    db_session.flush()
    message.author_entity_id = actor.id
    db_session.add(
        GraphRelationship(
            tenant_id=tenant.id,
            relationship_kind="authored_by",
            from_entity_id=message.id,
            to_entity_id=actor.id,
            direction="directed",
            confidence="certain",
            extractor_version=1,
            extractor_rule="test",
            evidence_kind="canon_ref",
            evidence_ref="author_entity_id",
            observed_at=now,
            status="active",
            created_at=now,
        ),
    )
    db_session.flush()

    assert count_unlinked_scoped_entities(db_session, tenant.id) == 1

    readiness = build_graph_readiness(db_session, tenant.id)
    assert readiness["scoped_entity_count"] == 3
    assert readiness["unlinked_scoped_entity_count"] == 1


def test_graph_stats_by_kind_includes_zero_extractable_kinds(db_session: Session) -> None:
    tenant, _conn = _tenant(db_session)
    stats = graph_stats_by_kind(db_session, tenant.id)
    kinds = [row["relationship_kind"] for row in stats]
    assert kinds == list(EXTRACTABLE_RELATIONSHIP_KINDS)
    authored = next(row for row in stats if row["relationship_kind"] == "authored_by")
    assigned = next(row for row in stats if row["relationship_kind"] == "assigned_to")
    replies = next(row for row in stats if row["relationship_kind"] == "replies_to")
    references = next(row for row in stats if row["relationship_kind"] == "references")
    assert authored["count"] == 0
    assert assigned["count"] == 0
    assert replies["count"] == 0
    assert references["count"] == 0


def test_prepare_graph_rebuild_enqueues_scoped_entities(db_session: Session) -> None:
    tenant, conn = _tenant(db_session)
    now = datetime.now(UTC)
    issue = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="github.issue",
        entity_key="i-1",
        display_label="Issue",
        materialized_at=now,
    )
    db_session.add(issue)
    db_session.flush()

    prep = prepare_graph_rebuild_for_tenant(db_session, tenant_id=tenant.id)
    assert prep["enqueued_entity_count"] == 1

    pending = db_session.scalars(
        select(GraphDirtyQueue).where(
            GraphDirtyQueue.tenant_id == tenant.id,
            GraphDirtyQueue.processed_at.is_(None),
        ),
    ).all()
    assert len(pending) == 1
    assert pending[0].reason == "rebuild"

    edge = db_session.scalar(select(GraphRelationship).where(GraphRelationship.tenant_id == tenant.id))
    assert edge is None or edge.status == STATUS_SUPERSEDED


def test_rebuild_graph_links_for_entity_supersedes_and_reextracts(db_session: Session) -> None:
    tenant, conn = _tenant(db_session)
    now = datetime.now(UTC)
    page = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="document",
        entity_key="page-1",
        display_label="Page",
        materialized_at=now,
    )
    parent = _canon_entity(
        tenant_id=tenant.id,
        connection_id=conn.id,
        entity_type="document",
        entity_key="page-parent",
        display_label="Parent",
        materialized_at=now,
    )
    db_session.add_all([page, parent])
    db_session.flush()
    page.parent_document_entity_id = parent.id
    old_edge = GraphRelationship(
        tenant_id=tenant.id,
        relationship_kind="parent_of",
        from_entity_id=page.id,
        to_entity_id=parent.id,
        confidence="certain",
        extractor_version=1,
        extractor_rule="canon.parent_document_entity_id",
        evidence_kind="canon_ref",
        evidence_ref="parent_document_entity_id",
        observed_at=now,
        status="active",
        created_at=now,
    )
    db_session.add(old_edge)
    db_session.flush()

    out = rebuild_graph_links_for_entity(db_session, tenant_id=tenant.id, canon_entity_id=page.id)
    assert out["status"] == "completed"
    assert out["stats"]["edges_superseded"] == 1

    active = list(
        db_session.scalars(
            select(GraphRelationship).where(
                GraphRelationship.tenant_id == tenant.id,
                GraphRelationship.status == "active",
                GraphRelationship.from_entity_id == page.id,
            ),
        ).all(),
    )
    assert len(active) >= 1
    assert all(e.extractor_version >= 8 for e in active)
