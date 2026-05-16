"""Phase 06 Step 35 — admin **TCRE-CERT-PACK-1** certification snapshot."""

from __future__ import annotations

import base64
import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.reasoning.reasoning_certification_pack import (
    verify_tcre_cert_pack_v1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p635-{uuid.uuid4().hex[:10]}@example.com", full_name="P635 User")
    tenant = Tenant(
        company_name="P635 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p635-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_reasoning_certification_pack_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/certification-pack",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["closure_passed"] is True
    assert body["reasoning_certification_pack_runtime_schema_version"] >= 1
    assert body["tcre_cert_pack_format"] == "TCRE-CERT-PACK-1"
    assert body["whole_file_sha256"] is not None
    assert body["pack_byte_length"] is not None
    raw = base64.b64decode(body["pack_gzip_base64"])
    assert verify_tcre_cert_pack_v1(raw).passed is True
