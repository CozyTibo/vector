"""Phase 08 Step 32 — admin synthesis publication HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_replay_equivalence import GP08_REPLAY_02_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8adm32-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm 32")
    tenant = Tenant(
        company_name="P8ADM32",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8adm32-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_publication_law_catalog(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/publication-law",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert GP08_REPLAY_02_GATE_ID_V1 in body["gate_ids"]


def test_admin_publication_status_and_publish_empty(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        publish_retrieval_index_epoch_v1,
    )

    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    epoch = f"ep-adm-{uuid.uuid4().hex[:6]}"
    publish_retrieval_index_epoch_v1(db_session, tenant_id=tenant_id, index_epoch=epoch)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/publication",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == GP08_REPLAY_02_GATE_ID_V1

    r2 = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/publish",
        json={"published_index_epoch": epoch, "allow_empty_scope": True},
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json().get("synthesis_publication_epoch")

    r3 = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r3.status_code == 200
    assert "publication_barrier" in r3.json()
