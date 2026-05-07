# Github Connector Strategy

## Connector Role
Adapter-only ingestion component that fetches source records and emits deterministic ingestion envelopes.

## Exact Object Types
- repositories
- issues
- pull requests
- commits
- reviews/comments
- workflow/check runs
- deployments
- labels/milestones/projects links

## Auth Strategy
- Tenant-scoped credential binding with scope verification at run start.
- Token expiry/rotation tracked in connector runtime state.
- Auth failures transition connector instance to `AUTH_FAILED` without cross-connector impact.

## Pagination Model
- REST cursor/page based links or GraphQL cursor pagination depending endpoint.
- Pagination checkpoints commit only after persistence acknowledgements.

## Cursor Model
- per resource stream high-watermark on updated_at plus endpoint pagination cursor.
- Cursor state is namespaced by tenant + connector + sync mode.

## Polling Model
- Scheduled incremental polling with overlap windows.
- Adaptive cadence based on delta volume, lag, and throttle pressure.
- Backfill and replay use isolated lanes and separate quotas.

## Delta Detection
- incremental by updated_at windows with overlap for late updates and force-push related revisions.
- Delta windows intentionally overlap to avoid late-update loss; dedupe enforced by idempotency keys.

## Source Identity Semantics
- source identity uses installation/org + repo_id + object_id + node_id/revision marker.
- Source identity + source revision drives deterministic idempotency key generation.

## Rate Limit Strategy
- token-scoped quotas (REST + GraphQL budget); adaptive throttling and budget-aware scheduling.
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
