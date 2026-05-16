"""Phase 06 Step 33 — admin reasoning runtime legality matrix HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.reasoning.reasoning_runtime_legality_matrix import (
    REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p6rlm-{uuid.uuid4().hex[:10]}@example.com", full_name="P6 RLM User")
    tenant = Tenant(
        company_name="P6RLM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p6rlm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_reasoning_runtime_legality_matrix_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/runtime-legality-matrix",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    contract = REASONING_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1
    assert body["reasoning_runtime_legality_matrix_contract"] == contract
    assert body["reasoning_runtime_legality_matrix_runtime_schema_version"] >= 1
    assert len(body["predicates"]) == 5
    assert body["predicates"][0]["predicate_id"] == "R-LEG-01"
    assert len(body["forbidden_deployments"]) == 2
    assert body["waiver_yaml_future_path"]
