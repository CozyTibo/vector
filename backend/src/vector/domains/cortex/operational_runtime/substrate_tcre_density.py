"""Phase 08.5 P085-19 — TCRE reconstruction density metrics (**G-P085-TCRE-02**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-tcre-maturity-doctrine.md`` §Reconstruction density.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    build_reasoning_runtime_health_v1,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_TCRE_DENSITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TCRE_DENSITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-tcre-maturity-doctrine.md"
)

GP085_TCRE02_GATE_ID_V1: Final[str] = "G-P085-TCRE-02"

METRIC_TCRE_MATERIALIZATION_TOTAL_V1: Final[str] = "tcre_materialization_total"
METRIC_TCRE_RECONSTRUCTED_COUNT_V1: Final[str] = "tcre_reconstructed_count"
METRIC_TCRE_PENDING_COUNT_V1: Final[str] = "tcre_pending_count"
METRIC_TCRE_SATURATION_PERCENT_V1: Final[str] = "tcre_saturation_percent"
METRIC_TCRE_DENSITY_SCORE_V1: Final[str] = "tcre_density_score"

TCRE_DENSITY_METRIC_IDS_V1: Final[tuple[str, ...]] = (
    METRIC_TCRE_MATERIALIZATION_TOTAL_V1,
    METRIC_TCRE_RECONSTRUCTED_COUNT_V1,
    METRIC_TCRE_PENDING_COUNT_V1,
    METRIC_TCRE_SATURATION_PERCENT_V1,
    METRIC_TCRE_DENSITY_SCORE_V1,
)

TCRE_MATURITY_R0_V1: Final[str] = "R0"
TCRE_MATURITY_R1_V1: Final[str] = "R1"
TCRE_MATURITY_R2_V1: Final[str] = "R2"
TCRE_MATURITY_R3_V1: Final[str] = "R3"

TCRE_MATURITY_CLASS_IDS_V1: Final[tuple[str, ...]] = (
    TCRE_MATURITY_R0_V1,
    TCRE_MATURITY_R1_V1,
    TCRE_MATURITY_R2_V1,
    TCRE_MATURITY_R3_V1,
)

TCRE_MATURITY_R1_SATURATION_LT_V1: Final[float] = 25.0
TCRE_MATURITY_R3_SATURATION_GTE_V1: Final[float] = 85.0


class SubstrateTcreDensityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def count_tcre_materialization_total_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )


def count_tcre_completed_reconstruct_jobs_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        )
        or 0
    )


def sum_tcre_reconstructed_from_completed_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_limit: int = 50,
) -> tuple[int, int]:
    """Return ``(reconstructed_count, degraded_chronology_count)`` from job summaries."""
    completed_jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(max(1, int(job_limit)))
        ).all()
    )
    reconstructed = 0
    degraded_chron = 0
    for job in completed_jobs:
        summary = dict(job.summary_json or {})
        reconstructed += int(
            summary.get("materialization_count")
            or summary.get("chronology_count")
            or summary.get("chronology_receipt_count")
            or 0
        )
        degraded_chron += int(summary.get("chronology_degraded_count") or 0)
    return reconstructed, degraded_chron


def compute_tcre_saturation_percent_v1(
    *,
    tcre_materialization_total: int,
    tcre_reconstructed_count: int,
) -> float:
    if tcre_materialization_total <= 0:
        return 0.0
    ratio = float(tcre_reconstructed_count) / float(tcre_materialization_total)
    return round(min(100.0, max(0.0, ratio * 100.0)), 2)


def compute_tcre_density_score_v1(*, tcre_saturation_percent: float) -> int:
    """Doctrine: ``tcre_density_score`` is 0–100 aligned with saturation percent."""
    return int(min(100, max(0, round(tcre_saturation_percent))))


def classify_tcre_maturity_class_v1(
    *,
    tcre_saturation_percent: float,
    completed_reconstruct_jobs: int,
) -> str:
    """Maturity **R0–R3** per doctrine saturation bands."""
    if completed_reconstruct_jobs <= 0:
        return TCRE_MATURITY_R0_V1
    if tcre_saturation_percent >= TCRE_MATURITY_R3_SATURATION_GTE_V1:
        return TCRE_MATURITY_R3_V1
    if tcre_saturation_percent >= TCRE_MATURITY_R1_SATURATION_LT_V1:
        return TCRE_MATURITY_R2_V1
    return TCRE_MATURITY_R1_V1


def derive_tcre_substrate_state_v1(
    *,
    mat_total: int,
    reconstructed: int,
    reconstruction_never_run: bool,
    failed_jobs: int,
    degraded_chron: int,
    pending: int,
) -> str:
    """**G-P085-ANTI-IDLE-01** — never healthy on ``reconstruction_not_yet_run``."""
    if mat_total == 0:
        return "critical"
    if failed_jobs and reconstructed == 0:
        return "critical"
    if reconstruction_never_run:
        return "degraded"
    if degraded_chron or failed_jobs or pending:
        return "degraded"
    return "healthy"


def compute_tcre_density_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant TCRE density snapshot (**G-P085-TCRE-02**)."""
    mat_total = count_tcre_materialization_total_v1(session, tenant_id=tenant_id)
    reconstructed_raw, degraded_chron = sum_tcre_reconstructed_from_completed_jobs_v1(
        session,
        tenant_id=tenant_id,
    )
    reconstructed = min(reconstructed_raw, mat_total) if mat_total else 0
    pending = max(0, mat_total - reconstructed) if mat_total else 0
    completed_jobs = count_tcre_completed_reconstruct_jobs_v1(session, tenant_id=tenant_id)
    saturation_percent = compute_tcre_saturation_percent_v1(
        tcre_materialization_total=mat_total,
        tcre_reconstructed_count=reconstructed,
    )
    density_score = compute_tcre_density_score_v1(tcre_saturation_percent=saturation_percent)
    maturity_class = classify_tcre_maturity_class_v1(
        tcre_saturation_percent=saturation_percent,
        completed_reconstruct_jobs=completed_jobs,
    )
    reconstruction_never_run = mat_total > 0 and completed_jobs == 0

    health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)
    failed_jobs = int(health.get("failed_job_count") or 0)

    substrate_state = derive_tcre_substrate_state_v1(
        mat_total=mat_total,
        reconstructed=reconstructed,
        reconstruction_never_run=reconstruction_never_run,
        failed_jobs=failed_jobs,
        degraded_chron=degraded_chron,
        pending=pending,
    )

    metrics = {
        METRIC_TCRE_MATERIALIZATION_TOTAL_V1: mat_total,
        METRIC_TCRE_RECONSTRUCTED_COUNT_V1: reconstructed,
        METRIC_TCRE_PENDING_COUNT_V1: pending,
        METRIC_TCRE_SATURATION_PERCENT_V1: saturation_percent,
        METRIC_TCRE_DENSITY_SCORE_V1: density_score,
        "completed_reconstruct_jobs": completed_jobs,
        "degraded_chronology_count": degraded_chron,
        "reconstruction_never_run": reconstruction_never_run,
        "saturation_ratio": round(saturation_percent / 100.0, 4) if mat_total else 0.0,
    }

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_TCRE02_GATE_ID_V1,
        "tcre_maturity_class": maturity_class,
        "substrate_state": substrate_state,
        "metrics": metrics,
        "runtime_health": {
            "degraded_chronology_percent": health.get("degraded_chronology_percent"),
            "degraded_edge_percent": health.get("degraded_edge_percent"),
            "failed_job_count": failed_jobs,
            "last_replay_result": health.get("last_replay_result"),
        },
    }


