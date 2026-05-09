"""Phase 03 Step 18 — canonical closure certification pack + archive."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_certification_pack import (
    CERTIFICATION_PACK_SCHEMA_VERSION,
)
from vector.domains.cortex.canonical.ontology import ONTOLOGY_SCHEMA_VERSION, build_phase03_step01_ontology_public_document
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def test_certification_pack_schema_version() -> None:
    assert CERTIFICATION_PACK_SCHEMA_VERSION >= 1


def test_ontology_includes_certification_pack_pointer() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == 20
    assert ONTOLOGY_SCHEMA_VERSION == 20
    assert "certification-pack" in doc["canonical_certification_pack_route"]
    assert "certification-pack/archive" in doc["canonical_certification_pack_archive_route"]


@pytest.mark.integration
def test_certification_pack_build_and_archive_http(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p318-{uuid.uuid4().hex[:8]}@example.com", full_name="P318 User")
    tenant = Tenant(
        company_name="P318 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p318-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        resource_type="slack.message",
        external_id="msg-v",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"channel": "C9", "ts": "9.0"},
        payload_hash="hash-v",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-v",
        source_identity_key="slack:slack.message:msg-v",
        source_revision_key="rev-v",
    )
    db_session.add(raw)
    db_session.flush()
    materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(raw.id),
    )
    db_session.commit()

    rv = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/verification/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": True, "materialization_sample_limit": 20},
    )
    assert rv.status_code == 200
    assert rv.json()["passed"] is True

    rs = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/stabilization-proof/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": True},
    )
    assert rs.status_code == 200
    assert rs.json()["hard_fail_passed"] is True

    snap = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/certification-pack?materialization_sample_limit=20",
        auth=("admin", "integration-admin-password"),
    )
    assert snap.status_code == 200
    pack = snap.json()
    assert pack["certification_pack_schema_version"] == CERTIFICATION_PACK_SCHEMA_VERSION
    assert pack["certification_pack_contract"]["passed"] is True
    ids = {g["id"] for g in pack["closure_gate_matrix"]}
    for gid in (
        "G-P03-14",
        "G-P03-15",
        "G-P03-16",
        "G-P03-17",
        "G-P03-18",
        "G-P03-19",
        "G-P03-20",
        "G-P03-21",
    ):
        assert gid in ids

    arch = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/certification-pack/archive",
        auth=("admin", "integration-admin-password"),
        json={"materialization_sample_limit": 20},
    )
    assert arch.status_code == 200
    body = arch.json()
    assert body["persisted"] is True
    assert body["passed"] is True
    assert body["archive_id"] is not None

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/certification-pack/archives?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    assert lst.json()["archives"]

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/certification-pack/archives/{body['archive_id']}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["pack"]["tenant_id"] == str(tenant.id)
