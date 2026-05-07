# Ingestion Locking & Concurrency

## Concurrency Model
- per tenant+connector concurrency caps.
- separate concurrency pools for live, backfill, and replay lanes.
- single active checkpoint writer per `(tenant_id, connector_instance_id, sync_mode, scope_key, replay_job_id?)`.

## Lock Ownership
- queue lease lock: owned by worker for visibility timeout window.
- checkpoint update lock: owned by active run task for scope.
- connector runtime state update lock: short-lived lock for state transitions.

## Overlap Prevention
- live sync overlap prevention:
  - reject concurrent active runs for same connector scope unless explicitly sharded by scope key.
- replay overlap prevention:
  - reject conflicting replay scopes unless marked compatible and isolated.

## Optimistic vs Pessimistic
- optimistic concurrency for run metrics/state increments (version/cas style).
- pessimistic or serialized updates for checkpoint progression to avoid regression races.

## Deadlock Avoidance
- fixed lock acquisition order:
  1. queue lease
  2. raw write
  3. checkpoint update
  4. run state update
- avoid long-lived locks across network fetches.

## Safety Guarantees
- no duplicate durable raw writes under parallel retries.
- no checkpoint regression under concurrent workers.
- no replay-live pointer collision without explicit override workflow.
