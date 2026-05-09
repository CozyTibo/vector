"""Phase 03 Step 15 — deterministic canonical verification (invariant gates + oracle harness).

Normative: `DOCS/cortex/03-canonical/phase-03-verification-engine-doctrine.md`,
`phase-03-closure-gates-doctrine.md` (G-P03-01,02,03,04,06,08,09,10 subset).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.canonical.logical_keys import logical_key_fields_for_kind
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.oracle_manifest import (
    oracle_vectors,
    validate_oracle_manifest_internal_consistency,
)
from vector.domains.cortex.canonical.transform_runtime import (
    MaterializeError,
    resolve_materialization_input,
)
from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import (
    CortexCanonicalAmbiguityRecord,
)
from vector.infrastructure.db.models.cortex_canonical_provenance_record import (
    CortexCanonicalProvenanceRecord,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import (
    CortexCanonicalReplayJobReceipt,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_canonical_verification_run import (
    CortexCanonicalVerificationRun,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle

CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION: Final[int] = 1
_FORBIDDEN_REPLAY: Final[frozenset[str]] = frozenset({"C3", "C4", "C5"})
_AMBIGUITY_WARN_THRESHOLD: Final[int] = 5000


def verification_run_public_dict(row: CortexCanonicalVerificationRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "engine_schema_version": row.engine_schema_version,
        "passed": row.passed,
        "gates_json": list(row.gates_json),
        "evidence_json": dict(row.evidence_json),
        "created_at": row.created_at,
    }


def _sample_materializations(
    session: Session, *, tenant_id: uuid.UUID, limit: int
) -> list[CortexCanonicalTransformMaterialization]:
    lim = max(1, min(limit, 200))
    return list(
        session.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
            .options(
                selectinload(CortexCanonicalTransformMaterialization.field_lineage),
            )
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.canonical_processed_at.desc()),
                CortexCanonicalTransformMaterialization.created_at.desc(),
            )
            .limit(lim)
        ).all()
    )


def _gate_oracle_manifest_static() -> dict[str, Any]:
    """G-P03-10 — frozen oracle vectors internally consistent (structural key-shape)."""
    try:
        validate_oracle_manifest_internal_consistency()
    except AssertionError as exc:
        return {
            "id": "G-P03-10",
            "name": "oracle_key_stability_harness",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"error": str(exc)},
        }
    vecs = oracle_vectors()
    mismatches: list[dict[str, Any]] = []
    for vec in vecs:
        for lk in vec.get("expected_logical_keys") or []:
            try:
                kind = CanonicalObjectKind(lk["canonical_object_kind"])
            except ValueError as exc:
                mismatches.append({"fixture_id": vec["fixture_id"], "error": str(exc)})
                continue
            expected_fields = list(logical_key_fields_for_kind(kind))
            got = lk.get("tuple_field_names")
            if got != expected_fields:
                mismatches.append(
                    {
                        "fixture_id": vec["fixture_id"],
                        "kind": kind.value,
                        "expected_fields": expected_fields,
                        "tuple_field_names": got,
                    }
                )
    passed = len(mismatches) == 0
    return {
        "id": "G-P03-10",
        "name": "oracle_key_stability_harness",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "vectors_checked": len(vecs),
            "logical_key_shape_mismatches": mismatches[:20],
            "mismatch_count": len(mismatches),
        },
    }


def _gate_gp03_01_determinism(
    session: Session, *, tenant_id: uuid.UUID, mats: list[CortexCanonicalTransformMaterialization]
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for mat in mats:
        try:
            res = resolve_materialization_input(
                session,
                tenant_id=tenant_id,
                bundle_id=mat.bundle_id,
                raw_record_id=int(mat.raw_record_id),
            )
        except MaterializeError as exc:
            mismatches.append(
                {
                    "materialization_id": str(mat.id),
                    "raw_record_id": mat.raw_record_id,
                    "reason": "oracle_resolution_failed",
                    "error": str(exc),
                }
            )
            continue
        lk_ok = res.logical_key_hash == mat.logical_key_hash
        snap_ok = res.emitted_snapshot_hash == mat.emitted_snapshot_hash
        if not (lk_ok and snap_ok):
            mismatches.append(
                {
                    "materialization_id": str(mat.id),
                    "raw_record_id": mat.raw_record_id,
                    "stored_logical_key_hash": mat.logical_key_hash,
                    "oracle_logical_key_hash": res.logical_key_hash,
                    "stored_snapshot_hash": mat.emitted_snapshot_hash,
                    "oracle_snapshot_hash": res.emitted_snapshot_hash,
                }
            )
    return {
        "id": "G-P03-01",
        "name": "determinism_oracle_vs_stored",
        "passed": len(mismatches) == 0,
        "severity": "hard_fail",
        "detail": {
            "sample_size": len(mats),
            "mismatches": mismatches[:30],
            "mismatch_count": len(mismatches),
        },
    }


def _gate_gp03_02_provenance_and_lineage(
    session: Session, *, tenant_id: uuid.UUID, mats: list[CortexCanonicalTransformMaterialization]
) -> dict[str, Any]:
    missing_prov: list[str] = []
    empty_primary: list[str] = []
    missing_lineage: list[str] = []
    for mat in mats:
        prov = session.scalars(
            select(CortexCanonicalProvenanceRecord).where(
                CortexCanonicalProvenanceRecord.materialization_id == mat.id
            )
        ).first()
        if prov is None:
            missing_prov.append(str(mat.id))
            continue
        if not prov.primary_raw_record_ids:
            empty_primary.append(str(mat.id))
        if not mat.field_lineage:
            missing_lineage.append(str(mat.id))
    issues = len(missing_prov) + len(empty_primary) + len(missing_lineage)
    return {
        "id": "G-P03-02",
        "name": "provenance_and_field_lineage",
        "passed": issues == 0,
        "severity": "hard_fail",
        "detail": {
            "sample_size": len(mats),
            "missing_provenance_materialization_ids": missing_prov[:25],
            "empty_primary_raw_ids": empty_primary[:25],
            "missing_field_lineage_materialization_ids": missing_lineage[:25],
            "issue_count": issues,
        },
    }


def _gate_gp03_03_replay_forbidden(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    jobs = list(
        session.scalars(
            select(CortexCanonicalReplayJob)
            .where(
                CortexCanonicalReplayJob.tenant_id == tenant_id,
                CortexCanonicalReplayJob.status == "completed",
            )
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(40)
        ).all()
    )
    bad_jobs: list[dict[str, Any]] = []
    for job in jobs:
        summary = job.summary_json if isinstance(job.summary_json, dict) else {}
        counts = summary.get("counts_by_divergence_class")
        if not isinstance(counts, dict):
            continue
        n = sum(int(counts.get(k, 0) or 0) for k in _FORBIDDEN_REPLAY)
        if n > 0:
            bad_jobs.append(
                {
                    "job_id": str(job.id),
                    "pinned_bundle_id": job.pinned_bundle_id,
                    "dry_run": bool(job.dry_run),
                    "counts_by_divergence_class": dict(counts),
                }
            )
    return {
        "id": "G-P03-03",
        "name": "replay_no_forbidden_divergence_recent_jobs",
        "passed": len(bad_jobs) == 0,
        "severity": "hard_fail",
        "detail": {"completed_jobs_scanned": len(jobs), "jobs_with_c3_c4_c5": bad_jobs[:15]},
    }


def _gate_gp03_04_ambiguity_backlog(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    n_open = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalAmbiguityRecord)
            .where(
                CortexCanonicalAmbiguityRecord.tenant_id == tenant_id,
                CortexCanonicalAmbiguityRecord.status == "open",
            )
        )
        or 0
    )
    warn = n_open >= _AMBIGUITY_WARN_THRESHOLD
    return {
        "id": "G-P03-04",
        "name": "ambiguity_open_backlog",
        "passed": not warn,
        "severity": "warn_only",
        "detail": {"open_ambiguity_count": n_open, "warn_threshold": _AMBIGUITY_WARN_THRESHOLD},
    }


def _gate_gp03_06_temporal_keys(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    n_bad = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.occurred_at.is_not(None),
                CortexCanonicalTransformMaterialization.temporal_ordering_key.is_(None),
            )
        )
        or 0
    )
    return {
        "id": "G-P03-06",
        "name": "temporal_ordering_key_present_when_occurred_at",
        "passed": n_bad == 0,
        "severity": "hard_fail",
        "detail": {"materializations_missing_ordering_key": n_bad},
    }


def _gate_gp03_08_duplicate_logical_keys(
    session: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    stmt = (
        select(
            CortexCanonicalTransformMaterialization.bundle_id,
            CortexCanonicalTransformMaterialization.logical_key_hash,
            func.count().label("n"),
        )
        .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        .group_by(
            CortexCanonicalTransformMaterialization.bundle_id,
            CortexCanonicalTransformMaterialization.logical_key_hash,
        )
        .having(func.count() > 1)
    )
    rows = list(session.execute(stmt).all())
    collisions = [
        {"bundle_id": r[0], "logical_key_hash": r[1], "count": int(r[2])} for r in rows[:40]
    ]
    return {
        "id": "G-P03-08",
        "name": "logical_key_collision_under_bundle",
        "passed": len(rows) == 0,
        "severity": "hard_fail",
        "detail": {"collision_groups": collisions, "collision_group_count": len(rows)},
    }


def _gate_gp03_09_registry_integrity(session: Session) -> dict[str, Any]:
    bad = list(
        session.scalars(
            select(CortexMappingBundle.bundle_id).where(
                CortexMappingBundle.lifecycle_state == "approved",
                CortexMappingBundle.manifest_hash == "",
            )
        ).all()
    )
    return {
        "id": "G-P03-09",
        "name": "approved_bundle_manifest_present",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {"approved_bundles_with_empty_manifest_hash": list(bad)[:20]},
    }


def _gate_gp03_17_stabilization_proof_contract(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-17 — stabilization / economics proof report satisfies structural contract."""
    from vector.domains.cortex.canonical.canonical_stabilization_proof import (
        build_stabilization_proof_report,
        verify_phase03_step17_stabilization_proof_contract,
    )

    report = build_stabilization_proof_report(session, tenant_id)
    vr = verify_phase03_step17_stabilization_proof_contract(report=report)
    return {
        "id": "G-P03-17",
        "name": "canonical_stabilization_proof_report_contract",
        "passed": bool(vr.get("passed")),
        "severity": "hard_fail",
        "detail": {"contract": vr},
    }


