"""Global Cortex operations overview for admin."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.runtime.lane_scheduler_tick import latest_lane_scheduler_tick_v1
from vector.domains.cortex.runtime.lane_scheduler_status import _tick_payload
from vector.domains.cortex.runtime.queue import count_passes_by_status_v1
from vector.infrastructure.cortex_lane_pause import read_all_lane_pause_flags
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
from vector.infrastructure.db.models.ingestion_scheduler_tick import IngestionSchedulerTick
from vector.infrastructure.db.models.orchestrator_run import OrchestratorRun
from vector.settings import Settings


def build_cortex_operations_overview_v1(session: Session, settings: Settings) -> dict[str, Any]:
    last_orch = session.scalar(
        select(OrchestratorRun).order_by(OrchestratorRun.started_at.desc()).limit(1),
    )
    pass_counts = count_passes_by_status_v1(session)
    return {
        "lane_pause": read_all_lane_pause_flags(settings),
        "pass_counts_by_status": pass_counts,
        "last_orchestrator_run": (
            {
                "id": str(last_orch.id),
                "started_at": last_orch.started_at.isoformat(),
                "completed_at": last_orch.completed_at.isoformat() if last_orch.completed_at else None,
                "outcome": last_orch.outcome,
                "ingestion_enqueued": last_orch.ingestion_enqueued,
                "passes_planned": last_orch.passes_planned,
                "passes_processed": last_orch.passes_processed,
                "detail_json": last_orch.detail_json,
                "error_summary": last_orch.error_summary,
            }
            if last_orch
            else None
        ),
        "last_ingestion_tick": _tick_payload(latest_lane_scheduler_tick_v1(session, IngestionSchedulerTick)),
        "last_canon_tick": _tick_payload(latest_lane_scheduler_tick_v1(session, CanonSchedulerTick)),
        "last_identity_tick": _tick_payload(latest_lane_scheduler_tick_v1(session, IdentitySchedulerTick)),
        "scheduler_intervals_seconds": {
            "ingestion": settings.cortex_ingestion_scheduler_interval_seconds,
            "canon_plan": settings.cortex_canon_scheduler_interval_seconds,
            "orchestrator": settings.cortex_orchestrator_interval_seconds,
            "poll": settings.cortex_runtime_poll_interval_seconds,
        },
    }
