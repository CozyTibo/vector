"""Next scheduled ingestion forecast."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from vector.domains.cortex.ingestion.ingestion_schedule_forecast import (
    estimate_tenant_next_scheduled_ingestion_v1,
)


def test_forecast_disabled_when_env_off() -> None:
    settings = MagicMock()
    settings.cortex_ingestion_scheduler_interval_seconds = 60
    settings.cortex_ingestion_min_gap_seconds = 300
    settings.cortex_ingestion_scheduler_enabled = False
    out = estimate_tenant_next_scheduled_ingestion_v1(
        MagicMock(),
        settings,
        tenant_id=uuid.uuid4(),
        scheduler={"env_scheduler_enabled": False, "paused_via_redis": False},
        connector_rows=[],
    )
    assert out["status"] == "disabled"
    assert out["next_at"] is None


def test_forecast_eligible_now_uses_next_beat_not_wall_clock_now() -> None:
    settings = MagicMock()
    settings.cortex_ingestion_scheduler_interval_seconds = 120
    settings.cortex_ingestion_min_gap_seconds = 600
    settings.cortex_ingestion_scheduler_enabled = True
    session = MagicMock()
    tenant_id = uuid.uuid4()
    last_scheduled = datetime.now(tz=UTC) - timedelta(seconds=30)
    session.scalar.side_effect = [None, last_scheduled]
    rows = [
        {
            "connector": "slack",
            "connection_id": uuid.uuid4(),
            "connection_status": "active",
            "cortex_routed": True,
            "checkpoint_last_incremental_at": None,
        },
    ]
    out = estimate_tenant_next_scheduled_ingestion_v1(
        session,
        settings,
        tenant_id=tenant_id,
        scheduler={"env_scheduler_enabled": True, "paused_via_redis": False, "beat_interval_seconds": 120, "min_gap_seconds": 600},
        connector_rows=rows,
    )
    assert out["status"] == "eligible_now"
    assert out["next_at"] is not None
    assert out["next_at"] > datetime.now(tz=UTC)
    assert "slack" in out["summary"]
    assert "next tick" in out["summary"].lower()


def test_forecast_waiting_cooldown() -> None:
    settings = MagicMock()
    settings.cortex_ingestion_scheduler_interval_seconds = 60
    settings.cortex_ingestion_min_gap_seconds = 3600
    settings.cortex_ingestion_scheduler_enabled = True
    session = MagicMock()
    session.scalar.return_value = None
    recent = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
    rows = [
        {
            "connector": "github",
            "connection_id": uuid.uuid4(),
            "connection_status": "active",
            "cortex_routed": True,
            "checkpoint_last_incremental_at": recent,
        },
    ]
    out = estimate_tenant_next_scheduled_ingestion_v1(
        session,
        settings,
        tenant_id=uuid.uuid4(),
        scheduler={"env_scheduler_enabled": True, "paused_via_redis": False, "beat_interval_seconds": 60, "min_gap_seconds": 3600},
        connector_rows=rows,
    )
    assert out["status"] == "waiting_cooldown"
    assert out["next_at"] is not None
    assert out["next_connector"] == "github"
