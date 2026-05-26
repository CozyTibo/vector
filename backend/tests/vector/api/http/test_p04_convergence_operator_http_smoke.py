"""P04 convergence — HTTP smoke for operator surfaces (read-only paths)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.identity.control_plane import IDENTITY_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION


@pytest.mark.integration
def test_p04_operator_http_smoke_core_surfaces(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p04cv-{uuid.uuid4().hex[:8]}@example.com", full_name="P04CV")
    tenant = Tenant(
        company_name="P04CV Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p04cv-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    tid = tenant.id
    auth = ("admin", "integration-admin-password")

    r0 = client.get(f"/admin/tenants/{tid}/cortex/identity/control-plane", auth=auth)
    assert r0.status_code == 200
    cp = r0.json()
    assert cp["identity_control_plane_runtime_schema_version"] == IDENTITY_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
    assert "operational_replay_canonical_guide" in cp["continuity_substrate"]
    assert "sparse_substrate_honesty" in cp["continuity_substrate"]

    r1 = client.get(f"/admin/tenants/{tid}/cortex/identity/link-candidates", auth=auth)
    assert r1.status_code == 200

    r2 = client.get(f"/admin/tenants/{tid}/cortex/identity/replay-jobs", auth=auth)
    assert r2.status_code == 410

    r2b = client.get(f"/admin/tenants/{tid}/cortex/substrate/truth", auth=auth)
    assert r2b.status_code == 200
    assert r2b.json()["surface_kind"] == "substrate_truth_v1"

    r3 = client.get(f"/admin/tenants/{tid}/cortex/identity/org-ambiguities", auth=auth)
    assert r3.status_code == 200

    r4 = client.get(f"/admin/tenants/{tid}/cortex/identity/graph-projection", auth=auth)
    assert r4.status_code == 200

    r5 = client.get(
        f"/admin/tenants/{tid}/cortex/identity/debug-anchor-evidence",
        auth=auth,
        params={"anchor_scan_limit": 500, "sample_limit": 2, "fixture_survival_sample_limit": 2},
    )
    assert r5.status_code == 200
    ev = r5.json()
    assert "substrate_sparse_honesty" in ev
    assert "candidate_pair_evidence_accumulation" in ev
    sh = ev["substrate_sparse_honesty"]
    assert isinstance(sh.get("candidate_generation_overflow_accounting"), dict)
