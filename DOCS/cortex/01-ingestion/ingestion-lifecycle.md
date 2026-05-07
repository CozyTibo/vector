# Ingestion Lifecycle

## Lifecycle Stages
1. Connector initialization:
   - Resolve tenant + connector config.
   - Load connector capability profile and extraction version.
2. Auth validation:
   - Verify credential existence, validity, and required scopes.
   - Fail-fast to `AUTH_FAILED` state on hard auth errors.
3. Sync registration:
   - Create `ingestion_sync_run` record with mode, scope, and priority.
   - Bind run to `replay_context` when replay mode is active.
4. Scheduling:
   - Enqueue connector sync task in lane (`live`, `backfill`, `replay`, or `recovery`).
5. Poll/fetch:
   - Read cursor/checkpoint.
   - Fetch source page with bounded window and pagination token.
6. Normalize:
   - Deterministically normalize payload into ingestion envelope schema.
7. Deduplicate/idempotency check:
   - Compute fingerprint and idempotency key.
   - Skip duplicate envelope persistence writes.
8. Raw persistence:
   - Persist immutable raw event envelope.
   - Persist ingestion metadata + provenance bootstrap metadata.
9. Acknowledge and checkpoint:
   - Commit checkpoint only after raw write ack.
   - Emit run metrics and per-page counters.
10. Downstream enqueue:
   - Emit raw event available signal for canonical stage.
11. Replay registration:
   - If replay mode, associate persisted events with `replay_job_id` and `replay_version`.
12. Completion:
   - Mark sync run `COMPLETED`, `PARTIAL_FAILURE`, or `FAILED`.

## Retry Points
- Source fetch retryable on transient/network/rate-limit failures.
- Raw persistence retryable when write timeout or transient DB errors.
- Checkpoint update retryable; must be idempotent.
- Non-retryable malformed payload moves to quarantine with operator visibility.

## Isolation Guarantees
- Connector failure in tenant A does not block connector of same type in tenant B.
- Connector X failure does not block connector Y in same tenant.
- Replay jobs are isolated from live polling worker pools.

## Replay Implications
- Live runs use live cursor progression.
- Replay runs pin version context and replay scope; no live cursor mutation unless explicitly in replacement mode.
- Replay publishes superseding metadata, never mutates raw payload rows.
