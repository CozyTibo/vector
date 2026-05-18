"""Phase 08 P08-22 — synthesis admin control plane catalog (**G-P08-CP-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md``.
Sixteen operator surfaces, RBAC matrix, OpenAPI path registry, structural aggregate.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SYNTHESIS_DEGRADATION_POSTURES_V1,
    build_synthesis_omission_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    build_synthesis_coverage_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    build_synthesis_degradation_topology_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_WORKLOAD_CLASSES_V1
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    build_synthesis_jobs_by_legality_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_observability import (
    build_synthesis_health_strip_v1,
    get_synthesis_jobs_total_v1,
    snapshot_synthesis_metrics_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_CP01_GATE_ID_V1: Final[str] = "G-P08-CP-01"

SYNTHESIS_CONTROL_PLANE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md"
)

SYNTHESIS_CONTROL_PLANE_CONTRACT_V1: Final[str] = "synthesis_control_plane_v1"

SYN_CP01_RULE_ID_V1: Final[str] = "SYN-CP-01"

SYNTHESIS_RBAC_PERMISSION_READ_V1: Final[str] = "cortex.synthesis.read"

SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1: Final[str] = "cortex.synthesis.job.run"

SYNTHESIS_RBAC_PERMISSION_PUBLISH_V1: Final[str] = "cortex.synthesis.publish"

SYNTHESIS_RBAC_PERMISSION_REPLAY_V1: Final[str] = "cortex.synthesis.replay"

SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1: Final[str] = "cortex.synthesis.dangerous"

_FORBIDDEN_PATH_SUBSTRINGS_CP01_V1: Final[tuple[str, ...]] = (
    "summarize",
    "prompt=",
    "/llm/generate",
    "insight",
)

SYNTHESIS_ADMIN_OPENAPI_OPERATIONS_V1: Final[dict[str, dict[str, str]]] = {
    "/admin/tenants/{tenant_id}/cortex/synthesis/control-plane": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/health": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/synthesis/observability": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/overview": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/synthesis/coverage": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/run": {
        "post": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-inspector": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-prove": {
        "post": SYNTHESIS_RBAC_PERMISSION_REPLAY_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/artifacts": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/tenants/{tenant_id}/cortex/synthesis/artifacts/{artifact_id}": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/artifact-explorer": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/degradation-topology": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/legality-matrix": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/runtime-legality-matrix": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/replay-explorer": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/evaluation": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/program": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/anti-goals": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/phase-boundaries": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/ingress-law": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/ingress/validate": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/job-contract": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/citation-law": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/citations/bind": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/retrieval-plan": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/retrieval-plan/preview": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/llm-model-routes": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/llm-model-routes/preview": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/prompt-templates": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/prompt-templates/preview": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/sd-explorer": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/degradation-topology": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/observability": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/artifact-query": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/artifact-explorer": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/bindings-law": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/lineage-law": {"get": SYNTHESIS_RBAC_PERMISSION_READ_V1},
    "/admin/catalog/cortex/synthesis/verification-harness": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/golden-vectors": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/evaluation": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/implementation-sequencing": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archive": {
        "post": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archives": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/certification-pack/archives/{archive_id}": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/program-closure": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/publication": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/publish": {
        "post": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/publish/skip": {
        "post": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/artifacts/{artifact_id}/retract": {
        "post": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    },
    "/admin/catalog/cortex/synthesis/publication-law": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/catalog/cortex/synthesis/durable-store": {
        "get": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/retention/apply": {
        "post": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
    },
    "/admin/tenants/{tenant_id}/cortex/synthesis/durable-store/smoke": {
        "post": SYNTHESIS_RBAC_PERMISSION_READ_V1,
    },
}

SYNTHESIS_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = tuple(
    sorted(SYNTHESIS_ADMIN_OPENAPI_OPERATIONS_V1),
)

SYNTHESIS_CONTROL_PLANE_SURFACES_V1: Final[tuple[dict[str, Any], ...]] = (
    {
        "surface_number": 1,
        "surface_id": "synthesis_health_strip",
        "label": "Synthesis health strip",
        "surface_kind": "runtime_backed",
        "operator_question": "Is synthesis replay-safe? Publication epoch? Job failure rate?",
        "admin_routes": ["/health", "/overview"],
        "wired": True,
        "closure_step": 21,
    },
    {
        "surface_number": 2,
        "surface_id": "coverage_panel",
        "label": "Coverage panel",
        "surface_kind": "derived_aggregate",
        "operator_question": "eligible scopes vs synthesized vs published",
        "admin_routes": ["/coverage", "/overview"],
        "wired": True,
        "closure_step": 19,
    },
    {
        "surface_number": 3,
        "surface_id": "policy_pack_inspector",
        "label": "Policy pack inspector",
        "surface_kind": "doctrine_catalog",
        "operator_question": "Active synthesis_policy_pack_digest, caps, model routes",
        "admin_routes": [
            "/catalog/cortex/synthesis/job-contract",
            "/catalog/cortex/synthesis/llm-model-routes",
        ],
        "wired": True,
        "closure_step": 13,
    },
    {
        "surface_number": 4,
        "surface_id": "job_debugger",
        "label": "Job debugger",
        "surface_kind": "runtime_backed",
        "operator_question": "Why this job failed / degraded",
        "admin_routes": ["/jobs/run", "/jobs/{job_id}"],
        "wired": True,
        "closure_step": 6,
    },
    {
        "surface_number": 5,
        "surface_id": "artifact_explorer",
        "label": "Artifact explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Claims, legality, publication state",
        "admin_routes": ["/artifacts", "/artifact-explorer", "/artifacts/{artifact_id}"],
        "wired": True,
        "closure_step": 14,
    },
    {
        "surface_number": 6,
        "surface_id": "citation_evidence_trace",
        "label": "Citation / evidence trace",
        "surface_kind": "runtime_backed",
        "operator_question": "Per-claim → retrieval hit → provenance",
        "admin_routes": ["/catalog/cortex/synthesis/citation-law", "/artifacts/{artifact_id}"],
        "wired": True,
        "closure_step": 9,
    },
    {
        "surface_number": 7,
        "surface_id": "synthesis_provenance",
        "label": "Synthesis provenance",
        "surface_kind": "runtime_backed",
        "operator_question": "Receipt embed, retrieval replay id",
        "admin_routes": ["/jobs/{job_id}/replay-inspector"],
        "wired": True,
        "closure_step": 8,
    },
    {
        "surface_number": 8,
        "surface_id": "synthesis_legality_explorer",
        "label": "Synthesis legality explorer",
        "surface_kind": "derived_aggregate",
        "operator_question": "S-LEG predicates + histogram",
        "admin_routes": ["/legality-matrix", "/runtime-legality-matrix"],
        "wired": True,
        "closure_step": 7,
    },
    {
        "surface_number": 9,
        "surface_id": "synthesis_degradation_explorer",
        "label": "Synthesis degradation explorer",
        "surface_kind": "derived_aggregate",
        "operator_question": "SD-* counts + upstream RD-*",
        "admin_routes": ["/degradation-topology", "/catalog/cortex/synthesis/sd-explorer"],
        "wired": True,
        "closure_step": 18,
    },
    {
        "surface_number": 10,
        "surface_id": "synthesis_replay_explorer",
        "label": "Synthesis replay explorer",
        "surface_kind": "runtime_backed",
        "operator_question": "Twin diff, structural vs wording",
        "admin_routes": ["/replay-explorer", "/jobs/{job_id}/replay-prove"],
        "wired": True,
        "closure_step": 17,
    },
    {
        "surface_number": 11,
        "surface_id": "evaluation_explorer",
        "label": "Evaluation explorer",
        "surface_kind": "verification_probe",
        "operator_question": "G-P08-EVAL-* quality metrics",
        "admin_routes": ["/evaluation", "/catalog/cortex/synthesis/evaluation"],
        "wired": True,
        "closure_step": 28,
    },
    {
        "surface_number": 12,
        "surface_id": "llm_trace_inspector",
        "label": "LLM trace inspector",
        "surface_kind": "runtime_backed",
        "operator_question": "prompt_hash, model_route",
        "admin_routes": ["/catalog/cortex/synthesis/llm-model-routes"],
        "wired": True,
        "closure_step": 11,
    },
    {
        "surface_number": 13,
        "surface_id": "pipeline_synthesis_panel",
        "label": "Pipeline synthesis panel",
        "surface_kind": "runtime_backed",
        "operator_question": "Phase 08 on substrate run detail",
        "admin_routes": [
            "/tenants/{tenant_id}/cortex/substrate-pipeline/runs/{pipeline_run_id}/synthesis-panel",
        ],
        "wired": True,
        "closure_step": 31,
    },
    {
        "surface_number": 14,
        "surface_id": "throughput_latency",
        "label": "Throughput / latency",
        "surface_kind": "derived_aggregate",
        "operator_question": "job duration, token usage, queue depth",
        "admin_routes": ["/observability"],
        "wired": True,
        "closure_step": 21,
    },
    {
        "surface_number": 15,
        "surface_id": "certification_view",
        "label": "Certification view",
        "surface_kind": "verification_probe",
        "operator_question": "SYNTHESIS-CERT-PACK-1 status",
        "admin_routes": ["/certification-pack", "/program-closure"],
        "wired": True,
        "closure_step": 30,
    },
    {
        "surface_number": 16,
        "surface_id": "control_plane_aggregate",
        "label": "Control plane aggregate",
        "surface_kind": "derived_aggregate",
        "operator_question": "Queue depth, workload histogram, economics",
        "admin_routes": ["/control-plane"],
        "wired": True,
        "closure_step": 22,
    },
)


def build_synthesis_rbac_matrix_v1() -> dict[str, Any]:
    return {
        "permissions": {
            SYNTHESIS_RBAC_PERMISSION_READ_V1: "read all GET synthesis surfaces",
            SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1: "create synthesis jobs (POST /jobs/run)",
            SYNTHESIS_RBAC_PERMISSION_PUBLISH_V1: "manual publish barrier override",
            SYNTHESIS_RBAC_PERMISSION_REPLAY_V1: "replay twin + replay explorer",
            SYNTHESIS_RBAC_PERMISSION_DANGEROUS_V1: "force re-synth, purge artifacts",
        },
        "dangerous_operations": [
            {
                "path": "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/run",
                "method": "post",
                "permission": SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1,
                "note": "scoped job creation — dangerous when mis-scoped",
            },
            {
                "path": "/admin/tenants/{tenant_id}/cortex/synthesis/jobs/{job_id}/replay-prove",
                "method": "post",
                "permission": SYNTHESIS_RBAC_PERMISSION_REPLAY_V1,
            },
        ],
    }


def build_synthesis_control_plane_surface_checklist_v1() -> list[dict[str, Any]]:
    """Sixteen surfaces with wiring status for operator closure checklist."""
    prefix = "/admin/tenants/{tenant_id}/cortex/synthesis"
    catalog_prefix = "/admin/catalog/cortex/synthesis"
    out: list[dict[str, Any]] = []
    for surface in SYNTHESIS_CONTROL_PLANE_SURFACES_V1:
        routes = surface.get("admin_routes") or []
        openapi_paths: list[str] = []
        for route in routes:
            if route.startswith("/catalog/"):
                openapi_paths.append(f"{catalog_prefix}{route.removeprefix('/catalog/cortex/synthesis')}")
            else:
                openapi_paths.append(f"{prefix}{route}")
        out.append(
            {
                **surface,
                "openapi_paths": openapi_paths,
                "wired_at_closure": bool(surface.get("wired")),
            }
        )
    return out


def build_synthesis_workload_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Workload histogram from durable synthesis jobs (integers only)."""
    hist = {wl: 0 for wl in sorted(SYNTHESIS_WORKLOAD_CLASSES_V1)}
    rows = session.execute(
        select(CortexSynthesisJob.synthesis_workload_class, func.count())
        .where(CortexSynthesisJob.tenant_id == tenant_id)
        .group_by(CortexSynthesisJob.synthesis_workload_class),
    ).all()
    for workload, count in rows:
        key = str(workload)
        hist[key] = int(count) if key in hist else hist.get(key, 0) + int(count)
    return hist


