"""Cortex Phase 01 — ingestion lifecycle (runs, raw rows, checkpoints)."""

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import (
    EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
    assert_conversation_execution_event,
    build_minimal_conversation_execution_event,
    derive_conversation_execution_event_id,
    derive_deterministic_id,
    validate_conversation_execution_event,
)
from vector.domains.cortex.ingestion.raw_envelope_contract import (
    EnvelopeContractViolation,
    core_envelope_fields,
    validate_raw_payload_for_persistence,
)
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.domains.cortex.ingestion.verification import (
    verify_ingestion_run,
    verify_tenant_ingestion_invariants,
)
from vector.domains.cortex.ingestion.raw_memory_contracts import (
    verify_phase02_step1_runtime_contracts,
)
from vector.domains.cortex.ingestion.raw_memory_persistence import (
    verify_phase02_step2_persistence_provenance,
)
from vector.domains.cortex.ingestion.raw_memory_temporal import (
    latest_known_before_t,
    list_revision_chain,
    verify_phase02_step3_temporal_continuity,
)
from vector.domains.cortex.ingestion.raw_memory_replay import (
    verify_phase02_step4_replay_equivalence,
)
from vector.domains.cortex.ingestion.raw_memory_query import (
    execute_raw_memory_query,
    verify_phase02_step5_query_model,
)
from vector.domains.cortex.ingestion.raw_memory_storage import (
    apply_raw_memory_retention_policy,
    verify_phase02_step6_storage_retention,
)
from vector.domains.cortex.ingestion.raw_memory_failure_recovery import (
    run_raw_memory_recovery_validation,
    sync_raw_memory_failure_cases,
    verify_phase02_step7_failure_recovery,
)
from vector.domains.cortex.ingestion.raw_memory_trust import (
    build_raw_memory_trust_annotation,
    verify_phase02_step8_trust_api_contract,
)
from vector.domains.cortex.ingestion.raw_memory_control_plane import (
    build_raw_memory_control_plane,
    verify_phase02_step9_control_plane_contract,
)
from vector.domains.cortex.ingestion.raw_memory_phase_closure import (
    evaluate_phase02_step10_closure_gate,
)
from vector.domains.cortex.ingestion.raw_memory_enforcement import (
    build_enforcement_summary,
    evaluate_progressive_enforcement,
    verify_phase02_step11_progressive_enforcement,
)

__all__ = [
    "EnvelopeContractViolation",
    "EXECUTION_RECONSTRUCTION_CONTRACT_VERSION",
    "IngestionSyncContext",
    "assert_conversation_execution_event",
    "build_minimal_conversation_execution_event",
    "core_envelope_fields",
    "derive_conversation_execution_event_id",
    "derive_deterministic_id",
    "execute_connector_sync",
    "validate_conversation_execution_event",
    "validate_raw_payload_for_persistence",
    "verify_ingestion_run",
    "verify_tenant_ingestion_invariants",
    "verify_phase02_step1_runtime_contracts",
    "verify_phase02_step2_persistence_provenance",
    "verify_phase02_step3_temporal_continuity",
    "list_revision_chain",
    "latest_known_before_t",
    "verify_phase02_step4_replay_equivalence",
    "execute_raw_memory_query",
    "verify_phase02_step5_query_model",
    "apply_raw_memory_retention_policy",
    "verify_phase02_step6_storage_retention",
    "sync_raw_memory_failure_cases",
    "run_raw_memory_recovery_validation",
    "verify_phase02_step7_failure_recovery",
    "build_raw_memory_trust_annotation",
    "verify_phase02_step8_trust_api_contract",
    "build_raw_memory_control_plane",
    "verify_phase02_step9_control_plane_contract",
    "evaluate_phase02_step10_closure_gate",
    "evaluate_progressive_enforcement",
    "build_enforcement_summary",
    "verify_phase02_step11_progressive_enforcement",
]
