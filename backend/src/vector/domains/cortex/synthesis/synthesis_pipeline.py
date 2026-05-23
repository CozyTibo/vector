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
    SD_PIPELINE_GAP_V1,
    SD_SCOPE_EMPTY_V1,
    build_synthesis_omission_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    pipeline_default_workloads_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import (
    compute_synthesis_job_envelope_digest_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_publication import publish_synthesis_epoch_v1
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
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.settings import Settings, get_settings


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
) -> dict[str, Any]:
    """Run bounded pipeline-default synthesis jobs and publish synthesis epoch."""
    from vector.domains.cortex.synthesis.synthesis_per_island import (
        is_per_island_synthesis_enabled_v1,
        materialize_synthesis_per_island_v1,
    )

    cfg = settings or get_settings()
    if is_per_island_synthesis_enabled_v1():
        return materialize_synthesis_per_island_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            settings=cfg,
        )
    index_epoch = published_index_epoch or get_published_index_epoch_v1(session, tenant_id=tenant_id)
    if not index_epoch:
        return {
            "published_index_epoch": None,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "artifact_digests": [],
            "synthesis_job_ids": [],
            "sd_rollup": {SD_SCOPE_EMPTY_V1: 1},
            "synthesis_publication_epoch": None,
            "scope_empty": True,
            "error_code": "no_published_index_epoch",
        }

    max_scopes = synthesis_pipeline_max_scopes_v1(settings=cfg)
    scopes = list(
        iter_pipeline_synthesis_scopes_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            max_scopes=max_scopes,
        )
    )
    job_results: list[dict[str, Any]] = []
    artifact_digests: list[str] = []
    job_ids: list[str] = []
    jobs_failed = 0

    if not scopes:
        pub = publish_synthesis_epoch_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            substrate_pipeline_run_id=pipeline_run_id,
            allow_empty_scope=True,
        )
        empty_out = {
            "published_index_epoch": index_epoch,
            "retrieval_epoch_pinned": index_epoch,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "artifact_digests": [],
            "synthesis_job_ids": [],
            "sd_rollup": {SD_SCOPE_EMPTY_V1: 1},
            "synthesis_publication_epoch": pub["synthesis_publication_epoch"],
            "scope_empty": True,
            "scopes_scheduled": 0,
            "scopes_overflow": False,
            "empty_scope_reason": "retrieval_empty",
            "workloads_applied": 0,
        }
        from vector.domains.cortex.synthesis.synthesis_activation_audit import (
            persist_synthesis_activation_audit_v1,
        )

        persist_synthesis_activation_audit_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            materialize_output=empty_out,
            scopes=[],
        )
        return empty_out

    workloads_applied = len({s.get("workload") for s in scopes if s.get("workload")})

    for scope in scopes:
        body = build_pipeline_synthesis_job_envelope_v1(
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            workload=scope["workload"],
            retrieval_lookup_id=scope["retrieval_lookup_id"],
            published_index_epoch=index_epoch,
        )
        try:
            out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
            job_results.append(out)
            if out.get("artifact_digest"):
                artifact_digests.append(str(out["artifact_digest"]))
            if out.get("job_id"):
                job_ids.append(str(out["job_id"]))
        except Exception as exc:  # noqa: BLE001
            jobs_failed += 1
            job_results.append(
                {
                    "error": str(exc)[:500],
                    "sd_code": SD_PIPELINE_GAP_V1,
                    "envelope_digest": compute_synthesis_job_envelope_digest_v1(body),
                }
            )

    artifact_ids: list[uuid.UUID] = []
    if job_ids:
        artifact_ids = [
            uuid.UUID(str(a))
            for a in session.scalars(
                select(CortexSynthesisArtifact.id).where(
                    CortexSynthesisArtifact.tenant_id == tenant_id,
                    CortexSynthesisArtifact.job_id.in_([uuid.UUID(j) for j in job_ids]),
                )
            ).all()
        ]
    sd_rollup = _rollup_sd_codes_v1(job_results)
    synthesis_publication_epoch: str | None = None
    artifacts_published = 0
    if not scopes:
        sd_rollup = {**sd_rollup, SD_SCOPE_EMPTY_V1: 1}
        pub = publish_synthesis_epoch_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            substrate_pipeline_run_id=pipeline_run_id,
            allow_empty_scope=True,
        )
        synthesis_publication_epoch = str(pub["synthesis_publication_epoch"])
        artifacts_published = int(pub["artifact_count"])
    elif artifact_ids:
        pub = publish_synthesis_epoch_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            substrate_pipeline_run_id=pipeline_run_id,
            artifact_ids=artifact_ids,
        )
        synthesis_publication_epoch = str(pub["synthesis_publication_epoch"])
        artifacts_published = int(pub["artifact_count"])
    elif jobs_failed:
        sd_rollup = {**sd_rollup, SD_PIPELINE_GAP_V1: jobs_failed}
    eligible = len(
        list(
            iter_pipeline_synthesis_scopes_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=index_epoch,
                max_scopes=10_000,
            )
        )
    )
    final_out = {
        "phase": PHASE_08_SYNTHESIS,
        "published_index_epoch": index_epoch,
        "retrieval_epoch_pinned": index_epoch,
        "jobs_completed": len(job_ids),
        "jobs_failed": jobs_failed,
        "artifact_digests": artifact_digests,
        "synthesis_job_ids": job_ids,
        "synthesis_publication_epoch": synthesis_publication_epoch,
        "artifacts_published": artifacts_published,
        "sd_rollup": sd_rollup,
        "sd_histogram": build_synthesis_omission_histogram_v1(),
        "scopes_scheduled": len(scopes),
        "scopes_overflow": eligible > max_scopes,
        "scope_empty": False,
        "workloads_applied": workloads_applied,
    }
    from vector.domains.cortex.synthesis.synthesis_activation_audit import (
        persist_synthesis_activation_audit_v1,
    )

    persist_synthesis_activation_audit_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        materialize_output=final_out,
        scopes=scopes,
    )
    return final_out


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
        out = materialize_synthesis_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            published_index_epoch=published,
            settings=cfg,
        )
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
