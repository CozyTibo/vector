# Convergence validation plan

**Status:** Phase B artifact (2026-05-20)  
**Purpose:** Prove the deterministic convergence runtime is stable under production-like load — not theoretical doctrine compliance.

**Prerequisites:** Convergence authoritative in target env (`CORTEX_CONVERGENCE_RUNTIME_ENABLED=true`, legacy progression beat disabled). Celery **worker + beat** running on `vector` queue.

---

## Validation principles

1. Measure **forward progress density**, not “no errors.”
2. Accept a **stable floor** of untreated rows when ingest is structurally incomplete (permanent orphans).
3. Compare **runtime vs ingest** gaps using deferral + coverage data.
4. Run tests on a **real tenant** (e.g. ~20k raw, mixed GitHub/Notion/Slack) over **hours**, not single admin clicks.

---

## Metrics dictionary

| Metric | Source | Healthy signal |
|--------|--------|----------------|
| `untreated_routable_estimate` | Phase 02 summary / forward-progress snapshot | Monotonic decrease, then plateau |
| `total_succeeded` per slice | `canonical_summary` in phase 02 output | > 0 on most slices when backlog exists |
| `progress_density_rows_per_batch` | `total_succeeded / batches_run` | > 0.1 when productive passes exist |
| `productive_batches` | Phase 02 summary | Majority of batches when not all passes cooled |
| `topology_only_batches` | Phase 02 summary | Isolated to hard passes; not 100% of slices |
| `blocked_pass_batch_ratio` | `topology_only_batches / batches_run` | < 0.7 when fairness working |
| `canonical_outcome` | `partial_progress` / `progressed` preferred | Rare global `topology_wait` with successes |
| `convergence_health` | Lease `detail_json` / phase 02 | `converging` or `progressing_normally` |
| `deferred_permanent_orphan` | `count_deferrals` | Rises then **stabilizes** |
| `deferred_waiting_cooldown` | deferral counts | Bounded, not ~all untreated |
| Rows/minute | Δ materialization count / Δ time | Stable positive until floor |

---

## B1 — Easy backlog drain

### Scenario

- ~20k raw rows, mixed connectors
- Partial topology incompleteness (timeline orphans, Notion rows pending)
- Continuous convergence (sweeper + post-ingest dirty), **no** repeated admin “Reprocess untreated”

### Procedure

1. Record baseline from admin coverage or SQL (below).
2. Let convergence run **≥ 2 hours** during normal ingest cadence.
3. Sample every **15 minutes**: untreated count, materialization count, lease status, phase 02 `total_succeeded`.

### SQL (tenant-scoped)

```sql
-- Untreated routable (approximate; matches forward-progress estimate)
SELECT COUNT(*) AS untreated
FROM raw_ingestion_records r
WHERE r.tenant_id = :tenant_id
  AND NOT EXISTS (
    SELECT 1 FROM cortex_canonical_transform_materializations m
    WHERE m.tenant_id = r.tenant_id
      AND m.raw_record_id = r.id
      AND m.bundle_id = :bundle_id
  );

-- Materialization velocity (last hour)
SELECT date_trunc('minute', m.created_at) AS minute,
       COUNT(*) AS rows_mat
FROM cortex_canonical_transform_materializations m
WHERE m.tenant_id = :tenant_id
  AND m.created_at > now() - interval '1 hour'
GROUP BY 1 ORDER BY 1;

-- Gap by resource type
SELECT r.resource_type,
       COUNT(*) AS raw_n,
       COUNT(m.id) AS mat_n,
       COUNT(*) - COUNT(m.id) AS gap
FROM raw_ingestion_records r
LEFT JOIN cortex_canonical_transform_materializations m
  ON m.raw_record_id = r.id AND m.tenant_id = r.tenant_id AND m.bundle_id = :bundle_id
WHERE r.tenant_id = :tenant_id
GROUP BY 1 ORDER BY gap DESC;
```

### Pass criteria

| Check | Target |
|-------|--------|
| Untreated delta over 2h | Negative (decreasing) until plateau |
| `notion.database_row` gap | Decreases without manual scoped drain |
| `github.deployment_status` / `pull_request_review` | Decreases while timeline may lag |
| `canonical_outcome` | Mostly `partial_progress` / `progressed` |
| Admin reprocess clicks required | **0** during validation window |

### Fail signals

- Untreated flat for 2h with active sweeper and `status=dirty`
- `total_succeeded=0` on every slice while easy passes have thousands untreated
- Materialization count frozen while ingest adds raw rows (B4 failure)

---

## B2 — Blocked pass isolation

### Hypothesis

`github.pull_request_timeline_event` topology pressure must **not** prevent materialization of:

