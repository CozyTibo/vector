"""Cortex Phase 01 — ingestion lifecycle (runs, raw rows, checkpoints)."""

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

__all__ = [
    "EnvelopeContractViolation",
    "IngestionSyncContext",
    "core_envelope_fields",
    "execute_connector_sync",
    "validate_raw_payload_for_persistence",
    "verify_ingestion_run",
    "verify_tenant_ingestion_invariants",
]
