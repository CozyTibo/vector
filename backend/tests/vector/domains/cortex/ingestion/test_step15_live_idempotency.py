"""Phase 01 Step 15 — live logical idempotency + revision-safe append semantics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import vector.domains.cortex.ingestion.sync_executor as sync_executor
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.calls_connection_detail import CallsConnectionDetail
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.settings import get_settings

pytestmark = pytest.mark.integration


class _MockResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = ""
        self.is_error = status_code >= 400

    def json(self) -> dict[str, Any]:
        return self._payload


def _tenant_with_calls(db_session: Session) -> uuid.UUID:
    user = User(email=f"step15-{uuid.uuid4().hex[:8]}@example.com", full_name="Step 15 User")
    tenant = Tenant(
        company_name="Step15 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"step15-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="calls",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    db_session.add(
        CallsConnectionDetail(
            connection_id=conn.id,
            access_token="mock-calls-token",
            refresh_token=None,
            token_expires_at=datetime.now(UTC),
            provider_user_id="provider-user-1",
            provider_email="owner@example.com",
            connected_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    return tenant.id


def test_step15_live_dedupe_and_revision_append(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("VECTOR_USE_MOCK_CONNECTORS", "true")
    monkeypatch.setenv("VECTOR_MOCK_CONNECTOR_BASE_URL", "http://127.0.0.1:9183")
    get_settings.cache_clear()
    settings = get_settings()
    tenant_id = _tenant_with_calls(db_session)

    state = {"version": 1}

    def _mock_get(url: str, **kwargs: Any) -> _MockResponse:
        if not url.endswith("/admin/dataset/full"):
            return _MockResponse({}, status_code=404)
        updated = "2026-05-08T10:00:00Z" if state["version"] == 1 else "2026-05-09T10:00:00Z"
        event = {
            "id": "evt-live-1",
            "summary": "Weekly sync",
            "updated": updated,
            "attendees": [{"email": "a@example.com", "response_status": "accepted"}],
        }
        return _MockResponse({"calls": {"events": [event]}})

    monkeypatch.setattr(sync_executor.httpx, "get", _mock_get)

    first = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="calls",
        source_trigger="manual_admin",
    )
    assert first["status"] == "completed"

    # Same identity + same revision => no duplicate live append.
    second = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="calls",
        source_trigger="manual_admin",
    )
    assert second["status"] == "completed"

    state["version"] = 2
    # Same identity + new revision => append new row.
    third = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant_id,
        connector_id="calls",
        source_trigger="manual_admin",
    )
    assert third["status"] == "completed"

    meeting_count = db_session.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connector == "calls",
            RawIngestionRecord.resource_type == "calls.meeting",
            RawIngestionRecord.external_id == "evt-live-1",
            RawIngestionRecord.replay_job_id.is_(None),
        )
    )
    assert int(meeting_count or 0) == 2

    rows = list(
        db_session.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.connector == "calls",
                RawIngestionRecord.resource_type == "calls.meeting",
                RawIngestionRecord.external_id == "evt-live-1",
            )
        ).all()
    )
    assert all(r.source_identity_key for r in rows)
    assert all(r.source_revision_key for r in rows)
    assert len({r.source_revision_key for r in rows}) == 2
