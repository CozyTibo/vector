# Minimal ingestion doctrine

**Status:** normative guardrail — overrides aspirational complexity in other plans when they conflict  
**Audience:** anyone adding code under `vector/domains/cortex/ingestion/`  
**Related:** [organizational_exhaust_implementation_plan.md](./organizational_exhaust_implementation_plan.md), [ingestion_production_evolution_plan.md](./ingestion_production_evolution_plan.md)

---

## 1. What ingestion is (one paragraph)

Cortex ingestion **acquires provider truth**: paginate APIs, append rows to `raw_ingestion_records`, store cursors in `connector_sync_state`. It does **not** interpret organizations, resolve identity across tools, build graphs, or derive execution state.

---

## 2. The only runtime loop

```text
load_checkpoint()
fetch_page()
append_raw()
update_checkpoint()
repeat_until_budget()
```

Everything else is **optional metadata** in the same checkpoint JSON or **admin SQL aggregates** computed on read — not a second runtime.

---

## 3. Three planes = call order only

Inside one `run_*_connector_sync()`:

```python
def run_slack_connector_sync(...):
    sync_users(...)           # people — provider user APIs
    sync_channels(...)        # structure — list/metadata
    sync_channel_history(...) # activity — messages, etc.
    patch_checkpoint(...)     # merge cursors + light meta
```

**Forbidden:** separate queues, plane orchestrators, plane-level Celery tasks, plane FSMs.

---

## 4. Allowed shared modules (small)

| Module | Role |
|--------|------|
| `sync_shared.py` | `append_raw`, checkpoint upsert, scope ping |
| `checkpoint_contract.py` | merge, migrate v2 |
| `sync_context.py` | live / replay / backfill lane |
| `live_idempotency.py` | dedupe keys only — **not** identity resolution |
| `sync_router.py` | dispatch to connector sync |
| `scheduler.py` | list jobs for Beat |
| `exhaust_coverage_registry.py` | static matrix for admin (data, not runtime) |

**Discouraged new modules** unless <150 lines and no runtime state: prefer functions in connector `sync.py`.

---

## 5. Coverage / trust — checkpoint-local only

**Persist (per stream, inside existing checkpoint `streams.{connector}`):**

| Field | Purpose |
|-------|---------|
| `next_cursor` / `next_page` | Resume |
| `backfill_complete` | bool — pagination done or policy cap |
| `introduced_at` | ISO date stream first shipped (trust honesty) |
| `last_ok_at` | Last successful page |
| counters | `pages_fetched_last_run`, `rows_seen_last_run` (already exist) |

**Compute on admin read (SQL), do not persist:**

- row counts by `resource_type`
- min/max `fetched_at`
- % users with email (from raw JSON)
- “repos never deep-fetched” = repos in checkpoint without `pull_requests.backfill_complete`

**Do not build:**

- coverage database tables
- debt planner / prioritization engine
- five-universe ontology as infrastructure
- `known_unknowns` arrays that grow without bound (log a warning; fix forward)

**Trust label (one field in checkpoint `meta`):**

```json
{ "exhaust_depth": "shallow" | "deepening" | "mature" }
```

Set by simple rules (operator override allowed), not T0–T5 framework.

---

## 6. People exhaust — provider user rows only

**Do:** `resource_type=slack.user`, store API `member` blob, normalize nothing cross-provider.

**Do not in ingestion:**

- match Slack user → Linear user
- org chart inference
- canonical Person entity
- “actor intelligence”

Use envelope field `person` as **documentation shape** in payload only; downstream `cortex/identity` owns meaning.

---

## 7. Replay / backfill — three modes, no platform

| Mode | How |
|------|-----|
| Incremental | Default Beat; `IngestionSyncContext.live_incremental()` |
| Backfill | Admin `sync_mode=backfill` or `IngestionSyncContext.backfill()` |
| Replay | Admin `trigger-replay`; isolated checkpoint scope |

**Stream reset:** delete one key path in checkpoint JSON (admin helper). No migration runtime.

**Do not build:** replay DAG, recovery planner, historical rebuild orchestrator.

---

## 8. Domain boundaries

```text
cortex/ingestion/     → fetch, paginate, append_raw, checkpoint
cortex/identity/      → (future) cross-provider person resolution
cortex/graph/         → (future) organizational graph
cortex/execution/     → (future) execution derivation
```

**Ingestion must not import** from identity/graph/execution.

**Existing `raw_memory_*` in ingestion/:** Phase 01–02 governance (trust, retention, replay equivalence). **Freeze** new surface area there; new exhaust work goes in `connectors/*/sync.py` + thin shared helpers only.

---

## 9. Adding a connector (checklist)

1. `connectors/{id}/sync.py` — one `run_*_connector_sync` loop  
2. `resource_type` strings + matrix row  
3. Checkpoint keys under `streams.{id}`  
4. Tests: pagination resume, append_raw dedupe, replay isolation  
5. No new framework  

---

## 10. PR rejection criteria

Reject if the PR:

- Adds orchestration across connectors or planes  
- Adds DB tables for coverage/planning  
- Adds FSM with >3 states per stream  
- Resolves or links identities across providers  
- Introduces “planner”, “engine”, “coordinator” in ingestion  
- Duplicates Airflow/Celery responsibilities  

---

## 11. Honest 3-year test

| Question | Answer if we follow this doctrine |
|----------|-----------------------------------|
| Understandable by small team? | **Yes** — debug path = connector sync file + checkpoint JSON + raw row |
| New connector cost? | **One file + matrix row** |
| Evolution manageable? | **New stream or cursor reset** — not replatform |
| Isolated from graph/identity? | **Yes** if we stop growing `raw_memory_*` and governance in ingestion |
| Airflow clone risk? | **Low** if Beat stays one task per connection and caps stay |

**Risk if we ignore doctrine:** `coverage_ledger` + trust DB + planners + 47-module ingestion folder → **slow internal platform**.

---

## 12. Simplified evolution policy (replaces long class tables)

| Change | Action |
|--------|--------|
| New `resource_type` | Ship; backfill once; set `introduced_at` |
| Deeper pages | Let cursors run |
| Richer fields on existing type | Reset that stream’s cursor + backfill **or** bump `ingestion_version.extraction` in payload |
| Never | Change `external_id` scheme without new resource_type suffix |
