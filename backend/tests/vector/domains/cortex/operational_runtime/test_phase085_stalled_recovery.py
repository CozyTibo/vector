"""P085-09 — Stalled pipeline watchdog (**G-P085-WATCH-01**)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_watchdog_gate import (
    verify_gp085_watchdog_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_continuity_watchdog import (
    CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1,
    DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1,
    GP085_WATCH01_GATE_ID_V1,
    build_substrate_continuity_watchdog_catalog_v1,
    build_watchdog_audit_record_v1,
    compute_watchdog_run_digest_v1,
    verify_gp085_watch01_static,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    mark_pipeline_waiting_on_tcre_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    detect_stalled_substrate_pipelines_v1,
    run_stalled_pipeline_watchdog_v1,
)


def test_watchdog_catalog_lists_algorithm_and_beat() -> None:
    cat = build_substrate_continuity_watchdog_catalog_v1()
    assert cat["primary_gate_id"] == GP085_WATCH01_GATE_ID_V1
    assert cat["celery_task_name"] == CELERY_CONTINUITY_WATCHDOG_TASK_NAME_V1
    assert cat["default_interval_seconds"] == DEFAULT_WATCHDOG_INTERVAL_SECONDS_V1
    assert len(cat["algorithm_steps"]) == 4


def test_verify_gp085_watch01_static_passes() -> None:
    assert verify_gp085_watch01_static()["passed"] is True
    assert verify_gp085_watchdog_gate_static()["passed"] is True


def test_watchdog_audit_digest_is_stable() -> None:
    d1 = compute_watchdog_run_digest_v1(
        watchdog_run_id="run-1",
        stall_threshold_seconds=1800,
        auto_recover=True,
        stalled_count=2,
        recoveries_succeeded=1,
        recoveries_failed=1,
    )
    d2 = compute_watchdog_run_digest_v1(
        watchdog_run_id="run-1",
        stall_threshold_seconds=1800,
        auto_recover=True,
        stalled_count=2,
        recoveries_succeeded=1,
        recoveries_failed=1,
    )
    assert d1 == d2
    audit = build_watchdog_audit_record_v1(
        watchdog_run_id="run-1",
        stall_threshold_seconds=1800,
        auto_recover=False,
        stalled=[{"pipeline_run_id": "p1"}],
        recovered=[],
    )
    assert audit["stalled_count"] == 1
    assert audit["watchdog_run_digest"].startswith("sha256:")


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085watch-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Watchdog Tenant",
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
def test_detect_stalled_marks_waiting_continuation(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085stall-{uuid.uuid4().hex[:12]}",
    )
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    cont.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=7200)
    db_session.flush()

    stalled = detect_stalled_substrate_pipelines_v1(
        db_session,
        stall_threshold_seconds=1800,
        limit=10,
    )
    assert len(stalled) >= 1
    assert any(s["pipeline_run_id"] == str(run.id) for s in stalled)
    db_session.refresh(cont)
    assert cont.continuation_status == CONTINUATION_STATUS_STALLED
    assert cont.recovery_required is True


@pytest.mark.integration
def test_watchdog_tick_returns_audit_without_auto_recover(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085watch-{uuid.uuid4().hex[:12]}",
    )
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    cont.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=7200)
    db_session.flush()

    out = run_stalled_pipeline_watchdog_v1(
        db_session,
        stall_threshold_seconds=1800,
        auto_recover=False,
        limit=10,
    )
    assert out["stalled_count"] >= 1
    assert "audit" in out
    assert out["audit"]["gate_id"] == GP085_WATCH01_GATE_ID_V1
    assert out["recovered"] == []


@pytest.mark.integration
def test_watchdog_auto_recover_phase07_complete(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085wrec-{uuid.uuid4().hex[:12]}",
    )
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    cont.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=7200)
    db_session.flush()

    phase07 = MagicMock()
    phase07.status = "completed"
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery.get_phase_run_v1",
        lambda *_a, **_k: phase07,
    )

    out = run_stalled_pipeline_watchdog_v1(
        db_session,
        stall_threshold_seconds=1800,
        auto_recover=True,
        limit=10,
    )
    assert out["audit"]["recoveries_succeeded"] >= 1
    assert any(r.get("recovered") for r in out["recovered"])
