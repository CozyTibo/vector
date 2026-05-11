"""Integration: Cortex ingestion executor (requires DATABASE_URL)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.models.tenant import Tenant
from vector.settings import get_settings

pytestmark = pytest.mark.integration


def test_execute_connector_sync_skipped_without_connection(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-min-32-characters-long!")
    get_settings.cache_clear()
    settings = get_settings()

    tenant = Tenant(
        company_name="Empty Conn",
        primary_email=f"sync-{uuid.uuid4().hex[:8]}@example.com",
        email_domain="example.com",
        slug=f"ec-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = execute_connector_sync(
        db_session,
        settings,
        tenant_id=tenant.id,
        connector_id="github",
        source_trigger="test",
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "no_connection"
