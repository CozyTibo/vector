# Ingestion Validation Model

## Objective
Define how Cortex proves ingestion correctness across persistence, replay, checkpointing, ordering, idempotency, and isolation.

## Validation Layers
1. Contract validation:
   - envelope schema conformance,
   - required field completeness,
   - version field presence.
2. Persistence validation:
   - immutable raw writes,
   - idempotency uniqueness enforcement,
   - transaction sequencing correctness.
3. Checkpoint validation:
   - monotonic checkpoint progression,
   - resumable recovery from latest stable checkpoint.
4. Replay validation:
   - deterministic reconstruction for fixed scope+version,
   - replay/live isolation.
5. Ordering validation:
   - connector-stream chronology consistency,
   - replay ordering stability.
6. Concurrency validation:
   - overlap prevention,
   - lock/lease safety,
   - no duplicate durable writes under retries.
7. Provenance validation:
   - bootstrap lineage completeness for every raw event.
8. Operational survivability validation:
   - failure probes and chaos scenarios preserve invariants.

## Correct Ingestion Definition
Ingestion is correct when:
- every accepted source payload is durably represented as immutable raw evidence,
- no duplicate durable event exists for the same deterministic idempotency identity,
- progress can resume from persisted checkpoint without data loss,
- replay can re-run with explainable divergence only under explicit version changes,
- no connector/tenant/replay fault violates isolation boundaries.

## Evidence Of Correctness
- invariant check pass reports,
- replay equivalence and divergence reports,
- failure probe pass matrix,
- concurrency probe results,
- readiness gate sign-off.
