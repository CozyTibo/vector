"""Phase 07 Step 28 — admin **RETRIEVAL-CERT-PACK-1** certification snapshot."""

from __future__ import annotations

import base64
import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_certification_pack import (
    verify_retrieval_cert_pack_v1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p728-{uuid.uuid4().hex[:10]}@example.com", full_name="P728 User")
    tenant = Tenant(
        company_name="P728 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p728-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_retrieval_certification_pack_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/certification-pack",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["closure_passed"] is True
    assert body["retrieval_certification_pack_runtime_schema_version"] >= 1
    assert body["retrieval_cert_pack_format"] == "RETRIEVAL-CERT-PACK-1"
    assert body["whole_file_sha256"] is not None
    assert body["pack_byte_length"] is not None
    raw = base64.b64decode(body["pack_gzip_base64"])
    assert verify_retrieval_cert_pack_v1(raw).passed is True
