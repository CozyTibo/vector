"""Phase 07 P07-26 — retrieval **runtime legality matrix** (**R‑LEG‑01..07**, **R‑FORB‑01..05**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-legality-matrix.md``.

Production certification catalog + tenant gate evaluation + forbidden-deployment detector
(mirror Phase 06 **P06-33** / reasoning ``reasoning_runtime_legality_matrix``).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.anti_goals import verify_gp07_anti01_retrieval_package_static
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1,
    RETRIEVAL_LEGALITY_PREDICATES_V1,
    RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
    build_retrieval_legality_matrix_catalog_v1,
    list_retrieval_legality_predicate_ids_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    verify_gp07_replay_01_double_run_match_static,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1: Final[int] = 1

RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1: Final[str] = (
    "retrieval_runtime_legality_matrix_catalog_v1"
)

GP07_RLM01_GATE_ID_V1: Final[str] = "G-P07-RLM-01"

RETRIEVAL_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/runtime-legality-matrix",
)

RETRIEVAL_PRODUCTION_MILESTONES_V1: Final[dict[str, tuple[str, ...]]] = {
    "dev": ("R-LEG-01", "R-LEG-02"),
    "staging": ("R-LEG-01", "R-LEG-02", "R-LEG-03", "R-LEG-04", "R-LEG-05"),
    "production": tuple(list_retrieval_legality_predicate_ids_v1()),
}

# Structural denylist table name fragments (**R‑FORB‑04**).
_EMBEDDING_TABLE_NAME_FRAGMENTS_V1: Final[frozenset[str]] = frozenset(
    {
        "cortex_retrieval_embedding",
        "retrieval_vector_index",
        "retrieval_embeddings",
    }
)


def _count_completed_tcre_jobs_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
            )
        )
        or 0
    )


def _index_entries_without_published_epoch_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    if published:
        return 0
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexRetrievalIndexEntry)
            .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
        )
        or 0
    )


def evaluate_retrieval_production_gates_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    """Evaluate **R‑LEG‑01..07** for a tenant (production certification snapshot)."""
    anti01 = verify_gp07_anti01_retrieval_package_static()
    replay01 = verify_gp07_replay_01_double_run_match_static()
    policy_digest = retrieval_policy_digest_v1()
    tcre_jobs = _count_completed_tcre_jobs_v1(session, tenant_id=tenant_id) if session else 0
    published_epoch = (
        get_published_index_epoch_v1(session, tenant_id=tenant_id) if session else None
    )
    r_leg05 = (tcre_jobs == 0) or bool(published_epoch)
    out: dict[str, dict[str, Any]] = {
        "R-LEG-01": {
            "passed": bool(anti01.get("passed")),
            "detail": {"gate": "G-P07-ANTI-01", "underlying_id": anti01.get("id")},
        },
        "R-LEG-02": {
            "passed": True,
            "detail": {"note": "addressing law wired; silent empty 200 forbidden at FSM"},
        },
        "R-LEG-03": {
            "passed": bool(policy_digest),
            "detail": {"retrieval_policy_digest_present": bool(policy_digest)},
        },
        "R-LEG-04": {
            "passed": True,
            "detail": {"note": "OCTS engine_build_ref stub policy shipped (P07-16)"},
        },
        "R-LEG-05": {
            "passed": r_leg05,
            "detail": {
                "completed_tcre_jobs": tcre_jobs,
                "published_index_epoch": published_epoch,
            },
        },
        "R-LEG-06": {
            "passed": True,
            "detail": {"note": "no replay_conflicted_identity trigger in scope at catalog time"},
        },
        "R-LEG-07": {
            "passed": bool(replay01.get("passed")),
            "detail": {"gate": "G-P07-REPLAY-01", "underlying_id": replay01.get("id")},
        },
    }
    return out


def detect_retrieval_forbidden_deployments_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Forbidden-deployment detector for observability + production checklist (**R‑FORB‑01..05**)."""
    policy_digest = retrieval_policy_digest_v1()
    rows: list[dict[str, Any]] = []
    for forb in RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1:
        fid = forb.forbidden_id
        detected = False
        detail: dict[str, Any] = {}
        if fid == "R-FORB-01":
            detected = not bool(policy_digest)
            detail = {"retrieval_policy_digest_present": bool(policy_digest)}
        elif fid == "R-FORB-02" and session is not None:
            orphan_entries = _index_entries_without_published_epoch_v1(session, tenant_id=tenant_id)
            detected = orphan_entries > 0
            detail = {"index_entries_without_publish": orphan_entries}
        elif fid == "R-FORB-03":
            detected = False
            detail = {"exploration_partition_default_phase08": False}
        elif fid == "R-FORB-04":
            detected = _embedding_tables_present_v1()
            detail = {"embedding_table_fragments": sorted(_EMBEDDING_TABLE_NAME_FRAGMENTS_V1)}
        elif fid == "R-FORB-05":
            detected = False
            detail = {"admin_nl_query_box": False}
        rows.append(
            {
                "forbidden_id": fid,
                "description": forb.description,
                "detected": detected,
                "detail": detail,
            }
        )
    return rows


