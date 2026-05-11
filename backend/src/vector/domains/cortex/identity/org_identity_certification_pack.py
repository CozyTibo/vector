"""Phase 04 Step 22 — org identity closure certification pack + archive (P04-22).

Normative: ``phase-04-closure-gates-doctrine.md``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.control_plane import build_identity_control_plane
from vector.domains.cortex.identity.readiness_economics import build_identity_readiness_economics
from vector.domains.cortex.identity.verification import (
    list_org_identity_verification_runs,
    org_verification_run_public_dict,
    phase04_identity_gate_slice,
)
from vector.infrastructure.db.models.cortex_org_certification_archive import CortexOrgCertificationArchive

ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION: Final[int] = 1


def _summarize_gate(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": g.get("id"),
        "passed": g.get("passed"),
        "severity": g.get("severity"),
    }


def verify_phase04_org_identity_certification_pack_contract(*, pack: dict[str, Any]) -> dict[str, Any]:
    """Structural contract for org certification pack JSON (closure row G-P04-CLOSE-01)."""
    errs: list[str] = []
    if pack.get("org_certification_pack_schema_version") != ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION:
        errs.append("org_certification_pack_schema_version_mismatch")
    if str(pack.get("tenant_id") or "") == "":
        errs.append("tenant_id_missing")
    for key in (
        "built_at_clock",
        "closure_gate_matrix",
        "canonical_verification_excerpt",
        "phase04_gate_excerpt",
        "identity_control_plane_excerpt",
        "readiness_economics_excerpt",
        "org_verification_last_excerpt",
    ):
        if key not in pack:
            errs.append(f"missing_{key}")
    matrix = pack.get("closure_gate_matrix")
    if not isinstance(matrix, list):
        errs.append("closure_gate_matrix_not_list")
    else:
        ids = {r.get("id") for r in matrix if isinstance(r, dict)}
        for gid in ("G-P04-CLOSE-MAP-01", "G-P04-CLOSE-MAP-02", "G-P04-CLOSE-01"):
            if gid not in ids:
                errs.append(f"missing_matrix_row_{gid}")
        for r in matrix:
            if not isinstance(r, dict):
                errs.append("matrix_row_not_object")
                continue
            for f in ("id", "name", "passed", "severity"):
                if f not in r:
                    errs.append(f"matrix_row_missing_{f}")
    passed = len(errs) == 0
    return {"passed": passed, "errors": errs}


def overall_org_identity_closure_passed(pack: dict[str, Any]) -> bool:
    matrix = pack.get("closure_gate_matrix") or []
    return all(
        bool(r.get("passed"))
        for r in matrix
        if isinstance(r, dict) and r.get("severity") == "hard_fail"
    )


def build_org_identity_certification_pack_from_snapshot(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Build pack from a **pre-computed** canonical verification snapshot (no nested engine run)."""
    gates = list(snapshot.get("gates") or [])
    all_hard_ok = all(
        bool(g.get("passed")) for g in gates if isinstance(g, dict) and g.get("severity") == "hard_fail"
    )
    failed_full = [
        str(g.get("id"))
        for g in gates
        if isinstance(g, dict) and g.get("severity") == "hard_fail" and not g.get("passed")
    ]

    p04_gates = phase04_identity_gate_slice(gates)
    p04_hard_ok = all(
        bool(g.get("passed")) for g in p04_gates if isinstance(g, dict) and g.get("severity") == "hard_fail"
    )
    failed_p04 = [
        str(g.get("id"))
        for g in p04_gates
        if isinstance(g, dict) and g.get("severity") == "hard_fail" and not g.get("passed")
    ]

    pre_rows: list[dict[str, Any]] = [
        {
            "id": "G-P04-CLOSE-MAP-01",
            "name": "canonical_verification_all_hard_fail_pass",
            "passed": all_hard_ok,
            "severity": "hard_fail",
            "detail": {
                "full_verification_passed": bool(snapshot.get("passed")),
                "failed_hard_fail_gate_ids": failed_full[:40],
            },
        },
        {
            "id": "G-P04-CLOSE-MAP-02",
            "name": "phase04_identity_hard_fail_slice_pass",
            "passed": p04_hard_ok,
            "severity": "hard_fail",
            "detail": {
                "phase04_gate_count": len(p04_gates),
                "failed_phase04_hard_fail_gate_ids": failed_p04[:40],
            },
        },
    ]

    icp = build_identity_control_plane(session, tenant_id=tenant_id)
    eco = build_identity_readiness_economics(session, tenant_id=tenant_id)
    ov_rows = list_org_identity_verification_runs(session, tenant_id=tenant_id, limit=1)
    last_ov = org_verification_run_public_dict(ov_rows[0]) if ov_rows else None

    card_values: dict[str, Any] = {}
    for k, v in (icp.get("cards") or {}).items():
        if isinstance(v, dict) and "value" in v:
            card_values[k] = v.get("value")

    identity_control_plane_excerpt: dict[str, Any] = {
        "schema_version": icp.get("schema_version"),
        "freshness_label": icp.get("freshness_label"),
        "card_values": card_values,
    }

    readiness_economics_excerpt: dict[str, Any] = {
        "overall_posture": eco.get("overall_posture"),
        "storage_estimate_bytes": eco.get("storage_estimate_bytes"),
        "warning_count": len(eco.get("warnings") or []),
    }

    canonical_verification_excerpt: dict[str, Any] = {
        "passed": bool(snapshot.get("passed")),
        "canonical_verification_engine_schema_version": snapshot.get(
            "canonical_verification_engine_schema_version"
        ),
        "hard_fail_failed_ids_sample": failed_full[:25],
        "gate_count": len(gates),
    }

    phase04_gate_excerpt: dict[str, Any] = {
        "gates": [_summarize_gate(g) for g in p04_gates],
        "phase04_slice_passed": p04_hard_ok,
    }

    org_verification_last_excerpt: dict[str, Any] = {"last_run": last_ov}

    pack_wo_close: dict[str, Any] = {
        "org_certification_pack_schema_version": ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "built_at_clock": datetime.now(tz=UTC).isoformat(),
        "canonical_verification_excerpt": canonical_verification_excerpt,
        "phase04_gate_excerpt": phase04_gate_excerpt,
        "identity_control_plane_excerpt": identity_control_plane_excerpt,
        "readiness_economics_excerpt": readiness_economics_excerpt,
        "org_verification_last_excerpt": org_verification_last_excerpt,
        "closure_gate_matrix": pre_rows,
        "doctrine_notes": {
            "phase03_certification_routes": "/cortex/canonical/certification-pack (Phase 03 Step 18).",
            "phase04_certification_routes": "/cortex/identity/certification-pack (Phase 04 Step 22).",
        },
    }

    slice_hard_ok = all(r.get("passed") for r in pre_rows if r.get("severity") == "hard_fail")
    struct = verify_phase04_org_identity_certification_pack_contract(
        pack={
            **pack_wo_close,
            "closure_gate_matrix": [
                *pre_rows,
                {
                    "id": "G-P04-CLOSE-01",
                    "name": "phase04_org_closure_certification_artifacts",
                    "passed": True,
                    "severity": "hard_fail",
                    "detail": {"placeholder": True},
                },
            ],
        }
    )
    close01_passed = bool(struct.get("passed")) and slice_hard_ok
    close01_detail: dict[str, Any] = {
        "closure_pre_rows_passed": slice_hard_ok,
        "structural_contract": struct,
    }
    matrix = [
        *pre_rows,
        {
            "id": "G-P04-CLOSE-01",
            "name": "phase04_org_closure_certification_artifacts",
            "passed": close01_passed,
            "severity": "hard_fail",
            "detail": close01_detail,
        },
    ]
    out = {
        **pack_wo_close,
        "closure_gate_matrix": matrix,
        "org_identity_certification_pack_contract": verify_phase04_org_identity_certification_pack_contract(
            pack={**pack_wo_close, "closure_gate_matrix": matrix}
        ),
    }
    return out


