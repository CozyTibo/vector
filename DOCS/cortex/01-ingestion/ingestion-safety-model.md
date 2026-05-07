# Ingestion Safety Model

## Critical Invariants
- Raw event immutability.
- Deterministic envelope generation for fixed version context.
- Idempotent persistence under retries and overlap windows.
- Tenant and connector isolation.
- Provenance bootstrap continuity.
- Replay-safe checkpoint semantics.
- Source traceability retention.

## Must-Never-Violate Rules
- Never overwrite existing raw payload records.
- Never advance checkpoint before persistence ack.
- Never allow replay mode to silently mutate live cursor state.
- Never drop source identity metadata required for downstream lineage.
- Never infer organizational meaning in ingestion phase.

## Safety Controls
- Unique idempotency key constraints.
- Checkpoint transaction ordering guards.
- Queue lane isolation.
- Failure quarantine for malformed payloads.
- Operator audit trail for manual overrides.

## Safety Failure Response
- Transition affected run to safe failed state.
- Preserve partial successful writes.
- Expose precise failure and checkpoint context for resumable recovery.
