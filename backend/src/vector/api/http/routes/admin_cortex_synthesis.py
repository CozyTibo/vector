"""Admin HTTP — Phase 08 synthesis doctrine catalog (SIL)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.execution.admin_deprecation import (
    execution_admin_path_v1,
    raise_admin_endpoint_gone,
)
from vector.contracts.admin import (
    AdminCortexSynthesisAntiGoalsCatalogResponse,
    AdminCortexSynthesisCitationBindingInspectorResponse,
    AdminCortexSynthesisCitationLawCatalogResponse,
    AdminCortexSynthesisIngressInspectorResponse,
    AdminCortexSynthesisIngressLawCatalogResponse,
    AdminCortexSynthesisJobContractCatalogResponse,
    AdminCortexSynthesisJobDetailResponse,
    AdminCortexSynthesisJobRunResponse,
    AdminCortexSynthesisJobReplayInspectorResponse,
    AdminCortexSynthesisLegalityMatrixCatalogResponse,
    AdminCortexSynthesisPhaseBoundariesCatalogResponse,
    AdminCortexSynthesisProgramCatalogResponse,
    AdminCortexSynthesisReplayExplorerResponse,
    AdminCortexSynthesisOperatorReplayProveResponse,
    AdminCortexSynthesisLlmModelRouteCatalogResponse,
    AdminCortexSynthesisLlmRoutePreviewResponse,
    AdminCortexSynthesisRetrievalPlanCatalogResponse,
    AdminCortexSynthesisPromptAssemblyPreviewResponse,
    AdminCortexSynthesisPromptTemplateCatalogResponse,
    AdminCortexSynthesisRetrievalPlanPreviewResponse,
    AdminCortexSynthesisSdOmissionExplorerResponse,
    AdminCortexSynthesisDegradationTopologyResponse,
    AdminCortexSynthesisArtifactExplorerResponse,
    AdminCortexSynthesisArtifactDetailResponse,
    AdminCortexSynthesisArtifactListResponse,
    AdminCortexSynthesisArtifactQueryCatalogResponse,
    AdminCortexSynthesisObservabilityCatalogResponse,
    AdminCortexSynthesisRuntimeHealthResponse,
    AdminCortexSynthesisBindingsCatalogResponse,
    AdminCortexSynthesisLineageCatalogResponse,
    AdminCortexSynthesisCertificationPackSnapshotResponse,
    AdminCortexSynthesisProgramClosureResponse,
    AdminCortexSynthesisCertificationArchiveListResponse,
    AdminCortexSynthesisCertificationArchiveDetailResponse,
)
from vector.domains.cortex.synthesis.anti_goals import build_synthesis_anti_goals_doctrine_catalog_v1
from vector.domains.cortex.synthesis.phase_boundaries import build_synthesis_phase_boundary_catalog_v1
from vector.domains.cortex.synthesis.synthesis_ingress import (
    build_synthesis_ingress_inspector_v1,
    build_synthesis_ingress_law_catalog_v1,
)
from vector.domains.cortex.synthesis.doctrine_catalog import (
    build_synthesis_program_doctrine_catalog_v1,
)
from vector.domains.cortex.synthesis.anti_goals import (
    SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
    SynthesisAntiGoalViolationError,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    SynthesisEvidenceBindingError,
    build_synthesis_citation_binding_inspector_v1,
    build_synthesis_citation_law_catalog_v1,
    normalize_retrieval_hits_v1,
)
from vector.domains.cortex.synthesis.synthesis_ingress import SynthesisIngressError
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SynthesisJobContractError,
    build_synthesis_job_contract_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import SynthesisJobEnvelopeError
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SynthesisLegalityError,
    build_synthesis_jobs_by_legality_histogram_v1,
    build_synthesis_legality_matrix_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (
    SynthesisOrchestratorError,
    execute_synthesis_job_envelope_v1,
    get_synthesis_job_detail_v1,
)
from vector.domains.cortex.synthesis.synthesis_repository import create_synthesis_job_row_v1
from vector.domains.cortex.synthesis.synthesis_llm_router import (
    SynthesisLlmRouterError,
    build_synthesis_llm_model_route_catalog_v1,
    build_synthesis_llm_route_preview_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    SynthesisArtifactMaterializationError,
    build_synthesis_artifact_explorer_catalog_v1,
    get_synthesis_artifact_detail_v1,
)
from vector.domains.cortex.synthesis.synthesis_bindings import (
    SynthesisBindingsError,
    build_synthesis_bindings_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_lineage import (
    SynthesisLineageError,
    build_synthesis_lineage_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SynthesisBoundedCapsError,
    build_synthesis_omission_explorer_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    build_synthesis_degradation_topology_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    build_synthesis_coverage_catalog_v1,
    build_synthesis_overview_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_control_plane import (
    build_synthesis_control_plane_v1,
)
from vector.domains.cortex.synthesis.synthesis_readiness_economics import (
    build_synthesis_readiness_economics_receipt_v1,
)
from vector.domains.cortex.synthesis.synthesis_runtime_legality_matrix import (
    build_synthesis_runtime_legality_matrix_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_verification_harness import (
    build_synthesis_verification_harness_receipt_v1,
)
from vector.domains.cortex.synthesis.synthesis_evaluation import (
    build_synthesis_evaluation_catalog_v1,
    build_synthesis_evaluation_explorer_v1,
)
from vector.domains.cortex.synthesis.synthesis_implementation_sequencing import (
    build_synthesis_implementation_sequencing_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_certification_pack import (
    build_synthesis_certification_pack_snapshot_v1,
    get_synthesis_certification_archive_v1,
    list_synthesis_certification_archives_v1,
    persist_synthesis_certification_archive_v1,
    synthesis_certification_archive_public_dict_v1,
)
from vector.domains.cortex.synthesis.synthesis_program_closure import (
    build_synthesis_program_closure_snapshot_v1,
)
from vector.domains.cortex.synthesis.synthesis_publication import (
    SynthesisPublicationError,
    build_synthesis_publication_law_catalog_v1,
    build_synthesis_publication_status_v1,
    publish_synthesis_epoch_v1,
    retract_synthesis_artifact_v1,
    skip_synthesis_publication_for_pipeline_v1,
)
from vector.domains.cortex.synthesis.synthesis_repository import (
    SynthesisRepositoryError,
    apply_synthesis_retention_policy_v1,
    build_synthesis_durable_store_catalog_v1,
    count_synthesis_store_rows_v1,
    run_synthesis_durable_store_load_smoke_v1,
)
from vector.domains.cortex.synthesis.synthesis_golden_vectors import (
    build_synthesis_golden_vectors_catalog_v1,
)
from vector.domains.cortex.synthesis.testing.e2e_operational_certification import (
    build_synthesis_e2e_operational_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_constitutional_freeze import (
    build_synthesis_constitutional_freeze_catalog_v1,
    build_synthesis_constitutional_freeze_signoff_snapshot_v1,
)
from vector.domains.cortex.synthesis.synthesis_tenant_verification import (
    build_org_graph_synthesis_verification_slice_v1,
    compute_synthesis_verification_slice_hash_v1,
    verify_tenant_synthesis_slice_v1,
)
from vector.domains.cortex.synthesis.synthesis_operator_workflows import (
    SynthesisOperatorWorkflowsError,
    build_synthesis_job_debugger_v1,
    build_synthesis_omissions_catalog_v1,
    build_synthesis_operator_workflows_catalog_v1,
    list_synthesis_jobs_admin_v1,
    resolve_tenant_slug_v1,
    retry_synthesis_job_v1,
    run_dangerous_resynthesize_v1,
)
from vector.domains.cortex.synthesis.synthesis_observability import (
    build_synthesis_health_strip_v1,
    build_synthesis_observability_catalog_v1,
    build_synthesis_runtime_health_v1,
    snapshot_synthesis_metrics_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_query import (
    SynthesisArtifactListFiltersV1,
    SynthesisArtifactQueryError,
    build_synthesis_artifact_query_catalog_v1,
    list_synthesis_artifacts_query_v1,
)
from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
    SynthesisPromptAssemblyError,
    build_synthesis_prompt_assembly_preview_v1,
    build_synthesis_prompt_template_catalog_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import (
    SynthesisQueryPlanError,
    build_synthesis_retrieval_plan_catalog_v1,
    build_synthesis_retrieval_plan_preview_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    SynthesisReplayEquivalenceError,
    build_synthesis_job_replay_inspector_v1,
    build_synthesis_replay_explorer_catalog_v1,
    list_recent_synthesis_jobs_replay_summary_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
    SynthesisReplayEquivalenceProofsError,
    run_operator_replay_prove_on_job_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_synthesis_routes(router: APIRouter) -> None:
    @router.get(
        "/catalog/cortex/synthesis/program",
        response_model=AdminCortexSynthesisProgramCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_program() -> AdminCortexSynthesisProgramCatalogResponse:
        """Phase 08 Step 01 — normative program freeze catalog (doctrine, not tenant truth)."""
        raw = build_synthesis_program_doctrine_catalog_v1()
        return AdminCortexSynthesisProgramCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/anti-goals",
        response_model=AdminCortexSynthesisAntiGoalsCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_anti_goals() -> AdminCortexSynthesisAntiGoalsCatalogResponse:
        """Phase 08 Step 02 — forbidden cognition keys + import boundary catalog."""
        raw = build_synthesis_anti_goals_doctrine_catalog_v1()
        return AdminCortexSynthesisAntiGoalsCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/phase-boundaries",
        response_model=AdminCortexSynthesisPhaseBoundariesCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_phase_boundaries() -> (
        AdminCortexSynthesisPhaseBoundariesCatalogResponse
    ):
        """Phase 08 Step 03 — SYN-BND phase boundary catalog (07 / 09 / 10)."""
        raw = build_synthesis_phase_boundary_catalog_v1()
        return AdminCortexSynthesisPhaseBoundariesCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/ingress-law",
        response_model=AdminCortexSynthesisIngressLawCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_ingress_law() -> AdminCortexSynthesisIngressLawCatalogResponse:
        """Phase 08 Step 04 — synthesis retrieval ingress law catalog."""
        raw = build_synthesis_ingress_law_catalog_v1()
        return AdminCortexSynthesisIngressLawCatalogResponse.model_validate(raw)

    @router.post(
        "/catalog/cortex/synthesis/ingress/validate",
        response_model=AdminCortexSynthesisIngressInspectorResponse,
    )
    def admin_catalog_cortex_synthesis_ingress_validate(
        body: dict[str, Any] = Body(...),
    ) -> AdminCortexSynthesisIngressInspectorResponse:
        """Phase 08 Step 04 — ingress inspector preview (retrieval response + optional job envelope)."""
        retrieval = body.get("retrieval_response") or {}
        job = body.get("job_envelope")
        if not isinstance(retrieval, dict):
            retrieval = {}
        job_envelope = job if isinstance(job, dict) else None
        partition = str(
            (job_envelope or {}).get("execution_partition")
            or body.get("job_execution_partition")
            or "authoritative",
        )
        raw = build_synthesis_ingress_inspector_v1(
            retrieval,
            job_envelope=job_envelope,
            job_execution_partition=partition,
        )
        return AdminCortexSynthesisIngressInspectorResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/job-contract",
        response_model=AdminCortexSynthesisJobContractCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_job_contract() -> AdminCortexSynthesisJobContractCatalogResponse:
        """Phase 08 Step 05 — synthesis workload classes + intent taxonomy (G-P08-SCHEMA-01)."""
        raw = build_synthesis_job_contract_catalog_v1()
        return AdminCortexSynthesisJobContractCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/citation-law",
        response_model=AdminCortexSynthesisCitationLawCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_citation_law() -> AdminCortexSynthesisCitationLawCatalogResponse:
        """Phase 08 Step 09 — cite-or-omit law + ``SynthesisCitationV1`` catalog (SYN-LAW-09)."""
        raw = build_synthesis_citation_law_catalog_v1()
        return AdminCortexSynthesisCitationLawCatalogResponse.model_validate(raw)

    @router.post(
        "/catalog/cortex/synthesis/citations/bind",
        response_model=AdminCortexSynthesisCitationBindingInspectorResponse,
    )
    def admin_catalog_cortex_synthesis_citations_bind(
        body: dict[str, Any] = Body(...),
    ) -> AdminCortexSynthesisCitationBindingInspectorResponse:
        """Phase 08 Step 09 — preview evidence binding for retrieval hits + optional claim plan."""
        retrieval = body.get("retrieval_response") or body.get("retrieval_hits") or []
        if isinstance(retrieval, dict):
            hits = normalize_retrieval_hits_v1(retrieval)
        elif isinstance(retrieval, list):
            hits = normalize_retrieval_hits_v1(retrieval)
        else:
            hits = []
        claim_plan = body.get("claim_plan")
        plan = claim_plan if isinstance(claim_plan, list) else None
        raw = build_synthesis_citation_binding_inspector_v1(retrieval_hits=hits, claim_plan=plan)
        return AdminCortexSynthesisCitationBindingInspectorResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/retrieval-plan",
        response_model=AdminCortexSynthesisRetrievalPlanCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_retrieval_plan() -> AdminCortexSynthesisRetrievalPlanCatalogResponse:
        """Phase 08 Step 10 — PLAN+RETRIEVE law catalog (fan-out + Phase **07** integration)."""
        raw = build_synthesis_retrieval_plan_catalog_v1()
        return AdminCortexSynthesisRetrievalPlanCatalogResponse.model_validate(raw)

    @router.post(
        "/catalog/cortex/synthesis/retrieval-plan/preview",
        response_model=AdminCortexSynthesisRetrievalPlanPreviewResponse,
    )
    def admin_catalog_cortex_synthesis_retrieval_plan_preview(
        body: dict[str, Any] = Body(...),
    ) -> AdminCortexSynthesisRetrievalPlanPreviewResponse:
        """Phase 08 Step 10 — preview retrieval sub-query plan for a synthesis job envelope."""
        from vector.domains.cortex.synthesis.synthesis_job_envelope import (
            coerce_body_to_synthesis_job_envelope_v1,
        )

        tenant_raw = body.get("tenant_id")
        tenant_id = uuid.UUID(str(tenant_raw)) if tenant_raw else uuid.UUID(int=0)
        envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
        raw = build_synthesis_retrieval_plan_preview_v1(envelope)
        return AdminCortexSynthesisRetrievalPlanPreviewResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/llm-model-routes",
        response_model=AdminCortexSynthesisLlmModelRouteCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_llm_model_routes() -> (
        AdminCortexSynthesisLlmModelRouteCatalogResponse
    ):
        """Phase 08 Step 11 — LLM model route registry (**SYN-AI-01**)."""
        raw = build_synthesis_llm_model_route_catalog_v1()
        return AdminCortexSynthesisLlmModelRouteCatalogResponse.model_validate(raw)

    @router.post(
        "/catalog/cortex/synthesis/llm-model-routes/preview",
        response_model=AdminCortexSynthesisLlmRoutePreviewResponse,
    )
    def admin_catalog_cortex_synthesis_llm_route_preview(
        body: dict[str, Any] = Body(...),
    ) -> AdminCortexSynthesisLlmRoutePreviewResponse:
        """Phase 08 Step 11 — preview selected routes + prompt hashes for an envelope."""
        from vector.domains.cortex.synthesis.synthesis_job_envelope import (
            coerce_body_to_synthesis_job_envelope_v1,
        )

        tenant_raw = body.get("tenant_id")
        tenant_id = uuid.UUID(str(tenant_raw)) if tenant_raw else uuid.UUID(int=0)
        envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
        claim_slots = body.get("claim_slots")
        slots = claim_slots if isinstance(claim_slots, list) else None
        raw = build_synthesis_llm_route_preview_v1(envelope, claim_slots=slots)
        return AdminCortexSynthesisLlmRoutePreviewResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/prompt-templates",
        response_model=AdminCortexSynthesisPromptTemplateCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_prompt_templates() -> (
        AdminCortexSynthesisPromptTemplateCatalogResponse
    ):
        """Phase 08 Step 12 — prompt template registry (**SYN-PRM-01**)."""
        raw = build_synthesis_prompt_template_catalog_v1()
        return AdminCortexSynthesisPromptTemplateCatalogResponse.model_validate(raw)

    @router.post(
        "/catalog/cortex/synthesis/prompt-templates/preview",
        response_model=AdminCortexSynthesisPromptAssemblyPreviewResponse,
    )
    def admin_catalog_cortex_synthesis_prompt_assembly_preview(
        body: dict[str, Any] = Body(...),
    ) -> AdminCortexSynthesisPromptAssemblyPreviewResponse:
        """Phase 08 Step 12 — preview prompt assemblies + hashes for an envelope."""
        from vector.domains.cortex.synthesis.synthesis_job_envelope import (
            coerce_body_to_synthesis_job_envelope_v1,
        )

        tenant_raw = body.get("tenant_id")
        tenant_id = uuid.UUID(str(tenant_raw)) if tenant_raw else uuid.UUID(int=0)
        envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
        claim_slots = body.get("claim_slots")
        slots = claim_slots if isinstance(claim_slots, list) else None
        raw = build_synthesis_prompt_assembly_preview_v1(envelope, claim_slots=slots)
        return AdminCortexSynthesisPromptAssemblyPreviewResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/sd-explorer",
        response_model=AdminCortexSynthesisSdOmissionExplorerResponse,
    )
    def admin_catalog_cortex_synthesis_sd_explorer() -> AdminCortexSynthesisSdOmissionExplorerResponse:
        """Phase 08 Step 13 — SD-* omission explorer + cap law catalog."""
        raw = build_synthesis_omission_explorer_catalog_v1()
        return AdminCortexSynthesisSdOmissionExplorerResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/degradation-topology",
        response_model=AdminCortexSynthesisDegradationTopologyResponse,
    )
    def admin_catalog_cortex_synthesis_degradation_topology() -> (
        AdminCortexSynthesisDegradationTopologyResponse
    ):
        """Phase 08 Step 18 — global synthesis degradation topology (RD→SD matrix)."""
        raw = build_synthesis_degradation_topology_catalog_v1()
        return AdminCortexSynthesisDegradationTopologyResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/observability",
        response_model=AdminCortexSynthesisObservabilityCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_observability() -> (
        AdminCortexSynthesisObservabilityCatalogResponse
    ):
        """Phase 08 Step 21 — synthesis observability law catalog."""
        raw = build_synthesis_observability_catalog_v1()
        return AdminCortexSynthesisObservabilityCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/artifact-query",
        response_model=AdminCortexSynthesisArtifactQueryCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_artifact_query() -> (
        AdminCortexSynthesisArtifactQueryCatalogResponse
    ):
        """Phase 08 Step 20 — artifact query substrate catalog (filters + indexes)."""
        raw = build_synthesis_artifact_query_catalog_v1()
        return AdminCortexSynthesisArtifactQueryCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/artifact-explorer",
        response_model=AdminCortexSynthesisArtifactExplorerResponse,
    )
    def admin_catalog_cortex_synthesis_artifact_explorer() -> (
        AdminCortexSynthesisArtifactExplorerResponse
    ):
        """Phase 08 Step 14 — artifact explorer doctrine + schema catalog."""
        raw = build_synthesis_artifact_explorer_catalog_v1()
        return AdminCortexSynthesisArtifactExplorerResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/bindings-law",
        response_model=AdminCortexSynthesisBindingsCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_bindings_law() -> AdminCortexSynthesisBindingsCatalogResponse:
        """Phase 08 Step 15 — retrieval/TCRE binding copy law catalog."""
        raw = build_synthesis_bindings_catalog_v1()
        return AdminCortexSynthesisBindingsCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/synthesis/lineage-law",
        response_model=AdminCortexSynthesisLineageCatalogResponse,
    )
    def admin_catalog_cortex_synthesis_lineage_law() -> AdminCortexSynthesisLineageCatalogResponse:
        """Phase 08 Step 16 — synthesis artifact lineage law catalog."""
        raw = build_synthesis_lineage_catalog_v1()
        return AdminCortexSynthesisLineageCatalogResponse.model_validate(raw)

    @router.get("/catalog/cortex/synthesis/verification-harness", response_model=None)
    def admin_catalog_cortex_synthesis_verification_harness(
        run: Annotated[str | None, Query()] = None,
    ) -> dict[str, Any]:
        """Phase 08 Step 26 — **G-P08-*** verification harness catalog + optional run receipt."""
        mode = (run or "catalog").strip().lower()
        return build_synthesis_verification_harness_receipt_v1(run_mode=mode)

    @router.get("/catalog/cortex/synthesis/golden-vectors", response_model=None)
    def admin_catalog_cortex_synthesis_golden_vectors() -> dict[str, Any]:
        """Phase 08 Step 27 — golden corpus manifest + policy pack fixture digest."""
        return build_synthesis_golden_vectors_catalog_v1()

    @router.get("/catalog/cortex/synthesis/evaluation", response_model=None)
    def admin_catalog_cortex_synthesis_evaluation() -> dict[str, Any]:
        """Phase 08 Step 28 — **G-P08-EVAL-01/02** evaluation harness catalog."""
        return build_synthesis_evaluation_catalog_v1()

    @router.get("/catalog/cortex/synthesis/implementation-sequencing", response_model=None)
    def admin_catalog_cortex_synthesis_implementation_sequencing() -> dict[str, Any]:
        """Phase 08 Step 29 — waves 0–7 sequencing catalog + Phase 09 handoff."""
        return build_synthesis_implementation_sequencing_catalog_v1()

    sr = APIRouter(prefix="/tenants/{tenant_id}/cortex/synthesis", tags=["admin-cortex-synthesis"])

    @sr.post("/jobs/run", response_model=None)
    def post_synthesis_job_run(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(...)],
    ) -> JSONResponse | AdminCortexSynthesisJobRunResponse:
        """Phase 08 Step 06 — run synthesis job FSM (sync) or enqueue Celery stub."""
        raise_admin_endpoint_gone(
            deprecated="/admin/tenants/{tenant_id}/cortex/synthesis/jobs/run",
            replacement=execution_admin_path_v1("/restart?from_phase=SYNTHESIS"),
            migration="Direct synthesis job run removed; use execution restart from SYNTHESIS (M8).",
        )
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            if bool(body.get("async")):
                from vector.domains.cortex.synthesis.synthesis_job_envelope import (
                    coerce_body_to_synthesis_job_envelope_v1,
                    compute_synthesis_job_envelope_digest_v1,
                )

                envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
                digest = compute_synthesis_job_envelope_digest_v1(envelope)
                job = create_synthesis_job_row_v1(
                    db,
                    tenant_id=tenant_id,
                    envelope=envelope,
                    envelope_digest=digest,
                )
                from app.tasks.cortex_synthesis_jobs import run_synthesis_job_task

                async_result = run_synthesis_job_task.delay(str(tenant_id), str(job.id))
                job.celery_task_id = async_result.id
                db.flush()
                raw = {
                    "surface_kind": "synthesis_job_run",
                    "phase08_synthesis_orchestrator_runtime_schema_version": 1,
                    "job_id": str(job.id),
                    "tenant_id": str(tenant_id),
                    "status": "queued",
                    "synthesis_workload_class": job.synthesis_workload_class,
                    "synthesis_intent": job.synthesis_intent,
                    "execution_partition": job.execution_partition,
                    "synthesis_legality_class": "synthesis_partial",
                    "synthesis_job_replay_identity": "",
                    "retrieval_ingress_digest": None,
                    "synthesis_orchestrator_build_id": job.synthesis_orchestrator_build_id,
                    "execution_trace": [],
                    "synthesis_job_receipt": {},
                    "idempotent_replay": False,
                    "execution_phases": [],
                    "celery_task_id": async_result.id,
                }
                return AdminCortexSynthesisJobRunResponse.model_validate(raw)
            out = execute_synthesis_job_envelope_v1(db, tenant_id=tenant_id, body=body)
            db.commit()
            return AdminCortexSynthesisJobRunResponse.model_validate(out)
        except SynthesisOrchestratorError as exc:
            db.rollback()
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        except (
            SynthesisJobEnvelopeError,
            SynthesisJobContractError,
            SynthesisAntiGoalViolationError,
            SynthesisIngressError,
            SynthesisLegalityError,
            SynthesisReplayEquivalenceError,
            SynthesisReplayEquivalenceProofsError,
            SynthesisEvidenceBindingError,
            SynthesisQueryPlanError,
            SynthesisLlmRouterError,
            SynthesisPromptAssemblyError,
            SynthesisBoundedCapsError,
            SynthesisArtifactMaterializationError,
            SynthesisBindingsError,
            SynthesisLineageError,
        ) as exc:
            db.rollback()
            return JSONResponse(
                status_code=getattr(exc, "http_status", 403),
                content={
                    "error": getattr(exc, "code", str(exc)),
                    "synthesis_legality_class": SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
                    "detail": getattr(exc, "detail", None),
                },
            )

    @sr.get(
        "/artifacts",
        response_model=AdminCortexSynthesisArtifactListResponse,
    )
    def list_synthesis_artifacts(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        retrieval_lookup_id: Annotated[str | None, Query()] = None,
        retrieval_query_replay_identity: Annotated[str | None, Query()] = None,
        synthesis_publication_epoch: Annotated[str | None, Query()] = None,
        artifact_kind: Annotated[str | None, Query()] = None,
        published: Annotated[bool | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> JSONResponse | AdminCortexSynthesisArtifactListResponse:
        """Phase 08 Step 20 — filtered artifact list (lookup id / epoch / lineage pins)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            raw = list_synthesis_artifacts_query_v1(
                db,
                tenant_id=tenant_id,
                filters=SynthesisArtifactListFiltersV1(
                    retrieval_lookup_id=retrieval_lookup_id,
                    retrieval_query_replay_identity=retrieval_query_replay_identity,
                    synthesis_publication_epoch=synthesis_publication_epoch,
                    artifact_kind=artifact_kind,
                    published=published,
                    limit=limit,
                ),
            )
            return AdminCortexSynthesisArtifactListResponse.model_validate(raw)
        except SynthesisArtifactQueryError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get(
        "/artifacts/{artifact_id}",
        response_model=None,
    )
    def get_synthesis_artifact(
        tenant_id: uuid.UUID,
        artifact_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisArtifactDetailResponse:
        """Phase 08 Step 14 — artifact detail + citations."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            raw = get_synthesis_artifact_detail_v1(
                db,
                tenant_id=tenant_id,
                artifact_id=artifact_id,
            )
            return AdminCortexSynthesisArtifactDetailResponse.model_validate(raw)
        except SynthesisArtifactMaterializationError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get(
        "/artifact-explorer",
        response_model=AdminCortexSynthesisArtifactExplorerResponse,
    )
    def get_synthesis_artifact_explorer(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisArtifactExplorerResponse:
        """Phase 08 Step 14 — tenant-scoped artifact explorer."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_artifact_explorer_catalog_v1(db, tenant_id=tenant_id)
        return AdminCortexSynthesisArtifactExplorerResponse.model_validate(raw)

    @sr.get(
        "/replay-explorer",
        response_model=AdminCortexSynthesisReplayExplorerResponse,
    )
    def get_synthesis_replay_explorer(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisReplayExplorerResponse:
        """Phase 08 Step 17 — synthesis replay explorer (pin law, harness, twin diff schema)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        recent = list_recent_synthesis_jobs_replay_summary_v1(db, tenant_id=tenant_id)
        raw = build_synthesis_replay_explorer_catalog_v1(
            tenant_id=str(tenant_id),
            recent_jobs=recent,
        )
        return AdminCortexSynthesisReplayExplorerResponse.model_validate(raw)

    @sr.get(
        "/jobs/{job_id}/replay-inspector",
        response_model=AdminCortexSynthesisJobReplayInspectorResponse,
    )
    def get_synthesis_job_replay_inspector(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisJobReplayInspectorResponse:
        """Phase 08 Step 08 — per-job replay inspector (receipt embed + identity vector)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            detail = get_synthesis_job_detail_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        raw = build_synthesis_job_replay_inspector_v1(
            job_id=str(job_id),
            tenant_id=str(tenant_id),
            envelope_json=detail["envelope_json"],
            synthesis_job_replay_identity=detail.get("synthesis_job_replay_identity"),
            receipt_json=detail.get("synthesis_job_receipt"),
            execution_trace=detail.get("execution_trace"),
        )
        return AdminCortexSynthesisJobReplayInspectorResponse.model_validate(raw)

    @sr.post(
        "/jobs/{job_id}/replay-prove",
        response_model=AdminCortexSynthesisOperatorReplayProveResponse,
    )
    def post_synthesis_job_replay_prove(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisOperatorReplayProveResponse:
        """Phase 08 Step 17 — operator twin: re-run job envelope and compare to stored receipt."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            raw = run_operator_replay_prove_on_job_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        except SynthesisReplayEquivalenceProofsError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": exc.code, "detail": exc.detail},
            )
        return AdminCortexSynthesisOperatorReplayProveResponse.model_validate(raw)

    @sr.get("/runtime-legality-matrix", response_model=None)
    def get_synthesis_runtime_legality_matrix(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 25 — synthesis runtime legality matrix + PROD-SYN-01."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_runtime_legality_matrix_catalog_v1(db, tenant_id=tenant_id)

    @sr.get("/evaluation", response_model=None)
    def get_synthesis_evaluation_explorer(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 28 — evaluation explorer (**G-P08-EVAL-01/02**)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_evaluation_explorer_v1(db, tenant_id=tenant_id)

    @sr.get("/readiness-economics", response_model=None)
    def get_synthesis_readiness_economics(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        profile: Annotated[str, Query()] = "clean",
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 24 — synthesis readiness economics receipt."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        prof: Literal["clean", "hostile"] = (
            "hostile" if profile.strip().lower() == "hostile" else "clean"
        )
        return build_synthesis_readiness_economics_receipt_v1(
            db,
            tenant_id=tenant_id,
            profile=prof,
        )

    @sr.get("/tenant-verification-slice", response_model=None)
    def get_synthesis_tenant_verification_slice(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        verification_run_id: Annotated[str | None, Query()] = None,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 24 — org_graph_synthesis verification slice + hash."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        slice_body = build_org_graph_synthesis_verification_slice_v1(
            db,
            tenant_id=tenant_id,
            verification_run_id=verification_run_id,
        )
        return {
            "slice": slice_body,
            "synthesis_slice_hash": compute_synthesis_verification_slice_hash_v1(slice_body),
        }

    @sr.get("/tenant-verification", response_model=None)
    def get_synthesis_tenant_verification(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 24 — full tenant synthesis substrate verification (**G-P08-TVER-01**)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return verify_tenant_synthesis_slice_v1(db, tenant_id=tenant_id)

    @sr.get("/workflows", response_model=None)
    def get_synthesis_operator_workflows(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — operator workflows W1–W4 + SPA route registry."""
        tenant = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if tenant is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_operator_workflows_catalog_v1(
            tenant_id=str(tenant_id),
            tenant_slug=str(tenant.slug),
        )

    @sr.get("/jobs", response_model=None)
    def list_synthesis_jobs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — synthesis job list for operator debugger hub."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return list_synthesis_jobs_admin_v1(db, tenant_id=tenant_id, limit=limit)

    @sr.get("/omissions", response_model=None)
    def get_synthesis_omissions(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — SD-* omission histogram + remediation links."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        _ = db
        return build_synthesis_omissions_catalog_v1(tenant_id=str(tenant_id))

    @sr.get("/jobs/{job_id}/debugger", response_model=None)
    def get_synthesis_job_debugger(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — job debugger (detail + SD remediation + Phase 07 cross-link)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            return build_synthesis_job_debugger_v1(db, tenant_id=tenant_id, job_id=job_id)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/jobs/{job_id}/retry", response_model=None)
    def post_synthesis_job_retry(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — W4 retry failed/completed job envelope."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            out = retry_synthesis_job_v1(db, tenant_id=tenant_id, job_id=job_id)
            db.commit()
            return out
        except SynthesisOrchestratorError as exc:
            db.rollback()
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )
        except SynthesisOperatorWorkflowsError as exc:
            db.rollback()
            return JSONResponse(
                status_code=400,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/jobs/resynthesize", response_model=None)
    def post_synthesis_resynthesize(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body(...)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 23 — W3 dangerous force re-synthesis."""
        raise_admin_endpoint_gone(
            deprecated="/admin/tenants/{tenant_id}/cortex/synthesis/jobs/resynthesize",
            replacement=execution_admin_path_v1("/rerun?from_phase=SYNTHESIS"),
            migration="Dangerous resynthesize bypass removed; use execution rerun from SYNTHESIS (M8).",
        )
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            slug = resolve_tenant_slug_v1(db, tenant_id=tenant_id)
            out = run_dangerous_resynthesize_v1(
                db,
                tenant_id=tenant_id,
                tenant_slug=slug,
                confirmation_phrase=body.get("confirmation_phrase"),
                body=body,
            )
            db.commit()
            return out
        except SynthesisOperatorWorkflowsError as exc:
            db.rollback()
            status_code = 403 if exc.code == "confirmation_phrase_invalid" else 400
            return JSONResponse(
                status_code=status_code,
                content={"error": exc.code, "detail": exc.detail},
            )
        except SynthesisOrchestratorError as exc:
            db.rollback()
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get("/control-plane", response_model=None)
    def get_synthesis_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 22 — synthesis admin control plane aggregate."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_control_plane_v1(db, tenant_id=tenant_id)

    @sr.get("/health", response_model=None)
    def get_synthesis_runtime_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisRuntimeHealthResponse:
        """Phase 08 Step 21 — synthesis runtime health + alerts."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_runtime_health_v1(db, tenant_id=tenant_id)
        return AdminCortexSynthesisRuntimeHealthResponse.model_validate(raw)

    @sr.get("/observability", response_model=None)
    def get_synthesis_observability(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 21 — observability catalog + tenant metrics snapshot."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        catalog = build_synthesis_observability_catalog_v1()
        catalog["tenant_id"] = str(tenant_id)
        catalog["metrics"] = snapshot_synthesis_metrics_v1()
        catalog["health_strip"] = build_synthesis_health_strip_v1(db, tenant_id=tenant_id)
        return catalog

    @sr.get("/overview", response_model=None)
    def get_synthesis_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 19 — synthesis substrate overview + health strip."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        overview = build_synthesis_overview_catalog_v1(db, tenant_id=tenant_id)
        overview["health_strip"] = build_synthesis_health_strip_v1(db, tenant_id=tenant_id)
        return overview

    @sr.get("/coverage", response_model=None)
    def get_synthesis_coverage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 19 — synthesis completeness coverage metrics."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_coverage_catalog_v1(db, tenant_id=tenant_id)

    @router.get("/catalog/cortex/synthesis/publication-law", response_model=None)
    def admin_catalog_cortex_synthesis_publication_law() -> dict[str, Any]:
        """Phase 08 Step 32 — publication barrier law catalog (**G-P08-REPLAY-02**)."""
        return build_synthesis_publication_law_catalog_v1()

    @router.get("/catalog/cortex/synthesis/durable-store", response_model=None)
    def admin_catalog_cortex_synthesis_durable_store() -> dict[str, Any]:
        """Phase 08 Step 33 — durable store indexes + retention policy catalog."""
        return build_synthesis_durable_store_catalog_v1()

    @router.get("/catalog/cortex/synthesis/e2e-operational", response_model=None)
    def admin_catalog_cortex_synthesis_e2e_operational() -> dict[str, Any]:
        """Phase 08 Step 34 — E2E operational certification catalog (**G-P08-E2E-01**)."""
        return build_synthesis_e2e_operational_catalog_v1()

    @router.get("/catalog/cortex/synthesis/constitutional-freeze", response_model=None)
    def admin_catalog_cortex_synthesis_constitutional_freeze() -> dict[str, Any]:
        """Phase 08 Step 35 — **P08-FINAL-FREEZE** constitutional sign-off catalog."""
        return build_synthesis_constitutional_freeze_catalog_v1()

    @sr.get("/constitutional-freeze/signoff", response_model=None)
    def get_synthesis_constitutional_freeze_signoff(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 35 — tenant-scoped constitutional freeze sign-off snapshot."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        _ = db
        return build_synthesis_constitutional_freeze_signoff_snapshot_v1()

    @sr.post("/retention/apply", response_model=None)
    def post_synthesis_retention_apply(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any] | None, Body()] = None,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 33 — apply (or dry-run) synthesis retention policy (dangerous when allow_delete)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        payload = body or {}
        try:
            out = apply_synthesis_retention_policy_v1(
                db,
                tenant_id=tenant_id,
                dry_run=bool(payload.get("dry_run", True)),
                failed_job_purge_after_days=payload.get("failed_job_purge_after_days"),
                exploration_unpublished_purge_after_days=payload.get(
                    "exploration_unpublished_purge_after_days",
                ),
                allow_delete=bool(payload.get("allow_delete", False)),
            )
            if not out.get("dry_run"):
                db.commit()
            return out
        except SynthesisRepositoryError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/durable-store/smoke", response_model=None)
    def post_synthesis_durable_store_smoke(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any] | None, Body()] = None,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 33 — index-path load smoke for synthesis durable store."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        payload = body or {}
        iterations = int(payload.get("iterations") or 8)
        out = run_synthesis_durable_store_load_smoke_v1(
            db,
            tenant_id=tenant_id,
            iterations=iterations,
        )
        out["row_counts"] = count_synthesis_store_rows_v1(db, tenant_id=tenant_id)
        db.rollback()
        return out

    @sr.get("/publication", response_model=None)
    def get_synthesis_publication_status(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 32 — synthesis publication epoch status."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        return build_synthesis_publication_status_v1(db, tenant_id=tenant_id)

    @sr.post("/publish", response_model=None)
    def post_synthesis_publish(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any] | None, Body()] = None,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 32 — bump synthesis publication epoch for eligible artifacts."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        payload = body or {}
        artifact_ids_raw = payload.get("artifact_ids") or []
        artifact_ids = [uuid.UUID(str(a)) for a in artifact_ids_raw if a]
        pipeline_raw = payload.get("substrate_pipeline_run_id")
        pipeline_id = uuid.UUID(str(pipeline_raw)) if pipeline_raw else None
        try:
            out = publish_synthesis_epoch_v1(
                db,
                tenant_id=tenant_id,
                published_index_epoch=payload.get("published_index_epoch"),
                substrate_pipeline_run_id=pipeline_id,
                artifact_ids=artifact_ids or None,
                allow_empty_scope=bool(payload.get("allow_empty_scope")),
            )
            db.commit()
            return out
        except SynthesisPublicationError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/publish/skip", response_model=None)
    def post_synthesis_publish_skip(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any], Body()],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 32 — dangerous skip of phase 08 publication (audited)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        pipeline_raw = body.get("substrate_pipeline_run_id")
        if not pipeline_raw:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "substrate_pipeline_run_id_required"},
            )
        reason = str(body.get("reason") or "operator_skip")
        try:
            out = skip_synthesis_publication_for_pipeline_v1(
                db,
                tenant_id=tenant_id,
                pipeline_run_id=uuid.UUID(str(pipeline_raw)),
                reason=reason,
                operator_id=str(body.get("operator_id") or ""),
            )
            db.commit()
            return out
        except SynthesisPublicationError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.post("/artifacts/{artifact_id}/retract", response_model=None)
    def post_synthesis_artifact_retract(
        tenant_id: uuid.UUID,
        artifact_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        body: Annotated[dict[str, Any] | None, Body()] = None,
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 32 — retract artifact without deleting epoch history."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        payload = body or {}
        reason = str(payload.get("reason") or "operator_retract")
        try:
            out = retract_synthesis_artifact_v1(
                db,
                tenant_id=tenant_id,
                artifact_id=artifact_id,
                reason=reason,
            )
            db.commit()
            return out
        except SynthesisPublicationError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get(
        "/degradation-topology",
        response_model=AdminCortexSynthesisDegradationTopologyResponse,
    )
    def get_synthesis_degradation_topology(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisDegradationTopologyResponse:
        """Phase 08 Step 18 — tenant-scoped degradation topology + omission histogram."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_degradation_topology_catalog_v1(tenant_id=str(tenant_id))
        return AdminCortexSynthesisDegradationTopologyResponse.model_validate(raw)

    @sr.get(
        "/legality-matrix",
        response_model=AdminCortexSynthesisLegalityMatrixCatalogResponse,
    )
    def get_synthesis_legality_matrix(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisLegalityMatrixCatalogResponse:
        """Phase 08 Step 07 — S-LEG legality matrix catalog + tenant job histogram."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_legality_matrix_catalog_v1(tenant_id=tenant_id)
        raw["synthesis_jobs_by_legality"] = build_synthesis_jobs_by_legality_histogram_v1(
            db,
            tenant_id=tenant_id,
        )
        return AdminCortexSynthesisLegalityMatrixCatalogResponse.model_validate(raw)

    @sr.get("/jobs/{job_id}", response_model=None)
    def get_synthesis_job(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisJobDetailResponse:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        try:
            raw = get_synthesis_job_detail_v1(db, tenant_id=tenant_id, job_id=job_id)
            return AdminCortexSynthesisJobDetailResponse.model_validate(raw)
        except SynthesisOrchestratorError as exc:
            return JSONResponse(
                status_code=exc.http_status,
                content={"error": exc.code, "detail": exc.detail},
            )

    @sr.get(
        "/certification-pack",
        response_model=AdminCortexSynthesisCertificationPackSnapshotResponse,
    )
    def get_synthesis_certification_pack_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisCertificationPackSnapshotResponse:
        """Phase 08 Step 30 — **SYNTHESIS-CERT-PACK-1** operator snapshot."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_certification_pack_snapshot_v1(tenant_id=tenant_id)
        return AdminCortexSynthesisCertificationPackSnapshotResponse.model_validate(raw)

    @sr.get(
        "/program-closure",
        response_model=AdminCortexSynthesisProgramClosureResponse,
    )
    def get_synthesis_program_closure(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisProgramClosureResponse:
        """Phase 08 Step 30 — FF-P08-5 program closure snapshot."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        raw = build_synthesis_program_closure_snapshot_v1(db, tenant_id=tenant_id)
        return AdminCortexSynthesisProgramClosureResponse.model_validate(raw)

    @sr.post("/certification-pack/archive", response_model=None)
    def post_synthesis_certification_pack_archive(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """Phase 08 Step 30 — persist certification archive when closure passes."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        out = persist_synthesis_certification_archive_v1(db, tenant_id=tenant_id)
        db.commit()
        if not out.get("persisted"):
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"error": "closure_not_passed", "detail": out},
            )
        return out

    @sr.get(
        "/certification-pack/archives",
        response_model=AdminCortexSynthesisCertificationArchiveListResponse,
    )
    def list_synthesis_certification_pack_archives(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query()] = 20,
    ) -> JSONResponse | AdminCortexSynthesisCertificationArchiveListResponse:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        rows = list_synthesis_certification_archives_v1(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexSynthesisCertificationArchiveListResponse.model_validate(
            {
                "archives": [
                    synthesis_certification_archive_public_dict_v1(r) for r in rows
                ],
            },
        )

    @sr.get(
        "/certification-pack/archives/{archive_id}",
        response_model=AdminCortexSynthesisCertificationArchiveDetailResponse,
    )
    def get_synthesis_certification_pack_archive(
        tenant_id: uuid.UUID,
        archive_id: int,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | AdminCortexSynthesisCertificationArchiveDetailResponse:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        row = get_synthesis_certification_archive_v1(
            db,
            tenant_id=tenant_id,
            archive_id=archive_id,
        )
        if row is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "archive_not_found"})
        return AdminCortexSynthesisCertificationArchiveDetailResponse.model_validate(
            {
                "archive": synthesis_certification_archive_public_dict_v1(row),
                "pack_json": dict(row.pack_json),
            },
        )

    @sr.get("/eligibility/explain", response_model=None)
    def get_synthesis_eligibility_explain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
            explain_synthesis_eligibility_v1,
        )

        return explain_synthesis_eligibility_v1(db, tenant_id=tenant_id)

    @sr.get("/eligibility/why-empty", response_model=None)
    def get_synthesis_why_empty_panel(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
            build_synthesis_empty_panel_v1,
        )

        return build_synthesis_empty_panel_v1(db, tenant_id=tenant_id)

    @sr.get("/activation-audits", response_model=None)
    def list_synthesis_activation_audits(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> JSONResponse | dict[str, Any]:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "tenant_not_found"})
        from vector.infrastructure.db.models.cortex_synthesis_activation_audit import (
            CortexSynthesisActivationAudit,
        )

        rows = list(
            db.scalars(
                select(CortexSynthesisActivationAudit)
                .where(CortexSynthesisActivationAudit.tenant_id == tenant_id)
                .order_by(CortexSynthesisActivationAudit.created_at.desc())
                .limit(limit)
            ).all()
        )
        return {
            "audits": [
                {
                    "audit_id": str(row.id),
                    "pipeline_run_id": str(row.pipeline_run_id) if row.pipeline_run_id else None,
                    "scopes_generated": row.scopes_generated,
                    "synthesis_jobs_completed": row.synthesis_jobs_completed,
                    "empty_scope_reason": row.empty_scope_reason,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ],
        }

    router.include_router(sr)
