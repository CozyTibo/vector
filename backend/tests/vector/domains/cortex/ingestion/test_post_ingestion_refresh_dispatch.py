"""Post-ingestion downstream pass scheduling."""

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


def test_schedule_enqueues_canon_and_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/vector_test",
    )
    monkeypatch.setenv("CORTEX_POST_INGESTION_SUBSTRATE_REFRESH_ENABLED", "true")
    monkeypatch.setenv("CORTEX_CANON_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("CORTEX_IDENTITY_SCHEDULER_ENABLED", "true")

    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )
    from vector.settings import get_settings

    get_settings.cache_clear()
    tid = uuid.uuid4()
    canon_delay = MagicMock()
    identity_delay = MagicMock()
    try:
        with (
            patch(
                "app.tasks.cortex_canon_sync.run_cortex_canon_pass_task.delay",
                canon_delay,
            ),
            patch(
                "app.tasks.cortex_identity_sync.run_cortex_identity_pass_task.delay",
                identity_delay,
            ),
        ):
            out = schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="sync_done")
    finally:
        get_settings.cache_clear()

    assert out["scheduled"] is True
    assert out["enqueued"] == ["canon_pass", "identity_pass"]
    canon_delay.assert_called_once_with(str(tid), source_trigger="ingestion_complete")
    identity_delay.assert_called_once_with(str(tid), source_trigger="ingestion_complete")
