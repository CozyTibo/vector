"""Phase 01 Step 6 — admin Cortex ingestion visibility, verification, and gated actions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"c6-{uuid.uuid4().hex[:10]}@cortex6.example", full_name="Cortex Six")
    tenant = Tenant(
        company_name="Cortex Six Co",
        primary_email=user.email,
        email_domain="cortex6.example",
        slug=f"c6-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, user.id


def _add_active_connection(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    provider: str,
) -> uuid.UUID:
    conn = TenantConnection(
        tenant_id=tenant_id,
        provider=provider,
        status="active",
        connected_by_user_id=user_id,
    )
    db_session.add(conn)
    db_session.flush()
    return conn.id


def _seed_raw_rows_for_stats_filters(db_session: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    connection = TenantConnection(
        tenant_id=tenant_id,
        provider="github",
        status="active",
        connected_by_user_id=user_id,
    )
    db_session.add(connection)
    db_session.flush()

    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connection_id=connection.id,
        connector="github",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        stats={"records_written": 3},
    )
    db_session.add(run)
    db_session.flush()

    base_t = datetime.now(UTC)
    rows = [
        RawIngestionRecord(
            tenant_id=tenant_id,
            connection_id=connection.id,
            connector="github",
            resource_type="github.pull_request",
            external_id="pr-1",
            api_endpoint="https://api.github.com/repos/acme/repo/pulls",
            query_params={"page": 1},
            payload_body={"title": "Add step 13 proof view"},
            payload_hash="h-pr-1",
            http_status=200,
            fetched_at=base_t - timedelta(hours=2),
            run_id=run.id,
            source_trigger="manual_admin",
            idempotency_key="idem-pr-1",
            source_identity_key="github:github.pull_request:pr-1",
            source_revision_key="provider:1",
        ),
        RawIngestionRecord(
            tenant_id=tenant_id,
            connection_id=connection.id,
            connector="github",
            resource_type="github.scope_ping",
            external_id="scope",
            api_endpoint="internal://github/scope_ping",
            query_params={},
            payload_body={"ping": True},
            payload_hash="h-ping",
            http_status=200,
            fetched_at=base_t - timedelta(hours=1),
            run_id=run.id,
            source_trigger="manual_admin",
            idempotency_key="idem-ping",
            source_identity_key="github:github.scope_ping:scope",
            source_revision_key="provider:1",
        ),
        RawIngestionRecord(
            tenant_id=tenant_id,
            connection_id=connection.id,
            connector="github",
            resource_type="github.pull_request",
            external_id="pr-2",
            api_endpoint="https://api.github.com/repos/acme/repo/pulls",
            query_params={"page": 2},
            payload_body={"title": "Payload search token alpha-needle"},
            payload_hash="h-pr-2",
            http_status=200,
            fetched_at=base_t,
            run_id=run.id,
            source_trigger="manual_admin",
            idempotency_key="idem-pr-2",
            source_identity_key="github:github.pull_request:pr-2",
            source_revision_key="provider:2",
        ),
    ]
    db_session.add_all(rows)
    db_session.flush()


def test_admin_cortex_ingestion_overview_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion",
            auth=("admin", "integration-admin-password"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == str(tid)
        assert data["company_name"] == "Cortex Six Co"
        assert "global_scheduler" in data
        assert len(data["connectors"]) == 5
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_connector_raw_records_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/connectors/github/raw-records",
            auth=("admin", "integration-admin-password"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == str(tid)
        assert data["connector"] == "github"
        assert data["items"] == []
        assert data["total_count"] == 0
        assert data["truncated"] is False
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_raw_stats_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/raw-stats",
            auth=("admin", "integration-admin-password"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == str(tid)
        assert "resources" in data
        assert isinstance(data["resources"], list)
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_raw_stats_filters_hide_health_by_default(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, uid = _tenant_with_owner(db_session)
        _seed_raw_rows_for_stats_filters(db_session, tid, uid)
        db_session.commit()

        default_r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/raw-stats",
            auth=("admin", "integration-admin-password"),
        )
        assert default_r.status_code == 200
        resources = default_r.json()["resources"]
        assert all(r["resource_type"] != "github.scope_ping" for r in resources)

        incl_r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/raw-stats?include_health_rows=true",
            auth=("admin", "integration-admin-password"),
        )
        assert incl_r.status_code == 200
        resources_incl = incl_r.json()["resources"]
        assert any(r["resource_type"] == "github.scope_ping" for r in resources_incl)
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_connector_raw_records_step13_filters(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, uid = _tenant_with_owner(db_session)
        _seed_raw_rows_for_stats_filters(db_session, tid, uid)
        db_session.commit()

        # Default hides health rows.
        r_default = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/connectors/github/raw-records",
            auth=("admin", "integration-admin-password"),
        )
        assert r_default.status_code == 200
        items_default = r_default.json()["items"]
        assert len(items_default) == 2
        assert all(it["resource_type"] != "github.scope_ping" for it in items_default)

        # Search drilldown matches payload text.
        r_search = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/connectors/github/raw-records?search_query=alpha-needle",
            auth=("admin", "integration-admin-password"),
        )
        assert r_search.status_code == 200
        items_search = r_search.json()["items"]
        assert len(items_search) == 1
        assert items_search[0]["external_id"] == "pr-2"

        # Include health rows and filter by resource_type.
        r_health = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/connectors/github/raw-records?include_health_rows=true&resource_type=github.scope_ping",
            auth=("admin", "integration-admin-password"),
        )
        assert r_health.status_code == 200
        items_health = r_health.json()["items"]
        assert len(items_health) == 1
        assert items_health[0]["resource_type"] == "github.scope_ping"
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_exhaust_coverage_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/exhaust-coverage",
            auth=("admin", "integration-admin-password"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == str(tid)
        assert "connector_exhaust_matrix_doc" in data
        assert len(data["connectors"]) == 5
        gh = next(c for c in data["connectors"] if c["connector"] == "github")
        assert gh["maturity_level"] >= 1
        assert gh["missing_resource_types"]
        assert any(row["resource_type"] == "commits" for row in gh["resources"])
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_trigger_sync_bad_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.post(
            f"/admin/tenants/{tid}/cortex/ingestion/actions/trigger-sync",
            auth=("admin", "integration-admin-password"),
            json={"connector": "github", "confirmation": "wrong"},
        )
        assert r.status_code == 400
    finally:
        get_settings.cache_clear()


def test_admin_cortex_scheduler_pause_requires_redis(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()
    try:
        r = client.post(
            "/admin/cortex/ingestion/scheduler-pause",
            auth=("admin", "integration-admin-password"),
            json={"paused": True, "confirmation": "PAUSE ALL SCHEDULED CORTEX INGESTION"},
        )
        assert r.status_code == 503
    finally:
        get_settings.cache_clear()


def test_admin_cortex_ingestion_verification_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, _ = _tenant_with_owner(db_session)
        db_session.commit()

        r = client.get(
            f"/admin/tenants/{tid}/cortex/ingestion/verification",
            auth=("admin", "integration-admin-password"),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["tenant_id"] == str(tid)
        assert "passed" in body
        assert body["runs_examined"] == 0
    finally:
        get_settings.cache_clear()


def test_admin_trigger_sync_requires_connection_id_when_multiple_active_connections(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, uid = _tenant_with_owner(db_session)
        _add_active_connection(db_session, tenant_id=tid, user_id=uid, provider="github")
        _add_active_connection(db_session, tenant_id=tid, user_id=uid, provider="github")
        db_session.commit()

        r = client.post(
            f"/admin/tenants/{tid}/cortex/ingestion/actions/trigger-sync",
            auth=("admin", "integration-admin-password"),
            json={
                "connector": "github",
                "confirmation": "RUN MANUAL CORTEX INGESTION SYNC",
            },
        )
        assert r.status_code == 409
        assert "Multiple active github connections" in r.text
    finally:
        get_settings.cache_clear()


def test_admin_trigger_sync_accepts_explicit_connection_scope(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    get_settings.cache_clear()
    try:
        tid, uid = _tenant_with_owner(db_session)
        conn_id = _add_active_connection(db_session, tenant_id=tid, user_id=uid, provider="github")
        db_session.commit()

        import app.tasks.cortex_ingestion_sync as sync_tasks

        called: list[tuple[object, ...]] = []
        monkeypatch.setattr(sync_tasks.run_cortex_connector_sync_task, "delay", lambda *args: called.append(args))

        r = client.post(
            f"/admin/tenants/{tid}/cortex/ingestion/actions/trigger-sync",
            auth=("admin", "integration-admin-password"),
            json={
                "connector": "github",
                "connection_id": str(conn_id),
                "confirmation": "RUN MANUAL CORTEX INGESTION SYNC",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["connection_id"] == str(conn_id)
        assert len(called) == 1
        assert called[0][-1] == str(conn_id)
    finally:
        get_settings.cache_clear()
