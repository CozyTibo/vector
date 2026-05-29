"""Graph admin readiness helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.admin import (
    build_graph_readiness,
    count_unlinked_scoped_entities,
    graph_stats_by_kind,
)
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
