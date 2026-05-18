"""Phase 08 Step 30 — admin synthesis certification + program closure HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p830-{uuid.uuid4().hex[:10]}@example.com", full_name="P830 User")
    tenant = Tenant(
        company_name="P830 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p830-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_synthesis_certification_pack_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/certification-pack",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["closure_passed"] is True
    assert body["synthesis_cert_pack_format"] == "SYNTHESIS-CERT-PACK-1"
    assert body["whole_file_sha256"] is not None


def test_admin_synthesis_program_closure_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/program-closure",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["program_closure_passed"] is True
    assert body["freeze_bundle_id"] == "FF-P08-5"
    assert all(c["passed"] for c in body["completion_criteria"] if c["criterion_id"].startswith("C0"))


def test_admin_synthesis_certification_archive_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tid}/cortex/synthesis/certification-pack/archive",
        auth=("admin", "integration-admin-password"),
    )
    assert post.status_code == 200
    archive_id = post.json()["archive_id"]
    assert archive_id is not None

    listing = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/certification-pack/archives",
        auth=("admin", "integration-admin-password"),
    )
    assert listing.status_code == 200
    assert len(listing.json()["archives"]) >= 1

    detail = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/certification-pack/archives/{archive_id}",
        auth=("admin", "integration-admin-password"),
    )
    assert detail.status_code == 200
    assert detail.json()["archive"]["passed"] is True
