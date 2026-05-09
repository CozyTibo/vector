"""Phase 03 Step 18 — canonical closure certification pack + gate matrix (G-P03-14–G-P03-21).

Normative: `phase-03-closure-gates-doctrine.md`, `phase-03-canonical-control-plane-doctrine.md`.

Note: engine **G-P03-17** is the Step 17 stabilization proof *report* contract.
Closure doctrine also names **G-P03-17** for lineage visibility; the operator
slice is closure-matrix row **G-P03-17** here (not the engine gate).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session, selectinload

from vector.infrastructure.db.models.cortex_canonical_ambiguity_record import (
    CortexCanonicalAmbiguityRecord,
)
from vector.infrastructure.db.models.cortex_canonical_certification_archive import (
    CortexCanonicalCertificationArchive,
)
from vector.infrastructure.db.models.cortex_canonical_provenance_record import (
    CortexCanonicalProvenanceRecord,
)
from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob
from vector.infrastructure.db.models.cortex_canonical_stabilization_proof_run import (
    CortexCanonicalStabilizationProofRun,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_mapping_bundle_pin import CortexMappingBundlePin

CERTIFICATION_PACK_SCHEMA_VERSION: Final[int] = 1
_AMBIGUITY_HARD_THRESHOLD: Final[int] = 5000


def _sample_materializations(
    session: Session, *, tenant_id: uuid.UUID, limit: int
) -> list[CortexCanonicalTransformMaterialization]:
    lim = max(1, min(limit, 200))
    return list(
        session.scalars(
            select(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
            .options(selectinload(CortexCanonicalTransformMaterialization.field_lineage))
            .order_by(
                nullslast(CortexCanonicalTransformMaterialization.canonical_processed_at.desc()),
                CortexCanonicalTransformMaterialization.created_at.desc(),
            )
            .limit(lim)
        ).all()
    )


def _lineage_operator_gate_detail(
    session: Session, *, tenant_id: uuid.UUID, mats: list[CortexCanonicalTransformMaterialization]
) -> dict[str, Any]:
    """Closure-matrix G-P03-17: field lineage visible on sampled materializations."""
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
        "sample_size": len(mats),
        "missing_provenance_materialization_ids": missing_prov[:25],
        "empty_primary_raw_ids": empty_primary[:25],
        "missing_field_lineage_materialization_ids": missing_lineage[:25],
        "issue_count": issues,
    }


def _build_closure_rows(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    verification_excerpt: dict[str, Any],
    stabilization_excerpt: dict[str, Any],
    control_plane_contract: dict[str, Any],
    replay_excerpt: dict[str, Any],
    ambiguity_excerpt: dict[str, Any],
    mapping_excerpt: dict[str, Any],
    lineage_detail: dict[str, Any],
) -> list[dict[str, Any]]:
    mats_n = int(lineage_detail.get("sample_size") or 0)
    lineage_issues = int(lineage_detail.get("issue_count") or 0)

    # G-P03-14 — ops certification / stabilization evidence path
    stab_runs = list(
        session.scalars(
            select(CortexCanonicalStabilizationProofRun)
            .where(CortexCanonicalStabilizationProofRun.tenant_id == tenant_id)
            .order_by(
                CortexCanonicalStabilizationProofRun.created_at.desc(),
                CortexCanonicalStabilizationProofRun.id.desc(),
            )
            .limit(1)
        ).all()
    )
    last_stab_ok = bool(stab_runs and stab_runs[0].passed)
    live_stab_ok = bool(stabilization_excerpt.get("hard_fail_passed"))
    last_ver = verification_excerpt.get("last_verification_run")
    last_ver_ok = last_ver is None or bool(last_ver.get("passed"))
    gp14_passed = last_stab_ok or (live_stab_ok and last_ver_ok)

    # G-P03-15 — operator-visible divergence summary on completed replay jobs
    bad_drift: list[dict[str, Any]] = []
    for job in replay_excerpt.get("completed_jobs") or []:
        if not isinstance(job, dict):
            continue
        summary = job.get("summary_json") if isinstance(job.get("summary_json"), dict) else {}
        if not isinstance(summary.get("counts_by_divergence_class"), dict):
            bad_drift.append(
                {"job_id": job.get("job_id"), "reason": "missing_counts_by_divergence_class"}
            )
    gp15_passed = len(bad_drift) == 0

    gp16_passed = bool(control_plane_contract.get("passed"))

    gp17_passed = mats_n == 0 or lineage_issues == 0

    n_open = int(ambiguity_excerpt.get("open_ambiguity_count") or 0)
    gp18_passed = n_open < _AMBIGUITY_HARD_THRESHOLD

    gp19_passed = bool(mapping_excerpt.get("mapping_governance_visible"))

    gp20_passed = bool(replay_excerpt.get("replay_generation_auditable"))

    rows: list[dict[str, Any]] = [
        {
            "id": "G-P03-14",
            "name": "ops_certification_stabilization_path",
            "passed": gp14_passed,
            "severity": "hard_fail",
            "detail": {
                "last_persisted_stabilization_passed": last_stab_ok,
                "live_stabilization_hard_passed": live_stab_ok,
                "last_verification_passed_or_absent": last_ver_ok,
                "last_stabilization_run_id": stab_runs[0].id if stab_runs else None,
            },
        },
        {
            "id": "G-P03-15",
            "name": "no_hidden_rebuild_drift",
            "passed": gp15_passed,
            "severity": "hard_fail",
            "detail": {"jobs_missing_divergence_ledger": bad_drift[:20]},
        },
        {
            "id": "G-P03-16",
            "name": "no_opaque_canonical_generation_control_plane_contract",
            "passed": gp16_passed,
            "severity": "hard_fail",
            "detail": {"contract": control_plane_contract},
        },
        {
            "id": "G-P03-17",
            "name": "transform_lineage_operator_audited_sample",
            "passed": gp17_passed,
            "severity": "hard_fail",
            "detail": {
                **lineage_detail,
                "note": (
                    "Closure doctrine G-P03-17 (lineage visibility). "
                    "Engine gate G-P03-17 remains stabilization proof contract (Step 17)."
                ),
            },
        },
        {
            "id": "G-P03-18",
            "name": "ambiguity_visibility_no_explosion",
            "passed": gp18_passed,
            "severity": "hard_fail",
            "detail": {"open_ambiguity_count": n_open, "hard_threshold": _AMBIGUITY_HARD_THRESHOLD},
        },
        {
            "id": "G-P03-19",
            "name": "mapping_invalidation_visible",
            "passed": gp19_passed,
            "severity": "hard_fail",
            "detail": mapping_excerpt,
        },
        {
            "id": "G-P03-20",
            "name": "replay_generation_auditable",
            "passed": gp20_passed,
            "severity": "hard_fail",
            "detail": {"replay_jobs_excerpt": replay_excerpt},
        },
    ]
    return rows


def verify_phase03_step18_certification_pack_contract(*, pack: dict[str, Any]) -> dict[str, Any]:
    """Structural contract for Step 18 pack JSON (verification engine G-P03-21)."""
    errs: list[str] = []
    if pack.get("certification_pack_schema_version") != CERTIFICATION_PACK_SCHEMA_VERSION:
        errs.append("certification_pack_schema_version_mismatch")
    if str(pack.get("tenant_id") or "") == "":
        errs.append("tenant_id_missing")
    for key in (
        "built_at_clock",
        "closure_gate_matrix",
        "verification_matrix_excerpt",
        "stabilization_proof_excerpt",
        "control_plane_excerpt",
        "replay_jobs_excerpt",
        "ambiguity_excerpt",
        "mapping_registry_excerpt",
    ):
        if key not in pack:
            errs.append(f"missing_{key}")
    matrix = pack.get("closure_gate_matrix")
    if not isinstance(matrix, list):
        errs.append("closure_gate_matrix_not_list")
    else:
        ids = {r.get("id") for r in matrix if isinstance(r, dict)}
        for gid in (
            "G-P03-14",
            "G-P03-15",
            "G-P03-16",
            "G-P03-17",
            "G-P03-18",
            "G-P03-19",
            "G-P03-20",
            "G-P03-21",
        ):
            if gid not in ids:
                errs.append(f"missing_matrix_row_{gid}")
        for r in matrix:
            if not isinstance(r, dict):
                errs.append("matrix_row_not_object")
                continue
            for f in ("id", "name", "passed", "severity"):
                if f not in r:
                    errs.append(f"matrix_row_missing_{f}")
    ve = pack.get("verification_matrix_excerpt")
    if not isinstance(ve, dict) or "last_verification_run" not in ve:
        errs.append("verification_matrix_excerpt_shape")
    passed = len(errs) == 0
    return {"passed": passed, "errors": errs}


def build_canonical_certification_pack(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
) -> dict[str, Any]:
    """Assemble operator-visible excerpts + closure matrix (G-P03-14–G-P03-21) for one tenant."""
    from vector.domains.cortex.canonical.ambiguity_runtime import build_ambiguity_aggregates
    from vector.domains.cortex.canonical.canonical_control_plane import (
        build_canonical_control_plane,
        verify_phase03_step16_canonical_control_plane_contract,
    )
    from vector.domains.cortex.canonical.canonical_stabilization_proof import (
        build_stabilization_proof_report,
        verify_phase03_step17_stabilization_proof_contract,
    )
    from vector.domains.cortex.canonical.canonical_verification_engine import (
        list_canonical_verification_runs,
        verification_run_public_dict,
    )

    lim = max(1, min(int(materialization_sample_limit), 200))
    mats = _sample_materializations(session, tenant_id=tenant_id, limit=lim)
    lineage_detail = _lineage_operator_gate_detail(session, tenant_id=tenant_id, mats=mats)

    v_rows = list_canonical_verification_runs(session, tenant_id=tenant_id, limit=1)
    last_ver: dict[str, Any] | None = None
    if v_rows:
        d = verification_run_public_dict(v_rows[0])
        last_ver = {
            "id": d["id"],
            "passed": d["passed"],
            "engine_schema_version": d["engine_schema_version"],
            "created_at": (
                d["created_at"].isoformat()
                if hasattr(d["created_at"], "isoformat")
                else str(d["created_at"])
            ),
            "gate_ids": [g.get("id") for g in (d.get("gates_json") or []) if isinstance(g, dict)],
        }
    verification_excerpt: dict[str, Any] = {
        "last_verification_run": last_ver,
        "note": "Last persisted verification run only; POST .../verification/run to refresh.",
    }

    stab_report = build_stabilization_proof_report(session, tenant_id)
    stab_contract = verify_phase03_step17_stabilization_proof_contract(report=stab_report)
    stabilization_excerpt: dict[str, Any] = {
        "stabilization_proof_schema_version": stab_report.get("stabilization_proof_schema_version"),
        "overall_passed": stab_report.get("overall_passed"),
        "hard_fail_passed": stab_report.get("hard_fail_passed"),
        "warn_only_all_passed": stab_report.get("warn_only_all_passed"),
        "contract": stab_contract,
    }

    cp = build_canonical_control_plane(session, tenant_id)
    cp_contract = verify_phase03_step16_canonical_control_plane_contract(control_plane_payload=cp)
    control_plane_excerpt: dict[str, Any] = {
        "canonical_control_plane_schema_version": cp.get("canonical_control_plane_schema_version"),
        "health_overview": cp.get("health_overview"),
        "verification_truth": cp.get("verification_truth"),
    }

    jobs = list(
        session.scalars(
            select(CortexCanonicalReplayJob)
            .where(
                CortexCanonicalReplayJob.tenant_id == tenant_id,
                CortexCanonicalReplayJob.status == "completed",
            )
            .order_by(CortexCanonicalReplayJob.created_at.desc())
            .limit(25)
            .options(selectinload(CortexCanonicalReplayJob.receipts))
        ).all()
    )
    completed_payload: list[dict[str, Any]] = []
    replay_auditable = True
    for job in jobs:
        summary = job.summary_json if isinstance(job.summary_json, dict) else {}
        counts = summary.get("counts_by_divergence_class")
        if not isinstance(counts, dict):
            replay_auditable = False
        n_receipts = len(job.receipts or [])
        writes_applied = int(summary.get("writes_applied") or 0)
        scope_n = len(job.scope_raw_record_ids or [])
        if scope_n > 0 and writes_applied > 0 and n_receipts < 1:
            replay_auditable = False
        completed_payload.append(
            {
                "job_id": str(job.id),
                "job_kind": job.job_kind,
                "pinned_bundle_id": job.pinned_bundle_id,
                "dry_run": bool(job.dry_run),
                "summary_json": summary,
                "receipt_count": n_receipts,
                "completed_at": job.completed_at.isoformat()
                if job.completed_at and hasattr(job.completed_at, "isoformat")
                else None,
            }
        )
    replay_excerpt: dict[str, Any] = {
        "completed_jobs": completed_payload,
        "completed_job_count": len(completed_payload),
        "replay_generation_auditable": replay_auditable,
    }

    ag = build_ambiguity_aggregates(session, tenant_id=tenant_id)
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
    ambiguity_excerpt: dict[str, Any] = {
        "aggregates": ag,
        "open_ambiguity_count": n_open,
    }

    mat_total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    approved = list(
        session.scalars(
            select(CortexMappingBundle.bundle_id).where(
                CortexMappingBundle.lifecycle_state == "approved"
            )
        ).all()
    )
    approved_set = set(approved)
    pin_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexMappingBundlePin)
            .where(CortexMappingBundlePin.tenant_id == tenant_id)
        )
        or 0
    )
    sampled_bundle_ids = {m.bundle_id for m in mats}
    bundles_ok = not sampled_bundle_ids or sampled_bundle_ids.issubset(approved_set)
    # Lab tenants may have approved bundles without pins; pins remain optional extras in excerpt.
    mapping_governance_visible = (mat_total == 0) or (bool(approved_set) and bundles_ok)

    mapping_excerpt: dict[str, Any] = {
        "approved_bundle_count": len(approved_set),
        "tenant_pin_count": pin_count,
        "materialization_count": mat_total,
        "sampled_bundle_ids": sorted(sampled_bundle_ids),
        "sampled_bundles_subset_of_approved": bundles_ok,
        "mapping_governance_visible": mapping_governance_visible,
    }

    control_plane_contract = dict(cp_contract)
    pre_rows = _build_closure_rows(
        session,
        tenant_id=tenant_id,
        verification_excerpt=verification_excerpt,
        stabilization_excerpt=stabilization_excerpt,
        control_plane_contract=control_plane_contract,
        replay_excerpt=replay_excerpt,
        ambiguity_excerpt=ambiguity_excerpt,
        mapping_excerpt=mapping_excerpt,
        lineage_detail=lineage_detail,
    )

    pack_wo_21: dict[str, Any] = {
        "certification_pack_schema_version": CERTIFICATION_PACK_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "built_at_clock": datetime.now(tz=UTC).isoformat(),
        "verification_matrix_excerpt": verification_excerpt,
        "stabilization_proof_excerpt": stabilization_excerpt,
        "control_plane_excerpt": control_plane_excerpt,
        "replay_jobs_excerpt": replay_excerpt,
        "ambiguity_excerpt": ambiguity_excerpt,
        "mapping_registry_excerpt": mapping_excerpt,
        "lineage_operator_sample_excerpt": lineage_detail,
        "closure_gate_matrix": pre_rows,
        "doctrine_notes": {
            "engine_gate_gp03_17": "stabilization proof report contract (engine G-P03-17).",
            "closure_matrix_gp03_17": "lineage sample for closure row G-P03-17.",
        },
    }
    slice_hard_ok = all(r.get("passed") for r in pre_rows if r.get("severity") == "hard_fail")
    gp21_detail: dict[str, Any] = {
        "closure_hard_slice_passed": slice_hard_ok,
    }
    matrix_for_contract = [
        *pre_rows,
        {
            "id": "G-P03-21",
            "name": "certification_proof_artifacts",
            "passed": True,
            "severity": "hard_fail",
            "detail": gp21_detail,
        },
    ]
    struct = verify_phase03_step18_certification_pack_contract(
        pack={**pack_wo_21, "closure_gate_matrix": matrix_for_contract}
    )
    gp21_passed = bool(struct.get("passed")) and slice_hard_ok
    gp21_detail["structural_contract"] = struct
    matrix = [
        *pre_rows,
        {
            "id": "G-P03-21",
            "name": "certification_proof_artifacts",
            "passed": gp21_passed,
            "severity": "hard_fail",
            "detail": gp21_detail,
        },
    ]
    return {
        **pack_wo_21,
        "closure_gate_matrix": matrix,
        "certification_pack_contract": verify_phase03_step18_certification_pack_contract(
            pack={**pack_wo_21, "closure_gate_matrix": matrix}
        ),
    }


def overall_closure_passed(pack: dict[str, Any]) -> bool:
    matrix = pack.get("closure_gate_matrix") or []
    return all(
        bool(r.get("passed"))
        for r in matrix
        if isinstance(r, dict) and r.get("severity") == "hard_fail"
    )


def persist_canonical_certification_archive(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
) -> dict[str, Any]:
    """Persist a certification pack when all hard-fail closure rows (incl. G-P03-21) pass."""
    pack = build_canonical_certification_pack(
        session,
        tenant_id=tenant_id,
        materialization_sample_limit=materialization_sample_limit,
    )
    ok = overall_closure_passed(pack)
    if not ok:
        return {
            "persisted": False,
            "passed": False,
            "archive_id": None,
            "pack": pack,
        }
    row = CortexCanonicalCertificationArchive(
        tenant_id=tenant_id,
        certification_pack_schema_version=CERTIFICATION_PACK_SCHEMA_VERSION,
        passed=True,
        pack_json=pack,
    )
    session.add(row)
    session.flush()
    return {"persisted": True, "passed": True, "archive_id": row.id, "pack": pack}


def certification_archive_public_dict(row: CortexCanonicalCertificationArchive) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "certification_pack_schema_version": row.certification_pack_schema_version,
        "passed": row.passed,
        "created_at": row.created_at,
    }


def list_canonical_certification_archives(
    session: Session, *, tenant_id: uuid.UUID, limit: int = 20
) -> list[CortexCanonicalCertificationArchive]:
    lim = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(CortexCanonicalCertificationArchive)
            .where(CortexCanonicalCertificationArchive.tenant_id == tenant_id)
            .order_by(
                CortexCanonicalCertificationArchive.created_at.desc(),
                CortexCanonicalCertificationArchive.id.desc(),
            )
            .limit(lim)
        ).all()
    )


def get_canonical_certification_archive(
    session: Session, *, tenant_id: uuid.UUID, archive_id: int
) -> CortexCanonicalCertificationArchive | None:
    return session.scalars(
        select(CortexCanonicalCertificationArchive).where(
            CortexCanonicalCertificationArchive.tenant_id == tenant_id,
            CortexCanonicalCertificationArchive.id == archive_id,
        )
    ).first()
