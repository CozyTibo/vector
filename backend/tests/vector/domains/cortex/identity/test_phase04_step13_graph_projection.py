"""P04-13 — OrgGraphProjectionV1 export, G-P04-10 / G-P04-EXP-01, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.link_ledger import append_authoritative_org_link
from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.identity.projection_export import (
    ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
    ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
    build_org_graph_projection_export_document,
    org_graph_projection_stable_hash_sha256,
    validate_org_graph_projection_v1_shape,
    verify_gp04_10_graph_boundary_export_contract_static,
    verify_gp04_exp01_export_hash_determinism_static,
    verify_org_graph_export_forbidden_leakage,
    verify_org_graph_projection_twice_same_hash,
)


def test_gp04_10_static_passes() -> None:
    st = verify_gp04_10_graph_boundary_export_contract_static()
    assert st["passed"] is True
    assert st["id"] == "G-P04-10"


def test_gp04_exp01_static_passes() -> None:
    st = verify_gp04_exp01_export_hash_determinism_static()
    assert st["passed"] is True


def test_forbidden_token_detection() -> None:
    bad = {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(uuid.uuid4()),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.uuid4()),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp_with_cortex_canonical_transform_token",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [],
    }
    bad["nodes"].sort(key=lambda x: str(x["id"]))
    assert verify_org_graph_export_forbidden_leakage(bad) != []


def test_build_projection_sorted_and_valid(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p413-{uuid.uuid4().hex[:8]}@example.com", full_name="P413")
    tenant = Tenant(
        company_name="P413 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p413-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    a = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "a"},
        metadata_json={},
    )
    b = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"k": "b"},
        metadata_json={},
    )
    db_session.flush()
    append_authoritative_org_link(
        db_session,
        tenant_id=tenant.id,
        link_type="PersonaBelongsToHuman",
        source_entity_id=a.id,
        target_entity_id=b.id,
        evidence_raw_record_ids=[42, 41],
    )
    db_session.commit()

    doc = build_org_graph_projection_export_document(db_session, tenant_id=tenant.id)
    inner = doc["projection"]
    assert validate_org_graph_projection_v1_shape(inner) == []
    assert verify_org_graph_export_forbidden_leakage(inner) == []
    twin = verify_org_graph_projection_twice_same_hash(db_session, tenant_id=tenant.id)
    assert twin["passed"] is True
    h1 = org_graph_projection_stable_hash_sha256(inner)
    h2 = org_graph_projection_stable_hash_sha256(inner)
    assert h1 == h2 == doc["stable_hash_sha256"]


@pytest.mark.integration
def test_admin_graph_projection_endpoint(client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p413h-{uuid.uuid4().hex[:8]}@example.com", full_name="P413h")
    tenant = Tenant(
        company_name="P413h Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p413h-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="team",
        identity_material={"t": 1},
        metadata_json={},
    )
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/graph-projection",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["org_graph_projection_schema_version"] == ORG_GRAPH_PROJECTION_SCHEMA_VERSION
    assert body["tenant_id"] == str(tenant.id)
    assert len(body["stable_hash_sha256"]) == 64
    assert body["projection"]["nodes"]


def test_verification_includes_graph_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p413v-{uuid.uuid4().hex[:8]}@example.com", full_name="P413v")
    tenant = Tenant(
        company_name="P413v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p413v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-10" in ids
    assert "G-P04-EXP-01" in ids
    g10 = next(g for g in out["gates"] if g["id"] == "G-P04-10")
    gexp = next(g for g in out["gates"] if g["id"] == "G-P04-EXP-01")
    assert g10["passed"] is True
    assert gexp["passed"] is True
