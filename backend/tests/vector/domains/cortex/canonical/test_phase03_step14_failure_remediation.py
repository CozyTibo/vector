"""Phase 03 Step 14 — canonical failure registry + remediation validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.failure_remediation_runtime import (
    FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
    sync_canonical_failure_cases,
    validate_canonical_remediation,
)
from vector.domains.cortex.canonical.ontology import ONTOLOGY_SCHEMA_VERSION, build_phase03_step01_ontology_public_document
from vector.domains.cortex.canonical.replay_runtime import execute_canonical_replay_job
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def test_failure_remediation_runtime_schema_version() -> None:
    assert FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION >= 1


def test_ontology_includes_failure_remediation_pointer() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == 20
    assert ONTOLOGY_SCHEMA_VERSION == 20
    assert doc["failure_remediation_surface_version"] >= 1
    assert "canonical/failures" in doc["canonical_failures_route"]
    assert "remediation/validate" in doc["canonical_remediation_validate_route"]


@pytest.mark.integration
def test_transform_materialize_failure_recorded_and_listed(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p314-{uuid.uuid4().hex[:8]}@example.com", full_name="P314 User")
    tenant = Tenant(
        company_name="P314 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p314-{uuid.uuid4().hex[:10]}",
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
        external_id="msg-f",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"text": "f"},
        payload_hash="hash-f",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-f",
        source_identity_key="slack:slack.message:msg-f",
        source_revision_key="rev-f",
    )
    db_session.add(raw)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/transform/materialize",
        auth=("admin", "integration-admin-password"),
        json={"raw_record_id": int(raw.id), "bundle_id": "unknown.bundle.id"},
    )
    assert r.status_code == 400

    listed = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/failures",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    body = listed.json()
    assert body["failure_remediation_runtime_schema_version"] == FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION
    assert body["active_failure_count"] >= 1
    assert body["active_failure_classes"].get("transform_materialize_error", 0) >= 1
    mat_cases = [c for c in body["cases"] if c["failure_class"] == "transform_materialize_error"]
    assert mat_cases
    sc0 = mat_cases[0]["scope_json"]
    assert sc0.get("connector") == "slack"
    assert sc0.get("resource_type") == "slack.message"
    assert sc0.get("raw_record_id") == int(raw.id)


@pytest.mark.integration
def test_replay_job_syncs_forbidden_divergence_failure_case(db_session: Session) -> None:
    user = User(email=f"p314b-{uuid.uuid4().hex[:8]}@example.com", full_name="P314b User")
    tenant = Tenant(
        company_name="P314b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p314b-{uuid.uuid4().hex[:10]}",
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
        external_id="msg-b",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"channel": "C1", "ts": "1.0"},
        payload_hash="hash-b",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-b",
        source_identity_key="slack:slack.message:msg-b",
        source_revision_key="rev-b",
    )
    db_session.add(raw)
    db_session.flush()
    materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(raw.id),
    )
    db_session.add(
        RawMemoryTrustState(
            tenant_id=tenant.id,
            trust_state="corrupted",
            severity="hard",
            state_reason_codes=["test"],
            gate_results={},
            blocking={},
            continuity_gaps=[],
            verification={},
        )
    )
    db_session.commit()

    job = execute_canonical_replay_job(
        db_session,
        tenant_id=tenant.id,
        pinned_bundle_id=_STUB_BUNDLE,
        job_kind="rebuild",
        raw_record_ids=[int(raw.id)],
        source_bundle_id=None,
        dry_run=True,
    )
    assert job.status == "completed"
    out = sync_canonical_failure_cases(db_session, tenant.id)
    assert out["active_failure_classes"].get("replay_forbidden_divergence", 0) >= 1


@pytest.mark.integration
def test_scoped_rebuild_remediation_blocked_when_trust_bad(db_session: Session) -> None:
    user = User(email=f"p314c-{uuid.uuid4().hex[:8]}@example.com", full_name="P314c User")
    tenant = Tenant(
        company_name="P314c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p314c-{uuid.uuid4().hex[:10]}",
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
        external_id="msg-c",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"channel": "C1", "ts": "2.0"},
        payload_hash="hash-c",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-c",
        source_identity_key="slack:slack.message:msg-c",
        source_revision_key="rev-c",
    )
    db_session.add(raw)
    db_session.flush()
    db_session.add(
        RawMemoryTrustState(
            tenant_id=tenant.id,
            trust_state="replay-diverged",
            severity="hard",
            state_reason_codes=["test"],
            gate_results={},
            blocking={},
            continuity_gaps=[],
            verification={},
        )
    )
    db_session.commit()

    out = validate_canonical_remediation(
        db_session,
        tenant_id=tenant.id,
        remediation_class="scoped_rebuild",
        dry_run=True,
        confirm_execution=False,
        failure_case_gap_id=None,
        payload={"pinned_bundle_id": _STUB_BUNDLE, "raw_record_ids": [int(raw.id)]},
    )
    assert out["validation"]["result_status"] == "blocked"


@pytest.mark.integration
def test_ambiguity_triage_ack_remediation_passes(db_session: Session) -> None:
    user = User(email=f"p314d-{uuid.uuid4().hex[:8]}@example.com", full_name="P314d User")
    tenant = Tenant(
        company_name="P314d Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p314d-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    out = validate_canonical_remediation(
        db_session,
        tenant_id=tenant.id,
        remediation_class="ambiguity_triage_ack",
        dry_run=True,
        confirm_execution=False,
        failure_case_gap_id=None,
        payload={"note": "operator_ack_test", "connector": "slack"},
    )
    assert out["validation"]["result_status"] == "pass"
    assert out["validation"]["remediation_class"] == "ambiguity_triage_ack"
