"""Admin HTTP — Phase 08.5 Continuous Execution Substrate Program (CESP)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette import status

from vector.api.http.deps import get_db
from vector.contracts.admin import (
    AdminCortexOperationalRuntimeGapMatrixCatalogResponse,
    AdminCortexOperationalRuntimePhaseBoundariesCatalogResponse,
    AdminCortexOperationalRuntimeProgramCatalogResponse,
    AdminCortexOperationalRuntimeVocabularyCatalogResponse,
)
from vector.domains.cortex.operational_runtime.cesp_anti_idle_gate import verify_gp085_anti_idle01_static
from vector.domains.cortex.operational_runtime.cesp_gap_matrix import build_cesp_gap_matrix_catalog_v1
from vector.domains.cortex.operational_runtime.cesp_gap_matrix_gate import (
    verify_gp085_gap_matrix_discipline_static,
)
from vector.domains.cortex.operational_runtime.cesp_phase_boundaries_gate import (
    verify_gp085_phase_boundaries_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_continuation_gate import (
    verify_gp085_continuation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_dlq_gate import verify_gp085_dlq_gate_static
from vector.domains.cortex.operational_runtime.cesp_recovery_receipt_gate import (
    verify_gp085_recovery_receipt_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_graph_density_gate import (
    verify_gp085_graph_density_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_promotion_gate import (
    verify_gp085_promotion_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_orphan_gate import (
    verify_gp085_orphan_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_graph_propagation_gate import (
    verify_gp085_graph_propagation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_traversal_scheduling_gate import (
    verify_gp085_traversal_scheduling_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_traversal_retry_gate import (
    verify_gp085_traversal_retry_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_stalled_traversal_gate import (
    verify_gp085_stalled_traversal_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_traversal_explainability_gate import (
    verify_gp085_traversal_explainability_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_tcre_saturation_gate import (
    verify_gp085_tcre_saturation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_tcre_density_gate import (
    verify_gp085_tcre_density_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_tcre_omission_explainability_gate import (
    verify_gp085_tcre_omission_explainability_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_retrieval_density_gate import (
    verify_gp085_retrieval_density_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_retrieval_starvation_gate import (
    verify_gp085_retrieval_starvation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_retrieval_propagation_gate import (
    verify_gp085_retrieval_propagation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_synthesis_activation_gate import (
    verify_gp085_synthesis_activation_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_synthesis_idle_starved_gate import (
    verify_gp085_synthesis_idle_starved_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_autonomous_recovery_gate import (
    verify_gp085_autonomous_recovery_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_operational_health_gate import (
    verify_gp085_operational_health_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score import (
    build_autonomous_recovery_card_v1,
    build_substrate_autonomous_recovery_catalog_v1,
    evaluate_autonomous_recovery_score_v1,
)
from vector.domains.cortex.operational_runtime.cesp_operational_cockpit_gate import (
    verify_gp085_operational_cockpit_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_operational_explorers_gate import (
    verify_gp085_operational_explorers_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_progression_timeline_causal_gate import (
    verify_gp085_progression_timeline_causal_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_runtime_economics_gate import (
    verify_gp085_runtime_economics_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_certification_pack import (
    build_cesp_certification_pack_snapshot_v1,
    verify_gp085_close01_static,
)
from vector.domains.cortex.operational_runtime.cesp_constitutional_freeze import (
    build_cesp_constitutional_freeze_catalog_v1,
    build_cesp_constitutional_freeze_signoff_snapshot_v1,
)
from vector.domains.cortex.operational_runtime.cesp_phase09_readiness_gate import (
    verify_gp085_phase09_readiness_gate_static,
)
from vector.domains.cortex.operational_runtime.cesp_replay_storm_gate import (
    verify_gp085_replay_storm_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
    build_phase09_readiness_catalog_v1,
    build_phase09_readiness_checklist_v1,
    evaluate_golden_tenant_profile_v1,
    evaluate_phase09_readiness_v1,
    record_phase09_soak_signoff_v1,
)
from vector.domains.cortex.operational_runtime.substrate_replay_storm_handling import (
    build_replay_storm_handling_catalog_v1,
    evaluate_replay_storm_for_tenant_v1,
    operator_acknowledge_replay_storm_v1,
)
from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
    build_runtime_economics_card_v1,
    build_substrate_runtime_economics_catalog_v1,
    evaluate_tenant_density_caps_v1,
    evaluate_vector_queue_backpressure_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_explorers import (
    build_operational_explorer_v1,
    build_operational_explorers_index_v1,
    build_substrate_operational_explorers_catalog_v1,
)
from vector.domains.cortex.operational_runtime.substrate_progression_timeline_causal import (
    build_causal_failure_chain_v1,
    build_overview_integration_v1,
    build_progression_timeline_causal_catalog_v1,
)
from vector.domains.cortex.operational_runtime.cesp_operational_maturity_gate import (
    verify_gp085_operational_maturity_gate_static,
)
from vector.domains.cortex.operational_runtime.operational_cockpit import (
    build_density_trend_rollups_7d_v1,
    build_operational_cockpit_catalog_v1,
    build_operational_cockpit_v1,
    build_operational_command_center_v1,
    build_pipeline_progression_timeline_v1,
    build_substrate_operational_heatmap_v1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions import (
    build_operational_health_card_v1,
    build_substrate_operational_health_catalog_v1,
    evaluate_operational_health_dimensions_v1,
)
from vector.domains.cortex.operational_runtime.cesp_synthesis_throughput_gate import (
    verify_gp085_synthesis_throughput_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    build_operational_maturity_card_v1,
    build_substrate_operational_maturity_catalog_v1,
    evaluate_multidimensional_operational_maturity_v1,
)
from vector.domains.cortex.operational_runtime.cesp_watchdog_gate import verify_gp085_watchdog_gate_static
from vector.domains.cortex.operational_runtime.graph_density import (
    build_graph_density_catalog_v1,
    compute_graph_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    build_graph_density_promotion_catalog_v1,
    evaluate_promotion_backlog_schedule_v1,
    run_graph_density_promotion_pass_v1,
    schedule_graph_density_pass_v1,
)
from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
    build_graph_completeness_propagation_catalog_v1,
    propagate_graph_completeness_stage_v1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    build_graph_orphan_continuity_catalog_v1,
    classify_tenant_graph_orphans_v1,
    run_continuity_stitching_pass_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    build_substrate_traversal_scheduling_catalog_v1,
    evaluate_traversal_schedule_v1,
    run_octs_walk_schedule_pass_v1,
    schedule_octs_walks_for_tenant_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_retry import (
    build_substrate_traversal_retry_catalog_v1,
    run_traversal_retry_and_heal_pass_v1,
    schedule_traversal_retry_and_heal_pass_v1,
)
from vector.domains.cortex.operational_runtime.substrate_stalled_traversal_recovery import (
    build_substrate_stalled_traversal_recovery_catalog_v1,
    evaluate_tenant_traversal_stall_v1,
    run_stalled_traversal_recovery_pass_v1,
    schedule_stalled_traversal_recovery_pass_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_explainability import (
    build_substrate_traversal_explainability_catalog_v1,
    build_traversal_explainability_panel_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
    build_substrate_tcre_saturation_scheduling_catalog_v1,
    evaluate_tcre_saturation_schedule_v1,
    run_tcre_saturation_schedule_pass_v1,
    schedule_tcre_saturation_for_tenant_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    build_substrate_tcre_density_catalog_v1,
    build_tcre_density_card_v1,
    compute_tcre_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability import (
    build_substrate_tcre_omission_explainability_catalog_v1,
    build_tcre_omission_explainability_panel_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    build_retrieval_density_card_v1,
    build_substrate_retrieval_density_catalog_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    build_retrieval_starvation_panel_v1,
    build_substrate_retrieval_starvation_catalog_v1,
    explain_retrieval_eligibility_v1,
)
from vector.domains.cortex.operational_runtime.retrieval_completeness_propagation import (
    build_retrieval_completeness_propagation_catalog_v1,
    propagate_retrieval_completeness_stage_v1,
)
from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
    build_substrate_synthesis_activation_scheduling_catalog_v1,
    evaluate_synthesis_activation_schedule_v1,
    run_synthesis_activation_schedule_pass_v1,
    schedule_synthesis_activation_for_tenant_v1,
)
from vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification import (
    build_synthesis_idle_classification_catalog_v1,
    build_synthesis_idle_classification_panel_v1,
    propagate_synthesis_idle_classification_stage_v1,
)
from vector.domains.cortex.operational_runtime.substrate_synthesis_throughput_maturity import (
    build_substrate_synthesis_throughput_catalog_v1,
    build_synthesis_throughput_card_v1,
    propagate_synthesis_throughput_maturity_stage_v1,
)
from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
    compute_synthesis_throughput_metrics_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.operational_runtime.recovery_receipts import (
    build_recovery_receipt_catalog_v1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity_watchdog import (
    build_substrate_continuity_watchdog_catalog_v1,
)
from vector.domains.cortex.operational_runtime.cesp_progression_gate import (
    verify_gp085_progression_gate_static,
)
from vector.domains.cortex.operational_runtime.recovery_continuity import (
    build_recovery_continuity_catalog_v1,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_progression import (
    build_autonomous_progression_catalog_v1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    build_substrate_continuity_catalog_v1,
)
from vector.domains.cortex.operational_runtime.vocabulary import build_phase085_vocabulary_catalog_v1
from vector.domains.cortex.operational_runtime.doctrine_catalog import (
    build_operational_runtime_program_doctrine_catalog_v1,
)
from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    verify_tenant_anti_idle_law_v1,
)
from vector.domains.cortex.operational_runtime.phase_boundaries import (
    build_operational_runtime_phase_boundary_catalog_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_operational_runtime_routes(router: APIRouter) -> None:
    @router.get(
        "/catalog/cortex/operational-runtime/program",
        response_model=AdminCortexOperationalRuntimeProgramCatalogResponse,
    )
    def admin_catalog_cortex_operational_runtime_program() -> (
        AdminCortexOperationalRuntimeProgramCatalogResponse
    ):
        """Phase 08.5 Step 01 — normative program freeze catalog (doctrine, not tenant truth)."""
        raw = build_operational_runtime_program_doctrine_catalog_v1()
        return AdminCortexOperationalRuntimeProgramCatalogResponse.model_validate(raw)

    @router.get("/catalog/cortex/operational-runtime/anti-idle-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_anti_idle_gate() -> dict[str, object]:
        """Phase 08.5 Step 02 — static **G-P085-ANTI-IDLE-01** gate."""
        return verify_gp085_anti_idle01_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/anti-idle-verification",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_anti_idle_verification(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 02 — tenant substrate completeness anti-idle verification."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return verify_tenant_anti_idle_law_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/phase-boundaries",
        response_model=AdminCortexOperationalRuntimePhaseBoundariesCatalogResponse,
    )
    def admin_catalog_cortex_operational_runtime_phase_boundaries() -> (
        AdminCortexOperationalRuntimePhaseBoundariesCatalogResponse
    ):
        """Phase 08.5 Step 03 — CESP-BND phase boundary catalog (08 / 08.5 / 09 / 10)."""
        raw = build_operational_runtime_phase_boundary_catalog_v1()
        return AdminCortexOperationalRuntimePhaseBoundariesCatalogResponse.model_validate(raw)

    @router.get("/catalog/cortex/operational-runtime/phase-boundaries-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_phase_boundaries_gate() -> dict[str, object]:
        """Phase 08.5 Step 03 — static **G-P085-BND** gate aggregate."""
        return verify_gp085_phase_boundaries_gate_static()

    @router.get(
        "/catalog/cortex/operational-runtime/gap-matrix",
        response_model=AdminCortexOperationalRuntimeGapMatrixCatalogResponse,
    )
    def admin_catalog_cortex_operational_runtime_gap_matrix() -> (
        AdminCortexOperationalRuntimeGapMatrixCatalogResponse
    ):
        """Phase 08.5 Step 04 — living P0/P1 gap matrix catalog (parsed from doctrine doc)."""
        raw = build_cesp_gap_matrix_catalog_v1()
        return AdminCortexOperationalRuntimeGapMatrixCatalogResponse.model_validate(raw)

    @router.get(
        "/catalog/cortex/operational-runtime/vocabulary",
        response_model=AdminCortexOperationalRuntimeVocabularyCatalogResponse,
    )
    def admin_catalog_cortex_operational_runtime_vocabulary() -> (
        AdminCortexOperationalRuntimeVocabularyCatalogResponse
    ):
        """Phase 08.5 Step 04 — closed CESP vocabulary (normative index §Vocabulary)."""
        raw = build_phase085_vocabulary_catalog_v1()
        return AdminCortexOperationalRuntimeVocabularyCatalogResponse.model_validate(raw)

    @router.get("/catalog/cortex/operational-runtime/gap-matrix-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_gap_matrix_gate() -> dict[str, object]:
        """Phase 08.5 Step 04 — static **G-P085-GAP-MATRIX** discipline gate."""
        return verify_gp085_gap_matrix_discipline_static()

    @router.get("/catalog/cortex/operational-runtime/substrate-continuity", response_model=None)
    def admin_catalog_cortex_operational_runtime_substrate_continuity() -> dict[str, object]:
        """Phase 08.5 Step 05 — continuation state machine catalog (**G-P085-CONT-01**)."""
        return build_substrate_continuity_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/continuation-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_continuation_gate() -> dict[str, object]:
        """Phase 08.5 Step 05 — static **G-P085-CONT-01** gate."""
        return verify_gp085_continuation_gate_static()

    @router.get("/catalog/cortex/operational-runtime/autonomous-progression", response_model=None)
    def admin_catalog_cortex_operational_runtime_autonomous_progression() -> dict[str, object]:
        """Phase 08.5 Step 06 — autonomous progression catalog (**G-P085-PROG-01**)."""
        return build_autonomous_progression_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/progression-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_progression_gate() -> dict[str, object]:
        """Phase 08.5 Step 06 — static **G-P085-PROG-01** gate."""
        return verify_gp085_progression_gate_static()

    @router.get("/catalog/cortex/operational-runtime/recovery-continuity", response_model=None)
    def admin_catalog_cortex_operational_runtime_recovery_continuity() -> dict[str, object]:
        """Phase 08.5 Step 07 — DLQ + recovery continuity catalog (**G-P085-DLQ-01**)."""
        return build_recovery_continuity_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/dlq-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_dlq_gate() -> dict[str, object]:
        """Phase 08.5 Step 07 — static **G-P085-DLQ-01** gate."""
        return verify_gp085_dlq_gate_static()

    @router.get("/catalog/cortex/operational-runtime/recovery-receipts", response_model=None)
    def admin_catalog_cortex_operational_runtime_recovery_receipts() -> dict[str, object]:
        """Phase 08.5 Step 08 — recovery receipt catalog (**G-P085-REC-01**)."""
        return build_recovery_receipt_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/recovery-receipt-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_recovery_receipt_gate() -> dict[str, object]:
        """Phase 08.5 Step 08 — static **G-P085-REC-01** gate."""
        return verify_gp085_recovery_receipt_gate_static()

    @router.get("/catalog/cortex/operational-runtime/continuity-watchdog", response_model=None)
    def admin_catalog_cortex_operational_runtime_continuity_watchdog() -> dict[str, object]:
        """Phase 08.5 Step 09 — continuity watchdog catalog (**G-P085-WATCH-01**)."""
        return build_substrate_continuity_watchdog_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/continuity-watchdog-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_continuity_watchdog_gate() -> dict[str, object]:
        """Phase 08.5 Step 09 — static **G-P085-WATCH-01** gate."""
        return verify_gp085_watchdog_gate_static()

    @router.get("/catalog/cortex/operational-runtime/graph-density", response_model=None)
    def admin_catalog_cortex_operational_runtime_graph_density() -> dict[str, object]:
        """Phase 08.5 Step 10 — graph density metrics catalog (**G-P085-GRAPH-01**)."""
        return build_graph_density_catalog_v1()

    @router.get("/catalog/cortex/operational-runtime/graph-density-gate", response_model=None)
    def admin_catalog_cortex_operational_runtime_graph_density_gate() -> dict[str, object]:
        """Phase 08.5 Step 10 — static **G-P085-GRAPH-01** gate."""
        return verify_gp085_graph_density_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/graph-density",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_graph_density(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 10 — tenant graph density explorer payload."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return compute_graph_density_metrics_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/graph-density-promotion",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_graph_density_promotion() -> dict[str, object]:
        """Phase 08.5 Step 11 — lawful edge promotion catalog (**G-P085-PROMO-01**)."""
        return build_graph_density_promotion_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/graph-density-promotion-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_graph_density_promotion_gate() -> dict[str, object]:
        """Phase 08.5 Step 11 — static **G-P085-PROMO-01** gate."""
        return verify_gp085_promotion_gate_static()

    @router.get(
        "/catalog/cortex/operational-runtime/graph-orphan-continuity",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_graph_orphan_continuity() -> dict[str, object]:
        """Phase 08.5 Step 12 — orphan continuity catalog (**G-P085-ORPHAN-01**)."""
        return build_graph_orphan_continuity_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/graph-orphan-continuity-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_graph_orphan_continuity_gate() -> dict[str, object]:
        """Phase 08.5 Step 12 — static **G-P085-ORPHAN-01** gate."""
        return verify_gp085_orphan_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/graph-orphan-continuity",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_graph_orphan_continuity(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 12 — tenant orphan classification explorer."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return classify_tenant_graph_orphans_v1(db, tenant_id=tenant_id)

    @router.get("/catalog/cortex/operational-runtime/traversal-retry", response_model=None)
    def admin_catalog_cortex_operational_runtime_traversal_retry() -> dict[str, object]:
        """Phase 08.5 Step 15 — traversal retry + frontier heal catalog (**G-P085-WALK-02**)."""
        return build_substrate_traversal_retry_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/traversal-retry-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_traversal_retry_gate() -> dict[str, object]:
        """Phase 08.5 Step 15 — static **G-P085-WALK-02** gate."""
        return verify_gp085_traversal_retry_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/traversal-retry",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_traversal_retry(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 15 — last retry/heal pass summary for tenant."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return run_traversal_retry_and_heal_pass_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/stalled-traversal-recovery",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_stalled_traversal_recovery() -> dict[str, object]:
        """Phase 08.5 Step 16 — stalled traversal recovery catalog (**G-P085-WALK-03**)."""
        return build_substrate_stalled_traversal_recovery_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/stalled-traversal-recovery-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_stalled_traversal_recovery_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 16 — static **G-P085-WALK-03** gate."""
        return verify_gp085_stalled_traversal_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/stalled-traversal-recovery",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_stalled_traversal_recovery(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 16 — evaluate traversal stall for tenant."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_tenant_traversal_stall_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/traversal-explainability",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_traversal_explainability() -> dict[str, object]:
        """Phase 08.5 Step 17 — traversal density explainability catalog (**G-P085-WALK-04**)."""
        return build_substrate_traversal_explainability_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/traversal-explainability-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_traversal_explainability_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 17 — static **G-P085-WALK-04** gate."""
        return verify_gp085_traversal_explainability_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/traversal-explainability",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_traversal_explainability(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 17 — traversal density + explainability operator panel."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_traversal_explainability_panel_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/tcre-saturation-scheduling",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_tcre_saturation_scheduling() -> dict[str, object]:
        """Phase 08.5 Step 18 — TCRE saturation scheduler catalog (**G-P085-TCRE-01**)."""
        return build_substrate_tcre_saturation_scheduling_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/tcre-saturation-scheduling-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_tcre_saturation_scheduling_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 18 — static **G-P085-TCRE-01** gate."""
        return verify_gp085_tcre_saturation_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/tcre-saturation-scheduling",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_tcre_saturation_scheduling(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 18 — evaluate TCRE saturation schedule eligibility."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_tcre_saturation_schedule_v1(db, tenant_id=tenant_id)

    @router.get("/catalog/cortex/operational-runtime/tcre-density", response_model=None)
    def admin_catalog_cortex_operational_runtime_tcre_density() -> dict[str, object]:
        """Phase 08.5 Step 19 — TCRE reconstruction density catalog (**G-P085-TCRE-02**)."""
        return build_substrate_tcre_density_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/tcre-density-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_tcre_density_gate() -> dict[str, object]:
        """Phase 08.5 Step 19 — static **G-P085-TCRE-02** gate."""
        return verify_gp085_tcre_density_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/tcre-density",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_tcre_density(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 19 — TCRE density metrics + maturity card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_tcre_density_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/tcre-omission-explainability",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_tcre_omission_explainability() -> dict[str, object]:
        """Phase 08.5 Step 20 — TCRE omission explainability catalog (**G-P085-TCRE-03**)."""
        return build_substrate_tcre_omission_explainability_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/tcre-omission-explainability-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_tcre_omission_explainability_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 20 — static **G-P085-TCRE-03** gate."""
        return verify_gp085_tcre_omission_explainability_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/tcre-omission-explainability",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_tcre_omission_explainability(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 20 — TCRE omission explainability operator panel."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_tcre_omission_explainability_panel_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-density",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_density() -> dict[str, object]:
        """Phase 08.5 Step 21 — retrieval density maturity catalog (**G-P085-RET-01**)."""
        return build_substrate_retrieval_density_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-density-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_density_gate() -> dict[str, object]:
        """Phase 08.5 Step 21 — static **G-P085-RET-01** gate."""
        return verify_gp085_retrieval_density_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/retrieval-density",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_retrieval_density(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 21 — retrieval density metrics + maturity card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_retrieval_density_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-starvation",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_starvation() -> dict[str, object]:
        """Phase 08.5 Step 22 — retrieval starvation + index freshness catalog (**G-P085-RET-02**)."""
        return build_substrate_retrieval_starvation_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-starvation-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_starvation_gate() -> dict[str, object]:
        """Phase 08.5 Step 22 — static **G-P085-RET-02** gate."""
        return verify_gp085_retrieval_starvation_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/retrieval-starvation",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_retrieval_starvation(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 22 — retrieval starvation + freshness operator panel."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_retrieval_starvation_panel_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/retrieval-eligibility/explain",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_retrieval_eligibility_explain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 22 — structured retrieval eligibility / starvation explain API."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return explain_retrieval_eligibility_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-completeness-propagation",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_completeness_propagation() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 23 — retrieval completeness propagation catalog (**G-P085-RET-PROP-01**)."""
        return build_retrieval_completeness_propagation_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/retrieval-completeness-propagation-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_retrieval_completeness_propagation_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 23 — static **G-P085-RET-PROP-01** gate."""
        return verify_gp085_retrieval_propagation_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/retrieval-completeness-propagation",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_retrieval_completeness_propagation(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 23 — propagated retrieval completeness stage card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return propagate_retrieval_completeness_stage_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-activation-scheduling",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_activation_scheduling() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 24 — synthesis activation scheduler catalog (**G-P085-SYN-01**)."""
        return build_substrate_synthesis_activation_scheduling_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-activation-scheduling-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_activation_scheduling_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 24 — static **G-P085-SYN-01** gate."""
        return verify_gp085_synthesis_activation_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-activation-scheduling",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_activation_scheduling(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 24 — evaluate synthesis activation schedule eligibility."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_synthesis_activation_schedule_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-idle-classification",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_idle_classification() -> dict[str, object]:
        """Phase 08.5 Step 25 — synthesis idle vs starved catalog (**G-P085-SYN-02**)."""
        return build_synthesis_idle_classification_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-idle-classification-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_idle_classification_gate() -> (
        dict[str, object]
    ):
        """Phase 08.5 Step 25 — static **G-P085-SYN-02** gate."""
        return verify_gp085_synthesis_idle_starved_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-idle-classification",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_idle_classification(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 25 — propagated synthesis stage card with idle classification."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return propagate_synthesis_idle_classification_stage_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-eligibility/explain",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_eligibility_explain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 25 — structured synthesis eligibility + classification explain API."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return explain_synthesis_eligibility_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-idle-classification/panel",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_idle_classification_panel(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 25 — synthesis idle vs starved operator panel."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_synthesis_idle_classification_panel_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-throughput",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_throughput() -> dict[str, object]:
        """Phase 08.5 Step 26 — synthesis throughput maturity catalog (**G-P085-SYN-03**)."""
        return build_substrate_synthesis_throughput_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/synthesis-throughput-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_synthesis_throughput_gate() -> dict[str, object]:
        """Phase 08.5 Step 26 — static **G-P085-SYN-03** gate."""
        return verify_gp085_synthesis_throughput_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_throughput(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 26 — synthesis throughput maturity metrics card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_synthesis_throughput_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput/stage",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_throughput_stage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 26 — full propagated synthesis stage (SYN-02 + SYN-03)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return propagate_synthesis_throughput_maturity_stage_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/synthesis-throughput/metrics",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_synthesis_throughput_metrics(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 26 — raw throughput metrics snapshot."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return compute_synthesis_throughput_metrics_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/operational-maturity",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_operational_maturity() -> dict[str, object]:
        """Phase 08.5 Step 27 — multi-dimensional operational maturity catalog (**G-P085-MAT-01**)."""
        return build_substrate_operational_maturity_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/operational-maturity-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_operational_maturity_gate() -> dict[str, object]:
        """Phase 08.5 Step 27 — static **G-P085-MAT-01** gate."""
        return verify_gp085_operational_maturity_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_operational_maturity(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 27 — operational maturity dashboard card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_operational_maturity_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity/evaluate",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_operational_maturity_evaluate(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 27 — raw **G-P085-MAT-01** multidimensional evaluation."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_multidimensional_operational_maturity_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/operational-health",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_operational_health() -> dict[str, object]:
        """Phase 08.5 Step 28 — operational health dimension catalog (**G-P085-HEALTH-01**)."""
        return build_substrate_operational_health_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/operational-health-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_operational_health_gate() -> dict[str, object]:
        """Phase 08.5 Step 28 — static **G-P085-HEALTH-01** gate."""
        return verify_gp085_operational_health_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/operational-health",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_operational_health(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 28 — operational health dashboard card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_operational_health_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/operational-health/evaluate",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_operational_health_evaluate(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 28 — full **G-P085-HEALTH-01** health evaluation."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_operational_health_dimensions_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/autonomous-recovery",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_autonomous_recovery() -> dict[str, object]:
        """Phase 08.5 Step 29 — autonomous recovery score catalog (**G-P085-HEALTH-02**)."""
        return build_substrate_autonomous_recovery_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/autonomous-recovery-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_autonomous_recovery_gate() -> dict[str, object]:
        """Phase 08.5 Step 29 — static **G-P085-HEALTH-02** gate."""
        return verify_gp085_autonomous_recovery_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/autonomous-recovery",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_autonomous_recovery(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 29 — autonomous recovery dashboard card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_autonomous_recovery_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/autonomous-recovery/evaluate",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_autonomous_recovery_evaluate(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 29 — raw **G-P085-HEALTH-02** recovery score evaluation."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_autonomous_recovery_score_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/cockpit",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_cockpit() -> dict[str, object]:
        """Phase 08.5 Step 30 — operational cockpit catalog (**G-P085-CP-01**)."""
        return build_operational_cockpit_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/cockpit-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_cockpit_gate() -> dict[str, object]:
        """Phase 08.5 Step 30 — static **G-P085-CP-01** gate."""
        return verify_gp085_operational_cockpit_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/cockpit",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_cockpit(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 30 — full operational cockpit aggregate."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_operational_cockpit_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/cockpit/command-center",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_cockpit_command_center(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 30 — operational command center (surface #1)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_operational_command_center_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/cockpit/timeline",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_cockpit_timeline(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: uuid.UUID | None = None,
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 30 — pipeline progression timeline (surfaces #2, #14)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_pipeline_progression_timeline_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/cockpit/heatmap",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_cockpit_heatmap(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 30 — substrate operational heatmap (surface #15)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_substrate_operational_heatmap_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/cockpit/density-trends",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_cockpit_density_trends(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 30 — 7d density trend rollups (surface #18)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_density_trend_rollups_7d_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/explorers",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_explorers() -> dict[str, object]:
        """Phase 08.5 Step 31 — dedicated explorer surfaces catalog (**G-P085-CP-02**)."""
        return build_substrate_operational_explorers_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/explorers-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_explorers_gate() -> dict[str, object]:
        """Phase 08.5 Step 31 — static **G-P085-CP-02** gate."""
        return verify_gp085_operational_explorers_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/explorers",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_explorers_index(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 31 — tenant explorer hub (all explorers summary cards)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_operational_explorers_index_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/explorers/{explorer_id}",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_explorer_detail(
        tenant_id: uuid.UUID,
        explorer_id: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 31 — single dedicated explorer tables-first payload."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        out = build_operational_explorer_v1(db, tenant_id=tenant_id, explorer_id=explorer_id)
        if out.get("error") == "explorer_not_found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=out)
        return out

    @router.get(
        "/catalog/cortex/operational-runtime/progression-timeline",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_progression_timeline() -> dict[str, object]:
        """Phase 08.5 Step 32 — progression timeline + causal chain catalog (**G-P085-CP-03**)."""
        return build_progression_timeline_causal_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/progression-timeline-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_progression_timeline_gate() -> dict[str, object]:
        """Phase 08.5 Step 32 — static **G-P085-CP-03** gate."""
        return verify_gp085_progression_timeline_causal_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/progression-timeline",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_progression_timeline(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: uuid.UUID | None = None,
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 32 — pipeline progression timeline with ASCII line + propagation."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_pipeline_progression_timeline_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/causal-failure-chain",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_causal_failure_chain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: uuid.UUID | None = None,
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 32 — causal failure / degradation propagation chain."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_causal_failure_chain_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/overview-integration",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_overview_integration(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 32 — overview badges + truthful stage cards (**G-P085-CP-03**)."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_overview_integration_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/runtime-economics",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_economics() -> dict[str, object]:
        """Phase 08.5 Step 33 — runtime economics catalog (**G-P085-ECON-01**)."""
        return build_substrate_runtime_economics_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/runtime-economics-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_economics_gate() -> dict[str, object]:
        """Phase 08.5 Step 33 — static **G-P085-ECON-01** gate."""
        return verify_gp085_runtime_economics_gate_static()

    @router.get(
        "/catalog/cortex/operational-runtime/queue-backpressure",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_queue_backpressure() -> dict[str, object]:
        """Phase 08.5 Step 33 — global vector queue backpressure snapshot."""
        return evaluate_vector_queue_backpressure_v1()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/runtime-economics",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_economics_card(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 33 — tenant runtime economics card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return build_runtime_economics_card_v1(db, tenant_id=tenant_id)

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/runtime-economics/density-caps",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_density_caps(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 33 — tenant density cap utilization."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_tenant_density_caps_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/replay-storm",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_replay_storm() -> dict[str, object]:
        """Phase 08.5 Step 34 — replay storm handling catalog (**G-P085-ECON-02**)."""
        return build_replay_storm_handling_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/replay-storm-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_replay_storm_gate() -> dict[str, object]:
        """Phase 08.5 Step 34 — static **G-P085-ECON-02** gate."""
        return verify_gp085_replay_storm_gate_static()

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/replay-storm",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_replay_storm_card(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 34 — tenant replay storm card."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_replay_storm_for_tenant_v1(db, tenant_id=tenant_id)

    @router.post(
        "/tenants/{tenant_id}/cortex/operational-runtime/replay-storm/acknowledge",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_replay_storm_acknowledge(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 34 — operator ack to resume saturation after replay storm."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return operator_acknowledge_replay_storm_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/phase09-readiness",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_phase09_readiness() -> dict[str, object]:
        """Phase 08.5 Step 35 — Phase 09 readiness catalog (**G-P085-READY-01**)."""
        return build_phase09_readiness_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/phase09-readiness-gate",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_phase09_readiness_gate() -> dict[str, object]:
        """Phase 08.5 Step 35 — static **G-P085-READY-01** gate."""
        return verify_gp085_phase09_readiness_gate_static()

    @router.get(
        "/catalog/cortex/operational-runtime/phase09-readiness/checklist",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_phase09_readiness_checklist(
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, object]:
        """Phase 08.5 Step 35 — readiness checklist **R1–R15**."""
        return evaluate_phase09_readiness_v1(db)

    @router.post(
        "/catalog/cortex/operational-runtime/phase09-readiness/soak-signoff",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_phase09_soak_signoff(
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, object]:
        """Phase 08.5 Step 35 — operator soak sign-off (**R15**)."""
        out = record_phase09_soak_signoff_v1(db, note="admin_catalog_soak_signoff")
        db.commit()
        return out

    @router.get(
        "/tenants/{tenant_id}/cortex/operational-runtime/phase09-readiness/golden-profile",
        response_model=None,
    )
    def admin_tenant_cortex_operational_runtime_phase09_golden_profile(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, object]:
        """Phase 08.5 Step 35 — golden tenant profile evaluation."""
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "tenant_not_found"},
            )
        return evaluate_golden_tenant_profile_v1(db, tenant_id=tenant_id)

    @router.get(
        "/catalog/cortex/operational-runtime/certification-pack",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_certification_pack() -> dict[str, object]:
        """Phase 08.5 Step 36 — **CESP-CERT-PACK-1** snapshot."""
        return build_cesp_certification_pack_snapshot_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/program-closure",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_program_closure() -> dict[str, object]:
        """Phase 08.5 Step 36 — **G-P085-CLOSE-01** closure gate."""
        return verify_gp085_close01_static()

    @router.get(
        "/catalog/cortex/operational-runtime/constitutional-freeze",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_constitutional_freeze() -> dict[str, object]:
        """Phase 08.5 Step 36 — **P085-FINAL-FREEZE** catalog."""
        return build_cesp_constitutional_freeze_catalog_v1()

    @router.get(
        "/catalog/cortex/operational-runtime/constitutional-freeze/signoff",
        response_model=None,
    )
    def admin_catalog_cortex_operational_runtime_constitutional_freeze_signoff() -> dict[
        str, object
    ]:
        """Phase 08.5 Step 36 — constitutional freeze sign-off snapshot."""
        return build_cesp_constitutional_freeze_signoff_snapshot_v1()
