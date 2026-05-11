# Phase 01 — Live-Lane Logical Idempotency Doctrine

**Status:** authoritative, mandatory, and implemented in Phase 01 Step 15 runtime.  
**Scope:** live-lane logical identity, revision-safe append semantics, replay/live isolation, canonical hashing, deterministic conflict-ignore insertion, and latest-state projection boundaries.

**Normative links:** `phase-01-organizational-exhaust-spec.md`, `phase-01-ingestion-continuity-doctrine.md`, `phase-01-raw-persistence-doctrine.md`, `phase-01-runtime-correctness-hardening-doctrine.md`, `../MASTER_TRACKER.md` Phase 01 Steps 15–16.

---

## 1) Non-negotiable requirement

Deep organizational exhaust is operationally unsafe without stable live-lane logical idempotency.

Phase 01 is **not complete** until live-lane idempotency semantics in this document are implemented and verified.

---

## A) Logical identity model

### A.1 Required fields

- `source_identity_key`: connector-stream stable identity for the provider object.
- `resource_type`: stream discriminator used in identity namespace.
- `connector`: provider namespace.

### A.2 Identity construction

- Identity must be based on provider-stable object identifiers, not run lifecycle metadata.
- `run_id` is forbidden as part of live-lane logical identity.
- Identity must be deterministic and reproducible across retries, overlapping windows, and re-fetches.

### A.3 Stream requirements

- Slack messages/replies: channel + message identifiers.
- GitHub PR/review/comment/check/deployment artifacts: provider IDs or stable repo+number composites.
- Linear issue/comment/project/cycle/relation/label/initiative: provider IDs.
- Notion and Calls streams: provider object IDs where available, documented composite key otherwise.

---

## B) Revision model

### B.1 Required fields

- `source_revision_key`: stable revision token for the identity (provider version marker).
- Distinct revisions for one `source_identity_key` must produce distinct live idempotency keys.

### B.2 Revision semantics

- Provider edits/state transitions become new append rows (new revision), never raw row overwrite.
- Identical refetch of same identity and same revision must not create duplicates.
- Payload drift with unchanged provider revision token remains observable via payload hash and diagnostics.

### B.3 Fallback when provider revision token is weak/missing

- Use canonical payload hash as revision fallback.
- Mark fallback usage in stream documentation and monitoring for false-positive/false-negative risk.

---

## C) Canonical hashing doctrine

### C.1 Canonical hash input

- Hash only normalized payload content.
- Deterministic serialization with stable key ordering.
- Stable array ordering when provider order is semantically fixed; preserve provider order otherwise.

### C.2 Must exclude from hash

- Transport metadata (HTTP status, headers, retry metadata).
- Ingestion metadata (`run_id`, `fetched_at`, queue labels, worker identifiers, replay scheduling metadata).
- Non-semantic envelope fields that are ingestion-transport concerns.

### C.3 Normalization rules

- Normalize timestamp formatting to a canonical representation before hashing.
- Normalize null-equivalent values consistently.
- Normalize map/object ordering recursively.
- Preserve semantically meaningful scalar values exactly.

### C.4 Envelope boundary

- Envelope identity/provenance fields remain stored, but canonical payload hashing operates on normalized source payload segment, not transport wrapper.

---

## D) Insertion semantics

- Raw storage remains append-only evidence.
- Live-lane writes must use deterministic conflict-ignore insertion semantics (`ON CONFLICT DO NOTHING` behavior against live unique keyspace once migrated).
- No raw row mutation or deletion for dedupe behavior.
- Deterministic conflict-ignore means duplicated fetch of same identity+revision resolves to no-op write.

### D.1 Latest-state projection

- Latest-state projection is an operational convenience layer derived from append-only raw rows.
- Projection is not source of truth and must never replace raw evidence.

---

## E) Replay/live isolation

- Replay and live lanes must remain isolated by unique key namespace.
- Replay uniqueness remains scoped to `(replay_job_id, idempotency_key)` partial index.
- Live uniqueness must be scoped independently of replay namespace.
- Operational queries must explicitly filter lane context (`replay_job_id IS NULL` for live corpus views unless replay comparison is intended).

---

## F) Failure-mode handling

Must remain correct under:

- overlapping incremental windows,
- cursor rewind and replay/retry overlap,
- concurrent workers on same stream scope,
- incremental/backfill overlap,
- provider mutation drift and eventual consistency delays.

Required behavior:

- no duplicate live rows for same identity+revision,
- revisions append safely when content/version changes,
- conflicts resolve deterministically (no race-dependent semantic divergence).

---

## G) Migration plan (from run-scoped live keys)

### G.1 Phased rollout

1. **Dual-write phase:** compute and persist new live logical identity/revision keys alongside existing behavior.
2. **Index rollout phase:** add live-lane unique constraints/indexes for deterministic conflict-ignore inserts.
3. **Cutover phase:** switch live writes to logical identity+revision keys (remove `run_id` coupling).
4. **Compatibility phase:** preserve legacy raw rows; no destructive rewrite required for old evidence.

### G.2 Safety requirements

- Backfill compatibility with existing rows and checkpoint continuity.
- Replay semantics unchanged and audit-safe.
- Rollback path documented if conflict rates or key quality regress.

---

## H) Operational/admin requirements

Required observability:

- duplicate-prevention metrics (attempted inserts vs conflict-noop rate),
- idempotency key quality/error metrics,
- revision churn metrics by stream,
- replay/live isolation visibility in admin and verification reports.

Required verification:

- no run-scoped live logical identity in configured Step 15 streams,
- duplicate-prevention assertions in Phase 01 verification,
- deterministic latest-state projection checks from raw evidence.

---

## Closure lock

Phase 01 closure requires Step 15 plus Step 16 runtime-correctness hardening:

1. stable live logical idempotency,
2. replay-safe revision semantics,
3. canonical hashing doctrine implemented,
4. no `run_id`-scoped live logical identity for Step 15-covered streams,
5. duplicate-prevention verification passing,
6. deterministic latest-state projection from append-only raw evidence.
