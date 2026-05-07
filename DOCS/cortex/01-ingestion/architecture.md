# Connector & Ingestion Layer Architecture

## Scope
Phase 01 owns source interaction and raw ingestion envelope production. It does not own canonical meaning, ontology reasoning, or graph inference.

## Responsibilities
- Connector runtime initialization and capability registration.
- Source authentication verification and scope validation.
- Polling, pagination, cursor management, and delta fetch.
- Deterministic envelope normalization and validation.
- Idempotent handoff to raw store writer.
- Ingestion checkpointing and sync completion accounting.

## Non-Responsibilities
- No project/decision/topic inference.
- No ownership/causal summarization.
- No AI semantic interpretation.
- No canonical mapping beyond deterministic source metadata normalization.

## Input Contracts
- Tenant connector configuration.
- Connector auth secrets + scope metadata.
- Sync request (`sync_mode`, `scope`, `priority`, `replay_context?`).
- Source API responses and pagination tokens.

## Output Contracts
- `ingestion_envelope` (validated, versioned, deterministic).
- `raw_persist_request` with idempotency keys.
- `ingestion_checkpoint` updates.
- `ingestion_sync_run` terminal status and metrics.

## Operational Boundaries
- Every connector run is tenant-scoped.
- Connector runs are isolated by connector type and tenant.
- Replay runs use dedicated replay queues and do not share live worker concurrency pools.
- Envelope emission is deterministic for identical source payload + extraction version.

## Transaction Boundaries
- Source fetch and raw persistence are separate transactions.
- Checkpoint commits only after successful raw persistence ack.
- Sync run completion marks only after final checkpoint + queue drain confirmation.

## Ordering Guarantees
- Per connector stream: best-effort chronological processing by `occurred_at`, fallback `observed_at`.
- Across connectors: no global ordering guarantee.
- Replay ordering uses persisted source chronology, not storage `created_at`.
