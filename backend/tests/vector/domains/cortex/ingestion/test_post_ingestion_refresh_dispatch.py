"""Post-ingestion substrate refresh scheduling (convergence lease only, M2)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

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


def test_schedule_always_uses_convergence_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")

    tenant_id = uuid.uuid4()
    with patch(
        "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.mark_dirty_and_enqueue_convergence_v1",
        return_value={
            "scheduled": True,
            "path": "convergence_lease",
            "execution_path": "convergence",
        },
    ) as dispatch:
        from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
            schedule_post_ingestion_substrate_refresh,
        )
        from vector.settings import get_settings

        get_settings.cache_clear()
        try:
            out = schedule_post_ingestion_substrate_refresh(tenant_id=tenant_id, reason="sync_done")
        finally:
            get_settings.cache_clear()

    assert out["scheduled"] is True
    assert out["path"] == "convergence_lease"
    assert out["execution_path"] == "convergence"
    dispatch.assert_called_once_with(
        tenant_id=tenant_id,
        settings=None,
        reason="sync_done",
        telemetry_trigger="post_ingestion:sync_done",
    )
