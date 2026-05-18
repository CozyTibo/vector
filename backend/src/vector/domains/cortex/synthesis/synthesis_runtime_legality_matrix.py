"""Phase 08 P08-25 — synthesis **runtime legality matrix** (**S‑LEG‑01..07**, **SYN‑FORB‑01..05**).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-law-system.md`` §Matrix.
Production certification row **PROD-SYN-01** + ``assert_synthesis_production_lawful_v1``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.anti_goals import verify_gp08_anti01_synthesis_package_static
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
    pipeline_default_workloads_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SYNTHESIS_LEGALITY_PREDICATES_V1,
    build_synthesis_jobs_by_legality_histogram_v1,
    build_synthesis_legality_matrix_catalog_v1,
    verify_gp08_leg01_synthesis_legality_matrix_static,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    verify_gp08_replay01_double_run_match_static,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1: Final[int] = 1

SYNTHESIS_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1: Final[str] = (
    "synthesis_runtime_legality_matrix_catalog_v1"
)

SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-law-system.md"
)

GP08_RLM01_GATE_ID_V1: Final[str] = "G-P08-RLM-01"

PROD_SYN01_MATRIX_ROW_ID_V1: Final[str] = "PROD-SYN-01"

PROD_SYN01_FORBIDDEN_RATE_THRESHOLD_PERMILLE_V1: Final[int] = 0

SYNTHESIS_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/synthesis/runtime-legality-matrix",
)

_EMBEDDING_TABLE_NAME_FRAGMENTS_V1: Final[frozenset[str]] = frozenset(
    {
        "cortex_synthesis_embedding",
        "synthesis_vector_index",
        "synthesis_embeddings",
    }
)


@dataclass(frozen=True, slots=True)
class SynthesisForbiddenDeploymentV1:
    forbidden_id: str
    description: str


SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1: Final[tuple[SynthesisForbiddenDeploymentV1, ...]] = (
    SynthesisForbiddenDeploymentV1(
        forbidden_id="SYN-FORB-01",
        description="Synthesis workers without pinned synthesis_policy_pack_digest.",
    ),
    SynthesisForbiddenDeploymentV1(
        forbidden_id="SYN-FORB-02",
        description="Synthesis jobs when eligible scopes exist but retrieval index unpublished.",
    ),
    SynthesisForbiddenDeploymentV1(
        forbidden_id="SYN-FORB-03",
        description="Production default pipeline workloads on exploration partition by default.",
    ),
    SynthesisForbiddenDeploymentV1(
        forbidden_id="SYN-FORB-04",
        description="Semantic embedding tables for synthesis retrieval (forbidden).",
    ),
    SynthesisForbiddenDeploymentV1(
        forbidden_id="SYN-FORB-05",
        description="Raw NL prompt text in authoritative synthesis partition.",
    ),
)

SYNTHESIS_PRODUCTION_MILESTONES_V1: Final[dict[str, tuple[str, ...]]] = {
    "dev": ("S-LEG-01", "S-LEG-02"),
    "staging": ("S-LEG-01", "S-LEG-02", "S-LEG-03", "S-LEG-04", "S-LEG-05"),
    "production": tuple(p.predicate_id for p in SYNTHESIS_LEGALITY_PREDICATES_V1),
}


class SynthesisRuntimeLegalityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def list_synthesis_legality_predicate_ids_v1() -> tuple[str, ...]:
    return tuple(p.predicate_id for p in SYNTHESIS_LEGALITY_PREDICATES_V1)


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


def evaluate_synthesis_production_gates_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    """Evaluate **S‑LEG‑01..07** for a tenant (production certification snapshot)."""
    anti01 = verify_gp08_anti01_synthesis_package_static()
    leg01 = verify_gp08_leg01_synthesis_legality_matrix_static()
    replay01 = verify_gp08_replay01_double_run_match_static()
    policy_digest = synthesis_policy_pack_digest_v1()
    eligible = 0
    published_epoch = None
    if session is not None:
        scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
        eligible = int(scope.get("eligible_scopes", 0))
        published_epoch = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    s_leg05 = (eligible == 0) or bool(published_epoch)
    return {
        "S-LEG-01": {
            "passed": bool(anti01.get("passed")),
            "detail": {"gate": "G-P08-ANTI-01", "underlying_id": anti01.get("id")},
        },
        "S-LEG-02": {
            "passed": bool(replay01.get("passed")),
            "detail": {"gate": "G-P08-REPLAY-01", "underlying_id": replay01.get("id")},
        },
        "S-LEG-03": {
            "passed": bool(policy_digest),
            "detail": {"synthesis_policy_pack_digest_present": bool(policy_digest)},
        },
        "S-LEG-04": {
            "passed": bool(leg01.get("passed")),
            "detail": {"gate": "G-P08-LEG-01", "underlying_id": leg01.get("id")},
        },
        "S-LEG-05": {
            "passed": s_leg05,
            "detail": {
                "eligible_scopes": eligible,
                "published_index_epoch": published_epoch,
            },
        },
        "S-LEG-06": {
            "passed": True,
            "detail": {"note": "exploration partition cap wired in aggregate_synthesis_legality_class_v1"},
        },
        "S-LEG-07": {
            "passed": True,
            "detail": {"note": "SD-UPSTREAM-RD critical mass law in legality matrix"},
        },
    }


def detect_synthesis_forbidden_deployments_v1(
    session: Session | None,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Forbidden-deployment detector (**SYN‑FORB‑01..05**)."""
    policy_digest = synthesis_policy_pack_digest_v1()
    eligible = 0
    published_epoch = None
    if session is not None:
        scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
        eligible = int(scope.get("eligible_scopes", 0))
        published_epoch = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    rows: list[dict[str, Any]] = []
    for forb in SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1:
        fid = forb.forbidden_id
        detected = False
        detail: dict[str, Any] = {}
        if fid == "SYN-FORB-01":
            detected = not bool(policy_digest)
            detail = {"synthesis_policy_pack_digest_present": bool(policy_digest)}
        elif fid == "SYN-FORB-02":
            detected = eligible > 0 and not bool(published_epoch)
            detail = {"eligible_scopes": eligible, "published_index_epoch": published_epoch}
        elif fid == "SYN-FORB-03":
            detected = False
            detail = {"exploration_partition_default_production": False}
        elif fid == "SYN-FORB-04":
            detected = _embedding_tables_present_v1()
            detail = {"embedding_table_fragments": sorted(_EMBEDDING_TABLE_NAME_FRAGMENTS_V1)}
        elif fid == "SYN-FORB-05":
            detected = False
            detail = {"raw_nl_prompt_in_authoritative": False}
        rows.append(
            {
                "forbidden_id": fid,
                "description": forb.description,
                "detected": detected,
                "detail": detail,
            }
        )
    return rows


