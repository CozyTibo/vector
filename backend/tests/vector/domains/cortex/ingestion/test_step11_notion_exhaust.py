"""Phase 01 Step 11 — Notion organizational exhaust integration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import vector.domains.cortex.ingestion.connectors.notion.sync as notion_sync
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
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


def _tenant_with_notion(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"notion-{uuid.uuid4().hex[:8]}@example.com", full_name="Notion User")
    tenant = Tenant(
        company_name="NotionCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"notion-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="notion",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    db_session.add(
        NotionConnectionDetail(
            connection_id=conn.id,
            access_token="mock-notion-token",
            token_type="bearer",
            workspace_id="ws-123",
            workspace_name="NotionCo",
            workspace_icon=None,
            owner_user_id="owner-1",
            bot_id="bot-1",
            connected_at=datetime.now(UTC),
        )
    )
    db_session.flush()
    return tenant.id, conn.id


def test_step11_notion_ingests_search_databases_rows_and_blocks(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, conn_id = _tenant_with_notion(db_session)

    def _mock_post(url: str, **kwargs: Any) -> _MockResponse:
        if url.endswith("/search"):
            return _MockResponse(
                {
                    "results": [
                        {
                            "object": "page",
                            "id": "page-1",
                            "last_edited_time": "2026-05-08T10:00:00Z",
                            "title": "Roadmap",
                        },
                        {
                            "object": "database",
                            "id": "db-1",
                            "last_edited_time": "2026-05-08T09:00:00Z",
                            "title": "Projects DB",
                        },
                    ],
                    "has_more": False,
                    "next_cursor": None,
                }
            )
        if url.endswith("/databases/db-1/query"):
            return _MockResponse(
                {
                    "results": [
                        {
                            "object": "page",
                            "id": "row-1",
                            "last_edited_time": "2026-05-08T08:00:00Z",
                            "properties": {"Name": {"title": []}},
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                }
            )
        return _MockResponse({})

    def _mock_get(url: str, **kwargs: Any) -> _MockResponse:
        if url.endswith("/databases/db-1"):
            return _MockResponse({"object": "database", "id": "db-1", "title": [{"plain_text": "Projects"}]})
        if "/blocks/page-1/children" in url:
            return _MockResponse(
                {
                    "results": [
                        {
                            "object": "block",
                            "id": "blk-1",
                            "type": "paragraph",
                            "has_children": True,
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                }
            )
        if "/blocks/blk-1/children" in url:
            return _MockResponse(
                {
                    "results": [
                        {
                            "object": "block",
                            "id": "blk-1-child",
                            "type": "to_do",
                            "has_children": False,
                        }
                    ],
                    "has_more": False,
                    "next_cursor": None,
                }
            )
        if "/blocks/row-1/children" in url:
            return _MockResponse({"results": [], "has_more": False, "next_cursor": None})
        return _MockResponse({})

    monkeypatch.setattr(notion_sync.httpx, "post", _mock_post)
    monkeypatch.setattr(notion_sync.httpx, "get", _mock_get)

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="notion",
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
    assert counts["notion.search_result"] == 2
    assert counts["notion.page"] == 1
    assert counts["notion.database"] == 1
    assert counts["notion.database_row"] == 1
    assert counts["notion.block"] == 2
    assert counts["notion.scope_ping"] == 1

    st = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "notion",
            ConnectorSyncState.scope_key == "default",
        )
    )
    assert st is not None
    notion_streams = (
        st.state.get("modes", {}).get("incremental", {}).get("streams", {}).get("notion", {})
        if isinstance(st.state, dict)
        else {}
    )
    assert notion_streams.get("search", {}).get("rows_seen_last_run") == 2
    assert notion_streams.get("database_rows", {}).get("rows_seen_last_run") == 1
    assert notion_streams.get("blocks", {}).get("rows_seen_last_run") == 2
