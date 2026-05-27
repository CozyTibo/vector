"""Post-ingestion substrate refresh scheduling (ingestion-only: no-op)."""

from __future__ import annotations

import uuid

import pytest


def test_schedule_noops_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "false")

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        out = schedule_post_ingestion_substrate_refresh(tenant_id=uuid.uuid4())
        assert out == {"scheduled": False, "reason": "disabled"}
    finally:
        get_settings.cache_clear()


def test_schedule_noops_when_enabled_substrate_removed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    try:
        out = schedule_post_ingestion_substrate_refresh(tenant_id=uuid.uuid4(), reason="sync_done")
    finally:
        get_settings.cache_clear()

    assert out == {"scheduled": False, "reason": "substrate_pipeline_removed"}
