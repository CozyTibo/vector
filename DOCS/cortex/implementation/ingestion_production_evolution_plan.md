# Cortex ingestion — production evolution, re-backfill & migration

**Status:** normative operations + implementation plan  
**Audience:** engineers operating production tenants while deepening exhaust  
**Guardrail:** [minimal_ingestion_doctrine.md](./minimal_ingestion_doctrine.md) **wins on any conflict** — no coverage DB, no T0–T5 trust framework, no `coverage_ledger`, no ingestion-time actor resolution metrics.  
**Related:** [organizational_exhaust_implementation_plan.md](./organizational_exhaust_implementation_plan.md), [phase-01-organizational-exhaust-spec.md](../01-ingestion/phase-01-organizational-exhaust-spec.md), [phase-01-live-idempotency-doctrine.md](../01-ingestion/phase-01-live-idempotency-doctrine.md), [phase-01-ingestion-continuity-doctrine.md](../01-ingestion/phase-01-ingestion-continuity-doctrine.md)

**Problem:** Production already has tenants and historical `raw_ingestion_records`. We are deepening ingestion (people streams, memberships, richer payloads). We must evolve **without** corrupting trust in existing history.

**Constraint:** No rewrite, no workflow engine, no distributed migration framework. Strengthen: checkpoints, append-only raw, Step 15 idempotency, replay isolation, backfill lane.

---

## Executive answer

| Question | Answer |
|----------|--------|
| Complete missing data incrementally? | **Yes** for new streams and not-yet-seen objects. **Partially** for enriching existing payloads without a new provider revision. |
| Full re-ingestion? | **Usually no.** Selective **stream checkpoint reset** + `sync_mode=backfill`. |
| Architecture evolution-safe? | **Yes** for additive streams; **careful** for Class C (payload enrichment). |
| What to add in code? | Stream reset helper, `introduced_at` on ship, optional extraction-version bump, admin SQL + checkpoint read. |

---

## 1. What production data means today

Each live row is evidence of one fetch at `fetched_at`:

- `source_identity_key` = `{connector}:{resource_type}:{external_id}`
- `source_revision_key` = provider token **or** `hash:{canonical_payload_hash}`
- Unique index on live lane: `(tenant, connection, connector, resource_type, source_identity_key, source_revision_key)` where `replay_job_id IS NULL`

Checkpoints hold **what the code knew how to fetch** at each cursor position — not guaranteed universe completeness.

**Honesty:** Old tenants have partial exhaust for the period and depth that was active. Downstream must use `introduced_at`, `backfill_complete`, and SQL time bounds — not assume full history.

---

## 2. Evolution classes (simplified)

| Class | Example | Existing rows | Action |
|-------|---------|---------------|--------|
| **A — New stream** | `github.user`, `slack.channel_member` | None | Ship → set `introduced_at` → backfill once → Beat |
| **B — Deeper traversal** | More history pages, larger rings | New `external_id`s only | Let cursors run; no reset |
| **C — Payload enrichment** | Linear `assignee` on existing issues | Same identity + revision → **no new row** | Stream reset + backfill **or** extraction-version bump |
| **D — Identity key change** | Change `external_id` formula | Orphaned keys | **Avoid**; new `resource_type` suffix if unavoidable |
| **E — Revision rule change** | Change hash basis | Dupes or misses | Extraction bump + controlled re-backfill |
| **F — Policy change** | Enable Slack DMs | New scope | Update `meta.ingest_policy`; backfill new scope only |

### What incremental backfill can and cannot do

**Can:**

- Ingest new `resource_type`s for history the API still exposes.
- Continue unfinished pagination (cursors, rings, block queues).
- Append new revisions when provider reports `updatedAt` / `ts` / new SHA.

**Cannot (without explicit policy):**

- UPDATE existing `payload_body` rows (append-only).
- Guarantee point-in-time membership without API history.
- Recover Slack edits/deletes before capture started.

---

## 3. Safety mechanisms (existing)

| Mechanism | Safety |
|-----------|--------|
| Append-only `append_raw` | No silent overwrite |
| `ON CONFLICT DO NOTHING` (live) | Same identity+revision not duplicated |
| Replay scope `replay:{job_id}` | Does not advance live cursors |
| `IngestionSyncContext.backfill()` | Historical lane in checkpoint |
| Deep merge checkpoints | New stream keys do not wipe siblings |
| Separate `resource_type` in identity | New streams do not collide |

### Gaps to close (small code)

| Gap | Fix |
|-----|-----|
| No stream reset admin action | `reset_stream_checkpoint()` + `POST …/actions/reset-stream` |
| Hash fallback blocks enrichment | Bump `ingestion_version.extraction` in revision fallback path |
| `introduced_at` missing | Set when stream ships |
| Inconsistent `backfill_complete` | Align per stream in connector sync |

**Do not add:** `coverage_ledger.py`, coverage tables, tenant trust level enums, `actor_resolvable_pct` in ingestion verification.

---

## 4. Step 15 idempotency (production)

```
source_identity_key = connector:resource_type:external_id
source_revision_key   = provider:<token> | hash:<canonical_payload_hash>
```

| Scenario | Result | Mitigation |
|----------|--------|------------|
| Crash, re-run same page | No duplicate | Unique index |
| New external_id | New row | Expected |
| Provider updates `updatedAt` | New row | Expected |
| Richer query, **same** revision | **No new row** | Stream reset or extraction bump |
| Unstable hash serialization | Extra hash rows | Stabilize canonicalization; prefer provider tokens |

**Replay:** isolated; use for audit/equivalence — **not** primary production fill.

**Proposed hash fallback extension (when implemented):**

