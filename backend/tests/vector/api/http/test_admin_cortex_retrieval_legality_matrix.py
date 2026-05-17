"""Phase 07 Step 7 — admin retrieval legality matrix HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1,
)
from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
    GP07_RLM01_GATE_ID_V1,
    RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7alm-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 ALM User")
    tenant = Tenant(
        company_name="P7ALM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7alm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_retrieval_legality_matrix_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/legality",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["retrieval_legality_matrix_contract"] == RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1
    assert len(body["predicates"]) == 7
    assert body["predicates"][0]["predicate_id"] == "R-LEG-01"
    assert len(body["forbidden_deployments"]) == 5
    assert "retrieval_queries_by_legality" in body


def test_admin_cortex_retrieval_runtime_legality_matrix_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/runtime-legality-matrix",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["retrieval_runtime_legality_matrix_contract"] == RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    assert body["gate_id"] == GP07_RLM01_GATE_ID_V1
    assert len(body["predicates"]) == 7
    assert "production_gates" in body
    assert "forbidden_deployment_detector" in body
