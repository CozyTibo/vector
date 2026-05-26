"""Phase 08 Step 31 — substrate pipeline ``phase_08_synthesis`` runner."""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SD_SCOPE_EMPTY_V1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    pipeline_default_workloads_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.phase_runner_receipt import (
    complete_phase_with_receipt_v1,
    fail_phase_with_receipt_v1,
    skip_phase_with_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    begin_phase_v1,
    get_phase_run_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import utc_now_iso_v1
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.settings import Settings, get_settings

__all__ = [
    "build_pipeline_synthesis_job_envelope_v1",
    "build_pipeline_synthesis_panel_v1",
    "execute_synthesis_job_envelope_v1",
    "materialize_synthesis_for_pipeline_v1",
    "run_substrate_phase_08_synthesis_v1",
    "synthesis_pipeline_max_scopes_v1",
]


def synthesis_pipeline_max_scopes_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    pack = load_synthesis_policy_pack_v1()
    pack_cap = int(pack.get("synthesis_pipeline_max_scopes_per_run") or 32)
    return min(int(cfg.cortex_synthesis_pipeline_max_scopes), pack_cap)


def build_pipeline_synthesis_job_envelope_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    workload: str,
    retrieval_lookup_id: str,
    published_index_epoch: str,
    synthesis_intent: str = "inspect",
    island_scope_id: str | None = None,
) -> dict[str, Any]:
    idem_payload: dict[str, Any] = {
        "pipeline_run_id": str(pipeline_run_id),
        "workload": workload,
        "retrieval_lookup_id": retrieval_lookup_id,
        "published_index_epoch": published_index_epoch,
    }
    if island_scope_id:
        idem_payload["island_scope_id"] = island_scope_id
    idem = hash_reasoning_canonical_json_sha256_v1(idem_payload)[:64]
    retrieval_scope: dict[str, Any] = {"retrieval_lookup_id": retrieval_lookup_id}
    if island_scope_id:
        retrieval_scope["island_scope_id"] = island_scope_id
    envelope: dict[str, Any] = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": workload,
        "synthesis_intent": synthesis_intent,
        "execution_partition": "authoritative",
        "retrieval_scope": retrieval_scope,
        "retrieval_pins": {"index_epoch": published_index_epoch},
        "substrate_pipeline_run_id": str(pipeline_run_id),
        "synthesis_policy_pack_id": DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
        "idempotency_key": f"pipe08-{idem}",
    }
    if island_scope_id:
        envelope["island_scope_id"] = island_scope_id
        envelope["synthesis_scope_law"] = "per_island_v1"
    return envelope


def iter_pipeline_synthesis_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    max_scopes: int,
    workloads: Sequence[str] | None = None,
) -> Iterator[dict[str, str]]:
    wl = list(workloads or pipeline_default_workloads_v1())
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry)
            .where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
                CortexRetrievalIndexEntry.index_epoch == published_index_epoch,
            )
            .order_by(CortexRetrievalIndexEntry.retrieval_lookup_id.asc())
        ).all()
    )
    count = 0
    for row in rows:
        for workload in wl:
            if count >= max_scopes:
                return
            yield {
                "retrieval_lookup_id": row.retrieval_lookup_id,
                "workload": workload,
            }
            count += 1


