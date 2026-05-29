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
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> Tenant:
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
    db_session.flush()
    return tenant


def test_count_unlinked_scoped_entities_excludes_linked_endpoints(db_session: Session) -> None:
    tenant = _tenant(db_session)
    now = datetime.now(UTC)
    actor = CanonEntity(
        tenant_id=tenant.id,
        connector="github",
        entity_type="actor",
        entity_key="actor:1",
        display_label="Alice",
        observed_at=now,
    )
    message = CanonEntity(
        tenant_id=tenant.id,
        connector="github",
        entity_type="message",
        entity_key="msg:1",
        display_label="Hello",
        observed_at=now,
        author_entity_id=None,
    )
    orphan = CanonEntity(
        tenant_id=tenant.id,
        connector="github",
        entity_type="message",
        entity_key="msg:2",
        display_label="Orphan",
        observed_at=now,
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
        ),
    )
    db_session.flush()

    assert count_unlinked_scoped_entities(db_session, tenant.id) == 1

    readiness = build_graph_readiness(db_session, tenant.id)
    assert readiness["scoped_entity_count"] == 3
    assert readiness["unlinked_scoped_entity_count"] == 1


def test_graph_stats_by_kind_includes_zero_extractable_kinds(db_session: Session) -> None:
    tenant = _tenant(db_session)
    stats = graph_stats_by_kind(db_session, tenant.id)
    kinds = [row["relationship_kind"] for row in stats]
    assert kinds == list(EXTRACTABLE_RELATIONSHIP_KINDS)
    authored = next(row for row in stats if row["relationship_kind"] == "authored_by")
    assigned = next(row for row in stats if row["relationship_kind"] == "assigned_to")
    assert authored["count"] == 0
    assert assigned["count"] == 0