- `notion.database_row`
- `github.deployment_status`
- `github.pull_request_review`
- `slack.*` (already complete on healthy tenants)

### Procedure

1. From phase 02 output or logs, capture per-slice:
   - `pass_productivity` (succeeded by pass_key)
   - `pass_topology_skips`
   - `pass_cooldown_until` keys
2. Confirm in same slice (or adjacent slices within 5 min):
   - Timeline pass cooled or skipped
   - Notion/GitHub easy passes show `total_succeeded > 0`

### Evidence to collect

```sql
-- Per-pass materialization in last slice window (if logging pass_key on materialization — else use resource_type)
SELECT m.connector, r.resource_type, COUNT(*) AS mat_last_hour
FROM cortex_canonical_transform_materializations m
JOIN raw_ingestion_records r ON r.id = m.raw_record_id
WHERE m.tenant_id = :tenant_id
  AND m.created_at > now() - interval '30 minutes'
GROUP BY 1, 2 ORDER BY 3 DESC;
```

### Pass criteria

| Check | Target |
|-------|--------|
| Same-hour mat rows for `notion.database_row` | > 0 while timeline gap remains |
| `pass_cooldown_until` contains timeline pass | Yes, when timeline blocks |
| Other passes not on cooldown | Continue rotating |
| `blocked_pass_batch_ratio` | < 0.85 averaged over 10 slices |

### Fail signals

- Only timeline pass attempted for multiple consecutive slices
- Notion gap unchanged for 2h with zero mat rows for `notion.database_row`

---

## B3 — Permanent orphan stability

### Scenario

Timeline (and similar) rows with **missing ingest parents** should stop consuming slice budget.

### Procedure