def build_org_identity_certification_pack(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
) -> dict[str, Any]:
    """Assemble Phase 04 closure pack (runs canonical verification **core** gates once, no G-P04-CLOSE-01)."""
    from vector.domains.cortex.canonical.canonical_verification_engine import (
        _canonical_verification_gate_results_core,
    )

    gates_core, mats = _canonical_verification_gate_results_core(
        session,
        tenant_id=tenant_id,
        materialization_sample_limit=materialization_sample_limit,
    )
    passed_core = all(
        bool(g.get("passed")) for g in gates_core if isinstance(g, dict) and g.get("severity") == "hard_fail"
    )
    from vector.domains.cortex.canonical.canonical_verification_engine import (
        CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
    )
    from vector.domains.cortex.canonical.oracle_manifest import oracle_vectors

    evidence: dict[str, Any] = {
        "materializations_sampled": len(mats),
        "oracle_vectors_count": len(oracle_vectors()),
        "engine_build_clock": datetime.now(tz=UTC).isoformat(),
    }
    snap: dict[str, Any] = {
        "passed": passed_core,
        "gates": gates_core,
        "evidence": evidence,
        "canonical_verification_engine_schema_version": CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
    }
    return build_org_identity_certification_pack_from_snapshot(session, tenant_id=tenant_id, snapshot=snap)


def persist_org_identity_certification_archive(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    materialization_sample_limit: int = 50,
) -> dict[str, Any]:
    """Persist org certification pack when all hard-fail closure rows (incl. G-P04-CLOSE-01) pass."""
    pack = build_org_identity_certification_pack(
        session,
        tenant_id=tenant_id,
        materialization_sample_limit=materialization_sample_limit,
    )
    ok = overall_org_identity_closure_passed(pack)
    if not ok:
        return {
            "persisted": False,
            "passed": False,
            "archive_id": None,
            "pack": pack,
        }
    row = CortexOrgCertificationArchive(
        tenant_id=tenant_id,
        org_certification_pack_schema_version=ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
        passed=True,
        pack_json=pack,
    )
    session.add(row)
    session.flush()
    return {"persisted": True, "passed": True, "archive_id": row.id, "pack": pack}


def org_certification_archive_public_dict(row: CortexOrgCertificationArchive) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": str(row.tenant_id),
        "org_certification_pack_schema_version": row.org_certification_pack_schema_version,
        "passed": row.passed,
        "created_at": row.created_at,
    }


def list_org_identity_certification_archives(
    session: Session, *, tenant_id: uuid.UUID, limit: int = 20
) -> list[CortexOrgCertificationArchive]:
    lim = max(1, min(limit, 100))
    return list(
        session.scalars(
            select(CortexOrgCertificationArchive)
            .where(CortexOrgCertificationArchive.tenant_id == tenant_id)
            .order_by(
                CortexOrgCertificationArchive.created_at.desc(),
                CortexOrgCertificationArchive.id.desc(),
            )
            .limit(lim)
        ).all()
    )


def get_org_identity_certification_archive(
    session: Session, *, tenant_id: uuid.UUID, archive_id: int
) -> CortexOrgCertificationArchive | None:
    return session.scalars(
        select(CortexOrgCertificationArchive).where(
            CortexOrgCertificationArchive.tenant_id == tenant_id,
            CortexOrgCertificationArchive.id == archive_id,
        )
    ).first()

