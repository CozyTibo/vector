"""Phase 03 Step 15 — canonical verification engine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import (
    CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
    _gate_gp03_23_execution_check_lifecycle,
    run_canonical_verification,
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


def test_verification_engine_schema_version() -> None:
    assert CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION >= 1


def test_ontology_includes_verification_engine_pointer() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == 20
    assert ONTOLOGY_SCHEMA_VERSION == 20
    assert doc["verification_engine_surface_version"] >= 1
    assert "verification/run" in doc["canonical_verification_run_route"]
    assert "G-P03-01" in doc["verification_engine_gate_ids"]
    assert "G-P03-16" in doc["verification_engine_gate_ids"]
    assert "G-P03-17" in doc["verification_engine_gate_ids"]
    assert "G-P03-21" in doc["verification_engine_gate_ids"]
    assert "G-P03-23" in doc["verification_engine_gate_ids"]
    assert "G-P03-24" in doc["verification_engine_gate_ids"]


@pytest.mark.integration
def test_run_canonical_verification_persists_run(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p315-{uuid.uuid4().hex[:8]}@example.com", full_name="P315 User")
    tenant = Tenant(
        company_name="P315 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p315-{uuid.uuid4().hex[:10]}",
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

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/verification/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": True, "materialization_sample_limit": 20},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_verification_engine_schema_version"] == CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION
    assert body["passed"] is True
    assert body["persisted_run_id"] is not None
    gate_ids = {g["id"] for g in body["gates"]}
    assert "G-P03-01" in gate_ids
    assert "G-P03-10" in gate_ids
    assert "G-P03-16" in gate_ids
    assert "G-P03-17" in gate_ids
    assert "G-P03-21" in gate_ids
    assert "G-P03-23" in gate_ids
    assert "G-P03-24" in gate_ids

    listed = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/verification/runs?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    lst = listed.json()
    assert lst["runs"]
    assert lst["runs"][0]["id"] == body["persisted_run_id"]


@pytest.mark.integration
def test_run_canonical_verification_direct_db(db_session: Session) -> None:
    user = User(email=f"p315b-{uuid.uuid4().hex[:8]}@example.com", full_name="P315b User")
    tenant = Tenant(
        company_name="P315b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p315b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(
        db_session,
        tenant_id=tenant.id,
        materialization_sample_limit=5,
        persist=False,
    )
    assert out["passed"] in (True, False)
    assert len(out["gates"]) >= 11
    assert out["persisted_run_id"] is None


def test_execution_check_gate_accepts_monotonic_lifecycle() -> None:
    mats = [
        SimpleNamespace(
            id=uuid.uuid4(),
            logical_key_hash="lk-1",
            emitted_snapshot_json={"status": "queued"},
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            logical_key_hash="lk-1",
            emitted_snapshot_json={"status": "in_progress"},
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            logical_key_hash="lk-1",
            emitted_snapshot_json={
                "status": "completed",
                "conclusion": "success",
                "started_at": "2026-05-09T08:00:00Z",
                "completed_at": "2026-05-09T08:00:03Z",
            },
        ),
    ]

    class _Res:
        def __init__(self, rows: list[object]) -> None:
            self._rows = rows

        def all(self) -> list[object]:
            return self._rows

    class _Session:
        def scalars(self, _stmt: object) -> _Res:
            return _Res(mats)

    gate = _gate_gp03_23_execution_check_lifecycle(_Session(), tenant_id=uuid.uuid4())
    assert gate["id"] == "G-P03-23"
    assert gate["passed"] is True


def test_execution_check_gate_rejects_regressions_and_inconsistent_status() -> None:
    mats = [
        SimpleNamespace(
            id=uuid.uuid4(),
            logical_key_hash="lk-2",
            emitted_snapshot_json={"status": "completed", "conclusion": "success"},
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            logical_key_hash="lk-2",
            emitted_snapshot_json={"status": "queued", "conclusion": "success"},
        ),
    ]

    class _Res:
        def __init__(self, rows: list[object]) -> None:
            self._rows = rows

        def all(self) -> list[object]:
            return self._rows

    class _Session:
        def scalars(self, _stmt: object) -> _Res:
            return _Res(mats)

    gate = _gate_gp03_23_execution_check_lifecycle(_Session(), tenant_id=uuid.uuid4())
    assert gate["passed"] is False
    assert gate["detail"]["issue_count"] >= 2