def _gate_gp03_21_certification_pack_contract(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-21 — Step 18 certification pack JSON satisfies structural contract (operator proof surface)."""
    from vector.domains.cortex.canonical.canonical_certification_pack import (
        build_canonical_certification_pack,
        verify_phase03_step18_certification_pack_contract,
    )

    pack = build_canonical_certification_pack(session, tenant_id=tenant_id)
    cr = verify_phase03_step18_certification_pack_contract(pack=pack)
    return {
        "id": "G-P03-21",
        "name": "canonical_certification_pack_contract",
        "passed": bool(cr.get("passed")),
        "severity": "hard_fail",
        "detail": {"contract": cr, "closure_gate_ids": [r.get("id") for r in pack.get("closure_gate_matrix") or []]},
    }


def _gate_gp03_16_operator_control_plane_contract(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-16 — aggregated operator control-plane payload satisfies structural contract."""
    from vector.domains.cortex.canonical.canonical_control_plane import (
        build_canonical_control_plane,
        verify_phase03_step16_canonical_control_plane_contract,
    )

    payload = build_canonical_control_plane(session, tenant_id)
    vr = verify_phase03_step16_canonical_control_plane_contract(control_plane_payload=payload)
    return {
        "id": "G-P03-16",
        "name": "canonical_operator_control_plane_contract",
        "passed": bool(vr.get("passed")),
        "severity": "hard_fail",
        "detail": {"contract": vr},
    }


def _gate_gp03_22_coverage_truth(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-22 — explicit ingest/routing/materialization coverage truth (no silent exclusions)."""
    from vector.domains.cortex.canonical.canonical_coverage_matrix import (
        build_canonical_coverage_matrix,
    )

    mx = build_canonical_coverage_matrix(session, tenant_id=tenant_id)
    rows = list(mx.get("rows") or [])
    ingest_rows = [r for r in rows if bool(r.get("ingest_supported"))]
    unsupported_rows = [r for r in ingest_rows if not bool(r.get("routable"))]
    routable_raw_no_materialization = [
        r
        for r in rows
        if bool(r.get("routable"))
        and int(r.get("tenant_raw_row_count") or 0) > 0
        and int(r.get("tenant_materialized_row_count") or 0) == 0
    ]
    ingest_total = len(ingest_rows)
    unsupported_pct = (len(unsupported_rows) / ingest_total * 100.0) if ingest_total > 0 else 0.0
    replay_certified_rows = [
        r
        for r in rows
        if bool(r.get("routable"))
        and str(r.get("oracle_coverage") or "").lower() not in {"none", "oracle_vector_pending"}
    ]
    return {
        "id": "G-P03-22",
        "name": "coverage_truth_no_silent_exclusions",
        "passed": len(routable_raw_no_materialization) == 0,
        "severity": "warn_only",
        "detail": {
            "matrix_row_count": int(mx.get("summary", {}).get("matrix_row_count", 0)),
            "routable_pair_count": int(mx.get("summary", {}).get("routable_pair_count", 0)),
            "ingest_only_pair_count": int(mx.get("summary", {}).get("ingest_only_pair_count", 0)),
            "unsupported_exhaust_pct": round(unsupported_pct, 2),
            "routable_raw_without_materialization_pairs": [
                f"{r.get('connector')}/{r.get('resource_type')}" for r in routable_raw_no_materialization[:50]
            ],
            "replay_certified_surface_pair_count": len(replay_certified_rows),
        },
    }


def _gate_gp03_23_execution_check_lifecycle(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-23 — execution_check lifecycle/status invariants."""
    mats = list(
        session.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(
                CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
                CortexCanonicalTransformMaterialization.canonical_object_kind
                == CanonicalObjectKind.EXECUTION_CHECK.value,
            )
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.canonical_processed_at.asc()),
                CortexCanonicalTransformMaterialization.created_at.asc(),
            )
        ).all()
    )
    if not mats:
        return {
            "id": "G-P03-23",
            "name": "execution_check_lifecycle_invariants",
            "passed": True,
            "severity": "hard_fail",
            "detail": {"execution_checks_scanned": 0},
        }

    transition_rank = {"queued": 0, "in_progress": 1, "completed": 2}
    last_rank_by_lk: dict[str, int] = {}
    active_count_by_lk_status: dict[tuple[str, str], int] = defaultdict(int)
    illegal_transitions: list[dict[str, Any]] = []
    completion_without_start: list[str] = []
    inconsistent_status_conclusion: list[str] = []
    invalid_temporal_ordering: list[str] = []

    for mat in mats:
        snap = mat.emitted_snapshot_json if isinstance(mat.emitted_snapshot_json, dict) else {}
        lk_hash = str(mat.logical_key_hash)
        status = str(snap.get("status") or "").strip().lower()
        conclusion_raw = snap.get("conclusion")
        conclusion = str(conclusion_raw).strip().lower() if conclusion_raw is not None else ""
        started_at = snap.get("started_at")
        completed_at = snap.get("completed_at")

        if status not in transition_rank:
            illegal_transitions.append(
                {
                    "materialization_id": str(mat.id),
                    "logical_key_hash": lk_hash,
                    "reason": "invalid_status",
                    "status": status,
                }
            )
            continue
        prior_rank = last_rank_by_lk.get(lk_hash)
        cur_rank = transition_rank[status]
        if prior_rank is not None and cur_rank < prior_rank:
            illegal_transitions.append(
                {
                    "materialization_id": str(mat.id),
                    "logical_key_hash": lk_hash,
                    "prior_rank": prior_rank,
                    "current_rank": cur_rank,
                    "status": status,
                }
            )
        last_rank_by_lk[lk_hash] = max(prior_rank, cur_rank) if prior_rank is not None else cur_rank

        if status in {"queued", "in_progress"}:
            active_count_by_lk_status[(lk_hash, status)] += 1
        if conclusion and status != "completed":
            inconsistent_status_conclusion.append(str(mat.id))
        if status == "completed" and not isinstance(started_at, str):
            completion_without_start.append(str(mat.id))
        if isinstance(started_at, str) and isinstance(completed_at, str):
            try:
                started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                completed_dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                if completed_dt < started_dt:
                    invalid_temporal_ordering.append(str(mat.id))
            except ValueError:
                invalid_temporal_ordering.append(str(mat.id))

    duplicate_active_identity_hashes = sorted(
        [k for (k, _status), v in active_count_by_lk_status.items() if v > 1]
    )
    issue_count = (
        len(illegal_transitions)
        + len(completion_without_start)
        + len(inconsistent_status_conclusion)
        + len(invalid_temporal_ordering)
        + len(duplicate_active_identity_hashes)
    )
    return {
        "id": "G-P03-23",
        "name": "execution_check_lifecycle_invariants",
        "passed": issue_count == 0,
        "severity": "hard_fail",
        "detail": {
            "execution_checks_scanned": len(mats),
            "illegal_status_transitions": illegal_transitions[:50],
            "completion_without_start_materialization_ids": completion_without_start[:50],
            "inconsistent_conclusion_status_materialization_ids": inconsistent_status_conclusion[:50],
            "invalid_temporal_ordering_materialization_ids": invalid_temporal_ordering[:50],
            "duplicate_active_identity_hashes": duplicate_active_identity_hashes[:50],
            "issue_count": issue_count,
        },
    }


