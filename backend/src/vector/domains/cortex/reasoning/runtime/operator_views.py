"""RUNTIME-02 — compose operator projections from persisted job artifacts."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.reasoning.runtime.causal_edge_explanation_projection import (
    project_causal_edge_explanation_v1,
)
from vector.domains.cortex.reasoning.runtime.chain_timeline_projection import (
    build_chain_timeline_v1,
)
from vector.domains.cortex.reasoning.runtime.chronology_explanation_projection import (
    chronology_projection_rule_id_v1,
    project_chronology_explanation_v1,
)
from vector.domains.cortex.reasoning.runtime.degradation_explanation_projection import (
    explain_chronology_degradation_v1,
    explain_edge_legality_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    TCRE_RUNTIME_ENGINE_BUILD_REF,
    TCRE_RUNTIME_SCHEMA_VERSION,
    _compare_in_memory_replay_twin_v1,
    _run_reconstruction_pipeline_in_memory_v1,
)
from vector.domains.cortex.reasoning.runtime.replay_diff_projection import build_replay_diff_v1
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

TCRE_OPERATOR_VIEW_SCHEMA_VERSION: Final[int] = 1
_REPLAY_POSTURE: Final[str] = "replay_safe_reasoning_posture_v1"


def _load_materializations_by_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    mat_ids: list[str],
) -> dict[str, CortexCanonicalTransformMaterialization]:
    if not mat_ids:
        return {}
    uuids = [uuid.UUID(x) for x in mat_ids]
    rows = list(
        db.scalars(
            select(CortexCanonicalTransformMaterialization).where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.id.in_(uuids),
            )
        ).all()
    )
    return {str(m.id): m for m in rows}


def _reconstruct_rows_from_artifacts(
    job: CortexTcreReconstructionJob,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    chronology: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    chain: dict[str, Any] | None = None
    for art in job.artifacts:
        if art.artifact_kind == "chronology_receipt":
            body = dict(art.body_json or {})
            chronology.append(
                {
                    "materialization_id": art.artifact_key,
                    "snapshot": body.get("snapshot") or {},
                    "chronology_legality_class": body.get("chronology_legality_class"),
                    "matched_projection_row_index": (body.get("receipt_body") or {}).get(
                        "matched_projection_row_index", 0
                    ),
                    "partitioned_exception_applied": (body.get("receipt_body") or {}).get(
                        "partitioned_exception_applied", False
                    ),
                    "receipt_body": body.get("receipt_body") or {},
                    "receipt_digest": art.artifact_digest,
                }
            )
        elif art.artifact_kind == "causal_edge":
            eb = dict(art.body_json or {})
            parent_ids = list(eb.get("parent_artifact_ids") or [])
            from_id = ""
            to_id = ""
            for pid in parent_ids:
                if pid.startswith("mat:"):
                    if not from_id:
                        from_id = pid[4:]
                    else:
                        to_id = pid[4:]
            edges.append(
                {
                    "tcre_causal_edge_id": art.artifact_key,
                    "edge_body": eb,
                    "from_materialization_id": from_id,
                    "to_materialization_id": to_id,
                }
            )
        elif art.artifact_kind == "causal_chain":
            chain = dict(art.body_json or {})
            chain["causal_chain_id"] = art.artifact_key
    chronology.sort(key=lambda r: str(r.get("materialization_id") or ""))
    edges.sort(key=lambda r: str(r.get("tcre_causal_edge_id") or ""))
    return chronology, edges, chain


def build_reconstruction_summary_v1(
    *,
    materialization_count: int,
    chronology_explanations: Sequence[Mapping[str, Any]],
    edge_explanations: Sequence[Mapping[str, Any]],
    degradation_explanations: Sequence[Mapping[str, Any]],
    replay_result: str,
    policy_pack_id: str,
    policy_digest: str,
    engine_build_ref: str,
    duration_seconds: float | None,
) -> dict[str, Any]:
    strict = sum(1 for c in chronology_explanations if c.get("chronology_legality_class") == "chronology_strict")
    degraded = sum(
        1 for c in chronology_explanations if c.get("chronology_legality_class") == "chronology_degraded"
    )
    edge_by_kind: dict[str, int] = {}
    for e in edge_explanations:
        k = str(e.get("tcre_causal_edge_kind") or "unknown")
        edge_by_kind[k] = edge_by_kind.get(k, 0) + 1
    return {
        "materializations_processed": materialization_count,
        "chronology_strict_count": strict,
        "chronology_degraded_count": degraded,
        "chronology_other_count": len(chronology_explanations) - strict - degraded,
        "edge_counts_by_kind": dict(sorted(edge_by_kind.items())),
        "degradation_explanation_count": len(degradation_explanations),
        "replay_result": replay_result,
        "policy_pack_id": policy_pack_id,
        "policy_digest": policy_digest,
        "engine_build_ref": engine_build_ref,
        "runtime_duration_seconds": duration_seconds,
    }


def build_job_operator_view_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any] | None:
    job = db.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.id == job_id,
            CortexTcreReconstructionJob.tenant_id == tenant_id,
        )
        .options(selectinload(CortexTcreReconstructionJob.artifacts))
    )
    if job is None:
        return None

    chronology_rows, edge_rows, chain = _reconstruct_rows_from_artifacts(job)
    mat_ids = [str(r["materialization_id"]) for r in chronology_rows]
    for e in edge_rows:
        mat_ids.append(str(e.get("from_materialization_id") or ""))
        mat_ids.append(str(e.get("to_materialization_id") or ""))
    mats = _load_materializations_by_ids(db, tenant_id=tenant_id, mat_ids=list({x for x in mat_ids if x}))

    policy_digest = job.tcre_policy_bundle_digest
    chronology_explanations: list[dict[str, Any]] = []
    chronology_by_mat: dict[str, dict[str, Any]] = {}
    degradation_explanations: list[dict[str, Any]] = []

    for row in chronology_rows:
        mid = str(row["materialization_id"])
        mat = mats.get(mid)
        snap = dict(row.get("snapshot") or {})
        idx = int(row.get("matched_projection_row_index") or 0)
        partitioned = bool(row.get("partitioned_exception_applied"))
        rule_id = chronology_projection_rule_id_v1(
            matched_projection_row_index=idx,
            partitioned=partitioned,
        )
        expl = project_chronology_explanation_v1(
            materialization_id=mid,
            canonical_object_kind=mat.canonical_object_kind if mat else None,
            bundle_id=mat.bundle_id if mat else snap.get("bundle_id"),
            occurred_at_iso=mat.occurred_at.isoformat() if mat and mat.occurred_at else None,
            observed_at_iso=mat.observed_at.isoformat() if mat and mat.observed_at else None,
            chronology_row=row,
            tcre_policy_bundle_digest=policy_digest,
            replay_posture=_REPLAY_POSTURE,
        )
        chronology_explanations.append(expl)
        chronology_by_mat[mid] = expl
        deg = explain_chronology_degradation_v1(
            materialization_id=mid,
            chronology_legality_class=str(expl.get("chronology_legality_class") or ""),
            projection_rule_id=rule_id,
            skew_detected=bool(snap.get("skew_detected")),
            late_arrival=bool(snap.get("late_arrival")),
        )
        if deg:
            degradation_explanations.append(deg)

    edge_explanations: list[dict[str, Any]] = []
    for er in edge_rows:
        from_id = str(er.get("from_materialization_id") or "")
        to_id = str(er.get("to_materialization_id") or "")
        from_chr = chronology_by_mat.get(from_id) or {}
        to_chr = chronology_by_mat.get(to_id) or {}
        fm = mats.get(from_id)
        tm = mats.get(to_id)
        ee = project_causal_edge_explanation_v1(
            edge_row=er,
            from_kind=fm.canonical_object_kind if fm else None,
            to_kind=tm.canonical_object_kind if tm else None,
            from_chronology_class=str(from_chr.get("chronology_legality_class") or "") or None,
            to_chronology_class=str(to_chr.get("chronology_legality_class") or "") or None,
            tcre_policy_bundle_digest=policy_digest,
            replay_posture=_REPLAY_POSTURE,
        )
        edge_explanations.append(ee)
        eb = dict(er.get("edge_body") or {})
        edge_deg = explain_edge_legality_v1(
            tcre_causal_edge_id=str(ee.get("tcre_causal_edge_id") or ""),
            causal_legality_class=str(eb.get("causal_legality_class") or ""),
            derivation_rule_id=str(eb.get("derivation_rule_id") or ""),
        )
        if edge_deg:
            degradation_explanations.append(edge_deg)

    timeline = build_chain_timeline_v1(
        chain=chain,
        edge_explanations=edge_explanations,
        chronology_by_mat_id=chronology_by_mat,
        tcre_policy_bundle_digest=policy_digest,
        replay_posture=_REPLAY_POSTURE,
    )

    duration: float | None = None
    if job.started_at and job.completed_at:
        duration = (job.completed_at - job.started_at).total_seconds()

    replay_result = str((job.summary_json or {}).get("replay_equivalence_passed", job.status))
    summary = build_reconstruction_summary_v1(
        materialization_count=len(chronology_explanations),
        chronology_explanations=chronology_explanations,
        edge_explanations=edge_explanations,
        degradation_explanations=degradation_explanations,
        replay_result=replay_result,
        policy_pack_id=job.reasoning_rule_pack_id,
        policy_digest=policy_digest,
        engine_build_ref=job.engine_build_ref or TCRE_RUNTIME_ENGINE_BUILD_REF,
        duration_seconds=duration,
    )

    replay_diff: dict[str, Any] | None = None
    if job.job_kind == "replay_twin" and job.status in ("completed", "failed"):
        parent_id = job.parent_job_id
        if parent_id:
            parent = db.get(CortexTcreReconstructionJob, parent_id)
            if parent:
                run_a = _run_reconstruction_pipeline_in_memory_v1(
                    db,
                    tenant_id=tenant_id,
                    scope=parent.scope_json,
                    tcre_policy_bundle_digest=parent.tcre_policy_bundle_digest,
                    reasoning_rule_pack_id=parent.reasoning_rule_pack_id,
                )
                run_b = _run_reconstruction_pipeline_in_memory_v1(
                    db,
                    tenant_id=tenant_id,
                    scope=parent.scope_json,
                    tcre_policy_bundle_digest=parent.tcre_policy_bundle_digest,
                    reasoning_rule_pack_id=parent.reasoning_rule_pack_id,
                )
                replay_diff = build_replay_diff_v1(
                    run_a,
                    run_b,
                    policy_digest_a=parent.tcre_policy_bundle_digest,
                    policy_digest_b=parent.tcre_policy_bundle_digest,
                )

    octs_binding: dict[str, Any] | None = None
    for art in job.artifacts:
        if art.artifact_kind == "octs_binding":
            octs_binding = dict(art.body_json or {})
            break

    return {
        "operator_view_schema_version": TCRE_OPERATOR_VIEW_SCHEMA_VERSION,
        "tcre_runtime_schema_version": TCRE_RUNTIME_SCHEMA_VERSION,
        "job_id": str(job.id),
        "tenant_id": str(tenant_id),
        "job_kind": job.job_kind,
        "status": job.status,
        "octs_binding": octs_binding,
        "reconstruction_summary": summary,
        "chronology_explanations": chronology_explanations,
        "edge_explanations": edge_explanations,
        "chain_timeline": timeline,
        "degradation_explanations": degradation_explanations,
        "replay_diff": replay_diff,
        "retrieval_refs": {
            "job_ref": f"job:{job.id}",
            "chain_ref": timeline.get("retrieval_chain_ref"),
            "chronology_window_refs": [c.get("chronology_window_ref") for c in chronology_explanations],
        },
    }


def build_operator_replay_diff_for_job_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    job = db.get(CortexTcreReconstructionJob, job_id)
    if job is None or job.tenant_id != tenant_id:
        msg = "job_not_found"
        raise ValueError(msg)
    cmp = _compare_in_memory_replay_twin_v1(db, job=job)
    run_a = _run_reconstruction_pipeline_in_memory_v1(
        db,
        tenant_id=tenant_id,
        scope=job.scope_json,
        tcre_policy_bundle_digest=job.tcre_policy_bundle_digest,
        reasoning_rule_pack_id=job.reasoning_rule_pack_id,
    )
    run_b = _run_reconstruction_pipeline_in_memory_v1(
        db,
        tenant_id=tenant_id,
        scope=job.scope_json,
        tcre_policy_bundle_digest=job.tcre_policy_bundle_digest,
        reasoning_rule_pack_id=job.reasoning_rule_pack_id,
    )
    diff = build_replay_diff_v1(
        run_a,
        run_b,
        policy_digest_a=job.tcre_policy_bundle_digest,
        policy_digest_b=job.tcre_policy_bundle_digest,
    )
    return {**cmp, "replay_diff": diff}
