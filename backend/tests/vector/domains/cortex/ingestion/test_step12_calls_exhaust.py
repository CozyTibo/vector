"""Phase 01 Step 12 — Calls organizational exhaust integration."""

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
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
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


def _tenant_with_calls(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"calls-{uuid.uuid4().hex[:8]}@example.com", full_name="Calls User")
    tenant = Tenant(
        company_name="CallsCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"calls-{uuid.uuid4().hex[:10]}",
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
            refresh_token="refresh-token",
            token_expires_at=datetime.now(UTC),
            provider_user_id="provider-user-1",
            provider_email="owner@example.com",
            connected_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    return tenant.id, conn.id


def test_step12_calls_ingests_meetings_transcripts_and_participants(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("VECTOR_USE_MOCK_CONNECTORS", "true")
    monkeypatch.setenv("VECTOR_MOCK_CONNECTOR_BASE_URL", "http://127.0.0.1:9183")
    get_settings.cache_clear()
    settings = get_settings()
    tid, conn_id = _tenant_with_calls(db_session)

    calls_events = [
        {
            "id": "evt-2",
            "summary": "Sprint sync",
            "updated": "2026-05-08T10:00:00Z",
            "attendees": [
                {"email": "a@example.com", "response_status": "accepted"},
                {"email": "b@example.com", "response_status": "accepted"},
            ],
            "transcript": {
                "provider": "mock",
                "generated_at": "2026-05-08T10:30:00Z",
                "segments": [
                    {"offset_seconds": 0, "speaker_email": "a@example.com", "text": "Kickoff"},
                    {"offset_seconds": 15, "speaker_email": "b@example.com", "text": "Update"},
                ],
            },
            "recording": {"recording_id": "rec-2", "duration_seconds": 1800},
        },
        {
            "id": "evt-1",
            "summary": "Design review",
            "updated": "2026-05-07T10:00:00Z",
            "attendees": [{"email": "c@example.com", "response_status": "accepted"}],
        },
    ]

    def _mock_get(url: str, **kwargs: Any) -> _MockResponse:
        if "/google-calendar/v3/calendars/" not in url or "/events" not in url:
            return _MockResponse({}, status_code=404)
        return _MockResponse({"items": calls_events, "nextPageToken": None})

    monkeypatch.setattr(sync_executor.httpx, "get", _mock_get)

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="calls",
        source_trigger="manual_admin",
    )
    assert out["status"] == "completed"
    run_id = uuid.UUID(str(out["run_id"]))

    counts = {
        rt: int(c)
        for rt, c in db_session.execute(
            select(RawIngestionRecord.resource_type, func.count())
            .where(RawIngestionRecord.run_id == run_id)
            .group_by(RawIngestionRecord.resource_type)
        ).all()
    }
    assert counts["calls.meeting"] == 2
    assert counts["calls.participant"] == 3
    assert counts["calls.transcript"] == 1
    assert counts["calls.transcript_segment"] == 2
    assert counts["calls.recording"] == 1
    assert counts["calls.scope_ping"] == 1

    st = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "calls",
            ConnectorSyncState.scope_key == "default",
        )
    )
    assert st is not None
    calls_streams = (
        st.state.get("modes", {}).get("incremental", {}).get("streams", {}).get("calls", {})
        if isinstance(st.state, dict)
        else {}
    )
    assert calls_streams.get("events", {}).get("rows_seen_last_run") == 2
    assert calls_streams.get("participants", {}).get("rows_seen_last_run") == 3
    assert calls_streams.get("transcript_segments", {}).get("rows_seen_last_run") == 2
    assert calls_streams.get("events", {}).get("updated_watermark") == "2026-05-08T10:00:00Z"


def test_step12_calls_incremental_watermark_skips_old_events(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    monkeypatch.setenv("VECTOR_USE_MOCK_CONNECTORS", "true")
    monkeypatch.setenv("VECTOR_MOCK_CONNECTOR_BASE_URL", "http://127.0.0.1:9183")
    get_settings.cache_clear()
    settings = get_settings()
    tid, conn_id = _tenant_with_calls(db_session)

    db_session.add(
        ConnectorSyncState(
            tenant_id=tid,
            connection_id=conn_id,
            connector="calls",
            scope_key="default",
            state={
                "checkpoint_schema_version": 2,
                "modes": {
                    "incremental": {
                        "streams": {
                            "calls": {
                                "events": {
                                    "cursor_owner": "calls.meeting",
                                    "updated_watermark": "2026-05-08T00:00:00Z",
                                }
                            }
                        },
                        "watermarks": {},
                    },
                    "backfill": {"streams": {}, "watermarks": {}},
                },
                "meta": {"last_writer_mode": "incremental"},
            },
        )
    )
    db_session.flush()

    calls_events = [
        {
            "id": "evt-new",
            "summary": "New",
            "updated": "2026-05-09T10:00:00Z",
            "attendees": [{"email": "n@example.com", "response_status": "accepted"}],
        },
        {
            "id": "evt-old",
            "summary": "Old",
            "updated": "2026-05-07T10:00:00Z",
            "attendees": [{"email": "o@example.com", "response_status": "accepted"}],
        },
    ]

    def _mock_get(url: str, **kwargs: Any) -> _MockResponse:
        if "/google-calendar/v3/calendars/" not in url or "/events" not in url:
            return _MockResponse({}, status_code=404)
        params = kwargs.get("params") if isinstance(kwargs.get("params"), dict) else {}
        updated_min = params.get("updatedMin") if isinstance(params.get("updatedMin"), str) else None
        items = list(calls_events)
        if updated_min:
            items = [e for e in items if isinstance(e.get("updated"), str) and e["updated"] > updated_min]
        return _MockResponse({"items": items, "nextPageToken": None})

    monkeypatch.setattr(sync_executor.httpx, "get", _mock_get)

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="calls",
        source_trigger="manual_admin",
    )
    assert out["status"] == "completed"
    run_id = uuid.UUID(str(out["run_id"]))

    meeting_count = db_session.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(
            RawIngestionRecord.run_id == run_id,
            RawIngestionRecord.resource_type == "calls.meeting",
        )
    )
    assert int(meeting_count or 0) == 1
