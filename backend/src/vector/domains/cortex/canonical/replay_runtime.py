"""Phase 03 Steps 10–12 — replay jobs (C0–C5) + deterministic temporal raw processing order.

Normative: `DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md`,
`phase-03-temporal-timeline-doctrine.md`.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.canonical.materialization_topology_engine import build_materialization_stage_plan
from vector.domains.cortex.canonical.replay_determinism import (
    build_replay_fingerprint_bundle,
    fingerprint_id_order,
)
from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.domains.cortex.canonical.temporal_runtime import preview_rebuild_raw_order
from vector.domains.cortex.canonical.transform_runtime import (
    ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM,
    ENGINE_BUILD_REF,
    MaterializeError,
    ResolvedMaterializationInput,
    materialize_raw_record,
    resolve_materialization_input,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import (
    CortexCanonicalReplayJobReceipt,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_mapping_bundle_compatibility import (
    CortexMappingBundleCompatibilityEdge,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_trust_state import RawMemoryTrustState

REPLAY_RUNTIME_SCHEMA_VERSION: Final[int] = 2
REPLAY_DIVERGENCE_CLASSES: Final[tuple[str, ...]] = ("C0", "C1", "C2", "C3", "C4", "C5")
FORBIDDEN_MATERIALIZE_DIVERGENCE: Final[frozenset[str]] = frozenset({"C3", "C4", "C5"})
BLOCKING_TRUST_STATES: Final[frozenset[str]] = frozenset(
    {"corrupted", "continuity-broken", "replay-diverged"}
)
JobKind = Literal["rebuild", "regeneration"]


class ReplayJobError(Exception):
    """Deterministic validation failure for replay job parameters."""


def compatibility_edge_exists(db: Session, *, from_bundle_id: str, to_bundle_id: str) -> bool:
    row = db.scalars(
        select(CortexMappingBundleCompatibilityEdge).where(
            CortexMappingBundleCompatibilityEdge.from_bundle_id == from_bundle_id,
            CortexMappingBundleCompatibilityEdge.to_bundle_id == to_bundle_id,
        )
    ).first()
    return row is not None


def _tenant_trust_state(db: Session, *, tenant_id: uuid.UUID) -> str | None:
    row = db.get(RawMemoryTrustState, tenant_id)
    return str(row.trust_state) if row is not None else None


def _replay_process_one_row(
    db: Session,
    *,
    job: CortexCanonicalReplayJob,
    tenant_id: uuid.UUID,
    pinned_bundle_id: str,
    job_kind: str,
    trust_state: str | None,
    source_bundle_id: str | None,
    compat_ok: bool,
    dry_run: bool,
    rid: int,
    counts: dict[str, int],
    receipt_dicts_accum: list[dict[str, Any]],
) -> tuple[int, int]:
    """Apply oracle + optional materialize + receipt for one raw id. Returns (writes_applied_delta, writes_skipped_delta)."""
    writes_applied = 0
    writes_skipped = 0
    prior = db.scalars(
        select(CortexCanonicalTransformMaterialization).where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.bundle_id == pinned_bundle_id,
            CortexCanonicalTransformMaterialization.raw_record_id == rid,
        )
    ).first()
    try:
        res = resolve_materialization_input(
            db, tenant_id=tenant_id, bundle_id=pinned_bundle_id, raw_record_id=int(rid)
        )
    except MaterializeError as exc:
        dj = {"note": "oracle_resolution_failed"}
        db.add(
            CortexCanonicalReplayJobReceipt(
                job_id=job.id,
                raw_record_id=int(rid),
                divergence_class="C4",
                detail_json=dj,
                materialize_error=str(exc),
            )
        )
        receipt_dicts_accum.append(
            {"raw_record_id": int(rid), "divergence_class": "C4", "detail_json": dj}
        )
        counts["C4"] += 1
        writes_skipped += 1
        return writes_applied, writes_skipped

    div, detail = classify_replay_divergence(
        job_kind=job_kind,
        prior=prior,
        resolved=res,
        tenant_trust_state=trust_state,
        source_bundle_id=source_bundle_id,
        pinned_bundle_id=pinned_bundle_id,
        compatibility_edge_present=compat_ok,
    )
    detail = {
        **detail,
        "raw_payload_hash": res.raw.payload_hash,
        "canonical_object_kind": res.kind.value,
    }
    counts[div] += 1

    should_write = not dry_run and div not in FORBIDDEN_MATERIALIZE_DIVERGENCE
    if should_write and div == "C0" and prior is not None:
        same_hashes = (
            prior.logical_key_hash == res.logical_key_hash
            and prior.emitted_snapshot_hash == res.emitted_snapshot_hash
        )
        if same_hashes:
            should_write = False

    if should_write:
        materialize_raw_record(
            db,
            tenant_id=tenant_id,
            bundle_id=pinned_bundle_id,
            raw_record_id=int(rid),
            replay_job_id=job.id,
            commit=False,
        )
        writes_applied += 1
    else:
        writes_skipped += 1

    db.add(
        CortexCanonicalReplayJobReceipt(
            job_id=job.id,
            raw_record_id=int(rid),
            divergence_class=div,
            detail_json=detail,
            materialize_error=None,
        )
    )
    receipt_dicts_accum.append(
        {
            "raw_record_id": int(rid),
            "divergence_class": div,
            "detail_json": detail,
        }
    )
    return writes_applied, writes_skipped


def classify_replay_divergence(
    *,
    job_kind: str,
    prior: CortexCanonicalTransformMaterialization | None,
    resolved: ResolvedMaterializationInput,
    tenant_trust_state: str | None,
    source_bundle_id: str | None,
    pinned_bundle_id: str,
    compatibility_edge_present: bool,
) -> tuple[str, dict[str, Any]]:
    """Return (C0|C1|…|C5, detail_json) for one raw row oracle vs stored prior to write."""
    if tenant_trust_state in BLOCKING_TRUST_STATES:
        return "C3", {
            "trust_state": tenant_trust_state,
            "reason": "tenant_raw_memory_trust_blocks_canonical_rebuild",
        }

    if job_kind == "regeneration" and source_bundle_id and not compatibility_edge_present:
        return "C5", {
            "reason": "undeclared_bundle_migration",
            "source_bundle_id": source_bundle_id,
            "pinned_bundle_id": pinned_bundle_id,
        }

    if prior is None:
        return "C0", {"note": "first_materialization"}

    same = (
        prior.logical_key_hash == resolved.logical_key_hash
        and prior.emitted_snapshot_hash == resolved.emitted_snapshot_hash
        and prior.engine_build_ref == ENGINE_BUILD_REF
        and prior.canonical_object_kind == resolved.kind.value
    )
    if same:
        return "C0", {"note": "stored_matches_oracle"}

    if job_kind == "regeneration":
        return "C2", {
            "note": "expected_regeneration_or_mapping_drift",
            "before": {
                "logical_key_hash": prior.logical_key_hash,
                "emitted_snapshot_hash": prior.emitted_snapshot_hash,
                "engine_build_ref": prior.engine_build_ref,
            },
            "after_oracle": {
                "logical_key_hash": resolved.logical_key_hash,
                "emitted_snapshot_hash": resolved.emitted_snapshot_hash,
                "engine_build_ref": ENGINE_BUILD_REF,
            },
        }

    return "C4", {
        "note": "unexpected_projection_drift_under_rebuild",
        "before": {
            "logical_key_hash": prior.logical_key_hash,
            "emitted_snapshot_hash": prior.emitted_snapshot_hash,
            "engine_build_ref": prior.engine_build_ref,
        },
        "after_oracle": {
            "logical_key_hash": resolved.logical_key_hash,
            "emitted_snapshot_hash": resolved.emitted_snapshot_hash,
            "engine_build_ref": ENGINE_BUILD_REF,
        },
    }


def _assert_scope_raw_records(db: Session, *, tenant_id: uuid.UUID, raw_record_ids: list[int]) -> None:
    if not raw_record_ids:
        raise ReplayJobError("empty_raw_record_scope")
    uniq = sorted(set(raw_record_ids))
    if len(uniq) > 500:
        raise ReplayJobError("raw_record_scope_too_large")
    n = db.scalar(
        select(func.count())
        .select_from(RawIngestionRecord)
        .where(RawIngestionRecord.tenant_id == tenant_id, RawIngestionRecord.id.in_(uniq))
    )
    if int(n or 0) != len(uniq):
        raise ReplayJobError("raw_record_scope_mismatch_tenant")


def resolve_replay_scope_raw_record_ids(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    raw_record_ids: list[int] | None = None,
    connector: str | None = None,
    resource_type: str | None = None,
    include_dependency_neighborhood: bool = False,
    subtree_anchor_raw_record_id: int | None = None,
    parent_anchor_raw_record_id: int | None = None,
    max_scope_size: int = 500,
) -> list[int]:
    """Resolve replay scope for localized replay modes (object/subtree/connector/resource_type)."""
    if subtree_anchor_raw_record_id is not None and parent_anchor_raw_record_id is not None:
        raise ReplayJobError("replay_scope_anchor_conflict")
    if subtree_anchor_raw_record_id is not None:
        anchor = int(subtree_anchor_raw_record_id)
        pool = list(
            db.scalars(
                select(RawIngestionRecord)
                .where(RawIngestionRecord.tenant_id == tenant_id)
                .order_by(RawIngestionRecord.id.desc())
                .limit(max_scope_size * 10)
            ).all()
        )
        temporal = {int(r.id): f"{int(r.id):012d}" for r in pool}
        topo = build_replay_dependency_topology(pool, temporal_key_by_id=temporal)
        children_by_parent: dict[int, list[int]] = defaultdict(list)
        for edge in topo.get("dependency_edges") or []:
            if not isinstance(edge, dict):
                continue
            p = int(edge["parent_raw_record_id"])
            c = int(edge["child_raw_record_id"])
            children_by_parent[p].append(c)
        seen: set[int] = {anchor}
        stack = [anchor]
        while stack:
            cur = int(stack.pop())
            for ch in sorted(children_by_parent.get(cur, [])):
                if ch in seen:
                    continue
                if len(seen) >= max_scope_size:
                    raise ReplayJobError("raw_record_scope_too_large")
                seen.add(ch)
                stack.append(ch)
        return sorted(seen)
    if parent_anchor_raw_record_id is not None:
        anchor = int(parent_anchor_raw_record_id)
        pool = list(
            db.scalars(
                select(RawIngestionRecord)
                .where(RawIngestionRecord.tenant_id == tenant_id)
                .order_by(RawIngestionRecord.id.desc())
                .limit(max_scope_size * 10)
            ).all()
        )
        temporal = {int(r.id): f"{int(r.id):012d}" for r in pool}
        topo = build_replay_dependency_topology(pool, temporal_key_by_id=temporal)
        parents_by_child: dict[int, list[int]] = defaultdict(list)
        for edge in topo.get("dependency_edges") or []:
            if not isinstance(edge, dict):
                continue
            p = int(edge["parent_raw_record_id"])
            c = int(edge["child_raw_record_id"])
            parents_by_child[c].append(p)
        seen: set[int] = {anchor}
        stack = [anchor]
        while stack:
            cur = int(stack.pop())
            for par in sorted(parents_by_child.get(cur, [])):
                if par in seen:
                    continue
                if len(seen) >= max_scope_size:
                    raise ReplayJobError("raw_record_scope_too_large")
                seen.add(par)
                stack.append(par)
        return sorted(seen)
    if raw_record_ids:
        base_ids = sorted(set(int(x) for x in raw_record_ids))
    else:
        q = select(RawIngestionRecord.id).where(RawIngestionRecord.tenant_id == tenant_id)
        if connector and connector.strip():
            q = q.where(RawIngestionRecord.connector == connector.strip())
        if resource_type and resource_type.strip():
            q = q.where(RawIngestionRecord.resource_type == resource_type.strip())
        q = q.order_by(RawIngestionRecord.id.desc()).limit(max_scope_size)
        base_ids = sorted(int(x) for x in db.scalars(q).all())
    if not base_ids:
        raise ReplayJobError("empty_raw_record_scope")
    if not include_dependency_neighborhood:
        if len(base_ids) > max_scope_size:
            raise ReplayJobError("raw_record_scope_too_large")
        return base_ids

    candidate_rows = list(
        db.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.id.in_(base_ids),
            )
        ).all()
    )
    parent_types = {
        "github.workflow_run",
        "github.deployment",
        "slack.message",
        "notion.database",
        "notion.block",
        "calls.meeting",
    }
    candidate_rows.extend(
        list(
            db.scalars(
                select(RawIngestionRecord)
                .where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.resource_type.in_(sorted(parent_types)),
                )
                .order_by(RawIngestionRecord.id.desc())
                .limit(max_scope_size * 4)
            ).all()
        )
    )
    # Deduplicate by id while preserving latest seen object.
    by_id: dict[int, RawIngestionRecord] = {int(r.id): r for r in candidate_rows}
    candidate_rows = list(by_id.values())
    temporal = {int(r.id): f"{int(r.id):012d}" for r in candidate_rows}
    topo = build_replay_dependency_topology(candidate_rows, temporal_key_by_id=temporal)
    rev: dict[int, list[int]] = {}
    for edge in topo.get("dependency_edges") or []:
        p = int(edge["parent_raw_record_id"])
        c = int(edge["child_raw_record_id"])
        rev.setdefault(c, []).append(p)
    expanded: set[int] = set(base_ids)
    stack = list(base_ids)
    while stack:
        cur = int(stack.pop())
        for parent in rev.get(cur, []):
            if parent in expanded:
                continue
            expanded.add(parent)
            stack.append(parent)
            if len(expanded) > max_scope_size:
                raise ReplayJobError("raw_record_scope_too_large")
    return sorted(expanded)


def replay_job_public_dict(job: CortexCanonicalReplayJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "pinned_bundle_id": job.pinned_bundle_id,
        "job_kind": job.job_kind,
        "status": job.status,
        "source_bundle_id": job.source_bundle_id,
        "dry_run": job.dry_run,
        "scope_raw_record_ids": list(job.scope_raw_record_ids),
        "resolved_pin_json": dict(job.resolved_pin_json),
        "engine_build_ref": job.engine_build_ref,
        "summary_json": dict(job.summary_json),
        "error_detail": job.error_detail,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


def replay_receipt_public_dict(r: CortexCanonicalReplayJobReceipt) -> dict[str, Any]:
    return {
        "id": r.id,
        "job_id": r.job_id,
        "raw_record_id": r.raw_record_id,
        "divergence_class": r.divergence_class,
        "detail_json": dict(r.detail_json),
        "materialize_error": r.materialize_error,
        "created_at": r.created_at,
    }


def get_replay_job(
    db: Session, *, tenant_id: uuid.UUID, job_id: uuid.UUID
) -> CortexCanonicalReplayJob | None:
    return db.scalars(
        select(CortexCanonicalReplayJob)
        .where(CortexCanonicalReplayJob.id == job_id, CortexCanonicalReplayJob.tenant_id == tenant_id)
        .options(selectinload(CortexCanonicalReplayJob.receipts))
    ).first()


def list_replay_jobs(db: Session, *, tenant_id: uuid.UUID, limit: int = 30) -> list[CortexCanonicalReplayJob]:
    lim = max(1, min(limit, 100))
    return list(
        db.scalars(
            select(CortexCanonicalReplayJob)
            .where(CortexCanonicalReplayJob.tenant_id == tenant_id)
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(lim)
        ).all()
    )


def execute_canonical_replay_job(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    pinned_bundle_id: str,
    job_kind: JobKind,
    raw_record_ids: list[int] | None,
    source_bundle_id: str | None,
    dry_run: bool,
    connector: str | None = None,
    resource_type: str | None = None,
    include_dependency_neighborhood: bool = False,
    subtree_anchor_raw_record_id: int | None = None,
    parent_anchor_raw_record_id: int | None = None,
) -> CortexCanonicalReplayJob:
    """Create a replay job row, run oracle vs stored classification, optionally materialize, commit once."""
    if job_kind not in ("rebuild", "regeneration"):
        raise ReplayJobError(f"invalid_job_kind:{job_kind}")
    scoped_ids = resolve_replay_scope_raw_record_ids(
        db,
        tenant_id=tenant_id,
        raw_record_ids=raw_record_ids,
        connector=connector,
        resource_type=resource_type,
        include_dependency_neighborhood=include_dependency_neighborhood,
        subtree_anchor_raw_record_id=subtree_anchor_raw_record_id,
        parent_anchor_raw_record_id=parent_anchor_raw_record_id,
    )
    _assert_scope_raw_records(db, tenant_id=tenant_id, raw_record_ids=scoped_ids)

    if job_kind == "regeneration" and source_bundle_id:
        if not compatibility_edge_exists(db, from_bundle_id=source_bundle_id, to_bundle_id=pinned_bundle_id):
            raise ReplayJobError(
                f"regeneration_requires_declared_compatibility_edge:{source_bundle_id}->{pinned_bundle_id}"
            )

    bundle = db.get(CortexMappingBundle, pinned_bundle_id)
    if bundle is None:
        raise ReplayJobError("unknown_bundle")
    if bundle.lifecycle_state not in ALLOWED_BUNDLE_LIFECYCLE_FOR_TRANSFORM:
        raise ReplayJobError(f"bundle_not_transformable:{bundle.lifecycle_state}")
    resolved_pin = {
        "pinned_bundle_id": pinned_bundle_id,
        "lifecycle_state": bundle.lifecycle_state,
        "manifest_hash": bundle.manifest_hash,
    }

    job = CortexCanonicalReplayJob(
        tenant_id=tenant_id,
        pinned_bundle_id=pinned_bundle_id,
        job_kind=job_kind,
        status="running",
        source_bundle_id=source_bundle_id,
        dry_run=dry_run,
        scope_raw_record_ids=list(sorted(set(scoped_ids))),
        resolved_pin_json=resolved_pin,
        engine_build_ref=ENGINE_BUILD_REF,
        summary_json={},
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()
    job_id = job.id

    trust_state = _tenant_trust_state(db, tenant_id=tenant_id)
    compat_ok = True
    if job_kind == "regeneration" and source_bundle_id:
        compat_ok = compatibility_edge_exists(db, from_bundle_id=source_bundle_id, to_bundle_id=pinned_bundle_id)

    counts: dict[str, int] = {k: 0 for k in REPLAY_DIVERGENCE_CLASSES}
    writes_applied = 0
    writes_skipped = 0

    preview_rows = preview_rebuild_raw_order(
        db,
        tenant_id=tenant_id,
        raw_record_ids=list(job.scope_raw_record_ids),
    )
    ordered_known = [int(r["raw_record_id"]) for r in preview_rows]
    raw_scope_rows = list(
        db.scalars(
            select(RawIngestionRecord).where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.id.in_(list(job.scope_raw_record_ids)),
            )
        ).all()
    )
    key_by_id = {int(r["raw_record_id"]): str(r["temporal_ordering_key"]) for r in preview_rows}
    for r in raw_scope_rows:
        key_by_id.setdefault(int(r.id), f"{int(r.id):012d}")
    topo = build_replay_dependency_topology(raw_scope_rows, temporal_key_by_id=key_by_id)
    plan = build_materialization_stage_plan(
        db,
        tenant_id=tenant_id,
        bundle_id=pinned_bundle_id,
        rows=raw_scope_rows,
        temporal_key_by_id=key_by_id,
    )
    scope_set = {int(x) for x in job.scope_raw_record_ids}
    stage_slices: list[list[int]] = []
    staged_ids: set[int] = set()
    for st in plan.get("stages") or []:
        slice_ids = [int(rid) for rid in st if int(rid) in scope_set]
        if slice_ids:
            stage_slices.append(slice_ids)
            staged_ids.update(slice_ids)
    leftover_scope = sorted(scope_set - staged_ids)
    if leftover_scope:
        stage_slices.append(leftover_scope)
    process_order_flat = [rid for sl in stage_slices for rid in sl]
    orphan_queue = list(plan.get("quarantine") or []) + list(plan.get("deferred_dependency_queue") or [])
    receipt_dicts_accum: list[dict[str, Any]] = []
    job.summary_json = {
        "deterministic_process_order": process_order_flat,
        "topology_stage_plan_total": len(stage_slices),
    }
    db.flush()

    try:
        for stage_idx, stage_ids in enumerate(stage_slices):
            for rid in stage_ids:
                wa, ws = _replay_process_one_row(
                    db,
                    job=job,
                    tenant_id=tenant_id,
                    pinned_bundle_id=pinned_bundle_id,
                    job_kind=job_kind,
                    trust_state=trust_state,
                    source_bundle_id=source_bundle_id,
                    compat_ok=compat_ok,
                    dry_run=dry_run,
                    rid=int(rid),
                    counts=counts,
                    receipt_dicts_accum=receipt_dicts_accum,
                )
                writes_applied += wa
                writes_skipped += ws
            barrier = {
                "topology_stage_index": stage_idx,
                "topology_stages_total": len(stage_slices),
                "stage_size": len(stage_ids),
                "stage_dependency_wait_count": int(plan.get("stage_dependency_wait_count") or 0),
                "deferred_child_count": int(plan.get("deferred_child_count") or 0),
                "replay_blocker_count": int(plan.get("replay_blocker_count") or 0),
                "deterministic_process_order_fp": fingerprint_id_order(process_order_flat),
            }
            prev = job.summary_json if isinstance(job.summary_json, dict) else {}
            job.summary_json = {
                **prev,
                "topology_checkpoint": barrier,
                "topology_stages_completed": stage_idx + 1,
                "orphan_operational_queues": {
                    "topology_quarantine_count": len(plan.get("quarantine") or []),
                    "deferred_dependency_count": len(plan.get("deferred_dependency_queue") or []),
                    "combined_queue_sample": orphan_queue[:60],
                    "orphan_class_histogram": dict(
                        Counter(str(x.get("orphan_class") or "unknown") for x in orphan_queue)
                    ),
                },
            }
            db.commit()

        fingerprints = build_replay_fingerprint_bundle(
            topology=topo,
            process_order=process_order_flat,
            receipt_dicts=receipt_dicts_accum,
            writes_applied=writes_applied,
            writes_skipped=writes_skipped,
            counts_by_divergence_class=counts,
        )
        replay_converged = len(receipt_dicts_accum) == len(job.scope_raw_record_ids) and sum(
            int(counts.get(k, 0) or 0) for k in FORBIDDEN_MATERIALIZE_DIVERGENCE
        ) == 0
        job.status = "completed"
        job.summary_json = {
            **(job.summary_json if isinstance(job.summary_json, dict) else {}),
            "counts_by_divergence_class": counts,
            "writes_applied": writes_applied,
            "writes_skipped": writes_skipped,
            "dry_run": dry_run,
            "temporal_ordering_policy": "preview_rebuild_raw_order_plus_topology_stages",
            "replay_dependency_edges_count": len(topo.get("dependency_edges") or []),
            "replay_dependency_cycle_detected": bool(topo.get("cycle_detected")),
            "topology_plan_cycle_detected": bool(plan.get("cycle_detected")),
            "replay_max_topology_depth": int(topo.get("max_replay_depth") or 0),
            "orphan_dependency_ref_count": len(topo.get("orphan_refs") or []),
            "orphan_dependency_refs_sample": list(topo.get("orphan_refs") or [])[:25],
            "topology_materialization_plan": {
                "topology_stage_count": plan.get("topology_stage_count"),
                "stage_sizes": plan.get("stage_sizes"),
                "replay_blocker_count": plan.get("replay_blocker_count"),
            },
            "replay_fingerprints": fingerprints,
            "replay_converged": replay_converged,
            "replay_convergence_evidence": {
                "scope_size": len(job.scope_raw_record_ids),
                "receipts_written": len(receipt_dicts_accum),
                "forbidden_divergence_total": sum(int(counts.get(k, 0) or 0) for k in FORBIDDEN_MATERIALIZE_DIVERGENCE),
            },
            "replay_runtime_schema_version": REPLAY_RUNTIME_SCHEMA_VERSION,
        }
        job.completed_at = datetime.now(UTC)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            sync_replay_job_into_canonical_failure_cases,
        )

        sync_replay_job_into_canonical_failure_cases(db, job=job)
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            record_replay_job_execution_failed,
        )

        record_replay_job_execution_failed(db, job=job, error=str(exc))
        db.commit()
        raise

    out = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
    assert out is not None
    return out


def resume_canonical_replay_job(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> CortexCanonicalReplayJob:
    """Resume a **failed** replay job without reordering scope (uses stored deterministic process order).

    Only raw ids without an existing receipt are processed. Commits once at the end (no partial stage resume yet).
    """
    job = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
    if job is None:
        raise ReplayJobError("replay_job_not_found")
    if job.status != "failed":
        raise ReplayJobError(f"resume_requires_failed_job:{job.status}")
    sj = job.summary_json if isinstance(job.summary_json, dict) else {}
    order = sj.get("deterministic_process_order")
    if not isinstance(order, list) or not order:
        raise ReplayJobError("replay_resume_missing_deterministic_process_order")
    process_order_flat = [int(x) for x in order]
    done = {int(r.raw_record_id) for r in job.receipts}
    missing = [rid for rid in process_order_flat if rid not in done]
    if not missing:
        job.status = "completed"
        job.error_detail = None
        job.completed_at = datetime.now(UTC)
        db.commit()
        out = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        assert out is not None
        return out

    trust_state = _tenant_trust_state(db, tenant_id=tenant_id)
    compat_ok = True
    if job.job_kind == "regeneration" and job.source_bundle_id:
        compat_ok = compatibility_edge_exists(
            db, from_bundle_id=job.source_bundle_id, to_bundle_id=job.pinned_bundle_id
        )
    counts: dict[str, int] = {k: 0 for k in REPLAY_DIVERGENCE_CLASSES}
    for r in job.receipts:
        k = str(r.divergence_class)
        if k in counts:
            counts[k] += 1
    writes_applied = int(sj.get("writes_applied") or 0)
    writes_skipped = int(sj.get("writes_skipped") or 0)
    receipt_dicts_accum: list[dict[str, Any]] = []

    job.status = "running"
    job.error_detail = None
    job.completed_at = None
    db.commit()

    try:
        for rid in process_order_flat:
            if rid in done:
                continue
            wa, ws = _replay_process_one_row(
                db,
                job=job,
                tenant_id=tenant_id,
                pinned_bundle_id=job.pinned_bundle_id,
                job_kind=str(job.job_kind),
                trust_state=trust_state,
                source_bundle_id=job.source_bundle_id,
                compat_ok=compat_ok,
                dry_run=bool(job.dry_run),
                rid=int(rid),
                counts=counts,
                receipt_dicts_accum=receipt_dicts_accum,
            )
            writes_applied += wa
            writes_skipped += ws
        preview_rows = preview_rebuild_raw_order(
            db, tenant_id=tenant_id, raw_record_ids=list(job.scope_raw_record_ids)
        )
        raw_scope_rows = list(
            db.scalars(
                select(RawIngestionRecord).where(
                    RawIngestionRecord.tenant_id == tenant_id,
                    RawIngestionRecord.id.in_(list(job.scope_raw_record_ids)),
                )
            ).all()
        )
        key_by_id = {int(r["raw_record_id"]): str(r["temporal_ordering_key"]) for r in preview_rows}
        for r in raw_scope_rows:
            key_by_id.setdefault(int(r.id), f"{int(r.id):012d}")
        topo = build_replay_dependency_topology(raw_scope_rows, temporal_key_by_id=key_by_id)
        plan = build_materialization_stage_plan(
            db,
            tenant_id=tenant_id,
            bundle_id=job.pinned_bundle_id,
            rows=raw_scope_rows,
            temporal_key_by_id=key_by_id,
        )
        all_receipts = list(
            db.scalars(
                select(CortexCanonicalReplayJobReceipt).where(
                    CortexCanonicalReplayJobReceipt.job_id == job.id
                )
            ).all()
        )
        all_receipt_dicts = [
            {
                "raw_record_id": int(r.raw_record_id),
                "divergence_class": r.divergence_class,
                "detail_json": dict(r.detail_json or {}),
            }
            for r in sorted(all_receipts, key=lambda x: int(x.id))
        ]
        fingerprints = build_replay_fingerprint_bundle(
            topology=topo,
            process_order=process_order_flat,
            receipt_dicts=all_receipt_dicts,
            writes_applied=writes_applied,
            writes_skipped=writes_skipped,
            counts_by_divergence_class=counts,
        )
        replay_converged = len(all_receipts) == len(job.scope_raw_record_ids) and sum(
            int(counts.get(k, 0) or 0) for k in FORBIDDEN_MATERIALIZE_DIVERGENCE
        ) == 0
        job.status = "completed"
        job.summary_json = {
            **(job.summary_json if isinstance(job.summary_json, dict) else {}),
            "counts_by_divergence_class": counts,
            "writes_applied": writes_applied,
            "writes_skipped": writes_skipped,
            "resumed": True,
            "resumed_raw_ids": missing,
            "replay_fingerprints": fingerprints,
            "replay_converged": replay_converged,
            "replay_convergence_evidence": {
                "scope_size": len(job.scope_raw_record_ids),
                "receipts_written": len(all_receipts),
                "forbidden_divergence_total": sum(int(counts.get(k, 0) or 0) for k in FORBIDDEN_MATERIALIZE_DIVERGENCE),
            },
            "topology_materialization_plan": {
                "topology_stage_count": plan.get("topology_stage_count"),
                "stage_sizes": plan.get("stage_sizes"),
                "replay_blocker_count": plan.get("replay_blocker_count"),
            },
            "replay_runtime_schema_version": REPLAY_RUNTIME_SCHEMA_VERSION,
        }
        job.completed_at = datetime.now(UTC)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            sync_replay_job_into_canonical_failure_cases,
        )

        sync_replay_job_into_canonical_failure_cases(db, job=job)
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(UTC)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            record_replay_job_execution_failed,
        )

        record_replay_job_execution_failed(db, job=job, error=str(exc))
        db.commit()
        raise

    out = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
    assert out is not None
    return out