1. Run convergence until deferral table populated.
2. Track `deferred_permanent_orphan` and quarantine queue counts over **≥ 6 hours**.
3. Confirm permanent orphans excluded from candidate selection (untreated count includes them, but batches don't select them).

### SQL

```sql
SELECT
  resource_type,
  deferral_reason,
  queue,
  COUNT(*) FILTER (WHERE detail_json->>'permanent_orphan' = 'true') AS permanent_n,
  COUNT(*) AS total
FROM cortex_canonical_materialization_deferrals
WHERE tenant_id = :tenant_id AND bundle_id = :bundle_id
GROUP BY 1, 2, 3 ORDER BY total DESC;

-- Missing parent breakdown (topology gap reporting)
SELECT
  split_part(missing_parent_ref, ':', 1) AS parent_kind,
  COUNT(*) AS n
FROM cortex_canonical_materialization_deferrals
WHERE tenant_id = :tenant_id
  AND bundle_id = :bundle_id
  AND missing_parent_ref IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC;
```

### Pass criteria

| Check | Target |
|-------|--------|
| `permanent_n` derivative | → 0 (stabilizes) |
| `topology_only_batches` with only permanent rows left | → 0 |
| `untreated` plateau | Above permanent orphan count only |
| Retry churn on same raw_record_id | Stops after threshold (~5) |

### Fail signals

- `retry_count` in deferral detail growing without bound on same ids
- Slices still selecting thousands of timeline rows with zero successes every batch

---

## B4 — Continuous ingest under convergence

### Scenario

Incremental ingest every ~30 min (scheduler) while convergence runs.

### Procedure

1. Enable ingestion scheduler tick.
2. Monitor for 4–8 hours:
   - `obligation_epoch` vs `target_epoch` on lease
   - Queue depth `vector` (Celery)
   - Untreated count vs raw count (gap should not grow unbounded)

### Pass criteria

| Check | Target |
|-------|--------|
| `obligation_epoch - target_epoch` | Stays 0–2 (brief dirty bursts ok) |
| Untreated / raw ratio | Stable or decreasing (not exponential) |
| Convergence tasks/min | Bounded (sweep limit 50 + dirty hints) |
| Lease `running` TTL recovery | Expired leases become dirty, not stuck forever |
| No coordinator revoke storms | No `substrate_pipeline_scheduled` logs in convergence mode |

### Fail signals

- Untreated grows ~1:1 with new raw for **easy** types
- Hundreds of duplicate `run_tenant` tasks per minute with no lease acquisition
- Perpetual `status=running` without heartbeat refresh

### Lease inspection

```sql
SELECT status, obligation_epoch, target_epoch, phase_cursor,
       next_attempt_at, lease_expires_at, last_heartbeat_at,
       detail_json->>'convergence_health' AS health,
       detail_json->>'last_canonical_outcome' AS last_outcome
FROM cortex_tenant_convergence_leases
WHERE tenant_id = :tenant_id;
```

---

## Phase C — Throughput optimization (after B1–B4 pass)

**Do not start until validation passes.** Targets only:

### C1 — Batch productivity

- Reduce topology-only **selects**: skip passes on cooldown before `list_forward_progress_candidate_ids` query (already partially done).
- Batch commit tuning in `materialize_raw_record` (profile commits per stage).
- Cap per-pass candidate fetch when `topology_only` streak > 1.

### C2 — Deferral indexing

Current indexes (`20260519_0087`):

- `(tenant_id, bundle_id, retry_ready_at)`
- `(tenant_id, bundle_id, pass_key)`

**Validate under load:**

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT r.id FROM raw_ingestion_records r
WHERE r.tenant_id = :tenant_id
  AND NOT EXISTS (SELECT 1 FROM cortex_canonical_transform_materializations m ...);
```

Add if needed:

- Partial index on permanent orphan JSONB
- `(tenant_id, bundle_id, resource_type)` on deferrals for pressure summaries

### C3 — Lease contention

- Keep `FOR UPDATE` acquisition — required for correctness.
- Reduce `enqueue_tenant_convergence` amplification: optional coalesce hint (same tenant, one pending task) — **design only**, not implemented.
- Heartbeat only between phases, not every row.

---

## Phase D — Structural topology (bounded)

### D1 — Topology gap reporting (recommended next)

Expose from deferrals + coverage:

| Bucket | Meaning |
|--------|---------|
| `github.pull_request_review:*` missing | Review not ingested |
| `github.commit:*` missing | Commit SHA not in raw store |
| `github.workflow_run:*` missing | Workflow run not ingested |
| `notion.database:*` missing | Database parent missing |

**Operator question answered:** “Is gap **runtime** or **ingest completeness**?”

Implement as: `summarize_topology_parent_gaps()` on deferral table → admin forward-progress snapshot (no new runtime).

### D2 — Ingest parity strategy (documentation)

Do **not** auto-couple caps yet. Track:

- `timeline_rows / review_rows` ratio per tenant sync
- Settings: `CORTEX_GITHUB_TIMELINE_MAX_PAGES_*` vs `CORTEX_GITHUB_REVIEWS_MAX_PAGES_*`

Alert when timeline raw growth exceeds review/commit growth for same PR population.

### D3 — Stub strategy (design only)

**Proposal:** `topology_anchor_stub` raw rows — minimal envelope:

- `connector`, `resource_type=*.topology_anchor`, `external_id=<parent ref>`, `payload_body={ref, stub_reason}`
- Never materialized to canonical objects
- Satisfy `node_key_to_id` for batch planning only
- Expire after 30d or on parent ingest
- Operator-visible in “synthetic anchors” count

**Not implemented.** Requires ingest + transform policy review.

---

## Validation runbook (single tenant)

### Day 0 — Baseline (30 min)

1. Coverage page: record untreated by type.
2. Forward-progress GET (if exposed): `metrics`, `operator_guidance`.
3. SQL baseline queries above.
4. Confirm env flags (audit doc §1).

### Day 1 — Soak (4–8 h)

- No manual backlog drain.
- Sample metrics every 15 min (spreadsheet).
- One incremental ingest cycle minimum.

### Day 2 — Sign-off

| Gate | Owner |
|------|-------|
| B1 easy drain | Untreated ↓, notion/github easy types ↓ |
| B2 isolation | Productive passes in same window as timeline cooldown |
| B3 orphan floor | permanent_orphan stable |
| B4 ingest + convergence | No starvation / amplification |

---

## Stable convergence floor (expected end state)

For a tenant with ~20k raw and known ingest caps:

| Category | Expected floor |
|----------|----------------|
| Slack | ~0 untreated |
| Notion pages/blocks | ~0 |
| Notion database_row | ~0 after fairness soak |
| GitHub deployment_status / reviews | Low (backlog drain) |
| Timeline events | **Structural floor** = permanent orphans + deferred parents |
| Unsupported (scope_ping) | 1 (ignored) |

**Success = floor stable + easy types still draining + operators understand structural remainder.**

---

## Logging hooks (minimal instrumentation)

Add structured log line on phase 02 complete (recommended):

```text
convergence_canonical_slice tenant_id=... outcome=... succeeded=... untreated=...
  progress_density=... blocked_pass_ratio=... health=... permanent_orphan=...
```

Enables Datadog/log SQL validation without new tables.

---

## Related documents

- [RUNTIME_SIMPLIFICATION_AUDIT.md](./RUNTIME_SIMPLIFICATION_AUDIT.md) — active vs legacy paths
- [phase-085-runtime-architecture.md](./phase-085-runtime-architecture.md) — doctrine (non-authoritative for hot path)
