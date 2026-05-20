"""Per-phase substrate pipeline execution (invoked from Celery)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.transform_runtime import (
    drain_stub_materialize_backlog,
    repair_tenant_materialization_oracle_determinism_drift,
    resolve_default_bundle_id_for_stub_transform,
)
from vector.domains.cortex.identity.continuity_rebuild import (
    finalize_identity_substrate_operator_audit,
    run_identity_handles_and_candidates_refresh,
    substrate_counts,
)
from vector.domains.cortex.identity.org_link_replay_runtime import execute_org_link_replay_job
from vector.domains.cortex.reasoning.runtime import enqueue_reconstruction_job_v1
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
)
from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_FAILED,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    begin_phase_v1,
    complete_phase_v1,
    fail_phase_v1,
    wait_phase_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_traversal_execution import (
    run_substrate_traversal_materialization_v1,
)
from vector.domains.cortex.traversal.tenant_verification_slice import (
    build_org_graph_traversal_verification_slice_v1,
    compute_octs_slice_hash_v1,
)
from vector.settings import Settings


def _resolve_bundle_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None,
) -> str | None:
    bid = (bundle_id or "").strip() or None
    if bid is not None:
        return bid
    return resolve_default_bundle_id_for_stub_transform(session, tenant_id)


def run_phase_02_canonical_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    bundle_id: str | None,
    batch_limit: int | None,
    pass_index: int = 0,
    pass_cooldowns: dict[str, datetime] | None = None,
    pass_stall_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_02_CANONICAL)
    bid = _resolve_bundle_id(session, tenant_id=tenant_id, bundle_id=bundle_id)
    if bid is None:
        out = {"skipped": True, "reason": "no_transformable_bundle"}
        complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_02_CANONICAL, output=out)
        return out
    lim_src = batch_limit if batch_limit is not None else settings.cortex_post_ingestion_canonical_batch_limit
    lim = max(1, min(int(lim_src), 2000))
    canonical_summary = drain_stub_materialize_backlog(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        connector=None,
        resource_type=None,
        batch_limit=lim,
        pass_index=pass_index,
        pass_cooldowns=pass_cooldowns,
        pass_stall_counts=pass_stall_counts,
    )
    outcome = str(canonical_summary.get("canonical_outcome") or "")
    repair_scan = min(5000, max(200, int(lim) * 4))
    determinism_repair = repair_tenant_materialization_oracle_determinism_drift(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        scan_limit=repair_scan,
        dry_run=False,
    )
    out = {
        "bundle_id": bid,
        "canonical_summary": canonical_summary,
        "canonical_outcome": outcome,
        "determinism_repair": determinism_repair,
        "pass_index_next": canonical_summary.get("pass_index_next"),
        "pass_cooldown_until": canonical_summary.get("pass_cooldown_until"),
        "pass_topology_stall_counts": canonical_summary.get("pass_topology_stall_counts"),
        "convergence_health": canonical_summary.get("convergence_health"),
    }
    if outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT and int(canonical_summary.get("total_succeeded") or 0) == 0:
        wait_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_02_CANONICAL,
            output=out,
            waiting_reason="topology_wait:parent_materialization_required",
        )
        return out
    if outcome == CANONICAL_OUTCOME_FAILED and int(canonical_summary.get("total_succeeded") or 0) == 0:
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_02_CANONICAL,
            error="canonical_materialization_failed",
            output=out,
        )
        return out
    complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_02_CANONICAL, output=out)
    return out


def run_phase_03_identity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    bundle_id: str | None,
    identity_substrate_trigger: str,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_03_IDENTITY)
    bid = _resolve_bundle_id(session, tenant_id=tenant_id, bundle_id=bundle_id)
    if bid is None:
        out = {"skipped": True, "reason": "no_bundle"}
        complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_03_IDENTITY, output=out)
        return out
    counts_before = substrate_counts(session, tenant_id=tenant_id)
    identity_continuity = run_identity_handles_and_candidates_refresh(
        session,
        tenant_id=tenant_id,
        dry_run=False,
        anchor_limit=5_000,
    )
    audit_report, audit_job_id = finalize_identity_substrate_operator_audit(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        substrate=identity_continuity,
        substrate_trigger=identity_substrate_trigger,
        counts_before=counts_before,
    )
    out = {
        "identity_continuity_substrate": identity_continuity,
        "identity_substrate_audit": audit_report,
        "identity_substrate_audit_replay_job_id": str(audit_job_id),
    }
    complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_03_IDENTITY, output=out)
    return out


def run_phase_04_graph_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_04_GRAPH)
    projection_job = execute_org_link_replay_job(
        session,
        tenant_id=tenant_id,
        job_kind="graph_projection_export",
    )
    session.flush()
    slice_body = build_org_graph_traversal_verification_slice_v1(
        session,
        tenant_id=tenant_id,
        verification_run_id=None,
    )
    slice_hash = compute_octs_slice_hash_v1(slice_body)
    proj_summary = dict(projection_job.summary_json or {})
    out = {
        "graph_projection_export_job_id": str(projection_job.id),
        "graph_projection_stable_hash_sha256": proj_summary.get("stable_hash_sha256"),
        "org_graph_traversal_verification_slice": slice_body,
        "org_graph_traversal_slice_hash": slice_hash,
    }
    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        schedule_graph_density_pass_v1,
    )

    promotion_schedule = schedule_graph_density_pass_v1(
        tenant_id=tenant_id,
        trigger="after_phase_04",
        pipeline_run_id=pipeline_run_id,
    )
    out["graph_density_promotion_schedule"] = promotion_schedule
    complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_04_GRAPH, output=out)
    return out


def run_phase_05_traversal_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    graph_projection_stable_hash: str | None = None,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_05_TRAVERSAL)
    try:
        out = run_substrate_traversal_materialization_v1(
            session,
            tenant_id=tenant_id,
            graph_projection_stable_hash=graph_projection_stable_hash,
        )
        from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
            TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
            schedule_octs_walks_for_tenant_v1,
        )

        traversal_schedule = schedule_octs_walks_for_tenant_v1(
            tenant_id=tenant_id,
            trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
            pipeline_run_id=pipeline_run_id,
            graph_projection_stable_hash=graph_projection_stable_hash,
        )
        out["octs_walk_schedule"] = traversal_schedule
        complete_phase_v1(
            session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_05_TRAVERSAL, output=out
        )
        return out
    except Exception as exc:  # noqa: BLE001
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_05_TRAVERSAL,
            error=str(exc),
        )
        raise


def run_phase_06_tcre_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    octs_walk_id: str | None = None,
) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE)
    p5 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_05_TRAVERSAL)
    walk_id = octs_walk_id
    if walk_id is None and p5 is not None:
        walk_id = (p5.output_json or {}).get("primary_octs_walk_id")

    scope: dict[str, Any] = {
        "substrate_pipeline_run_id": str(pipeline_run_id),
        "octs_strict_binding": False,
    }
    if walk_id:
        scope["octs_walk_id"] = str(walk_id)

    try:
        enqueue_out = enqueue_reconstruction_job_v1(
            session,
            tenant_id=tenant_id,
            scope=scope,
            dry_run=False,
            run_sync=False,
        )
        out = {**enqueue_out, "async": True}
        job_id_raw = enqueue_out.get("job_id")
        if job_id_raw:
            from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
                mark_pipeline_waiting_on_tcre_v1,
            )

            mark_pipeline_waiting_on_tcre_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                tcre_job_id=uuid.UUID(str(job_id_raw)),
                celery_task_id=str(enqueue_out.get("celery_task_id") or "") or None,
            )
        complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE, output=out)
        from vector.domains.cortex.operational_runtime.substrate_autonomous_progression import (
            enforce_phase06_progression_law_v1,
        )

        enforce_phase06_progression_law_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase06_output=out,
        )
        from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
            run_tcre_saturation_after_phase06_v1,
        )

        saturation_pass = run_tcre_saturation_after_phase06_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            octs_walk_id=str(walk_id) if walk_id else None,
            phase06_initial_job_enqueued=bool(job_id_raw),
        )
        out["tcre_saturation_pass"] = saturation_pass
        return out
    except Exception as exc:  # noqa: BLE001
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_06_TCRE,
            error=str(exc),
        )
        raise


def run_phase_07_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        get_published_index_epoch_v1,
    )

    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    try:
        out = materialize_retrieval_index_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
        published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
        if published:
            out = {**out, "published_index_epoch": published}
        complete_phase_v1(
            session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL, output=out
        )
        from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
            run_synthesis_activation_after_phase07_v1,
        )

        activation = run_synthesis_activation_after_phase07_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=out.get("published_index_epoch") or out.get("index_epoch"),
        )
        from vector.domains.cortex.operational_runtime.substrate_operational_progression import (
            PROGRESSION_TRIGGER_RETRIEVAL_PUBLISHED_V1,
            continue_substrate_operational_progression_v1,
        )

        progression = continue_substrate_operational_progression_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            trigger=PROGRESSION_TRIGGER_RETRIEVAL_PUBLISHED_V1,
        )
        return {
            **out,
            "synthesis_activation": activation,
            "next_phase_chain": activation.get("next_phase_chain"),
            "progression": progression,
        }
    except Exception as exc:  # noqa: BLE001
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_07_RETRIEVAL,
            error=str(exc),
        )
        raise


def run_phase_08_synthesis_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_pipeline import run_substrate_phase_08_synthesis_v1

    return run_substrate_phase_08_synthesis_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
    )
