# Connector Runtime Model

## Connector Runtime Entity
A connector runtime is a tenant-scoped adapter instance with:
- capability profile,
- auth/session state,
- sync state,
- cursor/checkpoint state,
- throttle/rate-limit state,
- failure/recovery state.

## Runtime Lifecycle States
- `UNREGISTERED`: connector not configured.
- `REGISTERED`: config exists, no active auth session.
- `READY`: auth valid, eligible for scheduling.
- `RUNNING`: sync currently executing.
- `THROTTLED`: temporary rate-limit constrained.
- `DEGRADED`: non-fatal repeated failures.
- `DISABLED`: operator-disabled, no scheduling.
- `MAINTENANCE`: temporarily paused for planned operations.
- `REPLAY_MODE`: runtime reserved for replay queue lane.
- `AUTH_FAILED`: credentials/scopes invalid.

## Runtime Substates
- Polling substate: `WINDOW_SELECTING` -> `FETCHING` -> `PAGINATING`.
- Cursor substate: `READING_CURSOR` -> `ADVANCING_CURSOR` -> `CHECKPOINTED`.
- Failure substate: `RETRY_WAIT` -> `RETRYING` -> `QUARANTINED`.

## Capability Registration
Each connector registers:
- supported object types,
- pagination mode(s),
- rate-limit policy model,
- cursor semantics (`timestamp`, `opaque_cursor`, `offset`, hybrid),
- replay support flags (full/partial/object-targeted).

## Adapter-Only Enforcement
Connectors may:
- fetch source data,
- normalize source metadata into envelope fields.
Connectors must not:
- infer organizational semantics,
- emit canonical entities or decisions,
- run AI interpretation.
