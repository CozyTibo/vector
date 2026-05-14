"""P05-23 — tenant verification ``org_graph_traversal`` slice + **G-P05-TVER-01**."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.verification import run_org_identity_verification
from vector.domains.cortex.traversal.tenant_verification_slice import (
    VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV,
    build_org_graph_traversal_verification_slice_v1,
    compute_octs_slice_hash_v1,
    octs_golden_vectors_v1_root_for_tenant_slice,
    validate_org_graph_traversal_verification_slice_v1,
    verify_gp05_tver01_org_graph_traversal_slice_golden_static,
)


def test_gp05_tver01_static_passes() -> None:
    out = verify_gp05_tver01_org_graph_traversal_slice_golden_static()
    assert out["id"] == "G-P05-TVER-01"
    assert out["passed"] is True, out


def test_golden_slice_matches_schema_and_expected_hash() -> None:
    path = octs_golden_vectors_v1_root_for_tenant_slice() / "tenant_verification" / "org_graph_traversal_slice_good_v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert validate_org_graph_traversal_verification_slice_v1(doc) == []
    h = compute_octs_slice_hash_v1(doc)
    assert len(h) == 64
    assert h == compute_octs_slice_hash_v1(doc)


def test_org_identity_verification_slice_absent_without_env(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p523-{uuid.uuid4().hex[:8]}@example.com", full_name="P523")
    tenant = Tenant(
        company_name="P523 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p523-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    monkeypatch.delenv(VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV, raising=False)
    org = run_org_identity_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=5, persist=False)
    assert "org_graph_traversal" not in org["evidence"]
    assert "octs_slice_hash" not in org["evidence"]


def test_org_identity_verification_slice_present_with_env(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    monkeypatch.setenv(VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV, "1")

    user = User(email=f"p523b-{uuid.uuid4().hex[:8]}@example.com", full_name="P523b")
    tenant = Tenant(
        company_name="P523b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p523b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    org = run_org_identity_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=5, persist=False)
    sl = org["evidence"].get("org_graph_traversal")
    assert isinstance(sl, dict)
    assert validate_org_graph_traversal_verification_slice_v1(sl) == []
    assert sl["tenant_id"] == str(tenant.id)
    assert sl["verification_run_id"] is None
    assert sl["walk_queue_depth"] == 0
    assert sl["last_index_epoch"] == 0
    assert sl["index_lag_epochs"] == 0
    assert org["evidence"]["octs_slice_hash"] == compute_octs_slice_hash_v1(sl)


def test_build_slice_matches_golden_fixture_fields(db_session: Session) -> None:
    path = octs_golden_vectors_v1_root_for_tenant_slice() / "tenant_verification" / "org_graph_traversal_slice_good_v1.json"
    golden = json.loads(path.read_text(encoding="utf-8"))
    tid = uuid.UUID(str(golden["tenant_id"]))
    got = build_org_graph_traversal_verification_slice_v1(
        db_session,
        tenant_id=tid,
        verification_run_id=str(golden["verification_run_id"]),
    )
    assert got == golden


def test_org_identity_verification_persist_includes_slice_in_row(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(VECTOR_OCTS_TENANT_VERIFICATION_SLICE_ENV, "1")
    from vector.infrastructure.db.models.cortex_org_verification_run import CortexOrgVerificationRun
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p523c-{uuid.uuid4().hex[:8]}@example.com", full_name="P523c")
    tenant = Tenant(
        company_name="P523c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p523c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    org = run_org_identity_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=5, persist=True)
    rid = org["persisted_run_id"]
    assert rid is not None
    sl = org["evidence"]["org_graph_traversal"]
    assert sl["verification_run_id"] == str(rid)

    row = db_session.get(CortexOrgVerificationRun, rid)
    assert row is not None
    assert row.evidence_json["org_graph_traversal"]["verification_run_id"] == str(rid)
    assert row.evidence_json["octs_slice_hash"] == compute_octs_slice_hash_v1(sl)
