"""Phase 03 Step 1 — admin canonical ontology read surface."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.ontology import ONTOLOGY_SCHEMA_VERSION

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p3-{uuid.uuid4().hex[:10]}@example.com", full_name="P3 User")
    tenant = Tenant(
        company_name="P3Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p3-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, user.id


def test_admin_cortex_canonical_ontology_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/ontology",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ontology_schema_version"] == ONTOLOGY_SCHEMA_VERSION
    assert body["implementation_step"] == 18
    assert body["completed_implementation_steps"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    assert body["tenant_id"] == str(tid)
    assert len(body["object_kinds"]) >= 10
    assert len(body["structural_arcs"]) >= 1
    assert body["taxonomy_families"]
    assert body["kind_taxonomy"]
    assert body["taxonomy_hard_rules"]
    assert body["logical_keys_by_kind"]
    assert body["evidence_grades"]
    assert body["mapping_table_row_shape"]
    assert body["mapping_registry_surface_version"] >= 1


def test_admin_cortex_canonical_mapping_registry_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/mapping-registry",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_schema_version"] >= 1
    assert body["implementation_step"] == 5
    assert isinstance(body["bundles"], list)


def test_admin_cortex_canonical_oracle_manifest_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/oracle-manifest",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["oracle_manifest_schema_version"] >= 1
    assert body["implementation_step"] == 3
    assert body["vectors"]
    assert body["vectors"][0]["fixture_id"]


def test_admin_cortex_canonical_control_plane_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["canonical_control_plane_schema_version"] >= 1
    assert "health_overview" in body
    assert "logical_information_architecture" in body
    assert isinstance(body["actions"], list)
    assert len(body["actions"]) >= 5


def test_admin_cortex_canonical_stabilization_proof_snapshot_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/stabilization-proof",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["stabilization_proof_schema_version"] >= 1
    assert "substrate_scale" in body
    assert body["persisted_run_id"] is None


def test_admin_cortex_canonical_stabilization_proof_run_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/stabilization-proof/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["persisted_run_id"] is None
    assert isinstance(body["proof_checklist"], list)

    listed = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/stabilization-proof/runs?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    assert "runs" in listed.json()


def test_admin_cortex_canonical_materialize_backlog_dry_run_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    reg = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/mapping-registry",
        auth=("admin", "integration-admin-password"),
    )
    assert reg.status_code == 200
    bundles = reg.json()["bundles"]
    assert bundles
    bundle_id = bundles[0]["bundle_id"]

    r = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/transform/materialize-backlog",
        auth=("admin", "integration-admin-password"),
        json={"bundle_id": bundle_id, "batch_limit": 50, "dry_run": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dry_run"] is True
    assert body["attempted"] >= 0
    assert isinstance(body["stub_resource_pairs_selected"], list)
    assert body["stub_resource_pairs_selected"]


def test_admin_cortex_canonical_materialize_backlog_async_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    reg = client.get(
        f"/admin/tenants/{tid}/cortex/canonical/mapping-registry",
        auth=("admin", "integration-admin-password"),
    )
    assert reg.status_code == 200
    bundles = reg.json()["bundles"]
    assert bundles

    with patch(
        "app.tasks.cortex_canonical_materialize_backlog.drain_stub_materialize_backlog_task.delay",
    ) as mock_delay:
        mock_delay.return_value = MagicMock(id="celery-task-integration-test")
        r = client.post(
            f"/admin/tenants/{tid}/cortex/canonical/transform/materialize-backlog-async",
            auth=("admin", "integration-admin-password"),
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["enqueued"] is True
        assert body["celery_task_id"] == "celery-task-integration-test"
        assert body["tenant_id"] == str(tid)
        bundle_used = body["bundle_id_used"]
        assert bundle_used
        mock_delay.assert_called_once()
        args = mock_delay.call_args.args
        assert len(args) == 5
        assert args[0] == str(tid)
        assert args[1] == bundle_used
        assert args[2] is None
        assert args[3] is None
        assert isinstance(args[4], int) and args[4] >= 1