def _gate_gp03_25_replay_convergence_evidence(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Completed replay jobs must declare replay_converged with matching receipt evidence when writes occurred."""
    jobs = list(
        session.scalars(
            select(CortexCanonicalReplayJob)
            .where(
                CortexCanonicalReplayJob.tenant_id == tenant_id,
                CortexCanonicalReplayJob.status == "completed",
            )
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(25)
        ).all()
    )
    bad: list[dict[str, Any]] = []
    for job in jobs:
        sj = job.summary_json if isinstance(job.summary_json, dict) else {}
        if not sj.get("replay_fingerprints"):
            continue
        if bool(sj.get("dry_run")):
            continue
        scope_n = len(job.scope_raw_record_ids or [])
        receipt_n = int(
            session.scalar(
                select(func.count())
                .select_from(CortexCanonicalReplayJobReceipt)
                .where(CortexCanonicalReplayJobReceipt.job_id == job.id)
            )
            or 0
        )
        converged = bool(sj.get("replay_converged"))
        ev = sj.get("replay_convergence_evidence") if isinstance(sj.get("replay_convergence_evidence"), dict) else {}
        ev_n = int(ev.get("receipts_written") or 0)
        if converged and (receipt_n != scope_n or ev_n != scope_n):
            bad.append({"job_id": str(job.id), "scope": scope_n, "receipts": receipt_n, "evidence_receipts": ev_n})
    return {
        "id": "G-P03-25",
        "name": "replay_convergence_evidence_consistent",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {"completed_jobs_scanned": len(jobs), "inconsistent": bad[:15]},
    }


def _gate_gp03_26_dormant_route_annotation(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Dormant routes must carry an explicit dormant_reason in coverage rows when marked dormant."""
    from vector.domains.cortex.canonical.canonical_coverage_matrix import build_canonical_coverage_matrix

    mx = build_canonical_coverage_matrix(session, tenant_id=tenant_id)
    rows = list(mx.get("rows") or [])
    dormant = [r for r in rows if bool(r.get("dormant"))]
    missing_reason = [r for r in dormant if not r.get("dormant_reason")]
    return {
        "id": "G-P03-26",
        "name": "dormant_routes_annotated",
        "passed": len(missing_reason) == 0,
        "severity": "warn_only",
        "detail": {
            "dormant_pair_count": len(dormant),
            "missing_dormant_reason": [f"{r.get('connector')}/{r.get('resource_type')}" for r in missing_reason[:40]],
        },
    }


def _gate_gp03_24_replay_topology_integrity(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P03-24 — dependency DAG integrity (cycles + orphaned children)."""
    from vector.domains.cortex.canonical.canonical_coverage_matrix import build_canonical_coverage_matrix

    mx = build_canonical_coverage_matrix(session, tenant_id=tenant_id)
    summary = mx.get("summary") or {}
    rows = list(mx.get("rows") or [])
    orphan_rows = [r for r in rows if int(r.get("orphan_count") or 0) > 0]
    cycle_detected = bool(summary.get("replay_dependency_cycle_detected"))
    orphan_count = int(summary.get("orphan_dependency_ref_count") or 0)
    return {
        "id": "G-P03-24",
        "name": "replay_topology_integrity",
        "passed": (not cycle_detected) and orphan_count == 0,
        "severity": "hard_fail",
        "detail": {
            "replay_dependency_cycle_detected": cycle_detected,
            "orphan_dependency_ref_count": orphan_count,
            "orphan_pairs": [f"{r.get('connector')}/{r.get('resource_type')}" for r in orphan_rows[:50]],
        },
    }


def run_canonical_verification(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
    persist: bool = False,
) -> dict[str, Any]:
    """Execute invariant gates for one tenant; optionally persist a verification run row."""
    lim = max(1, min(int(materialization_sample_limit), 200))
    mats = _sample_materializations(session, tenant_id=tenant_id, limit=lim)

    gates: list[dict[str, Any]] = [
        _gate_oracle_manifest_static(),
        _gate_gp03_09_registry_integrity(session),
        _gate_gp03_08_duplicate_logical_keys(session, tenant_id=tenant_id),
        _gate_gp03_06_temporal_keys(session, tenant_id=tenant_id),
        _gate_gp03_03_replay_forbidden(session, tenant_id=tenant_id),
        _gate_gp03_04_ambiguity_backlog(session, tenant_id=tenant_id),
        _gate_gp03_01_determinism(session, tenant_id=tenant_id, mats=mats),
        _gate_gp03_02_provenance_and_lineage(session, tenant_id=tenant_id, mats=mats),
        _gate_gp03_16_operator_control_plane_contract(session, tenant_id=tenant_id),
        _gate_gp03_17_stabilization_proof_contract(session, tenant_id=tenant_id),
        _gate_gp03_21_certification_pack_contract(session, tenant_id=tenant_id),
        _gate_gp03_22_coverage_truth(session, tenant_id=tenant_id),
        _gate_gp03_23_execution_check_lifecycle(session, tenant_id=tenant_id),
        _gate_gp03_24_replay_topology_integrity(session, tenant_id=tenant_id),
        _gate_gp03_25_replay_convergence_evidence(session, tenant_id=tenant_id),
        _gate_gp03_26_dormant_route_annotation(session, tenant_id=tenant_id),
    ]

    # Warn-only gates do not block overall PASS.
    passed = all(g["passed"] for g in gates if g.get("severity") == "hard_fail")

    evidence: dict[str, Any] = {
        "materializations_sampled": len(mats),
        "oracle_vectors_count": len(oracle_vectors()),
        "engine_build_clock": datetime.now(tz=UTC).isoformat(),
    }

    _ver_schema = CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION
    out: dict[str, Any] = {
        "canonical_verification_engine_schema_version": _ver_schema,
        "tenant_id": str(tenant_id),
        "passed": passed,
        "gates": gates,
        "evidence": evidence,
        "persisted_run_id": None,
    }

    if persist:
        row = CortexCanonicalVerificationRun(
            tenant_id=tenant_id,
            engine_schema_version=CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
            passed=passed,
            gates_json=gates,
            evidence_json=evidence,
        )
        session.add(row)
        session.flush()
        out["persisted_run_id"] = row.id

    return out


def list_canonical_verification_runs(
    session: Session, *, tenant_id: uuid.UUID, limit: int = 20
) -> list[CortexCanonicalVerificationRun]:
    lim = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(CortexCanonicalVerificationRun)
            .where(CortexCanonicalVerificationRun.tenant_id == tenant_id)
            .order_by(CortexCanonicalVerificationRun.created_at.desc())
            .limit(lim)
        ).all()
    )
