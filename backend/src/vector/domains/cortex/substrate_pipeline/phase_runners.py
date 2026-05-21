"""Per-phase substrate pipeline execution (invoked from Celery)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.drain_runtime import drain_forward_progress_backlog
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.identity.continuity_rebuild import run_identity_substrate_projection_for_pipeline_v1
from vector.domains.cortex.identity.projection_export import run_graph_projection_export_for_pipeline_v1
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
    run_traversal_slice_for_pipeline_v1,
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
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_02_CANONICAL)
    bid = _resolve_bundle_id(session, tenant_id=tenant_id, bundle_id=bundle_id)
    if bid is None:
        out = {"skipped": True, "reason": "no_transformable_bundle"}
        complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_02_CANONICAL, output=out)
        return out
    lim_src = batch_limit if batch_limit is not None else settings.cortex_post_ingestion_canonical_batch_limit
    lim = max(1, min(int(lim_src), 2000))
    canonical_summary = drain_forward_progress_backlog(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        connector=None,
        resource_type=None,
        batch_limit=lim,
        settings=settings,
    )
    outcome = str(canonical_summary.get("canonical_outcome") or "")
    out = {
        "bundle_id": bid,
        "canonical_summary": canonical_summary,
        "canonical_outcome": outcome,
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
    out = run_identity_substrate_projection_for_pipeline_v1(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        substrate_trigger=identity_substrate_trigger,
        anchor_limit=5_000,
    )
    complete_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_03_IDENTITY, output=out)
    return out


def run_phase_04_graph_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_04_GRAPH)
    try:
        out = run_graph_projection_export_for_pipeline_v1(session, tenant_id=tenant_id)
    except ValueError as exc:
        fail_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_04_GRAPH,
            error=str(exc),
            output={},
        )
        raise
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
        out = run_traversal_slice_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            graph_projection_stable_hash=graph_projection_stable_hash,
        )
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
        return out
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