def _rollup_sd_codes_v1(job_results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for result in job_results:
        receipt = result.get("synthesis_job_receipt") or {}
        for row in receipt.get("synthesis_omission_rows") or []:
            if not isinstance(row, Mapping):
                continue
            code = str(row.get("sd_code") or row.get("synthesis_omission_class") or "").strip()
            if code:
                hist[code] = hist.get(code, 0) + 1
    return dict(sorted(hist.items()))


def materialize_synthesis_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    settings: Settings | None = None,
    epoch_scope_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run bounded pipeline synthesis via inline per-island path only (S4.2)."""
    from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
        maybe_reconcile_synthesis_jobs_on_materialize_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_per_island import (
        is_per_island_synthesis_enabled_v1,
        materialize_synthesis_per_island_v1,
    )
    from vector.domains.cortex.synthesis.synthesis_pipeline_path_v1 import (
        PIPELINE_SYNTHESIS_PATH_KIND_V1,
        SynthesisPipelinePathError,
    )

    cfg = settings or get_settings()
    if not is_per_island_synthesis_enabled_v1():
        raise SynthesisPipelinePathError(
            "synthesis_pipeline_per_island_required",
            detail={
                "pipeline_path_kind": PIPELINE_SYNTHESIS_PATH_KIND_V1,
                "rollback": "set CORTEX_SYNTHESIS_PER_ISLAND_ENABLED=1",
            },
        )

    job_reconcile = maybe_reconcile_synthesis_jobs_on_materialize_v1(
        session,
        tenant_id=tenant_id,
        settings=cfg,
    )
    out = materialize_synthesis_per_island_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        settings=cfg,
    )
    out = dict(out)
    out["pipeline_path_kind"] = PIPELINE_SYNTHESIS_PATH_KIND_V1
    if job_reconcile is not None:
        out["synthesis_job_reconcile"] = job_reconcile
    if epoch_scope_snapshot:
        out["synthesis_epoch_scope_alignment"] = epoch_scope_snapshot
        out["retrieval_entries_in_scope"] = int(
            epoch_scope_snapshot.get("retrieval_entries_in_scope")
            or out.get("retrieval_entries_in_scope")
            or 0
        )
    return out


def run_substrate_phase_08_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run: CortexSubstratePipelineRun | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Phase runner entry: PIPE-08-01 gate on phase 07 published index epoch."""
    cfg = settings or get_settings()
    prid = pipeline_run_id or (pipeline_run.id if pipeline_run is not None else None)
    if prid is None:
        msg = "pipeline_run_id_required"
        raise ValueError(msg)

    if not cfg.cortex_substrate_pipeline_phase_08_enabled:
        started_at = utc_now_iso_v1()
        return skip_phase_with_receipt_v1(
            session,
            pipeline_run_id=prid,
            phase_id=PHASE_08_SYNTHESIS,
            tenant_id=tenant_id,
            reason="phase_08_disabled",
            started_at=started_at,
            raw_output={"skipped": True, "reason": "phase_08_disabled"},
        )

    phase07 = get_phase_run_v1(session, pipeline_run_id=prid, phase_id=PHASE_07_RETRIEVAL)
    if phase07 is None or phase07.status != "completed":
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=prid,
            phase_id=PHASE_08_SYNTHESIS,
            tenant_id=tenant_id,
            raw_output={},
            started_at=utc_now_iso_v1(),
            error="phase_07_not_completed",
        )
        msg = "phase_07_not_completed"
        raise ValueError(msg)

    p07_out = dict(phase07.output_json or {})
    published = (
        p07_out.get("published_index_epoch")
        or p07_out.get("index_epoch")
        or get_published_index_epoch_v1(session, tenant_id=tenant_id)
    )
    if isinstance(published, str):
        published = published.strip() or None
    else:
        published = None

    from vector.domains.cortex.synthesis.phase08_activation_gate import (
        SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
        evaluate_synthesis_activation_schedule_v1,
    )

    activation_eval = evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        published_index_epoch=published,
        trigger=SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
    )
    if not activation_eval.get("should_activate"):
        reason = str(activation_eval.get("activation_reason") or "synthesis_not_activated")
        from vector.domains.cortex.substrate_pipeline.orchestrator import (
            finalize_pipeline_if_complete_v1,
        )

        fin = finalize_pipeline_if_complete_v1(session, pipeline_run_id=prid)
        raw = {
            "skipped": True,
            "reason": reason,
            "activation_evaluation": activation_eval,
            "activation_reason": reason,
            "finalize": fin,
        }
        return skip_phase_with_receipt_v1(
            session,
            pipeline_run_id=prid,
            phase_id=PHASE_08_SYNTHESIS,
            tenant_id=tenant_id,
            reason=reason,
            started_at=utc_now_iso_v1(),
            raw_output=raw,
        )

    begin_phase_v1(session, pipeline_run_id=prid, phase_id=PHASE_08_SYNTHESIS)
    started_at = utc_now_iso_v1()
    try:
        scope_snapshot: dict[str, Any] = {}
        if published:
            from vector.domains.cortex.synthesis.synthesis_epoch_scope_alignment_v1 import (
                ensure_retrieval_scope_for_synthesis_v1,
            )
            from vector.domains.cortex.synthesis.synthesis_retrieval_semantic_gate_v1 import (
                SynthesisRetrievalSemanticError,
                enforce_retrieval_semantic_before_synthesis_v1,
            )

            try:
                enforce_retrieval_semantic_before_synthesis_v1(
                    session,
                    tenant_id=tenant_id,
                    published_index_epoch=published,
                )
            except SynthesisRetrievalSemanticError as exc:
                fail_phase_with_receipt_v1(
                    session,
                    pipeline_run_id=prid,
                    phase_id=PHASE_08_SYNTHESIS,
                    tenant_id=tenant_id,
                    raw_output=dict(exc.detail or {}),
                    started_at=started_at,
                    error=str(exc.code),
                )
                return dict(exc.detail or {})
            scope_snapshot = ensure_retrieval_scope_for_synthesis_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=published,
            )

        out = materialize_synthesis_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            published_index_epoch=published,
            settings=cfg,
            epoch_scope_snapshot=scope_snapshot,
        )
        from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
            attach_phase08_empty_scope_truth_gate_v1,
            should_fail_phase08_for_empty_scope_violation_v1,
        )
        from vector.domains.cortex.synthesis.synthesis_epoch_scope_alignment_v1 import (
            attach_synthesis_epoch_scope_gate_v1,
            should_fail_phase08_for_epoch_scope_violation_v1,
        )

        if scope_snapshot:
            out = attach_synthesis_epoch_scope_gate_v1(out, scope_snapshot=scope_snapshot)
        out = attach_phase08_empty_scope_truth_gate_v1(
            session,
            tenant_id=tenant_id,
            materialize_output=out,
            published_index_epoch=published,
        )
        if should_fail_phase08_for_epoch_scope_violation_v1(out):
            fail_phase_with_receipt_v1(
                session,
                pipeline_run_id=prid,
                phase_id=PHASE_08_SYNTHESIS,
                tenant_id=tenant_id,
                raw_output=out,
                started_at=started_at,
                error=str(out.get("error_code") or "synthesis_epoch_scope_zero_in_scope"),
            )
            return out
        if should_fail_phase08_for_empty_scope_violation_v1(out):
            fail_phase_with_receipt_v1(
                session,
                pipeline_run_id=prid,
                phase_id=PHASE_08_SYNTHESIS,
                tenant_id=tenant_id,
                raw_output=out,
                started_at=started_at,
                error=str(out.get("error_code") or "phase08_empty_scope_with_retrieval_entries"),
            )
            return out
        if out.get("jobs_failed") and not out.get("artifact_digests"):
            fail_phase_with_receipt_v1(
                session,
                pipeline_run_id=prid,
                phase_id=PHASE_08_SYNTHESIS,
                tenant_id=tenant_id,
                raw_output=out,
                started_at=started_at,
                error="synthesis_pipeline_all_jobs_failed",
            )
            return out
        return complete_phase_with_receipt_v1(
            session,
            pipeline_run_id=prid,
            phase_id=PHASE_08_SYNTHESIS,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
            input_epoch=published,
        )
    except Exception as exc:  # noqa: BLE001
        from vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate import (
            SynthesisPerIslandMaterializeError,
        )

        if isinstance(exc, SynthesisPerIslandMaterializeError):
            raw_output: dict[str, Any] = {"error_code": exc.code, **exc.detail}
            fail_phase_with_receipt_v1(
                session,
                pipeline_run_id=prid,
                phase_id=PHASE_08_SYNTHESIS,
                tenant_id=tenant_id,
                raw_output=raw_output,
                started_at=started_at,
                error=str(exc.code),
            )
            return raw_output
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=prid,
            phase_id=PHASE_08_SYNTHESIS,
            tenant_id=tenant_id,
            raw_output={},
            started_at=started_at,
            error=str(exc),
        )
        raise


def build_pipeline_synthesis_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin surface #13 — phase 08 synthesis block on a substrate pipeline run."""
    phase08 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
    phase07 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    return {
        "surface_kind": "runtime_backed",
        "surface_id": "pipeline_synthesis_panel",
        "pipeline_run_id": str(pipeline_run_id),
        "phase_07_retrieval": {
            "status": phase07.status if phase07 else None,
            "output_json": dict(phase07.output_json or {}) if phase07 else {},
        },
        "phase_08_synthesis": {
            "status": phase08.status if phase08 else None,
            "output_json": dict(phase08.output_json or {}) if phase08 else {},
        },
        "published_index_epoch": get_published_index_epoch_v1(session, tenant_id=tenant_id),
    }
