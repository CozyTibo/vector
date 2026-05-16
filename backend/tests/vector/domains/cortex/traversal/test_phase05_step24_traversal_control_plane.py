"""P05-24 — OCTS traversal control plane + **G-P05-CP-01**."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.traversal.runtime.durable_walk_store import OctsWalkApiDurableStore
from vector.domains.cortex.traversal.traversal_control_plane import (
    VECTOR_OCTS_CONTROL_PLANE_SHOW_EXPLORATION_ENV,
    build_octs_traversal_control_plane_v1,
    verify_gp05_cp01_traversal_control_plane_rbac_static,
    verify_octs_traversal_control_plane_v1_shape,
)
from vector.domains.cortex.traversal.walk_api_contract import build_stub_completed_walk_payload_v1


def _tenant_id(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p524-{uuid.uuid4().hex[:10]}@example.com", full_name="P524")
    tenant = Tenant(
        company_name="P524 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p524-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _seed_completed_walk(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
    request_body: dict[str, Any],
    walk_payload: dict[str, Any],
) -> None:
    OctsWalkApiDurableStore(session).insert_completed_sync(
        tenant_id=tenant_id,
        walk_id=walk_id,
        request_body=request_body,
        walk_payload=walk_payload,
        idempotency_key=None,
    )
    session.flush()


def test_gp05_cp01_static_passes() -> None:
    out = verify_gp05_cp01_traversal_control_plane_rbac_static()
    assert out["id"] == "G-P05-CP-01"
    assert out["passed"] is True, out


def test_build_control_plane_empty_queue(db_session: Session) -> None:
    tid = uuid.uuid4()
    doc = build_octs_traversal_control_plane_v1(db_session, tenant_id=tid, include_exploration=True)
    assert verify_octs_traversal_control_plane_v1_shape(doc) == []
    assert doc["traversal_queue"] == []
    assert doc["abort_classes"] == {}
    assert doc["budget_histogram"] == {}


def test_fs_cp02_exploration_hidden_by_default(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(VECTOR_OCTS_CONTROL_PLANE_SHOW_EXPLORATION_ENV, raising=False)
    tid = _tenant_id(db_session)
    body = {
        "temporal_anchor": {
            "tenant_id": str(tid),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "bb" * 32,
            "snapshot_unix_ns": {"unix_ns": 42},
            "graph_as_of_unix_ns": {"unix_ns": 42},
        },
        "walk_policy": {
            "max_hops": 4,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": True,
    }
    walk_id = uuid.uuid4()
    payload = build_stub_completed_walk_payload_v1(body, tenant_id=tid)
    _seed_completed_walk(
        db_session,
        tenant_id=tid,
        walk_id=walk_id,
        request_body=dict(body),
        walk_payload=payload,
    )
    hidden = build_octs_traversal_control_plane_v1(db_session, tenant_id=tid, include_exploration=False)
    assert hidden["traversal_queue"] == []
    assert hidden["abort_classes"] == {}

    shown = build_octs_traversal_control_plane_v1(db_session, tenant_id=tid, include_exploration=True)
    assert len(shown["traversal_queue"]) == 1
    assert shown["traversal_queue"][0]["walk_id"] == str(walk_id)
    assert shown["abort_classes"].get("budget_exhausted") == 1


def test_abort_classes_from_completed_stub(db_session: Session) -> None:
    tid = _tenant_id(db_session)
    body = {
        "temporal_anchor": {
            "tenant_id": str(tid),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "cc" * 32,
            "snapshot_unix_ns": {"unix_ns": 7},
            "graph_as_of_unix_ns": {"unix_ns": 7},
        },
        "walk_policy": {
            "max_hops": 8,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    walk_id = uuid.uuid4()
    payload = build_stub_completed_walk_payload_v1(body, tenant_id=tid)
    _seed_completed_walk(
        db_session,
        tenant_id=tid,
        walk_id=walk_id,
        request_body=dict(body),
        walk_payload=payload,
    )
    doc = build_octs_traversal_control_plane_v1(db_session, tenant_id=tid, include_exploration=True)
    assert doc["abort_classes"].get("budget_exhausted") == 1
    assert doc["budget_histogram"].get("8") == 1
    assert doc["t_as_of_unix_ns"] == 7
