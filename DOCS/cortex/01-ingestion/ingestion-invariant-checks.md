# Ingestion Invariant Checks

## Invariant: Raw Events Are Immutable
- Meaning: raw payload rows are append-only.
- Validation expectation: no in-place update path for payload or source identity.
- Detection mechanism: mutation audit alerts and row-version anomaly checks.
- Failure symptoms: payload hash drift for same `raw_event_id`.
- Downstream consequences: replay and provenance corruption.
- Replay implications: deterministic baseline invalid.
- Observability implications: critical severity alert.

## Invariant: Replay Cannot Mutate Original Raw Payloads
- Meaning: replay writes superseding records, never raw row edits.
- Validation expectation: replay writes must have replay metadata and new row ids.
- Detection mechanism: replay write audit + forbidden update query alarms.
- Failure symptoms: existing raw rows changed during replay window.
- Downstream consequences: non-auditable reconstruction.
- Replay implications: trust collapse.
- Observability implications: replay job auto-fail and escalation.

## Invariant: Checkpoint Progression Is Monotonic
- Meaning: `checkpoint_seq` and cursor progression cannot regress.
- Validation expectation: every checkpoint write has seq > previous stable seq.
- Detection mechanism: monotonicity constraint checks and regression counters.
- Failure symptoms: repeated windows, skipped windows, cursor rollback.
- Downstream consequences: duplicates or data loss risk.
- Replay implications: replay resumability uncertain.
- Observability implications: degraded state + operator intervention.

## Invariant: Duplicate Durable Persistence Is Prevented
- Meaning: same idempotency identity cannot create multiple committed raw rows.
- Validation expectation: unique key + deterministic idempotency derivation.
- Detection mechanism: duplicate-key anomaly reports and replay duplicate scans.
- Failure symptoms: row count >1 for same idempotency key.
- Downstream consequences: canonical duplication and graph inflation.
- Replay implications: false divergence and duplicate replay artifacts.
- Observability implications: high-priority data integrity alert.

## Invariant: Provenance Bootstrap Remains Reconstructable
- Meaning: each raw row has required provenance bootstrap metadata.
- Validation expectation: no missing chain/source refs in accepted rows.
- Detection mechanism: null/missing provenance integrity scans.
- Failure symptoms: orphaned raw rows without lineage linkage.
- Downstream consequences: explainability failure.
- Replay implications: incomplete equivalence analysis.
- Observability implications: integrity dashboard breach.

## Invariant: Connector/Tenant Isolation Is Preserved
- Meaning: one connector/tenant fault cannot corrupt unrelated scopes.
- Validation expectation: queue lanes and runtime state remain scoped.
- Detection mechanism: cross-scope anomaly probes and lane starvation checks.
- Failure symptoms: shared failure cascades, cross-tenant backlog spikes.
- Downstream consequences: ingestion starvation and reliability collapse.
- Replay implications: replay-live interference.
- Observability implications: isolation breach alarms.
