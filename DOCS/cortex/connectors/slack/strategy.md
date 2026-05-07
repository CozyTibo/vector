# Slack Connector Strategy

## Connector Role
Adapter-only ingestion component that fetches source records and emits deterministic ingestion envelopes.

## Exact Object Types
- workspace metadata
- channels (public/private where authorized)
- messages
- thread replies
- message edits/deletes
- reactions
- files and shares
- users and membership snapshots

## Auth Strategy
- Tenant-scoped credential binding with scope verification at run start.
- Token expiry/rotation tracked in connector runtime state.
- Auth failures transition connector instance to `AUTH_FAILED` without cross-connector impact.

## Pagination Model
- cursor-based pagination with `next_cursor`; threads require parent message traversal plus per-thread pagination.
- Pagination checkpoints commit only after persistence acknowledgements.

## Cursor Model
- high-watermark by message timestamp + cursor token per channel/thread stream.
- Cursor state is namespaced by tenant + connector + sync mode.

## Polling Model
- Scheduled incremental polling with overlap windows.
- Adaptive cadence based on delta volume, lag, and throttle pressure.
- Backfill and replay use isolated lanes and separate quotas.

## Delta Detection
- updated/deleted message events, edits, reactions, and membership changes via overlap polling windows.
- Delta windows intentionally overlap to avoid late-update loss; dedupe enforced by idempotency keys.

## Source Identity Semantics
- source identity uses workspace_id + channel_id + message_ts (+ thread_ts for replies).
- Source identity + source revision drives deterministic idempotency key generation.

## Rate Limit Strategy
- method-tier limits; honor retry-after headers; channel and thread substream concurrency caps.
- Retry-after honored when present.
- Exponential backoff with jitter for transient throttles.
- Replay throttling separate from live throttling to avoid live starvation.

## Historical Backfill Strategy
- Oldest-first window chunking for deterministic historical coverage.
- Progressive checkpointing for resumable multi-year ingestion.
- Throughput caps prevent provider and internal queue saturation.

## Replay Implications
- Replay reuses identical connector envelope schema.
- Replay cursor namespace is isolated from live cursor namespace.
- Replay outputs tagged with `replay_job_id` and `replay_version`.

## Payload/Versioning Assumptions
- Raw source payload retained in immutable JSONB envelope payload.
- Source revision markers stored when available.
- Extraction parser changes require `extraction_version` bump and replay plan.

## Canonical Mapping Boundary
- Connector emits source metadata hints only.
- No canonical entity inference, topic inference, ownership inference, or causal interpretation.