def build_synthesis_job_status_counts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    rows = session.execute(
        select(CortexSynthesisJob.status, func.count())
        .where(CortexSynthesisJob.tenant_id == tenant_id)
        .group_by(CortexSynthesisJob.status),
    ).all()
    for status, count in rows:
        counts[str(status)] = int(count)
    return counts


def build_synthesis_job_queue_depth_proxy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status.in_(("queued", "running")),
            )
        )
        or 0
    )


def list_recent_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 25,
) -> list[dict[str, Any]]:
    cap = max(1, min(int(limit), 100))
    rows = session.scalars(
        select(CortexSynthesisJob)
        .where(CortexSynthesisJob.tenant_id == tenant_id)
        .order_by(CortexSynthesisJob.created_at.desc())
        .limit(cap),
    ).all()
    return [
        {
            "job_id": str(row.id),
            "status": row.status,
            "synthesis_workload_class": row.synthesis_workload_class,
            "synthesis_intent": row.synthesis_intent,
            "synthesis_legality_class": row.synthesis_legality_class,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in rows
    ]


def build_synthesis_degradation_posture_summary_v1(
    *,
    tenant_id: str,
    coverage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    topo = build_synthesis_degradation_topology_catalog_v1(tenant_id=tenant_id)
    hist = dict(topo.get("omission_histogram") or build_synthesis_omission_histogram_v1())
    substrate_health = (coverage or {}).get("status") if coverage else None
    return {
        "synthesis_degradation_posture": _infer_degradation_posture_from_histogram_v1(hist),
        "substrate_health_state": substrate_health,
        "sd_code_total": sum(int(v) for v in hist.values()),
        "omission_histogram": hist,
        "degradation_postures": sorted(SYNTHESIS_DEGRADATION_POSTURES_V1),
    }


def _infer_degradation_posture_from_histogram_v1(hist: Mapping[str, int]) -> str:
    if not hist:
        return "stable"
    if any(
        sd in hist
        for sd in ("SD-PUBLISH-BLOCKED", "SD-LLM-SCHEMA", "SD-REPLAY-DRIFT")
    ):
        return "critical"
    if sum(hist.values()) > 0:
        return "degraded"
    return "stable"


def _operator_workflows_for_control_plane_v1() -> list[dict[str, Any]]:
    from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
        build_synthesis_operator_workflows_v1,
    )

    return build_synthesis_operator_workflows_v1()


def _publication_barrier_summary_for_control_plane_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_publication import build_synthesis_publication_status_v1

    status = build_synthesis_publication_status_v1(session, tenant_id=tenant_id)
    return {
        "synthesis_publication_epoch": status.get("synthesis_publication_epoch"),
        "published_index_epoch": status.get("published_index_epoch"),
        "gp08_replay02_monotonic": status.get("gp08_replay02_monotonic"),
        "lag_epochs": (status.get("lag_epochs") or {}).get("lag_vs_retrieval"),
        "closure_step": 32,
    }


def build_synthesis_control_plane_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Structural control plane aggregate (surface #16)."""
    checklist = build_synthesis_control_plane_surface_checklist_v1()
    wired_count = sum(1 for s in checklist if s.get("wired_at_closure"))
    coverage = build_synthesis_coverage_catalog_v1(session, tenant_id=tenant_id)
    metrics = snapshot_synthesis_metrics_v1()
    degradation = build_synthesis_degradation_posture_summary_v1(
        tenant_id=str(tenant_id),
        coverage=coverage,
    )
    return {
        "surface_kind": "derived_aggregate",
        "synthesis_control_plane_contract": SYNTHESIS_CONTROL_PLANE_CONTRACT_V1,
        "synthesis_control_plane_runtime_schema_version": (
            PHASE08_SYNTHESIS_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_CP01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_CONTROL_PLANE_SPEC_REF_V1,
        "tenant_id": str(tenant_id),
        "surface_checklist": checklist,
        "surfaces_wired_count": wired_count,
        "surfaces_total": len(SYNTHESIS_CONTROL_PLANE_SURFACES_V1),
        "workload_histogram": build_synthesis_workload_histogram_v1(session, tenant_id=tenant_id),
        "jobs_by_legality": build_synthesis_jobs_by_legality_histogram_v1(
            session,
            tenant_id=tenant_id,
        ),
        "job_status_counts": build_synthesis_job_status_counts_v1(session, tenant_id=tenant_id),
        "job_queue_depth_proxy": build_synthesis_job_queue_depth_proxy_v1(
            session,
            tenant_id=tenant_id,
        ),
        "global_synthesis_jobs_total": get_synthesis_jobs_total_v1(),
        "health_strip": build_synthesis_health_strip_v1(session, tenant_id=tenant_id),
        "coverage_summary": {
            "eligible_scopes": coverage.get("eligible_scopes"),
            "synthesized_scopes": coverage.get("synthesized_scopes"),
            "coverage_percent": coverage.get("coverage_percent"),
            "publication_epoch": coverage.get("publication_epoch"),
            "lag_vs_retrieval": coverage.get("lag_vs_retrieval"),
        },
        "publication_barrier": _publication_barrier_summary_for_control_plane_v1(
            session,
            tenant_id=tenant_id,
        ),
        "degradation_posture_summary": degradation,
        "recent_jobs": list_recent_synthesis_jobs_v1(session, tenant_id=tenant_id, limit=10),
        "metrics": metrics,
        "rbac_matrix": build_synthesis_rbac_matrix_v1(),
        "operator_workflows": _operator_workflows_for_control_plane_v1(),
        "openapi_path_count": len(SYNTHESIS_ADMIN_OPENAPI_PATHS_V1),
    }


def verify_synthesis_control_plane_surface_registry_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(SYNTHESIS_CONTROL_PLANE_SURFACES_V1) != 16:
        errors.append("surface_count_not_16")
    numbers = [int(s["surface_number"]) for s in SYNTHESIS_CONTROL_PLANE_SURFACES_V1]
    if sorted(numbers) != list(range(1, 17)):
        errors.append("surface_numbers_not_1_to_16")
    wired = [s for s in SYNTHESIS_CONTROL_PLANE_SURFACES_V1 if s.get("wired")]
    if len(wired) < 12:
        errors.append(f"expected_at_least_12_wired_got_{len(wired)}")
    aggregate = [s for s in SYNTHESIS_CONTROL_PLANE_SURFACES_V1 if s["surface_id"] == "control_plane_aggregate"]
    if len(aggregate) != 1 or not aggregate[0].get("wired"):
        errors.append("control_plane_aggregate_not_wired")
    return _cp_meta("synthesis_control_plane_surface_registry", errors)


def verify_gp08_cp01_synthesis_control_plane_rbac_static() -> dict[str, Any]:
    """**G-P08-CP-01** — OpenAPI matrix + RBAC + sixteen surfaces."""
    errors: list[str] = []
    reg = verify_synthesis_control_plane_surface_registry_static()
    if not reg.get("passed"):
        errors.extend(reg.get("detail", {}).get("errors") or [])

    for sub in _FORBIDDEN_PATH_SUBSTRINGS_CP01_V1:
        for p in SYNTHESIS_ADMIN_OPENAPI_PATHS_V1:
            if sub in p.lower():
                errors.append(f"forbidden_substring:{sub}:{p}")

    if "/admin/tenants/{tenant_id}/cortex/synthesis/control-plane" not in SYNTHESIS_ADMIN_OPENAPI_OPERATIONS_V1:
        errors.append("missing_control_plane_path")

    rb = build_synthesis_rbac_matrix_v1()
    if SYNTHESIS_RBAC_PERMISSION_JOB_RUN_V1 not in rb.get("permissions", {}):
        errors.append("rbac_job_run_permission_missing")

    cp = build_synthesis_control_plane_v1
    if not callable(cp):
        errors.append("missing_build_synthesis_control_plane_v1")

    return _cp_meta("gp08_cp01_synthesis_control_plane_rbac", errors)


def _cp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_CP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_control_plane_runtime_schema_version": (
                PHASE08_SYNTHESIS_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION
            ),
        },
    }
