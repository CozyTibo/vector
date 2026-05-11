"""Phase 03 Step 13 — canonical query runtime + anti-goals + ontology surface."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_query_runtime import (
    CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION,
    CanonicalQueryError,
    enforce_canonical_query_anti_goals,
    execute_canonical_query,
)
from vector.domains.cortex.canonical.ontology import (
    ONTOLOGY_SCHEMA_VERSION,
    build_phase03_step01_ontology_public_document,
)
from vector.domains.cortex.canonical.transform_runtime import materialize_raw_record
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def test_canonical_query_runtime_schema_version() -> None:
    assert CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION >= 1


def test_anti_goals_block_semantic_intent() -> None:
    with pytest.raises(CanonicalQueryError, match="Unsupported"):
        enforce_canonical_query_anti_goals(intent="semantic_search", query_text=None)


def test_anti_goals_block_query_text() -> None:
    with pytest.raises(CanonicalQueryError, match="Semantic search"):
        enforce_canonical_query_anti_goals(
            intent="evidence_retrieval",
            query_text="semantic search over canonical issues",
        )


def test_ontology_includes_canonical_query_pointer() -> None:
    doc = build_phase03_step01_ontology_public_document()
    assert doc["ontology_schema_version"] == ONTOLOGY_SCHEMA_VERSION
    assert doc["canonical_query_route"]
    assert "point_lookup_materialization" in doc["canonical_query_classes"]
    assert doc.get("failure_remediation_surface_version", 0) >= 1
    assert doc.get("verification_engine_surface_version", 0) >= 1


@pytest.mark.integration
def test_execute_point_lookup_and_evidence_backtrace(db_session: Session) -> None:
    user = User(email=f"p313-{uuid.uuid4().hex[:8]}@example.com", full_name="P313 User")
    tenant = Tenant(
        company_name="P313 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p313-{uuid.uuid4().hex[:10]}",
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
        external_id="msg-q",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"text": "q"},
        payload_hash="hash-q",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-q",
        source_identity_key="slack:slack.message:msg-q",
        source_revision_key="rev-q",
    )
    db_session.add(raw)
    db_session.flush()
    mat = materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(raw.id),
        commit=False,
    )

    out = execute_canonical_query(
        db_session,
        tenant_id=tenant.id,
        query_class="point_lookup_materialization",
        intent="point_lookup",
        params={"materialization_id": str(mat.id)},
        limit=10,
    )
    assert out["result_kind"] == "materialization"
    assert out["payload"]["found"] is True
    assert out["payload"]["materialization"]["id"] == str(mat.id)

    out2 = execute_canonical_query(
        db_session,
        tenant_id=tenant.id,
        query_class="evidence_backtrace",
        intent="evidence_backtrace",
        params={"raw_record_id": int(raw.id)},
        limit=10,
    )
    assert out2["result_kind"] == "provenance_records"
    assert len(out2["payload"]["records"]) >= 1


@pytest.mark.integration
def test_admin_canonical_query_route(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p313a-{uuid.uuid4().hex[:8]}@example.com", full_name="P313a User")
    tenant = Tenant(
        company_name="P313a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p313a-{uuid.uuid4().hex[:10]}",
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
        external_id="msg-a",
        api_endpoint="https://slack.com/api/test",
        query_params={},
        payload_body={"text": "a"},
        payload_hash="hash-a",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-a",
        source_identity_key="slack:slack.message:msg-a",
        source_revision_key="rev-a",
    )
    db_session.add(raw)
    db_session.flush()
    mat = materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(raw.id),
        commit=False,
    )
    db_session.flush()

    tid = tenant.id
    r = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/query",
        auth=("admin", "integration-admin-password"),
        json={
            "query_class": "replay_debug_snapshot",
            "intent": "replay_debug",
            "params": {},
            "limit": 5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["canonical_query_runtime_schema_version"] == CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION
    assert body["query_class"] == "replay_debug_snapshot"

    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/query",
        auth=("admin", "integration-admin-password"),
        json={
            "query_class": "point_lookup_materialization",
            "intent": "point_lookup",
            "params": {"materialization_id": str(mat.id)},
        },
    )
    assert r2.status_code == 200
    assert r2.json()["payload"]["found"] is True

    r3 = client.post(
        f"/admin/tenants/{tid}/cortex/canonical/query",
        auth=("admin", "integration-admin-password"),
        json={
            "query_class": "graph_neighborhood",
            "intent": "neighborhood_retrieval",
            "params": {"center_materialization_id": str(mat.id), "max_results": 5},
        },
    )
    assert r3.status_code == 200
    assert r3.json()["payload"]["found"] is True
