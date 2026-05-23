"""Per-phase substrate pipeline execution (invoked from execution worker)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_FAILED,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
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
from vector.domains.cortex.substrate_pipeline.phase_runner_receipt import (
    complete_async_phase_with_receipt_v1,
    complete_phase_with_receipt_v1,
    fail_phase_with_receipt_v1,
    skip_phase_with_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    begin_phase_v1,
    get_phase_run_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_BLOCKED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_SKIPPED_BY_POLICY,
    utc_now_iso_v1,
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
    started_at = utc_now_iso_v1()
    bid = _resolve_bundle_id(session, tenant_id=tenant_id, bundle_id=bundle_id)
    if bid is None:
        out = {"skipped": True, "reason": "no_transformable_bundle"}
        return skip_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_02_CANONICAL,
            tenant_id=tenant_id,
            reason="no_transformable_bundle",
            started_at=started_at,
            raw_output=out,
        )
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
        return complete_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_02_CANONICAL,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
            outcome=PHASE_OUTCOME_BLOCKED,
            blocked_reason="topology_wait:parent_materialization_required",
            processed_count=0,
        )
    if outcome == CANONICAL_OUTCOME_FAILED and int(canonical_summary.get("total_succeeded") or 0) == 0:
        return fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_02_CANONICAL,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
            error="canonical_materialization_failed",
        )
    return complete_phase_with_receipt_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_02_CANONICAL,
        tenant_id=tenant_id,
        raw_output=out,
        started_at=started_at,
        input_epoch=bid,
    )


def run_phase_03_identity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    bundle_id: str | None,
    identity_substrate_trigger: str,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_03_IDENTITY)
    started_at = utc_now_iso_v1()
    bid = _resolve_bundle_id(session, tenant_id=tenant_id, bundle_id=bundle_id)
    if bid is None:
        out = {"skipped": True, "reason": "no_bundle"}
        return complete_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_03_IDENTITY,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
            outcome=PHASE_OUTCOME_COMPLETED_EMPTY,
        )
    out = run_identity_substrate_projection_for_pipeline_v1(
        session,
        tenant_id=tenant_id,
        bundle_id=bid,
        substrate_trigger=identity_substrate_trigger,
        anchor_limit=5_000,
    )
    return complete_phase_with_receipt_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_03_IDENTITY,
        tenant_id=tenant_id,
        raw_output=out,
        started_at=started_at,
        input_epoch=bid,
    )


def run_phase_04_graph_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_04_GRAPH)
    started_at = utc_now_iso_v1()
    try:
        out = run_graph_projection_export_for_pipeline_v1(session, tenant_id=tenant_id)
    except ValueError as exc:
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_04_GRAPH,
            tenant_id=tenant_id,
            raw_output={},
            started_at=started_at,
            error=str(exc),
        )
        raise
    from vector.domains.cortex.execution.execution_event_triggers import (
        trigger_graph_hash_walk_schedule_v1,
    )

    out["event_trigger_graph_hash"] = trigger_graph_hash_walk_schedule_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash=str(out.get("graph_projection_stable_hash_sha256") or "") or None,
        pipeline_run_id=pipeline_run_id,
    )
    return complete_phase_with_receipt_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_04_GRAPH,
        tenant_id=tenant_id,
        raw_output=out,
        started_at=started_at,
    )


def run_phase_05_traversal_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    graph_projection_stable_hash: str | None = None,
) -> dict[str, Any]:
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_05_TRAVERSAL)
    started_at = utc_now_iso_v1()
    try:
        out = run_traversal_slice_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            graph_projection_stable_hash=graph_projection_stable_hash,
        )
        return complete_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_05_TRAVERSAL,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
            input_epoch=graph_projection_stable_hash,
        )
    except Exception as exc:  # noqa: BLE001
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_05_TRAVERSAL,
            tenant_id=tenant_id,
            raw_output={},
            started_at=started_at,
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
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE)
    started_at = utc_now_iso_v1()
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
        complete_async_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_06_TCRE,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
        )
        from vector.domains.cortex.execution.phase06_contract import (
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
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_06_TCRE,
            tenant_id=tenant_id,
            raw_output={},
            started_at=started_at,
            error=str(exc),
        )
        raise


def run_phase_07_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.execution.progression_status import (
        classify_retrieval_materialization_outcome_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        get_published_index_epoch_v1,
    )

    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    started_at = utc_now_iso_v1()
    try:
        out = materialize_retrieval_index_for_pipeline_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
        published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
        if published:
            out = {**out, "published_index_epoch": published}
        if out.get("publish_contract_audit") is None and published:
            from vector.domains.cortex.retrieval.retrieval_publish_contract import (
                audit_published_epoch_entry_alignment_v1,
            )

            out = {
                **out,
                "publish_contract_audit": audit_published_epoch_entry_alignment_v1(
                    session,
                    tenant_id=tenant_id,
                    index_epoch=published,
                ),
            }
        if out.get("retrieval_entries_in_scope") is None and published:
            from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
                count_retrieval_entries_in_scope_v1,
                resolve_primary_island_scope_id_v1,
            )

            scope_id = str(out.get("island_scope_id") or "") or resolve_primary_island_scope_id_v1(
                session, tenant_id=tenant_id
            )[0]
            out = {
                **out,
                "retrieval_entries_in_scope": count_retrieval_entries_in_scope_v1(
                    session,
                    tenant_id=tenant_id,
                    published_index_epoch=published,
                    island_scope_id=scope_id,
                ),
            }
        ret_class = classify_retrieval_materialization_outcome_v1(
            entries_materialized=int(out.get("entries_materialized") or out.get("entry_count") or 0),
            entry_count=int(out.get("entry_count") or 0),
            tcre_candidates=int(out.get("tcre_candidates") or 0),
            walks_candidates=int(out.get("walks_candidates") or 0),
            org_link_candidates=int(out.get("org_link_candidates") or 0),
        )
        out["retrieval_outcome"] = ret_class
        if published and bool(out.get("ok")):
            from vector.domains.cortex.operational_runtime.execution_island_registry import (
                record_retrieval_publish_on_island_registry_v1,
            )

            registry_publish = record_retrieval_publish_on_island_registry_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=published,
                pipeline_run_id=pipeline_run_id,
            )
            out = {**out, "island_registry_publish": registry_publish}
            if out.get("island_registry_sync") is None:
                out["island_registry_sync"] = registry_publish
        return complete_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_07_RETRIEVAL,
            tenant_id=tenant_id,
            raw_output=out,
            started_at=started_at,
        )
    except Exception as exc:  # noqa: BLE001
        fail_phase_with_receipt_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_07_RETRIEVAL,
            tenant_id=tenant_id,
            raw_output={},
            started_at=started_at,
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
