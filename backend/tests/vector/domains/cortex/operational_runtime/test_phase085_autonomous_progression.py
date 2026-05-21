"""P085-06 — Autonomous phase progression (**G-P085-PROG-01**, **PIPE-085-01**)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_progression_gate import (
    verify_gp085_progression_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_progression import (
    GP085_PROG01_GATE_ID_V1,
    PIPE085_CHAIN_RULE_ID_V1,
    SubstrateProgressionError,
    assert_pipe085_chain_after_phase06_legal_v1,
    assert_tcre_completion_uses_resume_path_v1,
    build_autonomous_progression_catalog_v1,
    enforce_phase06_progression_law_v1,
    verify_gp085_prog01_progression_static,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_06_TCRE, PHASE_07_RETRIEVAL
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    on_tcre_job_completed_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1


def test_autonomous_progression_catalog_lists_laws() -> None:
    cat = build_autonomous_progression_catalog_v1()
    assert cat["primary_gate_id"] == GP085_PROG01_GATE_ID_V1
    assert cat["pipe_rule_id"] == PIPE085_CHAIN_RULE_ID_V1
    assert "PROG-TCRE-RESUME" in cat["progression_law_ids"]
    assert len(cat["progression_steps"]) == 6


def test_verify_gp085_prog01_static_passes() -> None:
    assert verify_gp085_prog01_progression_static()["passed"] is True
    assert verify_gp085_progression_gate_static()["passed"] is True


def test_tcre_pipeline_scope_requires_job_id_for_resume() -> None:
    with pytest.raises(SubstrateProgressionError) as exc:
        assert_tcre_completion_uses_resume_path_v1(
            has_tcre_job_id=False,
            pipeline_scope=True,
        )
    assert exc.value.code == "tcre_pipeline_resume_requires_job_id"


def test_chain_after_phase_v1_removed_from_orchestrator() -> None:
    import vector.domains.cortex.substrate_pipeline.orchestrator as orch

    assert not hasattr(orch, "chain_after_phase_v1")


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085prog-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Progression Tenant",
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
def test_pipe085_chain_after_phase06_requires_execution_lease_waiting(
    db_session: Session,
    tenant: Any,
) -> None:
    from vector.domains.cortex.execution.lease import mark_tenant_waiting_v1

    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085pipe-{uuid.uuid4().hex[:12]}",
    )
    with pytest.raises(SubstrateProgressionError) as exc:
        assert_pipe085_chain_after_phase06_legal_v1(
            db_session,
            tenant_id=tenant.id,
            pipeline_run_id=run.id,
        )
    assert exc.value.code == "pipe085_missing_execution_lease_after_phase06"

    mark_tenant_waiting_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_cursor=PHASE_07_RETRIEVAL,
        waiting_reason="tcre_async",
    )
    assert_pipe085_chain_after_phase06_legal_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
    )


@pytest.mark.integration
def test_enforce_phase06_progression_law_requires_async_job_output(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085p06-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    enforce_phase06_progression_law_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase06_output={"async": True, "job_id": str(job_id)},
    )


@pytest.mark.integration
def test_on_tcre_pipeline_scope_rejects_missing_job_id(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085tcre-{uuid.uuid4().hex[:12]}",
    )
    with pytest.raises(SubstrateProgressionError):
        on_tcre_job_completed_for_pipeline_v1(
            db_session,
            tenant_id=tenant.id,
            job_scope={"substrate_pipeline_run_id": str(run.id)},
            tcre_job_id=None,
        )


@pytest.mark.integration
def test_on_tcre_pipeline_uses_resume_path(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085resume-{uuid.uuid4().hex[:12]}",
    )
    job_id = uuid.uuid4()
    from vector.domains.cortex.execution.lease import mark_tenant_waiting_v1

    mark_tenant_waiting_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        phase_cursor=PHASE_07_RETRIEVAL,
        waiting_reason="tcre_async",
    )

    enqueue_calls: list[dict[str, object]] = []

    def _capture_enqueue(**kwargs: object) -> dict[str, str]:
        enqueue_calls.append(kwargs)
        return {"phase_id": PHASE_07_RETRIEVAL}

    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.orchestrator.enqueue_next_pipeline_phase_v1",
        _capture_enqueue,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.execution.tcre_resume.enqueue_tenant_convergence_v1",
        lambda *_a, **_k: {"enqueued": True},
    )
    out = on_tcre_job_completed_for_pipeline_v1(
        db_session,
        tenant_id=tenant.id,
        job_scope={"substrate_pipeline_run_id": str(run.id)},
        tcre_job_id=job_id,
        tcre_job_status="completed",
    )
    assert out is not None
    assert out.get("resumed") is True
    assert out.get("path") == "convergence_lease"
    assert enqueue_calls == []


