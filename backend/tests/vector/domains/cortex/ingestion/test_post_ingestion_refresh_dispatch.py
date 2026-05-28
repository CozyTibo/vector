"""Post-ingestion downstream pass scheduling."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
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


def test_schedule_enqueues_pass_rows(monkeypatch: pytest.MonkeyPatch) -> None:
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

    upsert_calls: list[str] = []

    @contextmanager
    def _fake_scope():
        yield MagicMock()

    def _fake_upsert(_session, *, pass_type: str, **_kwargs: object) -> uuid.UUID:
        upsert_calls.append(pass_type)
        return uuid.uuid4()

    get_settings.cache_clear()
    tid = uuid.uuid4()
    try:
        with (
            patch(
                "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.session_scope",
                _fake_scope,
            ),
            patch(
                "vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch.upsert_pending_pass_v1",
                _fake_upsert,
            ),
        ):
            out = schedule_post_ingestion_substrate_refresh(tenant_id=tid, reason="sync_done")
    finally:
        get_settings.cache_clear()

    assert out["scheduled"] is True
    assert out["enqueued"] == ["canon_pass", "identity_pass"]
    assert upsert_calls == ["canon_pass", "identity_pass"]
