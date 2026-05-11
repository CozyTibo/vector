"""Phase 03 Step 15 — deterministic canonical verification (invariant gates + oracle harness).

Normative: `DOCS/cortex/03-canonical/phase-03-verification-engine-doctrine.md`,
`phase-03-closure-gates-doctrine.md` (G-P03-01,02,03,04,06,08,09,10 subset).
Phase 04 P04-02: **`G-P04-08`** topology-vs-meaning static gate (`vector.domains.cortex.identity.boundary_checks`).
Phase 04 P04-03: **`G-P04-ORG-01`** org entity determinism static gate.
Phase 04 P04-04: **`G-P04-LINK-01`** (static) + **`G-P04-06`** (persisted link ledger rows) via `vector.domains.cortex.identity.link_ledger`.  
Phase 04 P04-05: **`G-P04-04`** / **`G-P04-05`** (static hash contracts), **`G-P04-CAND-01`** (promotion audit), `candidate_generation` / `authoritative_writer`, Celery **`vector.cortex.identity.regenerate_link_candidates`** / **`replay_authoritative_links`**.  
Phase 04 P04-06: **`G-P04-MRG-01`** (static human-merge policy), **`G-P04-01`** (persisted human merge completeness), **`G-P04-13`** (compensating merge chain + append-only contract), `merge_governance`.  
Phase 04 P04-07: **`G-P04-02`** (merge-closure link-class whitelist static), **`G-P04-HINT-01`** (non-truth rows use `non_authoritative` authority plane), `link_classes` / `link_ledger`.  
Phase 04 P04-08: **`G-P04-TMP-01`** (half-open axis static checks + persisted authoritative overlap scan), **`G-P04-11`** (soft revocation tombstone contract static), `org_link_temporal` / `link_ledger`.  
Phase 04 P04-09: **`G-P04-BNDL-01`** (bundle-pair static contract + declaration integrity), **`G-P04-03`** (cross-bundle link metadata requires active declaration), **`G-P04-14`** (replay `replay_ordinal` monotonicity), `bundle_equivalence`.  
Phase 04 P04-10: **`G-P04-RPL-01`** (org link continuity replay: deterministic regen hash static + completed jobs must carry receipts), `org_link_replay_runtime`.  
Phase 04 P04-11: **`G-P04-RULE-01`** (linkage rule manifest hashing static + persisted manifest integrity + candidate batch pins), `linkage_rules`.  
Phase 04 P04-12: **`G-P04-09`** (execution primitive evidence discipline static), **`G-P04-PRIM-01`** (no persisted primitive without valid raw evidence ids), `identity.execution_primitives`.
Phase 04 P04-13: **`G-P04-10`** (org graph export boundary + static contract), **`G-P04-EXP-01`** (export JSON hash determinism static + per-tenant rebuild), `identity.projection_export`.
Phase 04 P04-14: **`G-P04-AMB-01`** (org ambiguity integrity static + persisted entity refs), **`G-P04-12`** (open org-ambiguity pressure warn), `identity.org_ambiguity`.
Phase 04 P04-15: **`G-P04-VER-01`** (Phase 04 normative gate tuple + verification metadata catalog coherence), `identity.verification` + optional **`cortex_org_verification_runs`** slice persistence.
Phase 04 P04-16: **`G-P04-19`** (org failure registry sync completeness), `identity.failure_remediation` + **`cortex_org_failure_cases`** / **`cortex_org_remediation_validations`**.
Phase 04 P04-17: **`G-P04-18`** (control-plane replay freshness + last-job pointers), **`G-P04-21`** (**identity_control_plane_v1** aggregate contract), `identity.control_plane`.
Phase 04 P04-18: **`G-P04-22`**–**`G-P04-26`** (operator console: link explorer filters, POST audit discipline, ambiguity queue honesty, projection preview metadata, primitive list without raw blob), `identity.operator_console_verification`.
Phase 04 P04-20: **`G-P04-BF-01`** (anchor→handle backfill lane must not touch authoritative org links), `identity.backfill`.
Phase 04 P04-21: **`G-P04-ECO-01`** (identity readiness economics / explosion posture; warn_only), `identity.readiness_economics`.
Phase 04 P04-22: **`G-P04-CLOSE-01`** (org identity closure certification pack), `identity.org_identity_certification_pack`.
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
from vector.domains.cortex.identity.bundle_equivalence import (
    bundle_equivalence_pair_static_errors,
    list_bundle_equivalence_bndl01_violations,
    list_bundle_equivalence_gp04_14_replay_order_violations,
    list_org_links_missing_cross_bundle_equivalence,
)
from vector.domains.cortex.identity.boundary_checks import verify_topology_meaning_boundary_static
from vector.domains.cortex.identity.candidate_generation import (
    verify_authoritative_replay_hash_static,
    verify_candidate_regen_hash_static,
)
from vector.domains.cortex.identity.link_classes import verify_merge_closure_excludes_non_authoritative_link_classes_static
from vector.domains.cortex.identity.link_ledger import (
    list_authoritative_temporal_overlap_violations_for_tenant,
    list_links_failing_evidence_or_rule,
    list_links_violating_hint_authority_invariant,
    verify_link_ledger_evidence_rule_static,
)
from vector.domains.cortex.identity.execution_primitives import (
    list_org_primitive_instances_missing_evidence,
    verify_gp04_09_primitive_evidence_discipline_static,
    verify_gp04_prim01_static_evidence_contract,
)
from vector.domains.cortex.identity.org_ambiguity import (
    ORG_AMBIGUITY_OPEN_WARN_THRESHOLD,
    count_open_org_ambiguity_records,
    list_org_ambiguity_records_invalid_entity_refs,
    verify_gp04_amb01_org_ambiguity_integrity_static,
)
from vector.domains.cortex.identity.projection_export import (
    verify_gp04_10_graph_boundary_export_contract_static,
    verify_gp04_exp01_export_hash_determinism_static,
    verify_org_graph_projection_twice_same_hash,
)
from vector.domains.cortex.identity.linkage_rules import (
    list_candidate_batches_with_rule_version_reference_errors,
    list_link_rule_version_manifest_mismatches,
    verify_link_rule_rule01_static,
)
from vector.domains.cortex.identity.org_link_replay_runtime import (
    list_completed_org_link_replay_jobs_missing_receipts,
    verify_org_link_replay_rpl01_static,
)
from vector.domains.cortex.identity.org_link_temporal import (
    org_link_temporal_axis_static_errors,
    verify_link_ledger_soft_revocation_tombstone_static,
)
from vector.domains.cortex.identity.merge_governance import (
    list_compensating_merges_with_broken_supersedes,
    list_human_merges_missing_dual_evidence_policy,
    verify_human_merge_two_persona_evidence_policy_static,
    verify_merge_rollback_via_compensating_only_static,
)
from vector.domains.cortex.identity.org_entities import verify_org_entity_determinism_static
from vector.domains.cortex.identity.control_plane import (
    verify_gp04_18_org_control_plane_replay_freshness,
    verify_gp04_21_identity_control_plane_aggregate,
)
from vector.domains.cortex.identity.operator_console_verification import (
    verify_gp04_22_link_explorer_filters_session,
    verify_gp04_23_operator_console_audit_discipline_static,
    verify_gp04_24_org_ambiguity_queue_honesty,
    verify_gp04_25_projection_preview_metadata_only,
    verify_gp04_26_primitive_default_list_shape,
)
from vector.domains.cortex.identity.failure_remediation import verify_gp04_19_org_failure_registry_sync
from vector.domains.cortex.identity.verification import verify_gp04_ver01_phase04_catalog_coherence_static
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

CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION: Final[int] = 2
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


def _gate_gp04_01_human_merge_dual_evidence_policy(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-01 — persisted human_actor_merge rows satisfy merge_record + dual evidence + operator."""
    bad = list_human_merges_missing_dual_evidence_policy(session, tenant_id=tenant_id)
    return {
        "id": "G-P04-01",
        "name": "human_merge_merge_record_and_dual_evidence",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {
            "violation_count": len(bad),
            "sample_merge_ids": [str(x.id) for x in bad[:20]],
        },
    }


