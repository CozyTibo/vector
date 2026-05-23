"""P2-D — per-island synthesis + global degradation brief (Phase 3 step 3.3)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    is_execution_island_registry_enabled_v1,
    list_execution_island_registry_v1,
    sync_execution_island_registry_v1,
)
from vector.domains.cortex.operational_runtime.graph_density import count_active_org_entities_v1
from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    P1_C_ISLAND_SCOPE_KEY_V1,
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
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_pipeline import (
    _rollup_sd_codes_v1,
    build_pipeline_synthesis_job_envelope_v1,
    synthesis_pipeline_max_scopes_v1,
)
from vector.domains.cortex.synthesis.synthesis_publication import publish_synthesis_epoch_v1
from vector.domains.cortex.synthesis.synthesis_job_envelope import (
    compute_synthesis_job_envelope_digest_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.infrastructure.db.models.cortex_execution_island_registry import (
    CortexExecutionIslandRegistry,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.settings import Settings, get_settings

P2_D_STEP: Final[str] = "3.3_p2d_per_island_synthesis"
P2_D_SYNTHESIS_SCOPE_LAW_V1: Final[str] = "per_island_v1"
GLOBAL_DEGRADATION_BRIEF_SURFACE_V1: Final[str] = "global_degradation_brief"
SYNTHESIS_OMISSION_OUTSIDE_ISLAND_SCOPE_V1: Final[str] = "outside_island_scope"


def is_per_island_synthesis_enabled_v1() -> bool:
    try:
        return bool(get_settings().cortex_synthesis_per_island_enabled)
    except Exception:  # noqa: BLE001
        return True


def synthesis_per_island_max_scopes_per_island_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return max(1, int(cfg.cortex_synthesis_per_island_max_scopes_per_island))


def _budget_scopes_per_island_v1(
    *,
    island_count: int,
    settings: Settings | None = None,
    max_scopes_override: int | None = None,
) -> int:
    if max_scopes_override is not None:
        return max(1, int(max_scopes_override))
    cfg = settings or get_settings()
    per_island_cap = synthesis_per_island_max_scopes_per_island_v1(settings=cfg)
    global_cap = synthesis_pipeline_max_scopes_v1(settings=cfg)
    shared = max(1, global_cap // max(1, island_count))
    return min(per_island_cap, shared)


def list_retrieval_entries_for_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
) -> list[CortexRetrievalIndexEntry]:
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
    return [
        row
        for row in rows
        if str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == island_scope_id
    ]


def iter_island_synthesis_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str,
    island_scope_id: str,
    max_scopes: int,
    workloads: Sequence[str] | None = None,
) -> Iterator[dict[str, str]]:
    wl = list(workloads or pipeline_default_workloads_v1())
    rows = list_retrieval_entries_for_island_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=published_index_epoch,
        island_scope_id=island_scope_id,
    )
    count = 0
    for row in rows:
        for workload in wl:
            if count >= max_scopes:
                return
            yield {
                "retrieval_lookup_id": row.retrieval_lookup_id,
                "workload": workload,
                "island_scope_id": island_scope_id,
            }
            count += 1


def build_global_degradation_brief_v1(
    *,
    tenant_entity_count: int,
    islands: Sequence[Mapping[str, Any]],
    island_results: Sequence[Mapping[str, Any]],
    published_index_epoch: str | None,
) -> dict[str, Any]:
    """Org-wide degradation summary: islands synthesized + documented outside-island omissions."""
    covered_entities = sum(int(i.get("entity_count") or 0) for i in islands)
    outside = max(0, int(tenant_entity_count) - covered_entities)
    result_by_scope = {
        str(r.get("island_scope_id") or ""): r for r in island_results if r.get("island_scope_id")
    }
    island_rows: list[dict[str, Any]] = []
    for island in islands:
        scope_id = str(island.get("island_scope_id") or "")
        result = dict(result_by_scope.get(scope_id) or {})
        entity_count = int(island.get("entity_count") or 0)
        island_rows.append(
            {
                "island_scope_id": scope_id,
                "entity_count": entity_count,
                "authoritative_edge_count": int(island.get("authoritative_edge_count") or 0),
                "retrieval_entries_in_scope": int(result.get("retrieval_entries_in_scope") or 0),
                "jobs_completed": int(result.get("jobs_completed") or 0),
                "jobs_failed": int(result.get("jobs_failed") or 0),
                "outside_island_scope_entity_count": max(0, int(tenant_entity_count) - entity_count),
                "synthesis_omission": SYNTHESIS_OMISSION_OUTSIDE_ISLAND_SCOPE_V1,
                "artifact_digests": list(result.get("artifact_digests") or []),
            }
        )
    synthesized = sum(1 for r in island_results if int(r.get("jobs_completed") or 0) > 0)
    return {
        "surface_kind": GLOBAL_DEGRADATION_BRIEF_SURFACE_V1,
        "schema_version": 1,
        "published_index_epoch": published_index_epoch,
        "tenant_entity_count": int(tenant_entity_count),
        "islands_eligible_count": len(islands),
        "islands_synthesized_count": synthesized,
        "outside_island_scope_entity_count": outside,
        "island_scope_key": P1_C_ISLAND_SCOPE_KEY_V1,
        "islands": island_rows,
    }


def record_island_synthesis_on_registry_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    island_scope_id: str,
    synthesis_job_ids: Sequence[str],
    artifact_digests: Sequence[str],
) -> None:
    if not is_execution_island_registry_enabled_v1():
        return
    row = session.scalar(
        select(CortexExecutionIslandRegistry).where(
            CortexExecutionIslandRegistry.tenant_id == tenant_id,
            CortexExecutionIslandRegistry.island_scope_id == island_scope_id,
        )
    )
    if row is None:
        return
    detail = dict(row.detail_json or {})
    detail["last_synthesis_at"] = datetime.now(UTC).isoformat()
    if synthesis_job_ids:
        detail["last_synthesis_job_id"] = str(synthesis_job_ids[-1])
    if artifact_digests:
        detail["last_synthesis_artifact_digest"] = str(artifact_digests[-1])
    detail["synthesis_scope_law"] = P2_D_SYNTHESIS_SCOPE_LAW_V1
    row.detail_json = detail
    session.flush()


def materialize_synthesis_per_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    settings: Settings | None = None,
    max_islands: int | None = None,
    max_scopes_per_island_override: int | None = None,
) -> dict[str, Any]:
    """Run bounded synthesis per execution island and publish a single synthesis epoch."""
    cfg = settings or get_settings()
    index_epoch = published_index_epoch or get_published_index_epoch_v1(session, tenant_id=tenant_id)
    if not index_epoch:
        return {
            "per_island_mode": True,
            "published_index_epoch": None,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "artifact_digests": [],
            "synthesis_job_ids": [],
            "sd_rollup": {SD_SCOPE_EMPTY_V1: 1},
            "synthesis_publication_epoch": None,
            "scope_empty": True,
            "error_code": "no_published_index_epoch",
            "global_degradation_brief": None,
        }

    if is_execution_island_registry_enabled_v1():
        sync_execution_island_registry_v1(session, tenant_id=tenant_id)
    islands = list_execution_island_registry_v1(session, tenant_id=tenant_id)
    if max_islands is not None and max_islands > 0:
        islands = islands[: int(max_islands)]

    tenant_entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    per_island_budget = _budget_scopes_per_island_v1(
        island_count=max(1, len(islands)),
        settings=cfg,
        max_scopes_override=max_scopes_per_island_override,
    )

    island_results: list[dict[str, Any]] = []
    job_results: list[dict[str, Any]] = []
    artifact_digests: list[str] = []
    job_ids: list[str] = []
    jobs_failed = 0
    scopes_scheduled = 0

    for island in islands:
        scope_id = str(island.get("island_scope_id") or "")
        if not scope_id:
            continue
        entries = list_retrieval_entries_for_island_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            island_scope_id=scope_id,
        )
        scopes = list(
            iter_island_synthesis_scopes_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=index_epoch,
                island_scope_id=scope_id,
                max_scopes=per_island_budget,
            )
        )
        scopes_scheduled += len(scopes)
        island_job_ids: list[str] = []
        island_artifacts: list[str] = []
        island_failed = 0

        for scope in scopes:
            body = build_pipeline_synthesis_job_envelope_v1(
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                workload=scope["workload"],
                retrieval_lookup_id=scope["retrieval_lookup_id"],
                published_index_epoch=index_epoch,
                island_scope_id=scope_id,
            )
            try:
                out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
                job_results.append(out)
                if out.get("artifact_digest"):
                    digest = str(out["artifact_digest"])
                    artifact_digests.append(digest)
                    island_artifacts.append(digest)
                if out.get("job_id"):
                    jid = str(out["job_id"])
                    job_ids.append(jid)
                    island_job_ids.append(jid)
            except Exception as exc:  # noqa: BLE001
                jobs_failed += 1
                island_failed += 1
                job_results.append(
                    {
                        "error": str(exc)[:500],
                        "sd_code": SD_PIPELINE_GAP_V1,
                        "envelope_digest": compute_synthesis_job_envelope_digest_v1(body),
                        "island_scope_id": scope_id,
                    }
                )

        record_island_synthesis_on_registry_v1(
            session,
            tenant_id=tenant_id,
            island_scope_id=scope_id,
            synthesis_job_ids=island_job_ids,
            artifact_digests=island_artifacts,
        )
        island_results.append(
            {
                "island_scope_id": scope_id,
                "entity_count": int(island.get("entity_count") or 0),
                "retrieval_entries_in_scope": len(entries),
                "scopes_scheduled": len(scopes),
                "jobs_completed": len(island_job_ids),
                "jobs_failed": island_failed,
                "artifact_digests": island_artifacts,
                "synthesis_job_ids": island_job_ids,
                "outside_island_scope_entity_count": max(
                    0, tenant_entity_count - int(island.get("entity_count") or 0)
                ),
            }
        )

    global_brief = build_global_degradation_brief_v1(
        tenant_entity_count=tenant_entity_count,
        islands=islands,
        island_results=island_results,
        published_index_epoch=index_epoch,
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
    scope_empty = scopes_scheduled == 0 and not islands

    if scope_empty:
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

    final_out = {
        "phase": PHASE_08_SYNTHESIS,
        "per_island_mode": True,
        "synthesis_scope_law": P2_D_SYNTHESIS_SCOPE_LAW_V1,
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
        "scopes_scheduled": scopes_scheduled,
        "scopes_per_island_budget": per_island_budget,
        "islands_processed": len(island_results),
        "island_results": island_results,
        "global_degradation_brief": global_brief,
        "scope_empty": scope_empty,
        "outside_island_scope_entity_count": global_brief.get("outside_island_scope_entity_count"),
    }

    from vector.domains.cortex.synthesis.synthesis_activation_audit import (
        persist_synthesis_activation_audit_v1,
    )

    persist_synthesis_activation_audit_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        materialize_output=final_out,
        scopes=[
            {"island_scope_id": r.get("island_scope_id"), "workload": "per_island_bundle"}
            for r in island_results
        ],
    )
    return final_out


def build_per_island_synthesis_inspect_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin inspect block for P2-D per-island synthesis."""
    index_epoch = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    islands = list_execution_island_registry_v1(session, tenant_id=tenant_id)
    tenant_entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    island_previews: list[dict[str, Any]] = []
    for island in islands[:8]:
        scope_id = str(island.get("island_scope_id") or "")
        entries = (
            list_retrieval_entries_for_island_v1(
                session,
                tenant_id=tenant_id,
                published_index_epoch=index_epoch,
                island_scope_id=scope_id,
            )
            if index_epoch and scope_id
            else []
        )
        detail = dict(island.get("detail_json") or {})
        island_previews.append(
            {
                "island_scope_id": scope_id,
                "entity_count": int(island.get("entity_count") or 0),
                "retrieval_entries_in_scope": len(entries),
                "last_synthesis_job_id": detail.get("last_synthesis_job_id"),
                "last_synthesis_at": detail.get("last_synthesis_at"),
                "last_synthesis_artifact_digest": detail.get("last_synthesis_artifact_digest"),
            }
        )
    covered = sum(int(i.get("entity_count") or 0) for i in islands)
    return {
        "surface_kind": "per_island_synthesis",
        "per_island_enabled": is_per_island_synthesis_enabled_v1(),
        "synthesis_scope_law": P2_D_SYNTHESIS_SCOPE_LAW_V1,
        "published_index_epoch": index_epoch,
        "tenant_entity_count": tenant_entity_count,
        "island_count": len(islands),
        "outside_island_scope_entity_count": max(0, tenant_entity_count - covered),
        "islands": island_previews,
    }
