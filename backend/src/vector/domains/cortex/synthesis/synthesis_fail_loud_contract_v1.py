"""Wave S4 step 16 — synthesis fail-loud contract (gates must stay enabled, never silent empty success)."""

from __future__ import annotations

import inspect
from typing import Any, Final

SYNTHESIS_FAIL_LOUD_CONTRACT_SCHEMA_VERSION: Final[int] = 1
WAVE_S4_STEP_16: Final[str] = "wave_s4_synthesis_fail_loud_contract"

# Non-negotiable gates (phase plan §7.1 / §7.4). Do not weaken or bypass for green dashboards.
SYNTHESIS_FAIL_LOUD_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "phase08_empty_scope_truth",
    "synthesis_per_island_all_scopes_failed",
    "synthesis_epoch_scope_in_scope",
    "synthesis_empty_claims_publish",
    "synthesis_retrieval_semantic_mix",
    "synthesis_execution_grounding",
    "synthesis_useful_artifact_v1",
)


def is_phase08_empty_scope_gate_enabled_v1() -> bool:
    from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
        is_phase08_empty_scope_truth_gate_enabled_v1,
    )

    return is_phase08_empty_scope_truth_gate_enabled_v1()


def is_synthesis_job_reconcile_on_materialize_enabled_v1() -> bool:
    from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
        is_synthesis_job_reconcile_on_materialize_enabled_v1,
    )

    return is_synthesis_job_reconcile_on_materialize_enabled_v1()


def snapshot_synthesis_fail_loud_contract_v1() -> dict[str, Any]:
    """Operator/audit snapshot — default-on gates for Wave S4 step 16."""
    return {
        "schema_version": SYNTHESIS_FAIL_LOUD_CONTRACT_SCHEMA_VERSION,
        "wave_step": WAVE_S4_STEP_16,
        "gate_ids": list(SYNTHESIS_FAIL_LOUD_GATE_IDS_V1),
        "phase08_empty_scope_gate_enabled": is_phase08_empty_scope_gate_enabled_v1(),
        "synthesis_job_reconcile_on_materialize": is_synthesis_job_reconcile_on_materialize_enabled_v1(),
        "policy": "empty_claims_and_empty_scope_are_worse_than_FAILED",
    }


def verify_synthesis_fail_loud_pipeline_wiring_v1() -> dict[str, Any]:
    """Static wiring proof — phase 08 runner must attach fail-loud gates before complete."""
    from vector.domains.cortex.synthesis import synthesis_pipeline as sp

    src = inspect.getsource(sp.run_substrate_phase_08_synthesis_v1)
    errors: list[str] = []
    if "attach_phase08_empty_scope_truth_gate_v1" not in src:
        errors.append("missing_empty_scope_truth_gate_in_phase08_runner")
    if "should_fail_phase08_for_empty_scope_violation_v1" not in src:
        errors.append("missing_empty_scope_fail_check_in_phase08_runner")
    if "SynthesisPerIslandMaterializeError" not in src:
        errors.append("missing_per_island_fail_loud_handler")
    if "enforce_retrieval_semantic_before_synthesis_v1" not in src:
        errors.append("missing_retrieval_semantic_gate_in_phase08_runner")
    from vector.domains.cortex.synthesis import synthesis_orchestrator as orch_mod

    orch_src = inspect.getsource(orch_mod.execute_synthesis_job_envelope_v1)
    if "enforce_execution_grounding_before_llm_v1" not in orch_src:
        errors.append("missing_execution_grounding_in_orchestrator")
    if "attach_synthesis_epoch_scope_gate_v1" not in src:
        errors.append("missing_epoch_scope_gate_in_phase08_runner")
    if "should_fail_phase08_for_epoch_scope_violation_v1" not in src:
        errors.append("missing_epoch_scope_fail_check_in_phase08_runner")
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "gates": list(SYNTHESIS_FAIL_LOUD_GATE_IDS_V1),
    }
