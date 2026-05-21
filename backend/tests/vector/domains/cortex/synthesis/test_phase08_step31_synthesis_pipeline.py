"""Phase 08 Step 31 — substrate pipeline phase_08_synthesis."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.retrieval.retrieval_query_engine import index_tcre_chain_for_retrieval_v1
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1
from vector.domains.cortex.substrate_pipeline.repository import (
    complete_phase_v1,
    compute_pipeline_idempotency_key_v1,
    create_pipeline_run_v1,
    get_phase_run_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import (
    build_pipeline_synthesis_job_envelope_v1,
    materialize_synthesis_for_pipeline_v1,
    run_substrate_phase_08_synthesis_v1,
)
from vector.domains.cortex.synthesis.synthesis_publication import get_current_synthesis_publication_epoch_v1
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_substrate_pipeline_phase_order_includes_synthesis() -> None:
    assert SUBSTRATE_PIPELINE_PHASE_ORDER[-1] == PHASE_08_SYNTHESIS
    assert PHASE_07_RETRIEVAL in SUBSTRATE_PIPELINE_PHASE_ORDER
    assert len(SUBSTRATE_PIPELINE_PHASE_ORDER) == 7


def test_pipeline_idempotency_key_includes_phase_order_version() -> None:
    key = compute_pipeline_idempotency_key_v1(
        tenant_id=uuid.uuid4(),
        trigger_kind="post_ingestion",
    )
    assert len(key) == 64


def test_enqueue_next_at_synthesis_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _enqueue(**kwargs: object) -> dict[str, str]:
        calls.append(str(kwargs.get("phase_cursor")))
        return {"phase_id": str(kwargs.get("phase_cursor")), "path": "execution_slice"}

    monkeypatch.setattr(
        "vector.domains.cortex.execution.enqueue.enqueue_execution_slice_at_phase_v1",
        _enqueue,
    )
    out = enqueue_next_pipeline_phase_v1(
        tenant_id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        phase_id=PHASE_08_SYNTHESIS,
    )
    assert out["path"] == "execution_slice"
    assert calls == [PHASE_08_SYNTHESIS]


def _tenant(db_session: Session) -> uuid.UUID:
    user = User(email=f"u-{uuid.uuid4().hex[:8]}@example.com", full_name="P08 Pipeline User")
    tenant = Tenant(
        company_name="P08 Pipeline Tenant",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p08pipe-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:p08-pipe31",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


@pytest.mark.integration
def test_phase08_pipeline_materialize_and_publish(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED", "true")
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_pipeline.pipeline_default_workloads_v1",
        lambda **_: ["degradation_brief"],
    )
    from vector.settings import get_settings

    get_settings.cache_clear()

    tenant_id = _tenant(db_session)
    epoch = f"epoch-p08-{uuid.uuid4().hex[:6]}"
    entry = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=f"replay-{uuid.uuid4().hex[:8]}",
        traversal_epoch=epoch,
    )
    lookup_id = entry.retrieval_lookup_id
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant_id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"test-{uuid.uuid4().hex}",
    )
    complete_phase_v1(
        db_session,
        pipeline_run_id=run.id,
        phase_id=PHASE_07_RETRIEVAL,
        output={"published_index_epoch": epoch, "build_state": "PUBLISHED"},
    )
    db_session.flush()

    body = build_pipeline_synthesis_job_envelope_v1(
        tenant_id=tenant_id,
        pipeline_run_id=run.id,
        workload="degradation_brief",
        retrieval_lookup_id=lookup_id,
        published_index_epoch=epoch,
    )
    assert body["substrate_pipeline_run_id"] == str(run.id)

    pinned_body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {"retrieval_lookup_id": lookup_id},
        "retrieval_pins": {"index_epoch": epoch},
        "substrate_pipeline_run_id": str(run.id),
        "pinned_retrieval_receipt": {"retrieval_response": _legal_retrieval_stub()},
    }
    job_out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=pinned_body)
    assert job_out.get("artifact_id")

    def _execute_stub(
        session: Session,
        *,
        tenant_id: uuid.UUID,
        body: dict[str, object],
        job_id: uuid.UUID | None = None,
        _twin_inner: bool = False,
    ) -> dict[str, Any]:
        stub = dict(pinned_body)
        stub["idempotency_key"] = body.get("idempotency_key")
        return execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=stub)

    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_pipeline.execute_synthesis_job_envelope_v1",
        _execute_stub,
    )

    out = run_substrate_phase_08_synthesis_v1(
        db_session,
        tenant_id=tenant_id,
        pipeline_run_id=run.id,
    )
    assert out.get("synthesis_publication_epoch")
    assert out.get("jobs_completed", 0) >= 1
    phase08 = get_phase_run_v1(db_session, pipeline_run_id=run.id, phase_id=PHASE_08_SYNTHESIS)
    assert phase08 is not None
    assert phase08.status == "completed"
    assert get_current_synthesis_publication_epoch_v1(db_session, tenant_id=tenant_id)


@pytest.mark.integration
def test_phase08_empty_scope_publishes_documented_sd(db_session: Session) -> None:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        publish_retrieval_index_epoch_v1,
    )

    tenant_id = _tenant(db_session)
    epoch = f"epoch-empty-{uuid.uuid4().hex[:6]}"
    publish_retrieval_index_epoch_v1(db_session, tenant_id=tenant_id, index_epoch=epoch)
    run = create_pipeline_run_v1(
        db_session,
        tenant_id=tenant_id,
        trigger_kind="manual",
        bundle_id=None,
        idempotency_key=f"empty-{uuid.uuid4().hex}",
    )
    out = materialize_synthesis_for_pipeline_v1(
        db_session,
        tenant_id=tenant_id,
        pipeline_run_id=run.id,
        published_index_epoch=epoch,
    )
    assert out.get("scope_empty") is True
    assert out.get("synthesis_publication_epoch")
    assert "SD-SCOPE-EMPTY" in (out.get("sd_rollup") or {})