def _gate_gp04_13_compensating_merge_chain(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-13 — compensating merges reference valid prior merge rows (append-only rollback path)."""
    static = verify_merge_rollback_via_compensating_only_static()
    broken = list_compensating_merges_with_broken_supersedes(session, tenant_id=tenant_id)
    passed = bool(static.get("passed")) and len(broken) == 0
    return {
        "id": "G-P04-13",
        "name": "merge_rollback_compensating_chain",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            **(static.get("detail") or {}),
            "broken_supersedes_count": len(broken),
            "sample_merge_ids": [str(x.id) for x in broken[:20]],
        },
    }


def _gate_gp04_cand01_promotion_audit(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-CAND-01 — promoted authoritative links must reference tenant-aligned policy + candidate."""
    from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
    from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
    from vector.infrastructure.db.models.cortex_org_link_promotion_policy import CortexOrgLinkPromotionPolicy

    rows = list(
        session.scalars(
            select(CortexOrgLink).where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.promoted_from_candidate_id.isnot(None),
            )
        ).all()
    )
    errors: list[str] = []
    for r in rows:
        if r.promotion_policy_id is None:
            errors.append(f"missing_policy:{r.id}")
            continue
        cand = session.get(CortexOrgLinkCandidate, r.promoted_from_candidate_id)
        pol = session.get(CortexOrgLinkPromotionPolicy, r.promotion_policy_id)
        if cand is None or cand.tenant_id != r.tenant_id:
            errors.append(f"candidate_tenant_mismatch:{r.id}")
        if pol is None or pol.tenant_id != r.tenant_id:
            errors.append(f"policy_tenant_mismatch:{r.id}")
    return {
        "id": "G-P04-CAND-01",
        "name": "candidate_promotion_requires_policy",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors[:40], "promoted_link_count": len(rows)},
    }


