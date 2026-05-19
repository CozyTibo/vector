"""P085-18 — TCRE saturation scheduler (**G-P085-TCRE-01**)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from vector.domains.cortex.operational_runtime.cesp_tcre_saturation_gate import (
    verify_gp085_tcre_saturation_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    TCRE_MATURITY_R0_V1,
    classify_tcre_maturity_class_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1,
    GP085_TCRE01_GATE_ID_V1,
    TCRE_SATURATION_TRIGGER_AFTER_PHASE_06_V1,
    _estimate_jobs_to_reach_saturation_v1,
    build_substrate_tcre_saturation_scheduling_catalog_v1,
    evaluate_tcre_saturation_schedule_v1,
    schedule_tcre_saturation_for_tenant_v1,
    verify_gp085_tcre01_static,
)
from vector.domains.cortex.reasoning.runtime.runtime_scope import (
    normalize_reconstruction_scope_v1,
)


def test_tcre_saturation_catalog() -> None:
    cat = build_substrate_tcre_saturation_scheduling_catalog_v1()
    assert cat["primary_gate_id"] == GP085_TCRE01_GATE_ID_V1
    assert cat["saturation_threshold"] == 0.85
    assert cat["pipeline_scope_field"] == "substrate_pipeline_run_id"


def test_verify_gp085_tcre01_static_passes() -> None:
    assert verify_gp085_tcre01_static()["passed"] is True
    assert verify_gp085_tcre_saturation_gate_static()["passed"] is True


def test_celery_registers_tcre_saturation_task() -> None:
    from app.tasks import cortex_substrate_tcre_saturation_scheduling  # noqa: F401

    assert CELERY_TCRE_SATURATION_SCHEDULE_TASK_NAME_V1 in celery_app.tasks


def test_normalize_scope_preserves_pipeline_run_id() -> None:
    prid = str(uuid.uuid4())
    norm = normalize_reconstruction_scope_v1(
        {"substrate_pipeline_run_id": prid, "materialization_limit": 10}
    )
    assert norm["substrate_pipeline_run_id"] == prid


def test_derive_tcre_maturity_classes() -> None:
    assert (
        classify_tcre_maturity_class_v1(tcre_saturation_percent=0.0, completed_reconstruct_jobs=0)
        == TCRE_MATURITY_R0_V1
    )
    assert classify_tcre_maturity_class_v1(tcre_saturation_percent=90.0, completed_reconstruct_jobs=2) == "R3"
    assert classify_tcre_maturity_class_v1(tcre_saturation_percent=50.0, completed_reconstruct_jobs=1) == "R2"


def test_estimate_jobs_to_reach_saturation() -> None:
    assert _estimate_jobs_to_reach_saturation_v1(mat_total=100, reconstructed=10, threshold=0.85) >= 2


def test_evaluate_schedule_no_materializations(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling."
        "compute_tcre_saturation_metrics_v1",
        lambda *_a, **_k: {
            "tcre_materialization_total": 0,
            "tcre_reconstructed_count": 0,
            "saturation_ratio": 0.0,
            "saturation_threshold": 0.85,
            "queued_running_jobs": 0,
            "jobs_enqueued_last_hour": 0,
            "tcre_reconstructed_count": 0,
        },
    )
    out = evaluate_tcre_saturation_schedule_v1(session, tenant_id=tid)
    assert out["should_schedule"] is False
    assert out["schedule_reason"] == "no_canonical_materializations"


def test_schedule_tcre_saturation_enqueues_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()

    class _FakeAsync:
        id = "tcre-sat-task"

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling."
        "evaluate_tcre_saturation_schedule_v1",
        lambda *_a, **_k: {"should_schedule": True, "schedule_reason": "test"},
    )
    monkeypatch.setattr(
        "app.tasks.cortex_substrate_tcre_saturation_scheduling."
        "run_tcre_saturation_schedule_pass_task.apply_async",
        lambda **kwargs: _FakeAsync(),  # noqa: ARG005
    )
    out = schedule_tcre_saturation_for_tenant_v1(
        tenant_id=tid,
        trigger=TCRE_SATURATION_TRIGGER_AFTER_PHASE_06_V1,
        force=True,
    )
    assert out["scheduled"] is True
    assert out["celery_task_id"] == "tcre-sat-task"


@pytest.mark.integration
def test_evaluate_tcre_saturation_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085tcre-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 TCRE",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    out = evaluate_tcre_saturation_schedule_v1(db_session, tenant_id=row.id)
    assert out["gate_id"] == GP085_TCRE01_GATE_ID_V1
    assert out["should_schedule"] is False
