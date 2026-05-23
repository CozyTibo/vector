"""P1-C — component-scoped retrieval materialization (largest eligible island)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_density import count_active_org_entities_v1
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    get_traversal_min_component_entities_v1,
    list_eligible_traversal_components_v1,
    stable_component_scope_id_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    derive_substrate_pipeline_replay_identity_v1,
)
from vector.domains.cortex.retrieval.retrieval_publish_contract import (
    RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
    begin_pipeline_retrieval_index_build_v1,
    finalize_pipeline_retrieval_index_build_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_GRAPH_DISCONNECTED_V1,
    normalize_retrieval_skip_reason_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1: Final[str] = "component"
RETRIEVAL_PROPAGATION_MODE_GLOBAL_V1: Final[str] = "global"
P1_C_ISLAND_SCOPE_KEY_V1: Final[str] = "island_scope_id"


def is_retrieval_component_scope_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_retrieval_component_scope_enabled)
    except Exception:  # noqa: BLE001
        return True


def get_retrieval_min_component_entities_v1() -> int:
    try:
        from vector.settings import get_settings

        cfg = get_settings()
        if hasattr(cfg, "cortex_retrieval_min_component_entities"):
            return max(1, int(cfg.cortex_retrieval_min_component_entities))
    except Exception:  # noqa: BLE001
        pass
    return get_traversal_min_component_entities_v1()


def select_largest_eligible_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> tuple[frozenset[uuid.UUID], dict[str, Any]]:
    """Pick largest authoritative connected component eligible for P1-C."""
    eligible = list_eligible_traversal_components_v1(
        session,
        tenant_id=tenant_id,
        min_entities=get_retrieval_min_component_entities_v1(),
    )
    if not eligible:
        return frozenset(), {
            "islands_eligible_count": 0,
            "largest_island_entity_count": 0,
            "island_scope_id": None,
        }
    island = max(eligible, key=len)
    scope_id = stable_component_scope_id_v1(island)
    return island, {
        "islands_eligible_count": len(eligible),
        "largest_island_entity_count": len(island),
        "island_scope_id": scope_id,
        "eligible_component_scope_ids": [
            stable_component_scope_id_v1(c) for c in eligible[:16]
        ],
    }


def walk_record_intersects_island_v1(
    record: Any,
    island: frozenset[uuid.UUID],
) -> bool:
    """True when walk start nodes lie in the island entity set."""
    payload = dict(getattr(record, "walk_payload", None) or {})
    blocks: list[dict[str, Any]] = []
    for key in ("walk_request", "request", "walk_result"):
        block = payload.get(key)
        if isinstance(block, dict):
            blocks.append(block)
    blocks.append(payload)
    for block in blocks:
        starts = block.get("start_node_ids")
        if not isinstance(starts, list):
            continue
        for sid in starts:
            try:
                if uuid.UUID(str(sid)) in island:
                    return True
            except ValueError:
                continue
    return False


def org_link_within_island_v1(link: CortexOrgLink, island: frozenset[uuid.UUID]) -> bool:
    return link.source_entity_id in island and link.target_entity_id in island


def _island_omission_summary_v1(
    *,
    island_scope_id: str,
    outside_island_scope_entity_count: int,
) -> dict[str, Any]:
    return {
        P1_C_ISLAND_SCOPE_KEY_V1: island_scope_id,
        "outside_island_scope_entity_count": outside_island_scope_entity_count,
        "retrieval_scope_law": "largest_eligible_island_v1",
    }


def materialize_retrieval_index_for_largest_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    max_tcre_jobs: int = 25,
) -> dict[str, Any]:
    """Materialize retrieval index entries scoped to the largest eligible island (P1-C)."""
    from vector.domains.cortex.execution.progression_status import (
        classify_retrieval_materialization_outcome_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        RetrievalGraphBindingError,
        materialize_retrieval_index_from_graph_ref_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_legality_projection import RetrievalLegalityError
    from vector.domains.cortex.retrieval.retrieval_materialization_diagnostics import (
        persist_retrieval_materialization_report_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_octs_binding import (
        RetrievalOctsBindingError,
        durable_row_from_walk_record_v1,
        materialize_retrieval_index_from_walk_v1,
    )
    from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
        RetrievalTcreBindingError,
        materialize_retrieval_index_from_tcre_job_v1,
    )
    from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1

    island, island_meta = select_largest_eligible_island_v1(session, tenant_id=tenant_id)
    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    outside_count = max(0, entity_count - len(island))
    island_scope_id = str(island_meta.get("island_scope_id") or "")
    omission_base = _island_omission_summary_v1(
        island_scope_id=island_scope_id,
        outside_island_scope_entity_count=outside_count,
    )

    replay = derive_substrate_pipeline_replay_identity_v1(
        tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
    )
    _, epoch_name = begin_pipeline_retrieval_index_build_v1(session, tenant_id=tenant_id)

    store = resolve_octs_walk_store_v1(session)
    walks_in_island = sum(
        1
        for record in store.list_walk_records_for_tenant_v1(tenant_id)
        if str(record.status) == "completed"
        and record.walk_payload
        and walk_record_intersects_island_v1(record, island)
    )
    links_in_island = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
                CortexOrgLink.source_entity_id.in_(island),
                CortexOrgLink.target_entity_id.in_(island),
            )
        )
        or 0
    )

    stats: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id),
        "index_epoch": epoch_name,
        "entries_materialized": 0,
        "skip_reasons": [],
        "tcre_candidates": 0,
        "walks_candidates": walks_in_island,
        "org_link_candidates": links_in_island,
        "retrieval_propagation_mode": RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
        "island_scope_id": island_scope_id,
        "island_entity_count": len(island),
        "outside_island_scope_entity_count": outside_count,
        "islands_eligible_count": island_meta.get("islands_eligible_count"),
        "largest_island_selected": True,
        "publish_contract_schema_version": RETRIEVAL_PUBLISH_CONTRACT_SCHEMA_VERSION,
        **island_meta,
    }

    if not island:
        stats["skip_reasons"].append(
            {
                "source": "island_scope",
                "code": RET_SKIP_GRAPH_DISCONNECTED_V1,
                "detail": "no_eligible_island_for_component_retrieval",
            }
        )
        stats["retrieval_outcome"] = "blocked_no_eligible_island"
        finalized = finalize_pipeline_retrieval_index_build_v1(
            session,
            tenant_id=tenant_id,
            index_epoch=epoch_name,
            pipeline_run_id=pipeline_run_id,
            sync_island_registry=False,
        )
        stats.update(finalized)
        stats["ok"] = False
        return stats

    prid = str(pipeline_run_id)
    walk_by_id = {
        record.walk_id: record for record in store.list_walk_records_for_tenant_v1(tenant_id)
    }
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(max(1, min(int(max_tcre_jobs), 50)))
        ).all()
    )
    stats["tcre_candidates"] = len(jobs)
    for job in jobs:
        scope = dict(job.scope_json or {})
        if str(scope.get("substrate_pipeline_run_id") or "") != prid:
            continue
        walk_raw = scope.get("octs_walk_id")
        if walk_raw:
            walk = walk_by_id.get(uuid.UUID(str(walk_raw)))
            if walk is None or not walk_record_intersects_island_v1(walk, island):
                continue
        try:
            out = materialize_retrieval_index_from_tcre_job_v1(
                session,
                tenant_id=tenant_id,
                job=job,
                replay_identity=replay,
                index_epoch=epoch_name,
                auto_publish=False,
            )
            stats["entries_materialized"] += len(out.get("materialized_lookup_ids") or [])
            stats["tcre_job_id"] = str(job.id)
            break
        except (RetrievalTcreBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append(
                {
                    "source": "tcre_job",
                    "code": getattr(exc, "code", str(exc)),
                    "island_scope_id": island_scope_id,
                }
            )

    for record in store.list_walk_records_for_tenant_v1(tenant_id):
        if str(record.status) != "completed" or not record.walk_payload:
            continue
        if not walk_record_intersects_island_v1(record, island):
            continue
        walk_replay = replay
        durable_row = durable_row_from_walk_record_v1(
            session, tenant_id=tenant_id, walk_id=record.walk_id
        )
        if durable_row is not None and durable_row.replay_identity:
            walk_replay = str(durable_row.replay_identity)
        try:
            materialize_retrieval_index_from_walk_v1(
                session,
                tenant_id=tenant_id,
                record=record,
                replay_identity=walk_replay,
                index_epoch=epoch_name,
                auto_publish=False,
                omission_summary=omission_base,
            )
            stats["entries_materialized"] += 1
        except (RetrievalOctsBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append(
                {
                    "source": "walk",
                    "walk_id": str(record.walk_id),
                    "code": normalize_retrieval_skip_reason_v1(getattr(exc, "code", str(exc))),
                    "island_scope_id": island_scope_id,
                }
            )

    for link in session.scalars(
        select(CortexOrgLink).where(
            CortexOrgLink.tenant_id == tenant_id,
            CortexOrgLink.revoked_at.is_(None),
            CortexOrgLink.source_entity_id.in_(island),
            CortexOrgLink.target_entity_id.in_(island),
        )
    ).all():
        if not org_link_within_island_v1(link, island):
            continue
        try:
            materialize_retrieval_index_from_graph_ref_v1(
                session,
                tenant_id=tenant_id,
                ref_kind="org_link_id",
                ref_value=str(link.id),
                replay_identity=replay,
                index_epoch=epoch_name,
                auto_publish=False,
                omission_summary=omission_base,
            )
            stats["entries_materialized"] += 1
        except (RetrievalGraphBindingError, RetrievalLegalityError) as exc:
            stats["skip_reasons"].append(
                {
                    "source": "org_link",
                    "org_link_id": str(link.id),
                    "code": getattr(exc, "code", str(exc)),
                    "island_scope_id": island_scope_id,
                }
            )

    finalized = finalize_pipeline_retrieval_index_build_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=epoch_name,
        pipeline_run_id=pipeline_run_id,
    )
    stats.update(finalized)
    stats["ok"] = bool(finalized.get("ok"))
    stats["retrieval_card_classification"] = classify_retrieval_materialization_outcome_v1(
        entries_materialized=int(stats.get("entries_materialized") or 0),
        entry_count=int(finalized.get("entry_count") or 0),
        tcre_candidates=int(stats.get("tcre_candidates") or 0),
        walks_candidates=walks_in_island,
        org_link_candidates=links_in_island,
    )
    persist_retrieval_materialization_report_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        stats=stats,
        tcre_candidates=int(stats.get("tcre_candidates") or 0),
        walks_candidates=walks_in_island,
        org_link_candidates=links_in_island,
    )
    return stats


def snapshot_retrieval_aa4_footprint_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str | None = None,
) -> dict[str, Any]:
    """AA4 partial — retrieval entry counts by UTC hour (optionally island-scoped)."""
    rows = list(
        session.scalars(
            select(CortexRetrievalIndexEntry).where(
                CortexRetrievalIndexEntry.tenant_id == tenant_id,
            )
        ).all()
    )
    if island_scope_id:
        rows = [
            r
            for r in rows
            if str((r.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == island_scope_id
        ]
    hours: dict[str, int] = {}
    for row in rows:
        created = row.created_at
        if created is None:
            continue
        hour_key = created.replace(minute=0, second=0, microsecond=0).isoformat()
        hours[hour_key] = hours.get(hour_key, 0) + 1
    return {
        "total_entries": len(rows),
        "distinct_created_hours": len(hours),
        "entries_by_hour": hours,
        "island_scope_id": island_scope_id,
    }


def evaluate_retrieval_component_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Evaluate whether P1-C largest-island retrieval law applies on tenant."""
    island, meta = select_largest_eligible_island_v1(session, tenant_id=tenant_id)
    aa4 = snapshot_retrieval_aa4_footprint_v1(
        session,
        tenant_id=tenant_id,
        island_scope_id=str(meta.get("island_scope_id") or "") or None,
    )
    return {
        "component_scope_enabled": is_retrieval_component_scope_enabled_v1(),
        "min_component_entities": get_retrieval_min_component_entities_v1(),
        "island_meta": meta,
        "island_entity_count": len(island),
        "aa4_footprint": aa4,
    }
