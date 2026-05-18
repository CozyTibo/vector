"""Phase 08 synthesis integration-test helpers (E2E operational certification)."""

from vector.domains.cortex.synthesis.testing.e2e_operational_certification import (
    GP08_E2E01_GATE_ID_V1,
    build_synthesis_e2e_operational_catalog_v1,
    run_synthesis_e2e_certification_bundle_v1,
    run_synthesis_e2e_scenario_a_v1,
    run_synthesis_e2e_scenario_b_v1,
    run_synthesis_e2e_scenario_c_v1,
    run_synthesis_e2e_scenario_d_v1,
    verify_gp08_e2e01_operational_certification_static,
)
from vector.domains.cortex.synthesis.testing.e2e_pipeline_harness import (
    build_synthesis_pipeline_execute_stub_v1,
    run_substrate_pipeline_sync_through_synthesis_v1,
)
from vector.domains.cortex.synthesis.testing.e2e_verification import (
    assert_synthesis_control_plane_runtime_backed_v1,
    assert_synthesis_substrate_ready_v1,
    legal_retrieval_stub_v1,
)

__all__ = [
    "GP08_E2E01_GATE_ID_V1",
    "assert_synthesis_control_plane_runtime_backed_v1",
    "assert_synthesis_substrate_ready_v1",
    "build_synthesis_e2e_operational_catalog_v1",
    "build_synthesis_pipeline_execute_stub_v1",
    "legal_retrieval_stub_v1",
    "run_substrate_pipeline_sync_through_synthesis_v1",
    "run_synthesis_e2e_certification_bundle_v1",
    "run_synthesis_e2e_scenario_a_v1",
    "run_synthesis_e2e_scenario_b_v1",
    "run_synthesis_e2e_scenario_c_v1",
    "run_synthesis_e2e_scenario_d_v1",
    "verify_gp08_e2e01_operational_certification_static",
]
