# Phase 01 Step 16 — Runtime Correctness Hardening Doctrine

Status: authoritative, mandatory, and implemented in Phase 01 Step 16 runtime.

## Purpose

Step 16 closes the audit-identified correctness risks that are runtime-critical today:

- concurrency correctness
- retry safety
- crash recovery correctness
- checkpoint and cursor correctness
- replay/live isolation validation
- overlapping-window correctness
- live dedupe correctness
- multi-connection uniqueness semantics

This step is about trustworthiness of current ingestion behavior, not future scaling.

## A) Finalized uniqueness scope doctrine

1. Live-lane logical uniqueness is connection-scoped:
   - `(tenant_id, connection_id, connector, resource_type, source_identity_key, source_revision_key)`
   - applied only where `replay_job_id IS NULL`
2. Replay-lane uniqueness remains replay-job scoped:
   - `(replay_job_id, idempotency_key)` where `replay_job_id IS NOT NULL`
3. Live and replay lanes are intentionally independent; overlap is allowed and must remain auditable.

## B) Finalized connection-scoping doctrine

1. Scheduler-enqueued sync tasks must include explicit `connection_id`.
2. Manual/replay admin triggers must accept explicit `connection_id`.
3. If a tenant has multiple active connections for one connector and no `connection_id` is provided, operations must reject with explicit ambiguity error.
4. Connection scope is part of correctness boundary for checkpoints and live dedupe.

## C) Required validation suite

Runtime invariants must be checked with a dedicated suite:

1. live connection-scoped uniqueness (no duplicate identity+revision within one connection)
2. replay job-scoped uniqueness
3. checkpoint scope namespace correctness (`default` and `replay:<job_id>`)
4. live logical idempotency key correctness derived from persisted payload identity+revision

## D) Test obligations

Step 16 requires tests for:

1. concurrency/retry/crash-adjacent correctness behaviors
2. checkpoint correctness and scope isolation
3. replay/live overlap behavior
4. dedupe correctness under retries
5. multi-connection scope semantics

## E) Runtime implementation notes

Implemented in Step 16:

- scheduler emits connection-scoped jobs
- sync/replay tasks accept and pass `connection_id`
- executor resolves explicit connection scope
- live uniqueness index is connection-scoped
- tenant verification includes runtime correctness invariants
- admin trigger sync/replay supports explicit `connection_id` and rejects ambiguous multi-active connector scope

