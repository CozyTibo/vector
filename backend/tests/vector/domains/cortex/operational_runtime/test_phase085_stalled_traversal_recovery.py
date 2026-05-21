"""P085-16 — Stalled traversal recovery (**G-P085-WALK-03**)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_stalled_traversal_gate import (
    verify_gp085_stalled_traversal_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
    CELERY_STALLED_TRAVERSAL_RECOVERY_TASK_NAME_V1,
    GP085_WALK03_GATE_ID_V1,
    POISON_REASON_MAX_RECOVERY_PASSES_V1,
    RECOVERY_ACTION_CANCEL_POISON_DLQ_V1,
    RECOVERY_ACTION_REENQUEUE_V1,
    apply_stalled_walk_recovery_v1,
    build_substrate_stalled_traversal_recovery_catalog_v1,
    classify_walk_poison_v1,
    detect_stalled_traversal_v1,
    evaluate_tenant_traversal_stall_v1,
    run_stalled_traversal_recovery_pass_v1,
    schedule_stalled_traversal_recovery_pass_v1,
    verify_gp085_walk03_static,
)
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1


def test_stalled_traversal_catalog() -> None:
    cat = build_substrate_stalled_traversal_recovery_catalog_v1()
    assert cat["primary_gate_id"] == GP085_WALK03_GATE_ID_V1
    assert cat["pass_entrypoint"] == "run_stalled_traversal_recovery_pass_v1"


def test_verify_gp085_walk03_static_passes() -> None:
    assert verify_gp085_walk03_static()["passed"] is True
    assert verify_gp085_stalled_traversal_gate_static()["passed"] is True


def test_detect_stalled_traversal() -> None:
    old = (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()
    stalled = detect_stalled_traversal_v1(
        pending_walks=3,
        last_walk_completed_at=old,
        stall_threshold_seconds=60,
    )
    assert stalled["stalled"] is True
    assert stalled["reason"] == "last_completion_exceeds_t_stall"

    fresh = detect_stalled_traversal_v1(
        pending_walks=3,
        last_walk_completed_at=datetime.now(tz=UTC).isoformat(),
        stall_threshold_seconds=3600,
    )
    assert fresh["stalled"] is False


def test_classify_walk_poison_by_recovery_passes() -> None:
    rec = WalkApiRecordV1(
        walk_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="running",
        request_body={
            "cesp_walk_stall_v1": {"recovery_pass_count": 99},
            "start_node_ids": ["n1"],
        },
    )
    is_poison, reason = classify_walk_poison_v1(rec)
    assert is_poison is True
    assert reason == POISON_REASON_MAX_RECOVERY_PASSES_V1


def test_apply_stalled_walk_recovery_reenqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    wid = uuid.uuid4()
    rec = WalkApiRecordV1(
        walk_id=wid,
        tenant_id=tid,
        status="queued",
        request_body={"start_node_ids": ["n1"]},
        job_id="job-old",
    )
    store = MagicMock()
    store.requeue_pending_walk_v1.return_value = WalkApiRecordV1(
        walk_id=wid,
        tenant_id=tid,
        status="queued",
        request_body=rec.request_body,
        job_id="job-new",
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery.resolve_octs_walk_store_v1",
        lambda *_a, **_k: store,
    )
    session.get.return_value = None
    out = apply_stalled_walk_recovery_v1(session, tenant_id=tid, record=rec)
    assert out["action"] == RECOVERY_ACTION_REENQUEUE_V1
    assert out["requeued"] is True


def test_apply_stalled_walk_recovery_poison_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    rec = WalkApiRecordV1(
        walk_id=uuid.uuid4(),
        tenant_id=tid,
        status="running",
        request_body={"cesp_walk_stall_v1": {"recovery_pass_count": 99}},
    )
    store = MagicMock()
    store.cancel.return_value = WalkApiRecordV1(
        walk_id=rec.walk_id,
        tenant_id=tid,
        status="cancelled",
        request_body=rec.request_body,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery.resolve_octs_walk_store_v1",
        lambda *_a, **_k: store,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery._resolve_pipeline_run_id_for_walk_v1",
        lambda *_a, **_k: None,
    )
    session.get.return_value = None
    out = apply_stalled_walk_recovery_v1(session, tenant_id=tid, record=rec)
    assert out["action"] == RECOVERY_ACTION_CANCEL_POISON_DLQ_V1


def test_schedule_stalled_traversal_recovery_runs_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = uuid.uuid4()

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery."
        "run_stalled_traversal_recovery_pass_v1",
        lambda *_a, **_k: {"gate_id": "G-P085-WALK-03", "recovered": False},
    )
    out = schedule_stalled_traversal_recovery_pass_v1(tenant_id=tid)
    assert out["scheduled"] is True
    assert out["path"] == "inline_execution_slice"
    assert "pass" in out


@pytest.mark.integration
def test_evaluate_tenant_traversal_stall_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085stall-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Stall",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    out = evaluate_tenant_traversal_stall_v1(db_session, tenant_id=row.id)
    assert out["gate_id"] == GP085_WALK03_GATE_ID_V1
    assert out["stalled"] is False

    pass_out = run_stalled_traversal_recovery_pass_v1(db_session, tenant_id=row.id)
    assert pass_out["recovered"] is False