def _gate_gp04_hint01_non_truth_authority_plane(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-HINT-01 — hint/inferred/prohibited rows must not use authoritative authority plane."""
    bad = list_links_violating_hint_authority_invariant(session, tenant_id=tenant_id)
    return {
        "id": "G-P04-HINT-01",
        "name": "hint_link_class_non_authoritative_authority",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {
            "violation_count": len(bad),
            "sample_link_ids": [str(x.id) for x in bad[:20]],
        },
    }


def _gate_gp04_bndl01_bundle_equivalence_integrity(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-BNDL-01 — ordered bundle-pair static contract + no duplicate replay ordinals per tenant."""
    static_errors = bundle_equivalence_pair_static_errors()
    dupes = list_bundle_equivalence_bndl01_violations(session, tenant_id=tenant_id)
    passed = len(static_errors) == 0 and len(dupes) == 0
    return {
        "id": "G-P04-BNDL-01",
        "name": "bundle_equivalence_integrity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"static_errors": static_errors, "duplicate_replay_ordinals": dupes[:40]},
    }


def _gate_gp04_03_cross_bundle_requires_declaration(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-03 — authoritative links with cross_bundle_canonical must have active equivalence row."""
    bad = list_org_links_missing_cross_bundle_equivalence(session, tenant_id=tenant_id)
    return {
        "id": "G-P04-03",
        "name": "cross_bundle_edge_requires_equivalence_declaration",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {
            "violation_count": len(bad),
            "sample_link_ids": [str(x.id) for x in bad[:20]],
        },
    }


def _gate_gp04_09_execution_primitive_evidence_discipline(
    _session: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """G-P04-09 — deterministic primitive keys + evidence id validation rules (static)."""
    st = verify_gp04_09_primitive_evidence_discipline_static()
    detail = dict(st.get("detail") or {})
    detail["tenant_id"] = str(tenant_id)
    return {**st, "detail": detail}


def _gate_gp04_prim01_org_primitive_instances(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-PRIM-01 — static evidence contract + no persisted primitive rows missing evidence."""
    st = verify_gp04_prim01_static_evidence_contract()
    bad = list_org_primitive_instances_missing_evidence(session, tenant_id=tenant_id)
    passed = bool(st.get("passed")) and len(bad) == 0
    detail = dict(st.get("detail") or {})
    detail["static_gate_passed"] = st.get("passed")
    detail["primitive_instance_ids_missing_evidence"] = [str(x) for x in bad[:40]]
    return {
        "id": "G-P04-PRIM-01",
        "name": "org_execution_primitive_evidence_integrity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": detail,
    }


def _gate_gp04_10_org_graph_export_boundary(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-10 — static org graph projection boundary + schema contract."""
    st = verify_gp04_10_graph_boundary_export_contract_static()
    detail = dict(st.get("detail") or {})
    detail["tenant_id"] = str(tenant_id)
    return {**st, "detail": detail}


def _gate_gp04_amb01_org_ambiguity_integrity(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-AMB-01 — static org ambiguity vocab + no persisted rows with broken org entity refs."""
    st = verify_gp04_amb01_org_ambiguity_integrity_static()
    bad = list_org_ambiguity_records_invalid_entity_refs(session, tenant_id=tenant_id)
    passed = bool(st.get("passed")) and len(bad) == 0
    detail = dict(st.get("detail") or {})
    detail["static_gate_passed"] = st.get("passed")
    detail["invalid_entity_ref_record_ids"] = [str(x) for x in bad[:40]]
    detail["tenant_id"] = str(tenant_id)
    return {
        "id": "G-P04-AMB-01",
        "name": "org_ambiguity_record_integrity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": detail,
    }


def _gate_gp04_12_org_ambiguity_open_pressure(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-12 — warn when open org-ambiguity backlog crosses pressure threshold (Phase 03 parity)."""
    n_open = count_open_org_ambiguity_records(session, tenant_id=tenant_id)
    warn = n_open >= ORG_AMBIGUITY_OPEN_WARN_THRESHOLD
    return {
        "id": "G-P04-12",
        "name": "org_ambiguity_open_backlog_pressure",
        "passed": not warn,
        "severity": "warn_only",
        "detail": {
            "tenant_id": str(tenant_id),
            "open_org_ambiguity_count": n_open,
            "warn_threshold": ORG_AMBIGUITY_OPEN_WARN_THRESHOLD,
        },
    }


def _gate_gp04_exp01_org_graph_export_determinism(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-EXP-01 — static fixture hash + per-tenant double-build identical hash."""
    st_static = verify_gp04_exp01_export_hash_determinism_static()
    twin = verify_org_graph_projection_twice_same_hash(session, tenant_id=tenant_id)
    passed = bool(st_static.get("passed")) and bool(twin.get("passed"))
    return {
        "id": "G-P04-EXP-01",
        "name": "org_graph_projection_export_stable_hash",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "tenant_id": str(tenant_id),
            "static": st_static.get("detail"),
            "tenant_rebuild": twin.get("detail"),
        },
    }


def _gate_gp04_rule01_linkage_rule_versions(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-RULE-01 — deterministic manifest hash (static) + stored manifest_sha256 integrity + batch pins."""
    st = verify_link_rule_rule01_static()
    bad_manifest = list_link_rule_version_manifest_mismatches(session, tenant_id=tenant_id)
    bad_batches = list_candidate_batches_with_rule_version_reference_errors(session, tenant_id=tenant_id)
    passed = bool(st.get("passed")) and len(bad_manifest) == 0 and len(bad_batches) == 0
    detail = dict(st.get("detail") or {})
    detail["static_gate_passed"] = st.get("passed")
    detail["manifest_mismatch_rule_version_ids"] = [str(x) for x in bad_manifest[:40]]
    detail["candidate_batch_reference_errors"] = [str(x) for x in bad_batches[:40]]
    return {
        "id": "G-P04-RULE-01",
        "name": "linkage_rule_versions_integrity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": detail,
    }


def _gate_gp04_rpl01_org_link_continuity_replay(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-RPL-01 — deterministic candidate regen hash (static) + receipt discipline on completed jobs."""
    st = verify_org_link_replay_rpl01_static()
    bad = list_completed_org_link_replay_jobs_missing_receipts(session, tenant_id=tenant_id)
    passed = bool(st.get("passed")) and len(bad) == 0
    detail = dict(st.get("detail") or {})
    detail["completed_jobs_missing_receipts"] = [str(x) for x in bad[:40]]
    detail["static_gate_passed"] = st.get("passed")
    return {
        "id": "G-P04-RPL-01",
        "name": "org_link_continuity_replay_regen_determinism",
        "passed": passed,
        "severity": "hard_fail",
        "detail": detail,
    }


def _gate_gp04_14_bundle_equivalence_replay_ordering(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-14 — non-revoked declarations have strictly increasing replay_ordinal along creation order."""
    bad = list_bundle_equivalence_gp04_14_replay_order_violations(session, tenant_id=tenant_id)
    return {
        "id": "G-P04-14",
        "name": "bundle_equivalence_replay_ordering",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {"violations": bad[:40]},
    }


def _gate_gp04_tmp01_org_link_temporal_integrity(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-TMP-01 — half-open axis static contract + no overlapping authoritative validity on same edge."""
    static_errors = org_link_temporal_axis_static_errors()
    overlaps = list_authoritative_temporal_overlap_violations_for_tenant(session, tenant_id=tenant_id)
    passed = len(static_errors) == 0 and len(overlaps) == 0
    return {
        "id": "G-P04-TMP-01",
        "name": "org_link_temporal_integrity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "static_errors": static_errors,
            "overlap_count": len(overlaps),
            "overlap_pairs": overlaps[:40],
        },
    }


def _gate_gp04_19_org_failure_registry_sync(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-19 — org derived failure signals stay aligned with ``cortex_org_failure_cases``."""
    return verify_gp04_19_org_failure_registry_sync(session, tenant_id=tenant_id)


def _gate_gp04_18_org_control_plane_replay_freshness(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-18 — org identity control-plane freshness matches replay job ledger."""
    return verify_gp04_18_org_control_plane_replay_freshness(session, tenant_id=tenant_id)


def _gate_gp04_21_identity_control_plane_aggregate(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-21 — **identity_control_plane_v1** includes all dashboard cards + required keys."""
    return verify_gp04_21_identity_control_plane_aggregate(session, tenant_id=tenant_id)


def _gate_gp04_22_link_explorer_filters(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-22 — link ledger explorer accepts all §9.2 filter dimensions."""
    return verify_gp04_22_link_explorer_filters_session(session, tenant_id=tenant_id)


def _gate_gp04_23_operator_console_audit_discipline(
    _session: Session, *, tenant_id: uuid.UUID
) -> dict[str, Any]:
    """G-P04-23 — operator-console dangerous POST surfaces declare audited action kinds."""
    st = verify_gp04_23_operator_console_audit_discipline_static()
    det = dict(st.get("detail") or {})
    det["tenant_id"] = str(tenant_id)
    return {**st, "detail": det}


def _gate_gp04_24_org_ambiguity_queue_honesty(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-24 — non-zero open ambiguity backlog implies listability."""
    return verify_gp04_24_org_ambiguity_queue_honesty(session, tenant_id=tenant_id)


def _gate_gp04_25_projection_preview_metadata_only(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-25 — projection preview response is metadata-only (allowlisted keys)."""
    return verify_gp04_25_projection_preview_metadata_only(session, tenant_id=tenant_id)


def _gate_gp04_26_primitive_default_list_shape(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-26 — primitive explorer default rows omit raw envelope JSON."""
    return verify_gp04_26_primitive_default_list_shape(session, tenant_id=tenant_id)


def _gate_gp04_ver01_phase04_catalog_coherence(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-VER-01 — static Phase 04 normative registry + verification metadata includes VER-01."""
    st = verify_gp04_ver01_phase04_catalog_coherence_static()
    det = st.get("detail") if isinstance(st.get("detail"), dict) else {}
    return {**st, "detail": {**det, "tenant_id": str(tenant_id)}}


def _gate_gp04_06_persisted_links_evidence_or_rule(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-06 — persisted org links must carry raw evidence ids or explicit rule_id."""
    bad = list_links_failing_evidence_or_rule(session, tenant_id=tenant_id)
    return {
        "id": "G-P04-06",
        "name": "org_link_evidence_or_rule_persisted",
        "passed": len(bad) == 0,
        "severity": "hard_fail",
        "detail": {
            "violation_count": len(bad),
            "sample_link_ids": [str(x.id) for x in bad[:20]],
        },
    }


def _gate_gp04_bf01_anchor_backfill_no_authoritative_links(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-BF-01 — Phase 03 anchor backfill lane must not touch authoritative org links."""
    from vector.domains.cortex.identity.backfill import verify_gp04_bf01_no_authoritative_links_on_backfill_handles

    return verify_gp04_bf01_no_authoritative_links_on_backfill_handles(session, tenant_id=tenant_id)


def _gate_gp04_eco01_identity_readiness_economics(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-ECO-01 — tenant economics probes (critical posture surfaces as gate failure; warn_only)."""
    from vector.domains.cortex.identity.readiness_economics import verify_gp04_eco01_identity_readiness_economics

    return verify_gp04_eco01_identity_readiness_economics(session, tenant_id=tenant_id)


def _canonical_verification_gate_results_core(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int,
) -> tuple[list[dict[str, Any]], list[CortexCanonicalTransformMaterialization]]:
    """All canonical verification gates **except** G-P04-CLOSE-01 (avoids recursion with org certification pack)."""
    lim = max(1, min(int(materialization_sample_limit), 200))
    mats = _sample_materializations(session, tenant_id=tenant_id, limit=lim)

    gates_core: list[dict[str, Any]] = [
        _gate_oracle_manifest_static(),
        verify_topology_meaning_boundary_static(),
        verify_org_entity_determinism_static(),
        verify_link_ledger_evidence_rule_static(),
        verify_candidate_regen_hash_static(),
        verify_authoritative_replay_hash_static(),
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
        _gate_gp04_06_persisted_links_evidence_or_rule(session, tenant_id=tenant_id),
        _gate_gp04_bf01_anchor_backfill_no_authoritative_links(session, tenant_id=tenant_id),
        _gate_gp04_cand01_promotion_audit(session, tenant_id=tenant_id),
        verify_human_merge_two_persona_evidence_policy_static(),
        _gate_gp04_01_human_merge_dual_evidence_policy(session, tenant_id=tenant_id),
        _gate_gp04_13_compensating_merge_chain(session, tenant_id=tenant_id),
        verify_merge_closure_excludes_non_authoritative_link_classes_static(),
        _gate_gp04_hint01_non_truth_authority_plane(session, tenant_id=tenant_id),
        _gate_gp04_tmp01_org_link_temporal_integrity(session, tenant_id=tenant_id),
        verify_link_ledger_soft_revocation_tombstone_static(),
        _gate_gp04_bndl01_bundle_equivalence_integrity(session, tenant_id=tenant_id),
        _gate_gp04_03_cross_bundle_requires_declaration(session, tenant_id=tenant_id),
        _gate_gp04_14_bundle_equivalence_replay_ordering(session, tenant_id=tenant_id),
        _gate_gp04_rpl01_org_link_continuity_replay(session, tenant_id=tenant_id),
        _gate_gp04_rule01_linkage_rule_versions(session, tenant_id=tenant_id),
        _gate_gp04_09_execution_primitive_evidence_discipline(session, tenant_id=tenant_id),
        _gate_gp04_prim01_org_primitive_instances(session, tenant_id=tenant_id),
        _gate_gp04_10_org_graph_export_boundary(session, tenant_id=tenant_id),
        _gate_gp04_exp01_org_graph_export_determinism(session, tenant_id=tenant_id),
        _gate_gp04_amb01_org_ambiguity_integrity(session, tenant_id=tenant_id),
        _gate_gp04_12_org_ambiguity_open_pressure(session, tenant_id=tenant_id),
        _gate_gp04_ver01_phase04_catalog_coherence(session, tenant_id=tenant_id),
        _gate_gp04_19_org_failure_registry_sync(session, tenant_id=tenant_id),
        _gate_gp04_18_org_control_plane_replay_freshness(session, tenant_id=tenant_id),
        _gate_gp04_21_identity_control_plane_aggregate(session, tenant_id=tenant_id),
        _gate_gp04_22_link_explorer_filters(session, tenant_id=tenant_id),
        _gate_gp04_23_operator_console_audit_discipline(session, tenant_id=tenant_id),
        _gate_gp04_24_org_ambiguity_queue_honesty(session, tenant_id=tenant_id),
        _gate_gp04_25_projection_preview_metadata_only(session, tenant_id=tenant_id),
        _gate_gp04_26_primitive_default_list_shape(session, tenant_id=tenant_id),
        _gate_gp04_eco01_identity_readiness_economics(session, tenant_id=tenant_id),
    ]
    return gates_core, mats


def _gate_gp04_close01_org_identity_closure_pack(
    session: Session, *, tenant_id: uuid.UUID, snapshot: dict[str, Any]
) -> dict[str, Any]:
    """G-P04-CLOSE-01 — Phase 04 org certification pack contract + closure matrix (hard_fail)."""
    from vector.domains.cortex.identity.org_identity_certification_pack import (
        build_org_identity_certification_pack_from_snapshot,
        overall_org_identity_closure_passed,
    )

    pack = build_org_identity_certification_pack_from_snapshot(session, tenant_id=tenant_id, snapshot=snapshot)
    contract = pack.get("org_identity_certification_pack_contract")
    ok = (
        overall_org_identity_closure_passed(pack)
        and isinstance(contract, dict)
        and bool(contract.get("passed"))
    )
    return {
        "id": "G-P04-CLOSE-01",
        "name": "phase04_org_closure_certification_pack",
        "passed": ok,
        "severity": "hard_fail",
        "detail": {
            "tenant_id": str(tenant_id),
            "org_certification_pack_schema_version": pack.get("org_certification_pack_schema_version"),
            "contract": contract,
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
    gates_core, mats = _canonical_verification_gate_results_core(
        session,
        tenant_id=tenant_id,
        materialization_sample_limit=materialization_sample_limit,
    )
    passed_core = all(
        bool(g.get("passed")) for g in gates_core if isinstance(g, dict) and g.get("severity") == "hard_fail"
    )
    evidence: dict[str, Any] = {
        "materializations_sampled": len(mats),
        "oracle_vectors_count": len(oracle_vectors()),
        "engine_build_clock": datetime.now(tz=UTC).isoformat(),
    }

    _ver_schema = CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION
    snap: dict[str, Any] = {
        "passed": passed_core,
        "gates": gates_core,
        "evidence": evidence,
        "canonical_verification_engine_schema_version": _ver_schema,
    }
    close_gate = _gate_gp04_close01_org_identity_closure_pack(session, tenant_id=tenant_id, snapshot=snap)
    gates = [*gates_core, close_gate]

    # Warn-only gates do not block overall PASS.
    passed = all(g["passed"] for g in gates if g.get("severity") == "hard_fail")

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