```text
source_revision_key =
  provider:<token>
  | extract:<extraction_version>:hash:<hash>
```

Bump `extraction` int in `payload_body.ingestion_version` when Class C requires re-materialization.

---

## 5. Operational decision tree

```text
Ship change?
├─ New resource_type (A)
│    → backfill once; introduced_at = deploy date
├─ Deeper pages only (B)
│    → do not reset cursors
├─ Richer payload, same type (C)
│    → if provider bumps revision on change: wait for incremental
│    → else: reset-stream + sync_mode=backfill OR extraction bump
├─ external_id formula change (D)
│    → avoid; design review; new resource_type if needed
└─ Validation only
     → trigger-replay; compare counts; do not treat replay as live truth
```

### When to reset a stream checkpoint

| Situation | Reset live cursor? |
|-----------|-------------------|
| Add `slack.channel_member` | **No** — new stream |
| Add `notion.user` | **No** |
| Linear assignee on **old** issues (same `updatedAt`) | **Yes** — `streams.linear.issues` (or extraction bump) |
| Notion block parent stuck | **Partial** — clear one parent in block map |
| GitHub repo never deep-fetched | **No** — ring reaches it; optional reset one repo sub-key |

**Never:** bulk DELETE `raw_ingestion_records`; reset entire connector checkpoint without scoping.

### Full connector re-backfill (rare)

Only when: `external_id` scheme changed; corrupt checkpoint unrecoverable; legal re-pull (documented).

Procedure: selective stream resets + `sync_mode=backfill` — not delete raw.

---

## 6. Trust & honesty (checkpoint-local)

### Per stream (persist)

| Field | Meaning |
|-------|---------|
| `introduced_at` | First deploy date for this stream |
| `backfill_complete` | Pagination done or policy cap recorded |
| `last_ok_at` | Last successful page (optional) |
| cursors / counters | Already exist |

### Connector `meta` (persist, optional)

```json
{
  "exhaust_depth": "shallow",
  "ingest_policy": { "slack_ingest_dms": false }
}
```

`exhaust_depth`: `shallow` | `deepening` | `mature` — simple rules or operator override. **Not** T0–T5.

### Admin read (SQL, not persisted)

- Counts and `MIN/MAX(fetched_at)` per `resource_type`
- Display copy: “Slack messages from **2024-03-01**; `slack.channel_member` from **2026-05-28** only.”

### Downstream responsibility

`cortex/identity` and graph layers own actor resolution and “can we trust this edge?” — ingestion only supplies rows + `introduced_at` honesty.

---

## 7. Minimal code changes

| Item | Size | Purpose |
|------|------|---------|
| `reset_stream_checkpoint()` + admin action | S | Class C / cursor repair |
| Extraction version in hash fallback | S | Controlled re-backfill |
| `introduced_at` on new streams | S | Trust labeling |
| People streams per connector | M each | Class A |
| Admin: checkpoint slice + SQL aggregates | S | Ops visibility |

**Explicitly out of scope:** `coverage_ledger.py`, `tenant_ingestion_trust` table, debt planner, `verify_*_actor_resolvable_pct` in ingestion.

---

## 8. Class C rollout example (Linear assignee)

1. Add GraphQL fields; bump `ingestion_version.extraction` for `linear.issue` if using hash fallback.
2. Pilot tenant: admin **reset-stream** for `linear.issue`.
3. `trigger-sync` with `sync_mode=backfill`.
4. Verify new rows include assignee; SQL count stable for unchanged revisions.
5. Roll cohorts; Beat incremental.

---

## 9. Production rollout phases

### E0 — Read path (1 week)

- Admin checkpoint + SQL stats.
- This doc + doctrine aligned.

### E1 — People streams (cohorts)

- Internal → pilots → all tenants.
- One backfill per connector after deploy; then Beat only.

### E2 — Structure / activity depth

- Env cap tuning; rings; Notion block queue — no new orchestration.

### E3 — Class C enrichments

- Selective reset or extraction bump per stream.

### E4 — Downstream gates (outside ingestion)

- Identity/graph features gate on their own readiness — not ingestion FSM.

---

## 10. Tests & invariants

| ID | Invariant |
|----|-----------|
| EV-1 | New `resource_type` does not collide with existing unique keys |
| EV-2 | Same identity+revision → `append_raw` returns false |
| EV-3 | Stream reset clears only targeted checkpoint paths |
| EV-4 | Backfill lane vs incremental lane separation preserved |
| EV-5 | Replay never updates live `default` checkpoint |
| EV-6 | Extraction bump changes hash-based `source_revision_key` |
| EV-7 | `introduced_at` set once per stream at ship |

**Suites (small):** `test_evolution_new_stream`, `test_stream_reset_checkpoint`, `test_backfill_then_incremental`, duplicate regression on re-insert.

**Drill:** pilot tenant snapshot counts before/after people backfill — monotonic growth, no drop in existing types.

---

## 11. Quick reference

| Question | Answer |
|----------|--------|
| Deepen existing tenants incrementally? | **Yes** for A/B; **careful** for C |
| Full re-ingestion? | **No** default — stream reset + backfill |
| Duplicates? | Strong for identity+revision; watch hash fallback |
| Operational trust? | `introduced_at`, `backfill_complete`, `meta.exhaust_depth`, SQL bounds — not run status alone |

---

## Document control

| Change | Update |
|--------|--------|
| New stream | Matrix, registry, Class A, set `introduced_at` |
| Enrichment | Class C + extraction version |
| Operator | Runbook: reset-stream, backfill, replay |
| Complexity | [minimal_ingestion_doctrine.md](./minimal_ingestion_doctrine.md) |