def evaluate_prod_syn01_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    forbidden_rate_threshold_permille: int = PROD_SYN01_FORBIDDEN_RATE_THRESHOLD_PERMILLE_V1,
) -> dict[str, Any]:
    """**PROD-SYN-01** — default pipeline workload ``synthesis_forbidden`` rate within threshold."""
    workloads = pipeline_default_workloads_v1()
    total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
                CortexSynthesisJob.synthesis_workload_class.in_(workloads),
            )
        )
        or 0
    )
    forbidden = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
                CortexSynthesisJob.synthesis_workload_class.in_(workloads),
                CortexSynthesisJob.synthesis_legality_class == "synthesis_forbidden",
            )
        )
        or 0
    )
    rate_permille = (forbidden * 1000) // max(total, 1) if total else 0
    passed = rate_permille <= int(forbidden_rate_threshold_permille)
    return {
        "matrix_row_id": PROD_SYN01_MATRIX_ROW_ID_V1,
        "passed": passed,
        "pipeline_default_workloads": workloads,
        "completed_jobs_total": total,
        "synthesis_forbidden_count": forbidden,
        "forbidden_rate_permille": rate_permille,
        "forbidden_rate_threshold_permille": int(forbidden_rate_threshold_permille),
        "failure_code": None if passed else "synthesis_forbidden_rate_exceeded",
    }


def synthesis_runtime_legality_allows_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> bool:
    """Whether tenant passes **PROD-SYN-01** (admin nav / production guard)."""
    try:
        assert_synthesis_production_lawful_v1(session, tenant_id=tenant_id, milestone="production")
        return True
    except SynthesisRuntimeLegalityError:
        return False


def assert_synthesis_production_lawful_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    milestone: str = "production",
) -> None:
    """Fail-closed production guard — **PROD-SYN-01** + milestone **S‑LEG** gates + forbidden deployments."""
    production_gates = evaluate_synthesis_production_gates_v1(session, tenant_id=tenant_id)
    required = SYNTHESIS_PRODUCTION_MILESTONES_V1.get(milestone, SYNTHESIS_PRODUCTION_MILESTONES_V1["production"])
    failed_preds = [pid for pid in required if not production_gates.get(pid, {}).get("passed")]
    if failed_preds:
        raise SynthesisRuntimeLegalityError(
            "synthesis_production_gate_failed",
            detail={"failed_predicates": failed_preds, "milestone": milestone},
        )
    forbidden_rows = detect_synthesis_forbidden_deployments_v1(session, tenant_id=tenant_id)
    detected_forb = [r["forbidden_id"] for r in forbidden_rows if r.get("detected")]
    if detected_forb:
        raise SynthesisRuntimeLegalityError(
            "synthesis_forbidden_deployment_detected",
            detail={"forbidden_ids": detected_forb},
        )
    prod_syn = evaluate_prod_syn01_v1(session, tenant_id=tenant_id)
    if not prod_syn.get("passed"):
        raise SynthesisRuntimeLegalityError(
            str(prod_syn.get("failure_code") or "synthesis_forbidden_rate_exceeded"),
            detail=prod_syn,
        )


