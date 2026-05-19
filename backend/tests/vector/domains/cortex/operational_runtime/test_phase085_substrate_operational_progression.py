"""Substrate operational progression coordinator (runtime closure)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.substrate_operational_progression import (
    PROGRESSION_OWNER_ID_V1,
    TENANT_PROGRESSION_CLASS_IDLE_V1,
    build_substrate_operational_progression_catalog_v1,
    build_substrate_progression_status_v1,
    classify_retrieval_materialization_outcome_v1,
    continue_substrate_operational_progression_v1,
)


def test_classify_retrieval_materialization_outcome() -> None:
    assert classify_retrieval_materialization_outcome_v1(
        entries_materialized=2,
        entry_count=2,
        tcre_candidates=1,
        walks_candidates=0,
        org_link_candidates=0,
    ) == "progressing"
    assert (
        classify_retrieval_materialization_outcome_v1(
            entries_materialized=0,
            entry_count=0,
            tcre_candidates=3,
            walks_candidates=1,
            org_link_candidates=0,
        )
        == "operational_starvation"
    )
    assert (
        classify_retrieval_materialization_outcome_v1(
            entries_materialized=0,
            entry_count=0,
            tcre_candidates=0,
            walks_candidates=0,
            org_link_candidates=0,
        )
        == "healthy_idle"
    )


def test_progression_catalog() -> None:
    cat = build_substrate_operational_progression_catalog_v1()
    assert cat["progression_owner_id"] == PROGRESSION_OWNER_ID_V1
    assert cat["entrypoint"] == "continue_substrate_operational_progression_v1"


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085prog2-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Progression Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.mark.integration
def test_progression_status_idle_without_pipeline(db_session: Session, tenant: Any) -> None:
    status = build_substrate_progression_status_v1(db_session, tenant_id=tenant.id)
    assert status["tenant_id"] == str(tenant.id)
    assert status["progression_class"] == TENANT_PROGRESSION_CLASS_IDLE_V1
    assert status["ingest_propagated_to_retrieval"] is False


@pytest.mark.integration
def test_continue_no_pipeline(db_session: Session, tenant: Any) -> None:
    out = continue_substrate_operational_progression_v1(db_session, tenant_id=tenant.id)
    assert out["continued"] is False
    assert out["reason"] == "no_active_pipeline_run"


def test_ingestion_scheduler_tick_does_not_schedule_substrate_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_INGESTION_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    schedule_mock = MagicMock()
    monkeypatch.setattr(
        "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch."
        "schedule_post_ingestion_substrate_refresh",
        schedule_mock,
    )

    from contextlib import contextmanager

    @contextmanager
    def _scope() -> MagicMock:
        yield MagicMock()

    monkeypatch.setattr("app.tasks.cortex_ingestion_scheduler.session_scope", _scope)
    monkeypatch.setattr(
        "app.tasks.cortex_ingestion_scheduler.iter_routed_live_sync_jobs",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "app.tasks.cortex_ingestion_scheduler.read_scheduler_paused_flag",
        lambda *_a, **_k: False,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        from app.tasks.cortex_ingestion_scheduler import tick_cortex_ingestion_scheduler

        out = tick_cortex_ingestion_scheduler()
        assert out["enqueued"] == 0
        schedule_mock.assert_not_called()
        assert "incremental_sync_complete" in out["substrate_refresh_note"]
    finally:
        get_settings.cache_clear()
