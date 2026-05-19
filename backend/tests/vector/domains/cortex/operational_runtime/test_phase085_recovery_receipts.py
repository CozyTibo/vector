"""P085-08 — Replay-safe recovery receipts (**G-P085-REC-01**)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_recovery_receipt_gate import (
    verify_gp085_recovery_receipt_gate_static,
)
from vector.domains.cortex.operational_runtime.recovery_receipts import (
    GP085_REC01_GATE_ID_V1,
    RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
    RECOVERY_RECEIPT_DIGEST_FIELD_V1,
    RECOVERY_RECEIPT_OUTCOME_RECOVERED,
    RECOVERY_RECEIPT_OUTCOME_SKIPPED,
    RecoveryReceiptError,
    assert_recovery_receipt_contract_v1,
    build_recovery_receipt_catalog_v1,
    build_recovery_receipt_v1,
    list_recovery_receipts_v1,
    normalize_stalled_recovery_action_v1,
    persist_recovery_receipt_v1,
    verify_gp085_rec01_static,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    mark_pipeline_waiting_on_tcre_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import create_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
    recover_stalled_pipeline_v1,
)


def test_recovery_receipt_catalog() -> None:
    cat = build_recovery_receipt_catalog_v1()
    assert cat["primary_gate_id"] == GP085_REC01_GATE_ID_V1
    assert "resume_phase_07" in cat["recovery_receipt_action_ids"]
    assert cat["storage_path"] == "continuation.detail_json.recovery_receipts[]"


def test_verify_gp085_rec01_static_passes() -> None:
    assert verify_gp085_rec01_static()["passed"] is True
    assert verify_gp085_recovery_receipt_gate_static()["passed"] is True


def test_recovery_receipt_digest_is_deterministic() -> None:
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    r1 = build_recovery_receipt_v1(
        tenant_id=tid,
        pipeline_run_id=prid,
        action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
        continuation_nonce="nonce-abc",
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        prior_resume_receipt_hash=None,
        recorded_at="2026-05-18T00:00:00+00:00",
    )
    r2 = build_recovery_receipt_v1(
        tenant_id=tid,
        pipeline_run_id=prid,
        action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
        continuation_nonce="nonce-abc",
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        prior_resume_receipt_hash=None,
        recorded_at="2026-05-18T00:00:00+00:00",
    )
    assert r1[RECOVERY_RECEIPT_DIGEST_FIELD_V1] == r2[RECOVERY_RECEIPT_DIGEST_FIELD_V1]
    assert_recovery_receipt_contract_v1(r1)


def test_invalid_action_rejected() -> None:
    with pytest.raises(RecoveryReceiptError):
        build_recovery_receipt_v1(
            tenant_id=uuid.uuid4(),
            pipeline_run_id=uuid.uuid4(),
            action="not_allowed",
            continuation_nonce="n",
            outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        )


def test_normalize_stalled_action() -> None:
    assert (
        normalize_stalled_recovery_action_v1("auto", reason="phase_06_re_enqueued")
        == "replay_phase_06"
    )
    assert (
        normalize_stalled_recovery_action_v1("auto", reason="phase_07_already_complete")
        == "resume_phase_07"
    )


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085rec-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Receipt Tenant",
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
def test_persist_recovery_receipt_on_continuation(
    db_session: Session,
    tenant: Any,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085rec-{uuid.uuid4().hex[:12]}",
    )
    cont = mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    receipt = persist_recovery_receipt_v1(
        db_session,
        continuation=cont,
        action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
        outcome=RECOVERY_RECEIPT_OUTCOME_SKIPPED,
        extra={"test": True},
    )
    assert receipt["action"] == RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07
    stored = list_recovery_receipts_v1(cont)
    assert len(stored) == 1
    assert stored[0][RECOVERY_RECEIPT_DIGEST_FIELD_V1] == receipt[RECOVERY_RECEIPT_DIGEST_FIELD_V1]


@pytest.mark.integration
def test_recover_stalled_pipeline_persists_receipt(
    db_session: Session,
    tenant: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant.id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"p085stall-{uuid.uuid4().hex[:12]}",
    )
    mark_pipeline_waiting_on_tcre_v1(
        db_session,
        tenant_id=tenant.id,
        pipeline_run_id=run.id,
        tcre_job_id=uuid.uuid4(),
    )
    phase07 = MagicMock()
    phase07.status = "completed"
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery.get_phase_run_v1",
        lambda *_a, **_k: phase07,
    )

    out = recover_stalled_pipeline_v1(db_session, pipeline_run_id=run.id, action="auto")
    assert out.get("recovery_receipt") is not None
    assert out["recovery_receipt"]["outcome"] == RECOVERY_RECEIPT_OUTCOME_RECOVERED