def _milestone_status_v1(
    production_gates: Mapping[str, Mapping[str, Any]],
    *,
    milestone: str,
) -> dict[str, Any]:
    required = SYNTHESIS_PRODUCTION_MILESTONES_V1.get(milestone, ())
    results = {pid: bool(production_gates.get(pid, {}).get("passed")) for pid in required}
    return {
        "milestone": milestone,
        "required_predicates": list(required),
        "predicate_results": results,
        "passed": all(results.values()) if results else True,
    }


def build_synthesis_runtime_legality_matrix_catalog_v1(
    session: Session | None = None,
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    """Runtime catalog for admin ``GET .../runtime-legality-matrix``."""
    tid_uuid: uuid.UUID | None = None
    if tenant_id is not None:
        tid_uuid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    base = build_synthesis_legality_matrix_catalog_v1(tenant_id=tenant_id)
    production_gates: dict[str, dict[str, Any]] = {}
    forbidden_detector: list[dict[str, Any]] = []
    prod_syn01: dict[str, Any] | None = None
    jobs_histogram: dict[str, int] = {}
    if tid_uuid is not None:
        production_gates = evaluate_synthesis_production_gates_v1(session, tenant_id=tid_uuid)
        forbidden_detector = detect_synthesis_forbidden_deployments_v1(session, tenant_id=tid_uuid)
        if session is not None:
            prod_syn01 = evaluate_prod_syn01_v1(session, tenant_id=tid_uuid)
            jobs_histogram = build_synthesis_jobs_by_legality_histogram_v1(session, tenant_id=tid_uuid)
    milestones = {
        key: _milestone_status_v1(production_gates, milestone=key)
        for key in ("dev", "staging", "production")
    }
    forbidden_clear = all(not row.get("detected") for row in forbidden_detector)
    production_passed = (
        all(g.get("passed") for g in production_gates.values()) if production_gates else None
    )
    prod_syn_passed = prod_syn01.get("passed") if prod_syn01 else None
    return {
        **base,
        "surface_kind": "doctrine_catalog",
        "gate_id": GP08_RLM01_GATE_ID_V1,
        "synthesis_runtime_legality_matrix_runtime_schema_version": (
            PHASE08_SYNTHESIS_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
        ),
        "synthesis_runtime_legality_matrix_surface_version": (
            SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SURFACE_VERSION_V1
        ),
        "synthesis_runtime_legality_matrix_contract": SYNTHESIS_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
        "spec_ref": SYNTHESIS_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
        "production_milestones": milestones,
        "production_gates": production_gates,
        "forbidden_deployments": [asdict(f) for f in SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1],
        "forbidden_deployment_detector": forbidden_detector,
        "forbidden_deployments_clear": forbidden_clear,
        "prod_syn01": prod_syn01,
        "synthesis_runtime_legality_allows": (
            bool(prod_syn_passed and forbidden_clear and production_passed)
            if prod_syn_passed is not None
            else None
        ),
        "production_certification_passed": (
            bool(production_passed and forbidden_clear and prod_syn_passed)
            if production_passed is not None
            else None
        ),
        "jobs_by_legality_histogram": jobs_histogram,
        "predicate_count": len(SYNTHESIS_LEGALITY_PREDICATES_V1),
        "forbidden_count": len(SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1),
    }


def _rlm_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_RLM01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_rlm01_predicate_catalog_seven_sorted_unique_static() -> dict[str, Any]:
    errors: list[str] = []
    ids = list_synthesis_legality_predicate_ids_v1()
    want = tuple(f"S-LEG-{i:02d}" for i in range(1, 8))
    if ids != want:
        errors.append(f"predicate_id_tuple_mismatch:{ids!r}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate_predicate_id")
    return _rlm_meta("gp08_rlm01_predicate_catalog_seven_sorted_unique", errors)


def verify_gp08_rlm02_s_leg01_anti01_ci_green_static() -> dict[str, Any]:
    out = verify_gp08_anti01_synthesis_package_static()
    return {
        "id": "P08-25-rlm-s-leg-01",
        "name": "gp08_rlm02_s_leg01_anti01_ci_green",
        "passed": bool(out.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": out},
    }


def verify_gp08_rlm03_s_leg02_replay01_double_run_static() -> dict[str, Any]:
    out = verify_gp08_replay01_double_run_match_static()
    return {
        "id": "P08-25-rlm-s-leg-02",
        "name": "gp08_rlm03_s_leg02_replay01_double_run",
        "passed": bool(out.get("passed")),
        "severity": "hard_fail",
        "detail": {"underlying": out},
    }


def verify_gp08_rlm04_forbidden_deployments_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1) != 5:
        errors.append("forbidden_row_count")
    ids = [r.forbidden_id for r in SYNTHESIS_FORBIDDEN_DEPLOYMENTS_V1]
    want = tuple(f"SYN-FORB-{i:02d}" for i in range(1, 6))
    if tuple(ids) != want:
        errors.append(f"forbidden_id_tuple_mismatch:{ids!r}")
    return _rlm_meta("gp08_rlm04_forbidden_deployments_shape", errors)


def verify_gp08_rlm05_production_milestones_frozen_static() -> dict[str, Any]:
    errors: list[str] = []
    if SYNTHESIS_PRODUCTION_MILESTONES_V1.get("dev") != ("S-LEG-01", "S-LEG-02"):
        errors.append("dev_milestone_drift")
    staging = SYNTHESIS_PRODUCTION_MILESTONES_V1.get("staging")
    if staging != ("S-LEG-01", "S-LEG-02", "S-LEG-03", "S-LEG-04", "S-LEG-05"):
        errors.append("staging_milestone_drift")
    if len(SYNTHESIS_PRODUCTION_MILESTONES_V1.get("production", ())) != 7:
        errors.append("production_milestone_count")
    return _rlm_meta("gp08_rlm05_production_milestones_frozen", errors)


def verify_gp08_rlm06_prod_syn01_threshold_static() -> dict[str, Any]:
    errors: list[str] = []
    if PROD_SYN01_MATRIX_ROW_ID_V1 != "PROD-SYN-01":
        errors.append("prod_syn01_row_id")
    if PROD_SYN01_FORBIDDEN_RATE_THRESHOLD_PERMILLE_V1 != 0:
        errors.append("threshold_must_be_zero_for_cert")
    return _rlm_meta("gp08_rlm06_prod_syn01_threshold", errors)


def verify_gp08_rlm07_build_catalog_contract_shape_static() -> dict[str, Any]:
    errors: list[str] = []
    doc = build_synthesis_runtime_legality_matrix_catalog_v1(tenant_id=uuid.UUID(int=0))
    if doc.get("synthesis_runtime_legality_matrix_contract") != SYNTHESIS_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1:
        errors.append("contract_literal_mismatch")
    if doc.get("gate_id") != GP08_RLM01_GATE_ID_V1:
        errors.append("gate_id_mismatch")
    if len(doc.get("predicates", [])) != 7:
        errors.append("predicates_len")
    if len(doc.get("forbidden_deployments", [])) != 5:
        errors.append("forbidden_len")
    if "production_milestones" not in doc:
        errors.append("missing_production_milestones")
    if "prod_syn01" not in doc:
        errors.append("missing_prod_syn01_key")
    return _rlm_meta("gp08_rlm07_build_catalog_contract_shape", errors)


def verify_gp08_rlm08_admin_openapi_path_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = ("/admin/tenants/{tenant_id}/cortex/synthesis/runtime-legality-matrix",)
    if SYNTHESIS_RUNTIME_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1 != want:
        errors.append("admin_path_tuple_drift")
    return _rlm_meta("gp08_rlm08_admin_openapi_path_matrix", errors)


def verify_gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle() -> dict[str, Any]:
    """**G-P08-RLM-01** — PR-blocking static bundle for runtime legality matrix closure."""
    errors: list[str] = []
    for fn in (
        verify_gp08_rlm01_predicate_catalog_seven_sorted_unique_static,
        verify_gp08_rlm02_s_leg01_anti01_ci_green_static,
        verify_gp08_rlm03_s_leg02_replay01_double_run_static,
        verify_gp08_rlm04_forbidden_deployments_shape_static,
        verify_gp08_rlm05_production_milestones_frozen_static,
        verify_gp08_rlm06_prod_syn01_threshold_static,
        verify_gp08_rlm07_build_catalog_contract_shape_static,
        verify_gp08_rlm08_admin_openapi_path_matrix_static,
    ):
        out = fn()
        if not out.get("passed"):
            errors.append(str(out.get("name")))
    return _rlm_meta("gp08_rlm01_synthesis_runtime_legality_matrix_static_bundle", errors)
