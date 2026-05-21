"""P085-24 — Synthesis activation scheduler (**G-P085-SYN-01**)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_synthesis_activation_gate import (
    verify_gp085_synthesis_activation_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
    CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1,
    GP085_SYN01_GATE_ID_V1,
    SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
    build_substrate_synthesis_activation_scheduling_catalog_v1,
    compute_min_synthesis_jobs_target_v1,
    evaluate_synthesis_activation_schedule_v1,
    schedule_synthesis_activation_for_tenant_v1,
    verify_gp085_syn01_static,
)


def test_synthesis_activation_catalog() -> None:
    cat = build_substrate_synthesis_activation_scheduling_catalog_v1()
    assert cat["primary_gate_id"] == GP085_SYN01_GATE_ID_V1
    assert cat["min_jobs_formula"] == "min(eligible_scopes, max_scopes_per_pass)"
    assert cat["activation_audit_table"] == "cortex_synthesis_activation_audits"


def test_verify_gp085_syn01_static_passes() -> None:
    assert verify_gp085_syn01_static()["passed"] is True
    assert verify_gp085_synthesis_activation_gate_static()["passed"] is True


def test_min_jobs_target_formula() -> None:
    assert compute_min_synthesis_jobs_target_v1(eligible_scopes=10, max_scopes=4) == 4
    assert compute_min_synthesis_jobs_target_v1(eligible_scopes=2, max_scopes=32) == 2
    assert compute_min_synthesis_jobs_target_v1(eligible_scopes=0, max_scopes=32) == 0


def test_evaluate_schedule_phase_08_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "is_phase_08_pipeline_enabled_v1",
        lambda: False,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_synthesis_eligible_scopes_v1",
        lambda *_a, **_k: {"eligible_scopes": 5, "published_index_epoch": "ep-1"},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_recent_synthesis_forbidden_v1",
        lambda *_a, **_k: {"forbidden_backoff_active": False},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "explain_synthesis_eligibility_v1",
        lambda *_a, **_k: {"synthesis_ready": True, "blocked_by": []},
    )
    out = evaluate_synthesis_activation_schedule_v1(session, tenant_id=tid)
    assert out["should_activate"] is False
    assert out["activation_reason"] == "phase_08_disabled"
    assert out["must_run_phase_08"] is False


def test_evaluate_schedule_eligible_requires_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "is_phase_08_pipeline_enabled_v1",
        lambda: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_synthesis_eligible_scopes_v1",
        lambda *_a, **_k: {"eligible_scopes": 8, "published_index_epoch": "ep-1"},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_recent_synthesis_forbidden_v1",
        lambda *_a, **_k: {"forbidden_backoff_active": False},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "explain_synthesis_eligibility_v1",
        lambda *_a, **_k: {"synthesis_ready": True, "blocked_by": []},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_pipeline."
        "synthesis_pipeline_max_scopes_v1",
        lambda: 32,
    )
    out = evaluate_synthesis_activation_schedule_v1(session, tenant_id=tid)
    assert out["should_activate"] is True
    assert out["must_run_phase_08"] is True
    assert out["activation_reason"] == "eligible_scopes_require_phase_08"
    assert out["min_jobs_target"] == 8


def test_evaluate_schedule_forbidden_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "is_phase_08_pipeline_enabled_v1",
        lambda: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_synthesis_eligible_scopes_v1",
        lambda *_a, **_k: {"eligible_scopes": 3, "published_index_epoch": "ep-1"},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "count_recent_synthesis_forbidden_v1",
        lambda *_a, **_k: {
            "forbidden_backoff_active": True,
            "forbidden_count": 5,
            "forbidden_backoff_threshold": 3,
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.phase08_activation_gate."
        "explain_synthesis_eligibility_v1",
        lambda *_a, **_k: {"synthesis_ready": True, "blocked_by": []},
    )
    out = evaluate_synthesis_activation_schedule_v1(session, tenant_id=tid)
    assert out["should_activate"] is False
    assert out["activation_reason"] == "synthesis_forbidden_backoff"


def test_schedule_synthesis_activation_runs_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling."
        "evaluate_synthesis_activation_schedule_v1",
        lambda *_a, **_k: {"should_activate": True, "activation_reason": "test"},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling."
        "run_synthesis_activation_schedule_pass_v1",
        lambda *_a, **_k: {"gate_id": "G-P085-SYN-01", "jobs_enqueued": 0},
    )
    out = schedule_synthesis_activation_for_tenant_v1(
        tenant_id=tid,
        trigger=SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
        force=True,
    )
    assert out["scheduled"] is True
    assert out["path"] == "inline_execution_slice"
    assert "pass" in out


@pytest.mark.integration
def test_evaluate_synthesis_activation_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085syn-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 SYN",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    out = evaluate_synthesis_activation_schedule_v1(db_session, tenant_id=row.id)
    assert out["gate_id"] == GP085_SYN01_GATE_ID_V1
    assert out["eligible_scopes"] == 0