def build_tcre_density_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator density card — canonical **G-P085-TCRE-02** surface."""
    snap = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(snap["metrics"])
    return {
        "surface_kind": "tcre_density_card",
        "gate_id": GP085_TCRE02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "tcre_maturity_class": snap["tcre_maturity_class"],
        "substrate_state": snap["substrate_state"],
        METRIC_TCRE_MATERIALIZATION_TOTAL_V1: metrics[METRIC_TCRE_MATERIALIZATION_TOTAL_V1],
        METRIC_TCRE_RECONSTRUCTED_COUNT_V1: metrics[METRIC_TCRE_RECONSTRUCTED_COUNT_V1],
        METRIC_TCRE_PENDING_COUNT_V1: metrics[METRIC_TCRE_PENDING_COUNT_V1],
        METRIC_TCRE_SATURATION_PERCENT_V1: metrics[METRIC_TCRE_SATURATION_PERCENT_V1],
        METRIC_TCRE_DENSITY_SCORE_V1: metrics[METRIC_TCRE_DENSITY_SCORE_V1],
        "metrics": metrics,
        "runtime_health": snap["runtime_health"],
        "detail_route": f"/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-density",
    }


def build_substrate_tcre_density_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_tcre_density_runtime_schema_version": int(
            PHASE085_TCRE_DENSITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TCRE_DENSITY_SPEC_REF_V1,
        "primary_gate_id": GP085_TCRE02_GATE_ID_V1,
        "metric_ids": list(TCRE_DENSITY_METRIC_IDS_V1),
        "tcre_maturity_class_ids": list(TCRE_MATURITY_CLASS_IDS_V1),
        "maturity_thresholds": {
            "r0_no_completed_jobs": True,
            "r1_saturation_lt_percent": TCRE_MATURITY_R1_SATURATION_LT_V1,
            "r2_saturation_range_percent": [
                TCRE_MATURITY_R1_SATURATION_LT_V1,
                TCRE_MATURITY_R3_SATURATION_GTE_V1,
            ],
            "r3_saturation_gte_percent": TCRE_MATURITY_R3_SATURATION_GTE_V1,
        },
        "runtime_package": "vector.domains.cortex.operational_runtime.substrate_tcre_density",
        "admin_explorer_route_hint": "/cortex/reasoning/saturation",
        "density_entrypoint": "compute_tcre_density_metrics_v1",
    }


def verify_gp085_tcre02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_tcre_density_catalog_v1()
    if cat["primary_gate_id"] != GP085_TCRE02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["metric_ids"]) != set(TCRE_DENSITY_METRIC_IDS_V1):
        errors.append("metric_ids_mismatch")

    pct = compute_tcre_saturation_percent_v1(
        tcre_materialization_total=100,
        tcre_reconstructed_count=85,
    )
    if pct != 85.0:
        errors.append("saturation_percent_formula")
    if compute_tcre_density_score_v1(tcre_saturation_percent=85.0) != 85:
        errors.append("density_score_alignment")

    if classify_tcre_maturity_class_v1(tcre_saturation_percent=0.0, completed_reconstruct_jobs=0) != TCRE_MATURITY_R0_V1:
        errors.append("maturity_r0")
    if classify_tcre_maturity_class_v1(tcre_saturation_percent=90.0, completed_reconstruct_jobs=2) != TCRE_MATURITY_R3_V1:
        errors.append("maturity_r3")
    if classify_tcre_maturity_class_v1(tcre_saturation_percent=50.0, completed_reconstruct_jobs=1) != TCRE_MATURITY_R2_V1:
        errors.append("maturity_r2")
    if classify_tcre_maturity_class_v1(tcre_saturation_percent=10.0, completed_reconstruct_jobs=1) != TCRE_MATURITY_R1_V1:
        errors.append("maturity_r1")

    if derive_tcre_substrate_state_v1(
        mat_total=10,
        reconstructed=0,
        reconstruction_never_run=True,
        failed_jobs=0,
        degraded_chron=0,
        pending=10,
    ) != "degraded":
        errors.append("never_run_must_degrade")

    from vector.domains.cortex.completeness import tcre_completeness_projection as tcp

    tcp_src = inspect.getsource(tcp.project_tcre_completeness_v1)
    if "compute_tcre_density_metrics_v1" not in tcp_src:
        errors.append("completeness_projection_missing_density_integration")

    from vector.domains.cortex.operational_runtime import substrate_tcre_saturation_scheduling as sts

    if "compute_tcre_density_metrics_v1" not in inspect.getsource(
        sts.compute_tcre_saturation_metrics_v1
    ):
        errors.append("saturation_scheduler_missing_density_delegate")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "compute_tcre_density_metrics_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_tcre_density")

    passed = not errors
    return {
        "id": GP085_TCRE02_GATE_ID_V1,
        "name": "cesp_substrate_tcre_density",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
