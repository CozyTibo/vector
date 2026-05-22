"""P0-B — continuity phase 05 proof evaluator (step 0.4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase05_proof import (
    evaluate_p0_b_phase05_proof_v1,
)
from vector.domains.cortex.substrate_pipeline.phase_runner_receipt import (
    complete_phase_with_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    create_pipeline_run_v1,
    get_phase_run_v1,
)
from vector.infrastructure.db.models.tenant import Tenant


@pytest.fixture
def tenant(db_session: Session) -> Tenant:
    slug = f"p0b-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P0B",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_evaluate_p0_b_passes_when_phase05_completed(db_session: Session, tenant: Tenant) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"test-{uuid.uuid4()}",
    )
    p04 = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=PHASE_04_GRAPH)
    assert p04 is not None
    p04.status = PHASE_STATUS_COMPLETED
    p04.completed_at = datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC)
    complete_phase_with_receipt_v1(
        db_session,
        pipeline_run_id=run.id,
        phase_id=PHASE_05_TRAVERSAL,
        tenant_id=tenant.id,
        raw_output={"walks_persisted": 2},
        started_at="2026-05-22T12:01:00Z",
    )
    db_session.flush()

    proof = evaluate_p0_b_phase05_proof_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
    )
    assert proof["checks"]["phase_05_status_completed"] is True
    assert proof["checks"]["walks_persisted_gt_0"] is True
    assert proof["checks"]["no_schema_path_error"] is True
    assert proof["p0_b_pass"] is True


def test_evaluate_p0_b_fails_on_schema_path_error(db_session: Session, tenant: Tenant) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="post_ingestion",
        bundle_id=None,
        idempotency_key=f"test-{uuid.uuid4()}",
    )
    p05 = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=PHASE_05_TRAVERSAL)
    assert p05 is not None
    p05.status = "failed"
    p05.error_detail = "Could not locate DOCS/cortex/05-traversal/schemas/octs-walk-policy-v1.schema.json"
    db_session.flush()

    proof = evaluate_p0_b_phase05_proof_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
    )
    assert proof["checks"]["no_schema_path_error"] is False
    assert proof["p0_b_pass"] is False