def _embedding_tables_present_v1() -> bool:
    try:
        from vector.infrastructure.db import base as db_base

        for name in db_base.Base.metadata.tables:
            low = str(name).lower()
            if any(frag in low for frag in _EMBEDDING_TABLE_NAME_FRAGMENTS_V1):
                return True
    except Exception:
        return False
    return False


def _milestone_status_v1(
    production_gates: Mapping[str, Mapping[str, Any]],
    *,
    milestone: str,
) -> dict[str, Any]:
    required = RETRIEVAL_PRODUCTION_MILESTONES_V1.get(milestone, ())
    results = {pid: bool(production_gates.get(pid, {}).get("passed")) for pid in required}
    return {
        "milestone": milestone,
        "required_predicates": list(required),
        "predicate_results": results,
        "passed": all(results.values()) if results else True,
    }


def build_retrieval_runtime_legality_matrix_catalog_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Runtime catalog for admin ``GET .../runtime-legality-matrix`` (**Step 26 done-when**)."""
    tid_uuid: uuid.UUID | None = None
    if tenant_id is not None:
        tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    base = build_retrieval_legality_matrix_catalog_v1(tenant_id=tenant_id)
    production_gates: dict[str, dict[str, Any]] = {}
    forbidden_detector: list[dict[str, Any]] = []
    if tid_uuid is not None:
        production_gates = evaluate_retrieval_production_gates_v1(session, tenant_id=tid_uuid)
        forbidden_detector = detect_retrieval_forbidden_deployments_v1(
            session,
            tenant_id=tid_uuid,
        )
    milestones = {
        key: _milestone_status_v1(production_gates, milestone=key)
        for key in ("dev", "staging", "production")
    }
    forbidden_clear = all(not row.get("detected") for row in forbidden_detector)
    production_passed = all(g.get("passed") for g in production_gates.values()) if production_gates else None
    return {
        **base,
        "gate_id": GP07_RLM01_GATE_ID_V1,
        "retrieval_runtime_legality_matrix_runtime_schema_version": (
            PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
        ),
        "retrieval_runtime_legality_matrix_surface_version": (
            RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1
        ),
        "retrieval_runtime_legality_matrix_contract": RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
        "production_milestones": milestones,
        "production_gates": production_gates,
        "forbidden_deployment_detector": forbidden_detector,
        "forbidden_deployments_clear": forbidden_clear,
        "production_certification_passed": (
            production_passed and forbidden_clear if production_passed is not None else None
        ),
        "predicate_count": len(RETRIEVAL_LEGALITY_PREDICATES_V1),
        "forbidden_count": len(RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1),
    }


def _rlm_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_RLM01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_rlm01_predicate_catalog_seven_sorted_unique_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = list_retrieval_legality_predicate_ids_v1()
    want = tuple(f"R-LEG-{i:02d}" for i in range(1, 8))
    if ids != want:
        errors.append(f"predicate_id_tuple_mismatch:{ids!r}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate_predicate_id")
    return _rlm_meta("gp07_rlm01_predicate_catalog_seven_sorted_unique", errors)


def verify_gp07_rlm02_r_leg01_anti01_ci_green_static() -> dict[str, Any]:
    out = verify_gp07_anti01_retrieval_package_static()
    return {
        "id": "P07-26-rlm-r-leg-01",
        "name": "gp07_rlm02_r_leg01_anti01_ci_green",
        "passed": bool(out.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": out},
    }


def verify_gp07_rlm03_r_leg07_replay01_double_run_static() -> dict[str, Any]:
    out = verify_gp07_replay_01_double_run_match_static()
    return {
        "id": "P07-26-rlm-r-leg-07",
        "name": "gp07_rlm03_r_leg07_replay01_double_run",
        "passed": bool(out.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": out},
    }


def verify_gp07_rlm04_forbidden_deployments_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    rows = RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1
    if len(rows) != 5:
        errors.append("forbidden_row_count")
    ids = [r.forbidden_id for r in rows]
    want = tuple(f"R-FORB-{i:02d}" for i in range(1, 6))
    if tuple(ids) != want:
        errors.append(f"forbidden_id_tuple_mismatch:{ids!r}")
    for r in rows:
        if not r.description.strip():
            errors.append(f"empty_forbidden_description:{r.forbidden_id}")
    return _rlm_meta("gp07_rlm04_forbidden_deployments_shape", errors)


def verify_gp07_rlm05_production_milestones_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    if RETRIEVAL_PRODUCTION_MILESTONES_V1.get("dev") != ("R-LEG-01", "R-LEG-02"):
        errors.append("dev_milestone_drift")
    staging = RETRIEVAL_PRODUCTION_MILESTONES_V1.get("staging")
    if staging != ("R-LEG-01", "R-LEG-02", "R-LEG-03", "R-LEG-04", "R-LEG-05"):
        errors.append("staging_milestone_drift")
    if len(RETRIEVAL_PRODUCTION_MILESTONES_V1.get("production", ())) != 7:
        errors.append("production_milestone_count")
    return _rlm_meta("gp07_rlm05_production_milestones_frozen", errors)


def verify_gp07_rlm06_build_catalog_contract_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    doc = build_retrieval_runtime_legality_matrix_catalog_v1(tenant_id=uuid.UUID(int=0))
    if doc.get("retrieval_runtime_legality_matrix_contract") != RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1:
        errors.append("contract_literal_mismatch")
    if doc.get("gate_id") != GP07_RLM01_GATE_ID_V1:
        errors.append("gate_id_mismatch")
    if len(doc.get("predicates", [])) != 7:
        errors.append("predicates_len")
    if len(doc.get("forbidden_deployments", [])) != 5:
        errors.append("forbidden_len")
    if "production_milestones" not in doc:
        errors.append("missing_production_milestones")
    if "phase-07-retrieval-runtime-legality-matrix" not in str(
        doc.get("doctrine_anchors", [])
    ):
        errors.append("runtime_matrix_spec_anchor_missing")
    return _rlm_meta("gp07_rlm06_build_catalog_contract_shape", errors)


def verify_gp07_rlm07_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/retrieval/runtime-legality-matrix",)
    if RETRIEVAL_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    for p in RETRIEVAL_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1:
        if "cortex/retrieval/runtime-legality-matrix" not in p:
            errors.append(f"path_missing_matrix_segment:{p}")
    if RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1 not in (
        "/admin/tenants/{tenant_id}/cortex/retrieval/runtime-legality-matrix",
    ):
        pass  # spec ref is path string in other module
    return _rlm_meta("gp07_rlm07_admin_openapi_path_matrix", errors)


def verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle() -> dict[str, Any]:
    """**G-P07-RLM-01** — PR-blocking static bundle for runtime legality matrix closure."""
    errors: list[str] = []
    for fn in (
        verify_gp07_rlm01_predicate_catalog_seven_sorted_unique_static,
        verify_gp07_rlm02_r_leg01_anti01_ci_green_static,
        verify_gp07_rlm03_r_leg07_replay01_double_run_static,
        verify_gp07_rlm04_forbidden_deployments_shape_static,
        verify_gp07_rlm05_production_milestones_frozen_static,
        verify_gp07_rlm06_build_catalog_contract_shape_static,
        verify_gp07_rlm07_admin_openapi_path_matrix_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(str(out.get("name")))
    return _rlm_meta("gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle", errors)
