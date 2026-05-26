"""Phase 08.5 P085-26 — CESP surface for synthesis throughput maturity (**G-P085-SYN-03**)."""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
    GP085_SYN03_GATE_ID_V1,
    METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1,
    METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1,
    METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1,
    SYNTHESIS_THROUGHPUT_METRIC_IDS_V1,
    compute_synthesis_activation_audit_empty_rate_v1,
    compute_synthesis_scope_coverage_percent_v1,
    compute_synthesis_throughput_metrics_v1,
    evaluate_synthesis_throughput_targets_v1,
    project_synthesis_completeness_with_throughput_maturity_v1,
)

PHASE085_SYNTHESIS_THROUGHPUT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SYNTHESIS_THROUGHPUT_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-synthesis-activation-doctrine.md"
)


def propagate_synthesis_throughput_maturity_stage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Project synthesis stage with **G-P085-SYN-02** + **G-P085-SYN-03** card law."""
    return project_synthesis_completeness_with_throughput_maturity_v1(
        session,
        tenant_id=tenant_id,
    )


def build_synthesis_throughput_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator throughput maturity card."""
    snap = compute_synthesis_throughput_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(snap["metrics"])
    return {
        "surface_kind": "synthesis_throughput_card",
        "gate_id": GP085_SYN03_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "synthesis_maturity_class": snap["synthesis_maturity_class"],
        "substrate_state": snap["substrate_state"],
        METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: metrics[METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1],
        METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: metrics[METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1],
        METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: metrics[
            METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1
        ],
        "throughput_policy": snap["throughput_policy"],
        "throughput_targets": snap["throughput_targets"],
        "activation_audit_stats": snap["activation_audit_stats"],
        "metrics": metrics,
        "detail_route": (
            f"/admin/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput"
        ),
    }


def build_substrate_synthesis_throughput_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_synthesis_throughput_runtime_schema_version": int(
            PHASE085_SYNTHESIS_THROUGHPUT_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SYNTHESIS_THROUGHPUT_SPEC_REF_V1,
        "primary_gate_id": GP085_SYN03_GATE_ID_V1,
        "metric_ids": list(SYNTHESIS_THROUGHPUT_METRIC_IDS_V1),
        "activation_audit_table": "cortex_synthesis_activation_audits",
        "throughput_targets": {
            METRIC_SYNTHESIS_JOBS_COMPLETED_PER_DAY_V1: "tenant_policy_floor",
            METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1: ">= 90%",
            METRIC_SYNTHESIS_ACTIVATION_AUDIT_EMPTY_RATE_V1: "<= 5% when eligible > 0",
        },
        "classification_package": "vector.domains.cortex.synthesis.synthesis_throughput_maturity",
        "propagation_entrypoint": "propagate_synthesis_throughput_maturity_stage_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_synthesis_throughput_maturity"
        ),
    }


def verify_gp085_syn03_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_synthesis_throughput_catalog_v1()
    if cat["primary_gate_id"] != GP085_SYN03_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["metric_ids"]) != set(SYNTHESIS_THROUGHPUT_METRIC_IDS_V1):
        errors.append("metric_ids_mismatch")

    if compute_synthesis_scope_coverage_percent_v1(eligible_scopes=10, synthesized_scopes=9) != 90.0:
        errors.append("scope_coverage_formula")

    targets = evaluate_synthesis_throughput_targets_v1(
        jobs_completed_per_day=2,
        scope_coverage_percent=95.0,
        activation_audit_empty_rate=2.0,
        eligible_scopes=5,
        policy={
            "jobs_per_day_floor": 1,
            "scope_coverage_target_percent": 90.0,
            "activation_audit_empty_rate_max_percent": 5.0,
        },
    )
    if not targets["all_throughput_targets_met"]:
        errors.append("targets_all_met_fixture")

    targets_fail = evaluate_synthesis_throughput_targets_v1(
        jobs_completed_per_day=0,
        scope_coverage_percent=50.0,
        activation_audit_empty_rate=10.0,
        eligible_scopes=8,
        policy={
            "jobs_per_day_floor": 1,
            "scope_coverage_target_percent": 90.0,
            "activation_audit_empty_rate_max_percent": 5.0,
        },
    )
    if targets_fail["all_throughput_targets_met"]:
        errors.append("targets_should_fail_fixture")

    from vector.domains.cortex.synthesis import synthesis_completeness_projection as scp

    if "project_synthesis_completeness_with_throughput_maturity_v1" not in inspect.getsource(
        scp.project_synthesis_completeness_v1
    ):
        errors.append("completeness_missing_throughput_delegate")

    from vector.domains.cortex.synthesis import synthesis_pipeline as sp

    from vector.domains.cortex.synthesis.synthesis_per_island import materialize_synthesis_per_island_v1

    mat_src = inspect.getsource(sp.materialize_synthesis_for_pipeline_v1)
    island_src = inspect.getsource(materialize_synthesis_per_island_v1)
    if "persist_synthesis_activation_audit_v1" not in mat_src and (
        "persist_synthesis_activation_audit_v1" not in island_src
    ):
        errors.append("materialize_missing_activation_audit")

    upstream = __import__(
        "vector.domains.cortex.operational_runtime.phase_boundaries",
        fromlist=["list_upstream_packages_importing_cesp_violations_v1"],
    ).list_upstream_packages_importing_cesp_violations_v1()
    if upstream:
        errors.append(f"acyclic_upstream_cesp_imports:{upstream[:3]}")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "evaluate_operational_health_dimensions_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_health01_delegate")

    passed = not errors
    return {
        "id": GP085_SYN03_GATE_ID_V1,
        "name": "cesp_substrate_synthesis_throughput_maturity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
