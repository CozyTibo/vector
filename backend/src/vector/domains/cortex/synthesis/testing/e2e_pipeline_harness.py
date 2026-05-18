"""Sync substrate pipeline runner through phase 08 synthesis (E2E)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.testing.e2e_pipeline_harness import (
    run_substrate_pipeline_sync_through_retrieval_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.domains.cortex.synthesis.synthesis_publication import (
    get_current_synthesis_publication_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import run_substrate_phase_08_synthesis_v1
from vector.settings import get_settings


def run_substrate_pipeline_sync_through_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    synthesis_execute_stub: Any | None = None,
) -> dict[str, Any]:
    """Run phases 02–08 synchronously (phase 08 optional when disabled in settings)."""
    pipeline = run_substrate_pipeline_sync_through_retrieval_v1(
        session,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
    out: dict[str, Any] = {
        **pipeline,
        "synthesis_phase_id": PHASE_08_SYNTHESIS,
    }
    if pipeline.get("skipped"):
        return {**out, "synthesis_skipped": True}

    cfg = get_settings()
    if not cfg.cortex_substrate_pipeline_phase_08_enabled:
        out["synthesis_skipped"] = True
        out["synthesis_skip_reason"] = "phase_08_disabled"
        return out

    if synthesis_execute_stub is not None:
        import vector.domains.cortex.synthesis.synthesis_pipeline as syn_pipe

        original = syn_pipe.execute_synthesis_job_envelope_v1  # type: ignore[attr-defined]
        syn_pipe.execute_synthesis_job_envelope_v1 = synthesis_execute_stub  # type: ignore[attr-defined]
        try:
            syn_out = run_substrate_phase_08_synthesis_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=uuid.UUID(str(pipeline["pipeline_run_id"])),
            )
        finally:
            syn_pipe.execute_synthesis_job_envelope_v1 = original  # type: ignore[attr-defined]
    else:
        syn_out = run_substrate_phase_08_synthesis_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=uuid.UUID(str(pipeline["pipeline_run_id"])),
        )

    phase08 = get_phase_run_v1(
        session,
        pipeline_run_id=uuid.UUID(str(pipeline["pipeline_run_id"])),
        phase_id=PHASE_08_SYNTHESIS,
    )
    out["phases"] = dict(pipeline.get("phases") or {})
    out["phases"][PHASE_08_SYNTHESIS] = syn_out
    out["synthesis_output"] = syn_out
    out["synthesis_publication_epoch"] = syn_out.get("synthesis_publication_epoch") or (
        get_current_synthesis_publication_epoch_v1(session, tenant_id=tenant_id)
    )
    out["phase_08_status"] = phase08.status if phase08 else None
    return out


def build_synthesis_pipeline_execute_stub_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str,
    retrieval_lookup_id: str,
    pinned_retrieval_response: Mapping[str, Any],
    workload: str = "degradation_brief",
) -> Any:
    """Factory for pinned-retrieval synthesis execute stub (stable E2E without live retrieval)."""
    from vector.domains.cortex.synthesis.synthesis_job_contract import (
        SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
    )
    from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1

    template: dict[str, Any] = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": workload,
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {"retrieval_lookup_id": retrieval_lookup_id},
        "retrieval_pins": {"index_epoch": published_index_epoch},
        "substrate_pipeline_run_id": str(pipeline_run_id),
        "pinned_retrieval_receipt": {"retrieval_response": dict(pinned_retrieval_response)},
    }

    def _stub(
        session: Session,
        *,
        tenant_id: uuid.UUID,
        body: Mapping[str, Any],
        job_id: uuid.UUID | None = None,
        _twin_inner: bool = False,
    ) -> dict[str, Any]:
        merged = dict(template)
        if body.get("idempotency_key"):
            merged["idempotency_key"] = body["idempotency_key"]
        if body.get("synthesis_workload_class"):
            merged["synthesis_workload_class"] = body["synthesis_workload_class"]
        if body.get("retrieval_scope"):
            merged["retrieval_scope"] = dict(body["retrieval_scope"])
        if body.get("retrieval_pins"):
            merged["retrieval_pins"] = dict(body["retrieval_pins"])
        return execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=merged, job_id=job_id)

    return _stub
