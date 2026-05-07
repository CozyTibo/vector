# Replay Foundation Model

## Why Raw Store Is Replay Foundation
Replay trust depends on immutable source evidence and deterministic access to historical windows. Raw store is the only layer with non-interpreted source truth.

## Replay Reconstruction Model
1. select replay scope (tenant, connector, time/object bounds),
2. resolve payload location (hot/cold),
3. scan raw events using chronology + identity indexes,
4. hydrate payload and version context,
5. emit deterministic replay input stream.

## Replay Determinism Assumptions
- immutable payload and source timestamps,
- stable scope filtering semantics,
- deterministic ordering precedence.

## Replay Version Pinning
Raw retrieval provides version context:
- ingestion schema/extraction/processor versions,
- replay version and replay job lineage.

## Replay Hydration Behavior
Archived rows are rehydrated through archival catalog pointers with integrity verification before replay stream emission.

## Operational Replay Constraints
- scoped replay is default; broad replay is budget-gated,
- replay scheduling must preserve tenant fairness and ingestion protection,
- replay observability must include queue depth, hydration lag, and scope-to-runtime variance.
