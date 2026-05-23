"""Wave S0 — semantic readiness snapshot."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.semantic_readiness_v1 import (
    build_graph_truth_audit_snapshot_v1,
    build_semantic_readiness_v1,
    format_semantic_readiness_text_v1,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User

pytestmark = pytest.mark.integration


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"sem-{uuid.uuid4().hex[:10]}@example.com", full_name="Sem")
    tenant = Tenant(
        company_name="Sem Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"sem-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_semantic_readiness_empty_tenant(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    snap = build_semantic_readiness_v1(db_session, tenant_id=tid)
    assert snap["surface_kind"] == "semantic_readiness"
    assert snap["product_substrate"] == "retrieval"
    g = snap["graph_truth"]
    assert g["unique_auth_pairs"] == 0
    assert g["auth_edge_rows"] == 0
    assert g["dup_factor"] is None
    assert g["primary_metric_key"] == "unique_auth_pairs"
    assert g["auth_edge_rows_deprecated_primary"] is True
    assert snap["retrieval"]["published_index_epoch"] is None
    panel = snap["semantic_operator_panel"]
    assert len(panel) == 6
    keys = {m["key"] for m in panel}
    assert keys == {
        "unique_auth_pairs",
        "promotion_rule_count",
        "retrieval_org_link_pct",
        "retrieval_execution_index_pct",
        "synthesis_published_claims_7d",
        "retrieval_freshness_minutes",
    }
    text = format_semantic_readiness_text_v1(snap)
    assert "Unique auth pairs" in text


def test_graph_truth_audit_snapshot_shape(db_session: Session) -> None:
    tid = _tenant(db_session)
    db_session.commit()
    snap = build_graph_truth_audit_snapshot_v1(db_session, tenant_id=tid)
    assert snap["surface_kind"] == "graph_truth_audit_snapshot"
    assert "candidates" in snap
    assert "repro_command" in snap
    assert snap["graph_truth"]["promotions_by_rule_id"] == []
