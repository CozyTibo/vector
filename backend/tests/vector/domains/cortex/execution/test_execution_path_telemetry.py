"""M0 shadow metrics — execution_path telemetry."""

from __future__ import annotations

import logging
import uuid
from unittest.mock import patch

import pytest

from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_ADMIN_BYPASS,
    EXECUTION_PATH_CONVERGENCE,
    EXECUTION_PATH_LEGACY,
    EXECUTION_PATH_PROGRESSION,
    EXECUTION_PATH_TELEMETRY_EVENT,
    emit_admin_bypass_telemetry_v1,
    emit_execution_path_telemetry_v1,
    execution_path_from_post_ingestion_path,
)


def test_execution_path_from_post_ingestion_path_maps_known_paths() -> None:
    assert execution_path_from_post_ingestion_path("convergence_lease") == EXECUTION_PATH_CONVERGENCE
    assert execution_path_from_post_ingestion_path("legacy_debounced_coordinator") == EXECUTION_PATH_LEGACY
    assert execution_path_from_post_ingestion_path(None) == EXECUTION_PATH_LEGACY


def test_emit_execution_path_telemetry_rejects_invalid_path() -> None:
    with pytest.raises(ValueError, match="invalid_execution_path"):
        emit_execution_path_telemetry_v1(
            tenant_id=uuid.uuid4(),
            execution_path="unknown",
            trigger="test",
        )


def test_emit_execution_path_telemetry_structured_payload(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    payload = emit_execution_path_telemetry_v1(
        tenant_id=tid,
        execution_path=EXECUTION_PATH_PROGRESSION,
        trigger="progression_tick",
        pipeline_run_id=prid,
        phase_id="phase_07_retrieval",
        detail={"force": False},
    )
    assert payload["event"] == EXECUTION_PATH_TELEMETRY_EVENT
    assert payload["execution_path"] == EXECUTION_PATH_PROGRESSION
    assert payload["tenant_id"] == str(tid)
    assert payload["pipeline_run_id"] == str(prid)
    assert payload["phase_id"] == "phase_07_retrieval"
    assert any(EXECUTION_PATH_TELEMETRY_EVENT in r.message for r in caplog.records)


def test_emit_admin_bypass_telemetry_sets_path_and_action() -> None:
    tid = uuid.uuid4()
    payload = emit_admin_bypass_telemetry_v1(
        tenant_id=tid,
        admin_action="canonical_transform_materialize",
    )
    assert payload["execution_path"] == EXECUTION_PATH_ADMIN_BYPASS
    assert payload["trigger"] == "admin:canonical_transform_materialize"
    assert payload["detail"]["admin_action"] == "canonical_transform_materialize"


def test_post_ingestion_convergence_dispatch_includes_execution_path() -> None:
    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )

    tenant_id = uuid.uuid4()
    cfg = type(
        "Cfg",
        (),
        {
            "cortex_post_ingestion_substrate_refresh_enabled": True,
            "cortex_convergence_runtime_enabled": True,
        },
    )()
    with (
        patch(
            "vector.domains.cortex.convergence.lease.mark_tenant_dirty_v1",
            return_value={"obligation_epoch": 1, "status": "dirty"},
        ),
        patch("vector.infrastructure.db.session.session_scope"),
        patch(
            "vector.domains.cortex.convergence.enqueue.enqueue_tenant_convergence_v1",
            return_value={"enqueued": True, "celery_task_id": "t1"},
        ),
    ):
        out = schedule_post_ingestion_substrate_refresh(
            tenant_id=tenant_id,
            settings=cfg,
            reason="incremental_sync_complete",
        )
    assert out["execution_path"] == EXECUTION_PATH_CONVERGENCE
    assert out["execution_path_telemetry"]["execution_path"] == EXECUTION_PATH_CONVERGENCE


def test_post_ingestion_legacy_dispatch_includes_execution_path() -> None:
    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )

    tenant_id = uuid.uuid4()
    cfg = type(
        "Cfg",
        (),
        {
            "cortex_post_ingestion_substrate_refresh_enabled": True,
            "cortex_convergence_runtime_enabled": False,
            "cortex_post_ingestion_substrate_refresh_debounce_seconds": 30,
            "cortex_post_ingestion_canonical_batch_limit": 100,
        },
    )()
    with patch(
        "vector.domains.cortex.substrate_pipeline.orchestrator.schedule_substrate_pipeline_v1",
        return_value={
            "scheduled": True,
            "celery_task_id": "legacy-1",
            "schedule_action": "enqueue",
        },
    ):
        out = schedule_post_ingestion_substrate_refresh(
            tenant_id=tenant_id,
            settings=cfg,
            reason="incremental_sync_complete",
        )
    assert out["execution_path"] == EXECUTION_PATH_LEGACY
    assert out["execution_path_telemetry"]["execution_path"] == EXECUTION_PATH_LEGACY
