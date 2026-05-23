"""RUNTIME-01 orchestration: load canonical slice → reduce → persist → health."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.reasoning.chronology_legality import (
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
)
from vector.domains.cortex.reasoning.reasoning_runtime_legality_matrix import (
    build_reasoning_runtime_legality_matrix_catalog_v1,
)
from vector.domains.cortex.reasoning.runtime.causal_chain_octs_binding import (
    hash_causal_chain_id_octs_bound_v1,
)
from vector.domains.cortex.reasoning.runtime.causal_chain_runtime_reducer import (
    reduce_causal_chain_v1,
)
from vector.domains.cortex.reasoning.runtime.causal_edge_runtime_reducer import (
    reduce_causal_edges_v1,
)
from vector.domains.cortex.reasoning.runtime.edge_expansion_runtime import (
    merge_edge_rows_deterministic_v1,
    reduce_all_expanded_edges_v1,
)
from vector.domains.cortex.reasoning.runtime.octs_binding_projection import (
    OctsBindingError,
    assert_replay_identity_stable_v1,
    build_octs_replay_identity_envelope_v1,
)
from vector.domains.cortex.reasoning.runtime.persisted_replay_diff_projection import (
    build_persisted_replay_diff_v1,
    build_replay_divergence_receipt_v1,
)
from vector.domains.cortex.reasoning.runtime.chronology_runtime_reducer import (
    reduce_chronology_rows_v1,
)
from vector.domains.cortex.reasoning.runtime.receipt_materialization import (
    aggregate_artifact_digest_v1,
    build_degradation_receipt_v1,
    build_equivalence_receipt_v1,
)
from vector.domains.cortex.reasoning.runtime.replay_diff_projection import build_replay_diff_v1
from vector.domains.cortex.reasoning.runtime.runtime_scope import normalize_reconstruction_scope_v1
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_artifact import (
    CortexTcreReconstructionArtifact,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

TCRE_RUNTIME_SCHEMA_VERSION: Final[int] = 1
TCRE_RUNTIME_ENGINE_BUILD_REF: Final[str] = "p06-runtime03-hardening-v1"
TCRE_RUNTIME_OPERATOR_PROJECTION_VERSION: Final[int] = 1

_ARTIFACT_CHRONOLOGY: Final[str] = "chronology_receipt"
_ARTIFACT_EDGE: Final[str] = "causal_edge"
_ARTIFACT_CHAIN: Final[str] = "causal_chain"
_ARTIFACT_DEGRADATION: Final[str] = "degradation_receipt"
_ARTIFACT_EQUIVALENCE: Final[str] = "replay_equivalence_receipt"
_ARTIFACT_AGGREGATE: Final[str] = "run_aggregate"
_ARTIFACT_OCTS_BINDING: Final[str] = "octs_binding"
_ARTIFACT_REPLAY_DIVERGENCE: Final[str] = "replay_divergence_receipt"


class TcreRuntimeError(ValueError):
    """Invalid reconstruction job state or scope."""


def _policy_context_v1() -> tuple[dict[str, Any], str, str]:
    pack = load_default_reasoning_policy_pack()
    pack_id = str(pack.get("tcre_policy_pack_id") or "ReasoningPolicyPackV1_Default")
    digest = TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST
    return pack, digest, pack_id


def load_bounded_materializations_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any],
) -> list[CortexCanonicalTransformMaterialization]:
    norm = normalize_reconstruction_scope_v1(scope)
    q = select(CortexCanonicalTransformMaterialization).where(
        CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
    )
    bundle_id = norm.get("bundle_id")
    if bundle_id:
        q = q.where(CortexCanonicalTransformMaterialization.bundle_id == str(bundle_id))
    lim = int(norm["materialization_limit"])
    q = (
        q.order_by(
            nullslast(CortexCanonicalTransformMaterialization.temporal_ordering_key.asc()),
            CortexCanonicalTransformMaterialization.id.asc(),
        )
        .limit(lim)
    )
    return list(db.scalars(q).all())


def _run_reconstruction_pipeline_in_memory_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any],
    tcre_policy_bundle_digest: str,
    reasoning_rule_pack_id: str,
) -> dict[str, Any]:
    policy, _, _ = _policy_context_v1()
    norm_scope = normalize_reconstruction_scope_v1(scope)
    mats = load_bounded_materializations_v1(db, tenant_id=tenant_id, scope=norm_scope)
    chronology_rows = reduce_chronology_rows_v1(
        mats,
        policy=policy,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
    )
    octs_envelope = build_octs_replay_identity_envelope_v1(
        tenant_id=tenant_id,
        scope=norm_scope,
        chronology_rows=chronology_rows,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        strict_binding=bool(norm_scope.get("octs_strict_binding")),
        session=db,
    )
    temporal_edges = reduce_causal_edges_v1(mats, tcre_policy_bundle_digest=tcre_policy_bundle_digest)
    expanded_edges = reduce_all_expanded_edges_v1(
        mats,
        chronology_rows,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
    )
    edge_rows = merge_edge_rows_deterministic_v1(temporal_edges, expanded_edges)
    chain = reduce_causal_chain_v1(
        edge_rows,
        tenant_id=str(tenant_id),
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
    )
    if chain and octs_envelope.get("ingestion_replay_identity"):
        bound_id = hash_causal_chain_id_octs_bound_v1(
            tcre_causal_edge_ids=chain["tcre_causal_edge_ids"],
            reasoning_rule_pack_id=reasoning_rule_pack_id,
            tcre_policy_bundle_digest=tcre_policy_bundle_digest,
            tenant_id=str(tenant_id),
            octs_binding_envelope=octs_envelope,
        )
        chain = {**chain, "causal_chain_id": bound_id, "octs_bound": True}
    digests: list[str] = [r["receipt_digest"] for r in chronology_rows]
    digests.extend(hash_tcre_causal_edge_id_placeholder(e) for e in edge_rows)
    if chain:
        digests.append(str(chain["causal_chain_id"]))
    if octs_envelope.get("octs_binding_digest"):
        digests.append(str(octs_envelope["octs_binding_digest"]))
    deg = build_degradation_receipt_v1(chronology_rows, tcre_policy_bundle_digest=tcre_policy_bundle_digest)
    if deg:
        digests.append(deg["receipt_digest"])
    aggregate = aggregate_artifact_digest_v1(digests)
    return {
        "materialization_count": len(mats),
        "chronology_rows": chronology_rows,
        "edge_rows": edge_rows,
        "chain": chain,
        "degradation_receipt": deg,
        "aggregate_digest": aggregate,
        "causal_chain_id": chain["causal_chain_id"] if chain else None,
        "octs_binding_envelope": octs_envelope,
    }


def hash_tcre_causal_edge_id_placeholder(edge_row: Mapping[str, Any]) -> str:
    return str(edge_row["tcre_causal_edge_id"])


def _persist_artifact(
    db: Session,
    *,
    job: CortexTcreReconstructionJob,
    artifact_kind: str,
    artifact_key: str,
    artifact_digest: str,
    body_json: Mapping[str, Any],
) -> None:
    db.add(
        CortexTcreReconstructionArtifact(
            job_id=job.id,
            tenant_id=job.tenant_id,
            artifact_kind=artifact_kind,
            artifact_key=artifact_key,
            artifact_digest=artifact_digest,
            body_json=dict(body_json),
        )
    )


def execute_tcre_reconstruction_job_v1(db: Session, job: CortexTcreReconstructionJob) -> dict[str, Any]:
    from vector.domains.cortex.execution.tcre_job_lifecycle import (
        ORPHAN_RUNNING_CODE_V1,
        terminalize_tcre_job_failed_v1,
    )

    if job.status not in ("queued", "running"):
        return {"job_id": str(job.id), "status": job.status, "skipped": True}
    now = datetime.now(UTC)
    job.status = "running"
    job.started_at = now
    db.flush()
    try:
        run = _run_reconstruction_pipeline_in_memory_v1(
            db,
            tenant_id=job.tenant_id,
            scope=job.scope_json,
            tcre_policy_bundle_digest=job.tcre_policy_bundle_digest,
            reasoning_rule_pack_id=job.reasoning_rule_pack_id,
        )
        if not job.dry_run:
            for row in run["chronology_rows"]:
                mid = str(row["materialization_id"])
                _persist_artifact(
                    db,
                    job=job,
                    artifact_kind=_ARTIFACT_CHRONOLOGY,
                    artifact_key=mid,
                    artifact_digest=str(row["receipt_digest"]),
                    body_json={
                        "receipt_body": row["receipt_body"],
                        "snapshot": row["snapshot"],
                        "chronology_legality_class": row["chronology_legality_class"],
                    },
                )
            for edge in run["edge_rows"]:
                eid = str(edge["tcre_causal_edge_id"])
                _persist_artifact(
                    db,
                    job=job,
                    artifact_kind=_ARTIFACT_EDGE,
                    artifact_key=eid,
                    artifact_digest=eid,
                    body_json=edge["edge_body"],
                )
            chain = run.get("chain")
            if chain:
                cid = str(chain["causal_chain_id"])
                chain_body = dict(chain)
                octs = run.get("octs_binding_envelope") or {}
                if octs:
                    chain_body["walk_hash"] = octs.get("walk_hash")
                    chain_body["traversal_receipt_digest"] = octs.get("traversal_receipt_digest")
                    chain_body["ingestion_replay_identity"] = octs.get("ingestion_replay_identity")
                    chain_body["continuity_proof_ref"] = octs.get("continuity_proof_ref")
                    chain_body["traversal_epoch"] = octs.get("traversal_epoch")
                    chain_body["traversal_permutation_profile"] = octs.get(
                        "traversal_permutation_profile"
                    )
                _persist_artifact(
                    db,
                    job=job,
                    artifact_kind=_ARTIFACT_CHAIN,
                    artifact_key=cid,
                    artifact_digest=cid,
                    body_json=chain_body,
                )
            deg = run.get("degradation_receipt")
            if deg:
                _persist_artifact(
                    db,
                    job=job,
                    artifact_kind=_ARTIFACT_DEGRADATION,
                    artifact_key="tenant_slice",
                    artifact_digest=str(deg["receipt_digest"]),
                    body_json=deg["receipt_body"],
                )
            octs = run.get("octs_binding_envelope") or {}
            if octs:
                _persist_artifact(
                    db,
                    job=job,
                    artifact_kind=_ARTIFACT_OCTS_BINDING,
                    artifact_key="envelope",
                    artifact_digest=str(octs.get("octs_binding_digest") or ""),
                    body_json=octs,
                )
            agg = str(run["aggregate_digest"])
            _persist_artifact(
                db,
                job=job,
                artifact_kind=_ARTIFACT_AGGREGATE,
                artifact_key="run",
                artifact_digest=agg,
                body_json={
                    "materialization_count": run["materialization_count"],
                    "causal_chain_id": run.get("causal_chain_id"),
                },
            )
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        chron_rows = run["chronology_rows"]
        edge_rows = run["edge_rows"]
        chron_degraded = sum(
            1 for r in chron_rows if r.get("chronology_legality_class") == "chronology_degraded"
        )
        edge_non_equiv = sum(
            1
            for e in edge_rows
            if (e.get("edge_body") or {}).get("causal_legality_class") != "causal_replay_equivalent"
        )
        job.summary_json = {
            "materialization_count": run["materialization_count"],
            "chronology_receipt_count": len(chron_rows),
            "chronology_count": len(chron_rows),
            "chronology_degraded_count": chron_degraded,
            "causal_edge_count": len(edge_rows),
            "edge_count": len(edge_rows),
            "edge_non_replay_equivalent_count": edge_non_equiv,
            "causal_chain_id": run.get("causal_chain_id"),
            "aggregate_digest": run["aggregate_digest"],
            "dry_run": job.dry_run,
        }
        job.error_detail = None
        db.flush()
        return dict(job.summary_json)
    except OctsBindingError as exc:
        terminalize_tcre_job_failed_v1(job, error_code=str(exc)[:4000])
        db.flush()
        raise
    except Exception as exc:
        terminalize_tcre_job_failed_v1(job, error_code=str(exc)[:4000])
        db.flush()
        raise
    finally:
        if job.status == "running":
            terminalize_tcre_job_failed_v1(job, error_code=ORPHAN_RUNNING_CODE_V1)
            db.flush()


def create_reconstruction_job_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any] | None = None,
    dry_run: bool = False,
    job_kind: str = "reconstruct",
    parent_job_id: uuid.UUID | None = None,
) -> CortexTcreReconstructionJob:
    _, digest, pack_id = _policy_context_v1()
    job = CortexTcreReconstructionJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_kind=job_kind,
        status="queued",
        dry_run=dry_run,
        scope_json=normalize_reconstruction_scope_v1(scope),
        summary_json={},
        tcre_policy_bundle_digest=digest,
        reasoning_rule_pack_id=pack_id,
        parent_job_id=parent_job_id,
        engine_build_ref=TCRE_RUNTIME_ENGINE_BUILD_REF,
    )
    db.add(job)
    db.flush()
    return job


def enqueue_reconstruction_job_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    scope: Mapping[str, Any] | None = None,
    dry_run: bool = False,
    run_sync: bool = False,
) -> dict[str, Any]:
    job = create_reconstruction_job_v1(
        db,
        tenant_id=tenant_id,
        scope=scope,
        dry_run=dry_run,
    )
    if run_sync:
        execute_tcre_reconstruction_job_v1(db, job)
        return {"job_id": str(job.id), "status": job.status, "sync": True}
    from app.tasks.cortex_tcre_reconstruction_jobs import run_tcre_reconstruction_job_task

    async_result = run_tcre_reconstruction_job_task.delay(str(tenant_id), str(job.id))
    job.celery_task_id = async_result.id
    db.flush()
    return {"job_id": str(job.id), "status": job.status, "celery_task_id": async_result.id}


def list_reconstruction_jobs_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 25,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 100))
    rows = list(
        db.scalars(
            select(CortexTcreReconstructionJob)
            .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .limit(lim)
        ).all()
    )
    return [_job_public_dict(j) for j in rows]


def get_reconstruction_job_detail_v1(
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
    out = _job_public_dict(job)
    arts = sorted(job.artifacts, key=lambda a: (a.artifact_kind, a.artifact_key))
    out["artifacts"] = [_artifact_public_dict(a) for a in arts]
    return out


def _compare_in_memory_replay_twin_v1(
    db: Session,
    *,
    job: CortexTcreReconstructionJob,
) -> dict[str, Any]:
    scope = dict(job.scope_json or {})
    run_a = _run_reconstruction_pipeline_in_memory_v1(
        db,
        tenant_id=job.tenant_id,
        scope=scope,
        tcre_policy_bundle_digest=job.tcre_policy_bundle_digest,
        reasoning_rule_pack_id=job.reasoning_rule_pack_id,
    )
    run_b = _run_reconstruction_pipeline_in_memory_v1(
        db,
        tenant_id=job.tenant_id,
        scope=scope,
        tcre_policy_bundle_digest=job.tcre_policy_bundle_digest,
        reasoning_rule_pack_id=job.reasoning_rule_pack_id,
    )
    digest_a = str(run_a["aggregate_digest"])
    digest_b = str(run_b["aggregate_digest"])
    passed = digest_a == digest_b
    changed: list[str] = []
    if not passed:
        changed.append("aggregate_digest")
    if run_a.get("causal_chain_id") != run_b.get("causal_chain_id"):
        changed.append("causal_chain_id")
    try:
        env_a = run_a.get("octs_binding_envelope") or {}
        env_b = run_b.get("octs_binding_envelope") or {}
        if env_a.get("ingestion_replay_identity") or env_b.get("ingestion_replay_identity"):
            assert_replay_identity_stable_v1(env_a, env_b)
    except OctsBindingError:
        passed = False
        changed.append("octs_replay_identity")
    replay_diff = build_replay_diff_v1(
        run_a,
        run_b,
        policy_digest_a=job.tcre_policy_bundle_digest,
        policy_digest_b=job.tcre_policy_bundle_digest,
    )
    return {
        "replay_equivalence_passed": passed,
        "double_run_digest_a": digest_a,
        "double_run_digest_b": digest_b,
        "changed_fields": changed,
        "materialization_count": run_a.get("materialization_count", 0),
        "replay_diff": replay_diff,
    }


def compare_replay_twin_for_job_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source_job_id: uuid.UUID,
) -> dict[str, Any]:
    source = db.get(CortexTcreReconstructionJob, source_job_id)
    if source is None or source.tenant_id != tenant_id:
        msg = "source_job_not_found"
        raise TcreRuntimeError(msg)
    twin_job = create_reconstruction_job_v1(
        db,
        tenant_id=tenant_id,
        scope=source.scope_json,
        dry_run=False,
        job_kind="replay_twin",
        parent_job_id=source.id,
    )
    cmp = _compare_in_memory_replay_twin_v1(db, job=twin_job)
    try:
        execute_tcre_reconstruction_job_v1(db, twin_job)
    except OctsBindingError:
        cmp = {**cmp, "replay_equivalence_passed": False}
    source_detail = get_reconstruction_job_detail_v1(db, tenant_id=tenant_id, job_id=source.id)
    twin_detail = get_reconstruction_job_detail_v1(db, tenant_id=tenant_id, job_id=twin_job.id)
    persisted_diff: dict[str, Any] | None = None
    if source_detail and twin_detail:
        persisted_diff = build_persisted_replay_diff_v1(
            source_detail.get("artifacts") or [],
            twin_detail.get("artifacts") or [],
            policy_digest_a=source.tcre_policy_bundle_digest,
            policy_digest_b=twin_job.tcre_policy_bundle_digest,
        )
        if not persisted_diff.get("identical"):
            cmp = {**cmp, "replay_equivalence_passed": False}
    equiv = build_equivalence_receipt_v1(
        double_run_digest_a=str(cmp["double_run_digest_a"]),
        double_run_digest_b=str(cmp["double_run_digest_b"]),
    )
    if twin_job.status not in ("completed", "failed"):
        twin_job.status = "completed" if cmp["replay_equivalence_passed"] else "failed"
        twin_job.completed_at = datetime.now(UTC)
    twin_job.summary_json = {
        **cmp,
        "equivalence_receipt_digest": equiv["receipt_digest"],
        "replay_diff": cmp.get("replay_diff"),
        "persisted_replay_diff": persisted_diff,
    }
    if not cmp["replay_equivalence_passed"]:
        twin_job.error_detail = "replay_equivalence_mismatch"
        if persisted_diff and not twin_job.dry_run:
            div = build_replay_divergence_receipt_v1(
                replay_diff=persisted_diff,
                source_job_id=str(source.id),
                twin_job_id=str(twin_job.id),
                tcre_policy_bundle_digest=source.tcre_policy_bundle_digest,
            )
            _persist_artifact(
                db,
                job=twin_job,
                artifact_kind=_ARTIFACT_REPLAY_DIVERGENCE,
                artifact_key="twin",
                artifact_digest=str(div["receipt_digest"]),
                body_json=div["receipt_body"],
            )
    if not twin_job.dry_run:
        _persist_artifact(
            db,
            job=twin_job,
            artifact_kind=_ARTIFACT_EQUIVALENCE,
            artifact_key="twin",
            artifact_digest=str(equiv["receipt_digest"]),
            body_json=equiv["receipt_body"],
        )
    db.flush()
    return {
        "twin_job_id": str(twin_job.id),
        "source_job_id": str(source.id),
        **cmp,
        "equivalence_receipt": equiv,
    }


def build_reasoning_runtime_health_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    _, digest, pack_id = _policy_context_v1()
    status_rows = list(
        db.execute(
            select(
                CortexTcreReconstructionJob.status,
                func.count(),
            )
            .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
            .group_by(CortexTcreReconstructionJob.status)
        ).all()
    )
    status_counts = {str(row[0]): int(row[1]) for row in status_rows}
    last_ok = db.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.status == "completed",
        )
        .order_by(CortexTcreReconstructionJob.completed_at.desc())
        .limit(1)
    )
    last_twin = db.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.tenant_id == tenant_id,
            CortexTcreReconstructionJob.job_kind == "replay_twin",
        )
        .order_by(CortexTcreReconstructionJob.completed_at.desc())
        .limit(1)
    )
    failed_jobs = int(status_counts.get("failed", 0))
    queued_depth = int(status_counts.get("queued", 0)) + int(status_counts.get("running", 0))
    legality = build_reasoning_runtime_legality_matrix_catalog_v1(tenant_id=tenant_id)
    mat_count = int(
        db.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    completed_jobs = list(
        db.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(20)
        ).all()
    )
    durations: list[float] = []
    degraded_chron = 0
    total_chron = 0
    degraded_edges = 0
    total_edges = 0
    for j in completed_jobs:
        if j.started_at and j.completed_at:
            durations.append((j.completed_at - j.started_at).total_seconds())
        summary = j.summary_json or {}
        total_chron += int(
            summary.get("chronology_count") or summary.get("chronology_receipt_count") or 0
        )
        degraded_chron += int(summary.get("chronology_degraded_count", 0) or 0)
        total_edges += int(summary.get("edge_count") or summary.get("causal_edge_count") or 0)
        degraded_edges += int(summary.get("edge_non_replay_equivalent_count", 0) or 0)
    avg_duration = sum(durations) / len(durations) if durations else None
    degraded_chron_pct = (100.0 * degraded_chron / total_chron) if total_chron else 0.0
    degraded_edge_pct = (100.0 * degraded_edges / total_edges) if total_edges else 0.0
    last_replay_result = None
    last_divergence_at = None
    if last_twin:
        summary = last_twin.summary_json or {}
        last_replay_result = summary.get("replay_equivalence_passed")
        if last_replay_result is False:
            last_divergence_at = (
                last_twin.completed_at.isoformat() if last_twin.completed_at else None
            )
    return {
        "tenant_id": str(tenant_id),
        "tcre_runtime_schema_version": TCRE_RUNTIME_SCHEMA_VERSION,
        "operator_projection_version": TCRE_RUNTIME_OPERATOR_PROJECTION_VERSION,
        "engine_build_ref": TCRE_RUNTIME_ENGINE_BUILD_REF,
        "active_tcre_policy_bundle_digest": digest,
        "active_reasoning_rule_pack_id": pack_id,
        "canonical_materialization_count": mat_count,
        "job_status_counts": status_counts,
        "queue_depth_proxy": queued_depth,
        "failed_job_count": failed_jobs,
        "last_successful_job": _job_public_dict(last_ok) if last_ok else None,
        "last_replay_twin_job": _job_public_dict(last_twin) if last_twin else None,
        "last_replay_result": last_replay_result,
        "last_replay_divergence_at": last_divergence_at,
        "last_successful_replay_twin_passed": (
            bool((last_twin.summary_json or {}).get("replay_equivalence_passed"))
            if last_twin and last_twin.status == "completed"
            else None
        ),
        "degraded_chronology_percent": round(degraded_chron_pct, 2),
        "degraded_edge_percent": round(degraded_edge_pct, 2),
        "avg_reconstruction_duration_seconds": (
            round(avg_duration, 3) if avg_duration is not None else None
        ),
        "replay_equivalence_status": (
            "unknown"
            if last_ok is None
            else str((last_ok.summary_json or {}).get("replay_equivalence_passed", "not_run"))
        ),
        "runtime_legality": {
            "predicate_count": len(legality.get("predicates", [])),
            "forbidden_deployment_count": len(legality.get("forbidden_deployments", [])),
        },
    }


def _job_public_dict(job: CortexTcreReconstructionJob) -> dict[str, Any]:
    return {
        "job_id": str(job.id),
        "tenant_id": str(job.tenant_id),
        "job_kind": job.job_kind,
        "status": job.status,
        "dry_run": job.dry_run,
        "scope_json": dict(job.scope_json or {}),
        "summary_json": dict(job.summary_json or {}),
        "tcre_policy_bundle_digest": job.tcre_policy_bundle_digest,
        "reasoning_rule_pack_id": job.reasoning_rule_pack_id,
        "parent_job_id": str(job.parent_job_id) if job.parent_job_id else None,
        "engine_build_ref": job.engine_build_ref,
        "error_detail": job.error_detail,
        "celery_task_id": job.celery_task_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _artifact_public_dict(art: CortexTcreReconstructionArtifact) -> dict[str, Any]:
    return {
        "artifact_id": art.id,
        "artifact_kind": art.artifact_kind,
        "artifact_key": art.artifact_key,
        "artifact_digest": art.artifact_digest,
        "body_json": dict(art.body_json or {}),
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }
