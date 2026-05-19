"""Phase 08.5 P085-20 — TCRE omission explainability (**G-P085-TCRE-03**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-tcre-maturity-doctrine.md`` §Omission explainability.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    GP085_TCRE02_GATE_ID_V1,
    compute_tcre_density_metrics_v1,
    derive_tcre_substrate_state_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    build_reasoning_runtime_health_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE085_TCRE_OMISSION_EXPLAINABILITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_TCRE_OMISSION_EXPLAINABILITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-tcre-maturity-doctrine.md"
)

GP085_TCRE03_GATE_ID_V1: Final[str] = "G-P085-TCRE-03"

OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1: Final[str] = "chronology_degraded_count"
OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1: Final[str] = "causal_legality_unverified"
OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1: Final[str] = "reconstruction_coverage_gap"
UPSTREAM_UNMATERIALIZED_RAW_V1: Final[str] = "unmaterialized_raw"
UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1: Final[str] = "traversal_never_executed"
OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1: Final[str] = "reconstruction_not_yet_run"

TCRE_OMISSION_FIELD_IDS_V1: Final[tuple[str, ...]] = (
    OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1,
    OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1,
    OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1,
    UPSTREAM_UNMATERIALIZED_RAW_V1,
    UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1,
)

_EXPLAINABILITY_PANEL_REQUIRED_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "gate_id",
        "tenant_id",
        "omission_counts",
        "upstream_omissions",
        "per_job_explanations",
        "substrate_state",
        "completeness_law",
    }
)


class SubstrateTcreOmissionExplainabilityError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def explain_tcre_reconstruction_job_omissions_v1(
    job: CortexTcreReconstructionJob,
) -> dict[str, Any]:
    """Per-job omission surface (**G-P085-TCRE-03**)."""
    summary = dict(job.summary_json or {})
    scope = dict(job.scope_json or {})

    chronology_degraded_count = int(summary.get("chronology_degraded_count") or 0)
    causal_legality_unverified = 0
    if job.status == "failed":
        causal_legality_unverified = 1
    else:
        causal_legality_unverified = int(summary.get("edge_non_replay_equivalent_count") or 0)

    reconstruction_coverage_gap = 0
    if summary.get("reconstruction_coverage_gap") is not None:
        reconstruction_coverage_gap = int(summary["reconstruction_coverage_gap"])
    elif summary.get("coverage_gap") is not None:
        reconstruction_coverage_gap = int(summary["coverage_gap"])
    else:
        limit = int(scope.get("materialization_limit") or 0)
        mat_count = int(summary.get("materialization_count") or 0)
        if limit > 0 and mat_count >= limit and job.status == "completed":
            reconstruction_coverage_gap = 1

    return {
        "job_id": str(job.id),
        "job_kind": str(job.job_kind),
        "status": str(job.status),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1: chronology_degraded_count,
        OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1: causal_legality_unverified,
        OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1: reconstruction_coverage_gap,
        "materialization_count": int(summary.get("materialization_count") or 0),
        "substrate_pipeline_run_id": scope.get("substrate_pipeline_run_id"),
    }


def build_upstream_omissions_for_tcre_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Upstream omissions blocking or starving TCRE (**G-P085-TCRE-03**)."""
    from vector.domains.cortex.completeness.canonical_completeness_projection import (
        project_canonical_completeness_v1,
    )
    from vector.domains.cortex.completeness.traversal_completeness_projection import (
        project_traversal_completeness_v1,
    )

    canonical = project_canonical_completeness_v1(session, tenant_id=tenant_id)
    traversal = project_traversal_completeness_v1(session, tenant_id=tenant_id)

    canon_omissions = dict(canonical.get("omission_classes") or {})
    trav_omissions = dict(traversal.get("omission_classes") or {})
    canon_metrics = dict(canonical.get("metrics") or {})

    unmaterialized_raw = int(canon_omissions.get("canonical_backlog_unmaterialized") or 0)
    if unmaterialized_raw <= 0:
        raw_count = int(canon_metrics.get("raw_count") or 0)
        mat_count = int(canon_metrics.get("mat_count") or canonical.get("processed_count") or 0)
        unmaterialized_raw = max(0, raw_count - mat_count)

    traversal_never_executed = int(trav_omissions.get("traversal_never_executed") or 0)

    return {
        UPSTREAM_UNMATERIALIZED_RAW_V1: unmaterialized_raw,
        UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1: traversal_never_executed,
        "canonical_substrate_state": canonical.get("substrate_state"),
        "traversal_substrate_state": traversal.get("substrate_state"),
        "detail_routes": {
            "canonical": canonical.get("detail_route"),
            "traversal": traversal.get("detail_route"),
        },
    }


def compute_tcre_omission_counts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_limit: int = 50,
) -> dict[str, int]:
    """Tenant-level omission counts for completeness + operator panels."""
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    mat_total = int(dm["tcre_materialization_total"])
    reconstructed = int(dm["tcre_reconstructed_count"])
    pending = int(dm["tcre_pending_count"])
    reconstruction_never_run = bool(dm.get("reconstruction_never_run"))
    degraded_chron = int(dm.get("degraded_chronology_count") or 0)

    health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)
    failed_jobs = int(health.get("failed_job_count") or 0)

    upstream = build_upstream_omissions_for_tcre_v1(session, tenant_id=tenant_id)

    counts: dict[str, int] = {
        OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1: degraded_chron,
        OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1: failed_jobs,
        UPSTREAM_UNMATERIALIZED_RAW_V1: int(upstream[UPSTREAM_UNMATERIALIZED_RAW_V1]),
        UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1: int(upstream[UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1]),
        OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1: 0,
    }

    if pending and reconstruction_never_run:
        counts[OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1] = pending
    elif pending:
        counts[OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1] = pending

    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .limit(max(1, min(int(job_limit), 200)))
        ).all()
    )
    for job in jobs:
        job_exp = explain_tcre_reconstruction_job_omissions_v1(job)
        counts[OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1] = max(
            counts[OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1],
            int(job_exp[OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1]),
        )
        if job.status == "failed":
            counts[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1] = max(
                counts[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1],
                int(job_exp[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1]),
            )

    if mat_total > 0 and reconstruction_never_run:
        counts.setdefault(OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1, pending or mat_total)

    return counts


def build_tcre_omission_classes_for_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Omission class map for ``project_tcre_completeness_v1`` (**G-P085-TCRE-03**)."""
    counts = compute_tcre_omission_counts_v1(session, tenant_id=tenant_id)
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    reconstruction_never_run = bool(dm.get("reconstruction_never_run"))

    health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)
    omission_classes: dict[str, int] = {}

    if counts.get(OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1):
        omission_classes[OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1] = int(
            counts[OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1]
        )
    elif counts.get(OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1):
        omission_classes[OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1] = int(
            counts[OMISSION_RECONSTRUCTION_COVERAGE_GAP_V1]
        )

    if health.get("last_replay_result") is False:
        omission_classes["replay_divergence_detected"] = 1
    if float(health.get("degraded_chronology_percent") or 0) > 0:
        omission_classes["degradation_propagated"] = int(
            counts.get(OMISSION_CHRONOLOGY_DEGRADED_COUNT_V1) or 0
        )
    if counts.get(OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1):
        omission_classes[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1] = int(
            counts[OMISSION_CAUSAL_LEGALITY_UNVERIFIED_V1]
        )
    if counts.get(UPSTREAM_UNMATERIALIZED_RAW_V1):
        omission_classes[UPSTREAM_UNMATERIALIZED_RAW_V1] = int(counts[UPSTREAM_UNMATERIALIZED_RAW_V1])
    if counts.get(UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1):
        omission_classes[UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1] = int(
            counts[UPSTREAM_TRAVERSAL_NEVER_EXECUTED_V1]
        )

    if reconstruction_never_run and OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1 not in omission_classes:
        pending = int(dm.get("tcre_pending_count") or 0)
        if pending:
            omission_classes[OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1] = pending

    return omission_classes


def build_tcre_omission_explainability_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    per_job_limit: int = 32,
) -> dict[str, Any]:
    """Operator panel — per-job + tenant TCRE omissions (**G-P085-TCRE-03**)."""
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    mat_total = int(dm["tcre_materialization_total"])
    pending = int(dm["tcre_pending_count"])
    reconstruction_never_run = bool(dm.get("reconstruction_never_run"))

    omission_counts = compute_tcre_omission_counts_v1(session, tenant_id=tenant_id)
    upstream = build_upstream_omissions_for_tcre_v1(session, tenant_id=tenant_id)

    lim = max(1, min(int(per_job_limit), 200))
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .limit(lim)
        ).all()
    )
    per_job = [explain_tcre_reconstruction_job_omissions_v1(job) for job in jobs]

    substrate_state = str(density["substrate_state"])
    completeness_law = (
        "TCRE stage MUST be degraded when reconstruction_not_yet_run > 0 AND mat_total > 0"
    )
    if mat_total > 0 and reconstruction_never_run and substrate_state == "healthy":
        substrate_state = "degraded"

    return {
        "gate_id": GP085_TCRE03_GATE_ID_V1,
        "related_gate_id": GP085_TCRE02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "computed_at_utc": datetime.now(tz=UTC).isoformat(),
        "omission_counts": omission_counts,
        "upstream_omissions": upstream,
        "per_job_explanations": per_job,
        "substrate_state": substrate_state,
        "tcre_maturity_class": density["tcre_maturity_class"],
        "density_metrics": dm,
        "completeness_law": completeness_law,
        "completeness_law_satisfied": not (
            mat_total > 0 and reconstruction_never_run and substrate_state == "healthy"
        ),
        "detail_route": (
            f"/admin/tenants/{tenant_id}/cortex/operational-runtime/tcre-omission-explainability"
        ),
    }


def build_substrate_tcre_omission_explainability_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_tcre_omission_explainability_runtime_schema_version": int(
            PHASE085_TCRE_OMISSION_EXPLAINABILITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_TCRE_OMISSION_EXPLAINABILITY_SPEC_REF_V1,
        "primary_gate_id": GP085_TCRE03_GATE_ID_V1,
        "omission_field_ids": list(TCRE_OMISSION_FIELD_IDS_V1),
        "panel_entrypoint": "build_tcre_omission_explainability_panel_v1",
        "completeness_entrypoint": "build_tcre_omission_classes_for_completeness_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability"
        ),
    }


def verify_gp085_tcre03_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_tcre_omission_explainability_catalog_v1()
    if cat["primary_gate_id"] != GP085_TCRE03_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["omission_field_ids"]) != set(TCRE_OMISSION_FIELD_IDS_V1):
        errors.append("omission_field_ids_mismatch")

    if derive_tcre_substrate_state_v1(
        mat_total=10,
        reconstructed=0,
        reconstruction_never_run=True,
        failed_jobs=0,
        degraded_chron=0,
        pending=10,
    ) != "degraded":
        errors.append("never_run_must_degrade")

    panel_src = inspect.getsource(build_tcre_omission_explainability_panel_v1)
    for key in _EXPLAINABILITY_PANEL_REQUIRED_KEYS_V1:
        if key not in panel_src:
            errors.append(f"panel_missing_key:{key}")

    from vector.domains.cortex.completeness import tcre_completeness_projection as tcp

    if "build_tcre_omission_classes_for_completeness_v1" not in inspect.getsource(
        tcp.project_tcre_completeness_v1
    ):
        errors.append("completeness_projection_missing_omission_delegate")

    from vector.domains.cortex.operational_runtime import substrate_tcre_saturation_scheduling as sts

    if "build_tcre_omission_explainability_panel_v1" not in inspect.getsource(
        sts.run_tcre_saturation_schedule_pass_v1
    ):
        errors.append("saturation_pass_missing_omission_explainability")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "build_tcre_omission_explainability_panel_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_tcre_omission_explainability")

    passed = not errors
    return {
        "id": GP085_TCRE03_GATE_ID_V1,
        "name": "cesp_substrate_tcre_omission_explainability",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
