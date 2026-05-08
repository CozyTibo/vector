"""Phase 01 Step 10 — Linear organizational exhaust integration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import vector.domains.cortex.ingestion.sync_executor as sync_executor
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
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

    def json(self) -> dict[str, Any]:
        return self._payload


def _tenant_with_linear(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"lin-{uuid.uuid4().hex[:8]}@example.com", full_name="Linear User")
    tenant = Tenant(
        company_name="LinearCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"lin-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="linear",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    db_session.add(
        LinearConnectionDetail(
            connection_id=conn.id,
            access_token="mock-linear-token",
            refresh_token=None,
            token_expires_at=datetime.now(UTC),
            linear_organization_id="org_lin",
            linear_organization_name="LinearCo",
        )
    )
    db_session.flush()
    return tenant.id, conn.id


def test_step10_linear_paginates_and_ingests_deep_streams(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, conn_id = _tenant_with_linear(db_session)

    issue_page_1 = {
        "data": {
            "issues": {
                "nodes": [
                    {
                        "id": "iss-2",
                        "identifier": "LIN-2",
                        "title": "Newest",
                        "url": "https://linear.app/lin/issue/LIN-2",
                        "createdAt": "2026-05-08T08:00:00Z",
                        "updatedAt": "2026-05-08T10:00:00Z",
                        "state": {"name": "In Progress"},
                        "metadata": {},
                        "attachments": [{"id": "att-1", "title": "Spec"}],
                        "activityHistory": [{"id": "act-1", "type": "status_change"}],
                    },
                    {
                        "id": "iss-1",
                        "identifier": "LIN-1",
                        "title": "Middle",
                        "url": "https://linear.app/lin/issue/LIN-1",
                        "createdAt": "2026-05-07T08:00:00Z",
                        "updatedAt": "2026-05-07T10:00:00Z",
                        "state": {"name": "Todo"},
                        "metadata": {},
                    },
                ],
                "pageInfo": {"hasNextPage": True, "endCursor": "iss-1"},
            }
        }
    }
    issue_page_2 = {
        "data": {
            "issues": {
                "nodes": [
                    {
                        "id": "iss-0",
                        "identifier": "LIN-0",
                        "title": "Oldest",
                        "url": "https://linear.app/lin/issue/LIN-0",
                        "createdAt": "2026-05-01T08:00:00Z",
                        "updatedAt": "2026-05-01T10:00:00Z",
                        "state": {"name": "Done"},
                        "metadata": {},
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }

    def _mock_post(url: str, **kwargs: Any) -> _MockResponse:
        body = kwargs.get("json") or {}
        op = body.get("operationName")
        variables = body.get("variables") if isinstance(body.get("variables"), dict) else {}
        after = variables.get("after")
        if op == "LinearIngestIssues":
            return _MockResponse(issue_page_2 if after == "iss-1" else issue_page_1)
        if op == "LinearIngestComments":
            return _MockResponse(
                {
                    "data": {
                        "comments": {
                            "nodes": [{"id": "c-1"}, {"id": "c-2"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op == "LinearIngestProjects":
            return _MockResponse(
                {
                    "data": {
                        "projects": {
                            "nodes": [{"id": "p-1"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op == "LinearIngestCycles":
            return _MockResponse(
                {
                    "data": {
                        "cycles": {
                            "nodes": [{"id": "cy-1"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op == "LinearIngestIssueRelations":
            return _MockResponse(
                {
                    "data": {
                        "issueRelations": {
                            "nodes": [{"id": "rel-1"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op == "LinearIngestIssueLabels":
            return _MockResponse(
                {
                    "data": {
                        "issueLabels": {
                            "nodes": [{"id": "lbl-1"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op == "LinearIngestInitiatives":
            return _MockResponse(
                {
                    "data": {
                        "initiatives": {
                            "nodes": [{"id": "ini-1"}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        return _MockResponse({"data": {"viewer": {"id": "v1", "name": "Linear User"}}})

    monkeypatch.setattr(sync_executor.httpx, "post", _mock_post)

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="linear",
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
    assert counts["linear.issue"] == 3
    assert counts["linear.comment"] == 2
    assert counts["linear.project"] == 1
    assert counts["linear.cycle"] == 1
    assert counts["linear.issue_relation"] == 1
    assert counts["linear.issue_label"] == 1
    assert counts["linear.initiative"] == 1
    assert counts["linear.issue_attachment"] == 1
    assert counts["linear.activity_history"] == 1
    assert counts["linear.viewer_ping"] == 1

    st = db_session.scalar(
        select(ConnectorSyncState).where(
            ConnectorSyncState.tenant_id == tid,
            ConnectorSyncState.connection_id == conn_id,
            ConnectorSyncState.connector == "linear",
            ConnectorSyncState.scope_key == "default",
        )
    )
    assert st is not None
    linear_streams = (
        st.state.get("modes", {}).get("incremental", {}).get("streams", {}).get("linear", {})
        if isinstance(st.state, dict)
        else {}
    )
    assert linear_streams.get("issues", {}).get("issues_fetched") == 3
    assert (
        linear_streams.get("issues", {}).get("issues_updated_at_watermark")
        == "2026-05-08T10:00:00Z"
    )
    assert linear_streams.get("comments", {}).get("rows_seen_last_run") == 2


def test_step10_linear_incremental_watermark_filters_old_issues(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()
    tid, conn_id = _tenant_with_linear(db_session)

    db_session.add(
        ConnectorSyncState(
            tenant_id=tid,
            connection_id=conn_id,
            connector="linear",
            scope_key="default",
            state={
                "checkpoint_schema_version": 2,
                "modes": {
                    "incremental": {
                        "streams": {
                            "linear": {
                                "issues": {
                                    "cursor_owner": "linear.issue",
                                    "issues_updated_at_watermark": "2026-05-08T00:00:00Z",
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

    def _mock_post(url: str, **kwargs: Any) -> _MockResponse:
        body = kwargs.get("json") or {}
        op = body.get("operationName")
        if op == "LinearIngestIssues":
            return _MockResponse(
                {
                    "data": {
                        "issues": {
                            "nodes": [
                                {
                                    "id": "iss-new",
                                    "identifier": "LIN-NEW",
                                    "createdAt": "2026-05-09T00:00:00Z",
                                    "updatedAt": "2026-05-09T00:00:00Z",
                                    "state": {"name": "In Progress"},
                                    "metadata": {},
                                },
                                {
                                    "id": "iss-old",
                                    "identifier": "LIN-OLD",
                                    "createdAt": "2026-05-07T00:00:00Z",
                                    "updatedAt": "2026-05-07T00:00:00Z",
                                    "state": {"name": "Done"},
                                    "metadata": {},
                                },
                            ],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            )
        if op in {
            "LinearIngestComments",
            "LinearIngestProjects",
            "LinearIngestCycles",
            "LinearIngestIssueRelations",
            "LinearIngestIssueLabels",
            "LinearIngestInitiatives",
        }:
            root = {
                "LinearIngestComments": "comments",
                "LinearIngestProjects": "projects",
                "LinearIngestCycles": "cycles",
                "LinearIngestIssueRelations": "issueRelations",
                "LinearIngestIssueLabels": "issueLabels",
                "LinearIngestInitiatives": "initiatives",
            }[op]
            return _MockResponse(
                {
                    "data": {
                        root: {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
                    }
                }
            )
        return _MockResponse({"data": {"viewer": {"id": "v1", "name": "Linear User"}}})

    monkeypatch.setattr(sync_executor.httpx, "post", _mock_post)

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tid,
        connector_id="linear",
        source_trigger="manual_admin",
    )
    assert out["status"] == "completed"
    run_id = uuid.UUID(str(out["run_id"]))
    issue_count = db_session.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(
            RawIngestionRecord.run_id == run_id,
            RawIngestionRecord.resource_type == "linear.issue",
        )
    )
    assert int(issue_count or 0) == 1
