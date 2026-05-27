"""People-plane streams — linear users/teams (mock GraphQL)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import vector.domains.cortex.ingestion.connectors.linear.sync as linear_sync
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
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


def _tenant_with_linear(db_session: Session) -> uuid.UUID:
    user = User(email=f"people-{uuid.uuid4().hex[:8]}@example.com", full_name="People User")
    tenant = Tenant(
        company_name="PeopleCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"people-{uuid.uuid4().hex[:10]}",
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
            linear_organization_name="PeopleCo",
        )
    )
    db_session.flush()
    return tenant.id


def test_linear_people_plane_ingests_users_and_teams(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    tid = _tenant_with_linear(db_session)

    def _fake_graphql(
        settings: object,
        token: str,
        *,
        operation_name: str,
        query: str,
        root_field: str,
        first: int,
        after: str | None,
    ) -> tuple[int, dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        del settings, token, query, first, after
        if operation_name == "LinearIngestUsers":
            return (
                200,
                {},
                [{"id": "u1", "name": "Ada", "email": "ada@example.com"}],
                {"hasNextPage": False, "endCursor": None},
            )
        if operation_name == "LinearIngestTeams":
            return (
                200,
                {},
                [
                    {
                        "id": "t1",
                        "name": "Eng",
                        "slug": "eng",
                        "members": {"nodes": [{"id": "u1", "name": "Ada"}]},
                    },
                ],
                {"hasNextPage": False, "endCursor": None},
            )
        if operation_name == "LinearIngestIssues":
            return 200, {}, [], {"hasNextPage": False, "endCursor": None}
        return 200, {}, [], {"hasNextPage": False, "endCursor": None}

    monkeypatch.setattr(linear_sync, "linear_graphql_connection_page", _fake_graphql)
    monkeypatch.setattr(
        linear_sync,
        "linear_graphql_ping",
        lambda *_a, **_k: (200, {"data": {"viewer": {"id": "v1"}}}),
    )

    execute_connector_sync(
        db_session,
        get_settings(),
        tenant_id=tid,
        connector_id="linear",
        source_trigger="test",
    )
    db_session.commit()

    types = {
        r[0]
        for r in db_session.execute(
            select(RawIngestionRecord.resource_type).where(
                RawIngestionRecord.tenant_id == tid,
                RawIngestionRecord.connector == "linear",
            ),
        ).all()
    }
    assert "linear.user" in types
    assert "linear.team" in types
    assert "linear.team_membership" in types
