# Phase 01 — Ingestion Continuity Doctrine

**Status:** normative — locked and implemented through **Step 16** runtime correctness hardening.  
**Scope:** how raw organizational exhaust **progresses over time**, **converges historically**, **avoids duplicate logical events**, and **separates live vs replay** — **without** canonicalization, graphs, or inferred semantics.

**Related:** `phase-01-organizational-exhaust-spec.md`, `phase-01-raw-persistence-doctrine.md`, **`phase-01-live-idempotency-doctrine.md`**, **`phase-01-runtime-correctness-hardening-doctrine.md`**, `persistence-architecture.md`, `replay-consistency-verification.md`, `../implementation/organizational-exhaust-execution-track.md`, `../MASTER_TRACKER.md` Phase 01.

**Complements:** `phase-01-raw-persistence-doctrine.md` (what is a **row**); **this doc** (how **time**, **modes**, and **identity** behave across runs).

### Authority map (FINAL OUTPUT ↔ sections)


| #   | Topic                             | Where                        |
| --- | --------------------------------- | ---------------------------- |
| 1   | Formal ingestion mode doctrine    | **§1** (modes 1.1–1.5)       |
| 2   | Historical backfill strategy      | **§2**                       |
| 3   | Incremental continuation strategy | **§1.2**, **§9**             |
| 4   | Logical idempotency doctrine      | **§4**                       |
| 5   | Replay vs live-lane doctrine      | **§6**                       |
| 6   | Raw revision / evolution doctrine | **§5**                       |
| 7   | Checkpoint evolution proposal     | **§7**                       |
| 8   | Duplication prevention model      | **§8**                       |
| 9   | Historical convergence model      | **§3**                       |
| 10  | Operational scheduling model      | **§9**                       |
| 11  | Open risks / unresolved tradeoffs | **FINAL OUTPUT §11** (table) |
| —   | Empty → deep memory summary       | **§10**                      |


**Primary objective (locked):** Define how Cortex moves from **empty workspace** → **replay-safe, incrementally maintained, historically converging** raw organizational exhaust — without canonicalization or inferred semantics.

---

## Step 1 — Formal ingestion modes

### 1.1 Historical backfill


| Aspect                      | Definition                                                                                                                                                                             |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**                 | Move a stream’s cursor from **“no history”** or **“partial window”** toward **policy depth** (oldest-first or bounded window per §2–3).                                                |
| **Trigger**                 | New connection; new stream enabled; explicit operator “deepen history”; scheduled **low-priority walker** after incremental is healthy.                                                |
| **Cursor behavior**         | **Backfill cursor** distinct from incremental watermark where both exist (e.g. `backfill.oldest_ts` advancing toward target floor; or `backfill.page` for repo-scoped lists).          |
| **Checkpoint semantics**    | Merge **monotonic progress** for backfill pointers (never move backward without explicit repair). Separate keys from `incremental.since` to avoid conflation.                          |
| **Ordering**                | **Provider order** (e.g. Slack `latest` pagination backward, or `oldest` forward per API). Document per stream.                                                                        |
| **Retry**                   | Same idempotency key → **no second logical row**; transient failures resume from last committed checkpoint.                                                                            |
| **Duplication risks**       | Overlapping backfill + incremental on **same** time range if watermarks merged incorrectly — **prevent** by **non-overlapping ranges** or **single-writer per stream scope** per tick. |
| **Operational constraints** | Rate limits, time-budget per task, chunk boundaries (channel/repo/page).                                                                                                               |


### 1.2 Incremental continuation


| Aspect                      | Definition                                                                                                                                                        |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**                 | Capture **new or updated** organizational events **since** last successful cursor position — **near-real-time** freshness for ongoing execution.                  |
| **Trigger**                 | Beat (`cortex_live`), manual sync, post-backfill handoff.                                                                                                         |
| **Cursor behavior**         | **High watermark** per stream: Slack `latest_ts` per channel or global; GitHub `updated_since` / ETag; Linear `updatedAt`; Notion `last_edited_time`.             |
| **Checkpoint semantics**    | Advance only after **successful persist** of all pages in the current batch (or record partial page for resume).                                                  |
| **Ordering**                | Best-effort chronological by provider; **no** global cross-connector order.                                                                                       |
| **Retry**                   | Idempotent keys absorb duplicate fetches of same event.                                                                                                           |
| **Duplication risks**       | Watermark advanced **before** persist → retry duplicates; **mitigation:** advance checkpoint **after** commit (or two-phase: `pending_watermark` vs `committed`). |
| **Operational constraints** | Must complete within Beat interval or yield to next chunk.                                                                                                        |


**Critical distinction — historical convergence vs near-real-time continuation**


|                      | Historical convergence                                        | Near-real-time continuation              |
| -------------------- | ------------------------------------------------------------- | ---------------------------------------- |
| **Goal**             | Depth into the **past** toward policy horizon                 | **Fresh** tail since last run            |
| **Cursor**           | Backfill pointer(s), often **oldest-remaining** or page index | **Since / latest** watermark             |
| **Priority**         | Lower; can be throttled                                       | Higher; runs every scheduled incremental |
| **User expectation** | “Memory gets deeper over days/weeks”                          | “Today’s work shows up quickly”          |


Both may run in the same codebase but **must use distinct checkpoint keys** or a **mode flag** per stream to avoid cursor corruption.

### 1.3 Replay


| Aspect                      | Definition                                                                                                                                                                                                                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Purpose**                 | Re-execute ingestion **logic** for a **fixed replay job** with **isolated checkpoint scope** — verification, audit, disaster recovery — **not** to invent new organizational facts.                                                                                                              |
| **Trigger**                 | Operator enqueue `cortex_replay` with `replay_job_id` + `replay_version`.                                                                                                                                                                                                                        |
| **Cursor behavior**         | **Replay-scoped** `connector_sync_state` key `replay:<job_id>` (or equivalent); **does not** advance live cursors.                                                                                                                                                                               |
| **Checkpoint semantics**    | Independent; may mirror live structure under replay scope.                                                                                                                                                                                                                                       |
| **Ordering**                | Same as live for same inputs; deterministic envelope + idempotency.                                                                                                                                                                                                                              |
| **Retry**                   | Idempotency on `(replay_job_id, idempotency_key)` → **insert once** per key.                                                                                                                                                                                                                     |
| **Duplication risks**       | **Live vs replay** rows both present — **acceptable** if **lineage** distinguishes them (`replay_job_id`, `cortex_replay_metadata`); **not** “fake events” if payloads are **re-fetched truth** from API at replay time (same as live). **Problem:** if replay **synthesizes** data — forbidden. |
| **Operational constraints** | Separate queue; worker capacity.                                                                                                                                                                                                                                                                 |


### 1.4 Recovery / repair


| Aspect                      | Definition                                                                                                                                |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**                 | Fix **corrupted checkpoint**, **gap** after outage, or **partial failure** without duplicating logical events.                            |
| **Trigger**                 | Operator action, automated health check detecting regression (e.g. watermark behind `max(fetched_at)`).                                   |
| **Cursor behavior**         | **Rewind** or **re-seed** with explicit audit log; prefer **re-fetch overlapping window** with **idempotency** rather than delete rows.   |
| **Checkpoint semantics**    | Monotonic merge may **block** backward moves — repair may require **administrative override** key or scoped reset (documented procedure). |
| **Duplication risks**       | Re-fetch overlap — **mitigated** by logical idempotency (§4).                                                                             |
| **Operational constraints** | Manual approval for destructive checkpoint reset.                                                                                         |


### 1.5 Targeted re-sync


| Aspect                      | Definition                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **Purpose**                 | Re-pull **one** narrow scope (one channel, one PR, one page) for debugging or known drift — **not** full tenant replay. |
| **Trigger**                 | Operator/API with explicit **scope** (resource ids).                                                                    |
| **Cursor behavior**         | Optional **one-off** cursor bypass or **temporary** sub-checkpoint; must not reset global incremental without intent.   |
| **Duplication risks**       | Same as incremental; idempotency must hold.                                                                             |
| **Operational constraints** | Rate limits; log scope in `ingestion_runs` / stats.                                                                     |


---

## Step 2 — Initial history strategy (“time-to-first-value”)

**Doctrine:** A **new workspace** MUST reach **useful execution exhaust quickly** (hours, not weeks), then **deepen** via convergence (Step 9).

**Default policy bands** (tune per tenant tier; document in settings):


| Connector  | Initial window (suggested default)                                                                                                                     | Rationale                                                           |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| **Slack**  | **90–180 days** of message history for **top-K active channels** (by recent activity or allowlist), plus **current** users/channels list               | Avoids full-archive crawl on day one; K and depth env-configurable. |
| **GitHub** | **12 months** of PR/review/comment activity for repos in installation, or **all open + merged in window**, whichever is smaller cap                    | Balances delivery reconstruction vs clone time.                     |
| **Linear** | **Full issue set** may be feasible (smaller cardinality); if huge, **12 months `updatedAt`** then walk older in background                             | API is GraphQL-friendly for pagination.                             |
| **Notion** | **Active databases** (allowlist or recently edited) + pages **touched in last N days**; block depth **gated** (`phase-01-raw-persistence-doctrine.md`) | Rate limits + row explosion.                                        |
| **Calls**  | **90 days** of meetings or last **N** recordings                                                                                                       | Transcript size.                                                    |


**Not required:** “Wait weeks until backfill finishes” before **any** value — **incremental** on the **tail** runs **alongside** truncated initial backfill.

**Handoff rule:** After first successful incremental, mark stream `**incremental_ready`**; backfill continues in **lower priority** until `**backfill_complete`** or policy floor reached.

---

## Step 3 — Historical convergence model

**Goal:** From partial history → **policy-depth** memory without starving the tail.

**Mechanisms (combine as needed):**

1. **Dual cursors per stream** (where applicable): `incremental_high_watermark` + `backfill_low_watermark` (or `backfill_oldest_remaining_ts`).
2. **Rolling backfill:** each low-priority tick advances backfill by **budget** (messages/repos/issues) until floor reached.
3. **Fairness:** Slack **rotate channel ring** for backfill so one noisy channel does not monopolize.
4. **Active-stream prioritization:** channels/repos with **recent** incremental traffic may get **slightly more** backfill share (optional).
5. **Oldest-first within channel** (Slack) or **since ascending** (GitHub/Linear) for backfill leg — **document** per API.

**Balance:**


| Priority | Work                                                 |
| -------- | ---------------------------------------------------- |
| **P0**   | Incremental continuation every Beat cycle (bounded). |
| **P1**   | Initial window completion (Step 2).                  |
| **P2**   | Deep historical walker toward policy horizon.        |


**Convergence metric (operational):** per stream, `oldest_ingested_event_time` approaches `now - policy_horizon` (or API limit) — tracked in admin aggregates, not “maturity” narrative.

---

## Step 4 — Logical idempotency doctrine

### 4.1 Principle

`**run_id` MUST NOT define logical identity** of an organizational event.  
**Logical identity** = provider-stable key derived from **API identity** (see `phase-01-raw-persistence-doctrine.md`).

**Lock:** this is a mandatory Phase 01 closure requirement (tracker Step 15), not an optimization.

### 4.2 Stable key examples (live lane base)


| Stream                | Suggested logical key suffix (concat with connector + stream) |
| --------------------- | ------------------------------------------------------------- |
| Slack message         | `channel_id:ts`                                               |
| Slack reply           | `channel_id:thread_ts:reply_ts`                               |
| GitHub PR             | `owner/repo:number`                                           |
| GitHub review         | `review_id`                                                   |
| GitHub review comment | `comment_id`                                                  |
| GitHub check run      | `check_run_id`                                                |
| Linear issue          | `issue_id` (with **revision** — §5)                           |
| Linear comment        | `comment_id`                                                  |
| Notion block          | `block_id`                                                    |
| Notion page           | `page_id` (with revision — §5)                                |


**Idempotency key format:** `hmac_or_trunc(connector:resource_type:logical_key)` ≤ 128 chars; **replay:** append `:rj:{replay_job_id}` per existing pattern.

### 4.3 Retries

Same logical event, transient failure, retry → **same idempotency key** → **at-most-one** row. Live-lane deterministic conflict-ignore insertion and supporting uniqueness strategy are mandatory by Step 15.

For Phase 01 closure, deterministic conflict-ignore insertion on live lane is mandatory per `phase-01-live-idempotency-doctrine.md`.

### 4.4 Overlapping windows

Incremental `[T0, T1]` and backfill overlapping `[T0, T2]` → **same keys** → duplicates prevented **if** keys are stable; **if** two different fetches return **different payload** for same logical id (edit) → §5.

### 4.5 Replay

Replay uses **different** idempotency namespace `(replay_job_id, key)` so **replayed** rows may **coexist** with live rows for audit; **not** duplicate *within* same replay job.

### 4.6 Edits / versioned payloads

**Logical identity stable; payload revision changes** → §5 (append revision row or revision idempotency).

---

## Step 5 — Raw revision / evolution model

### 5.1 Terms


| Term                  | Meaning                                                                                           |
| --------------------- | ------------------------------------------------------------------------------------------------- |
| **Logical identity**  | Provider id for the “thing” (message, PR, issue).                                                 |
| **Payload revision**  | New API body for same logical id (edit, state transition).                                        |
| **Ingestion attempt** | One executor run + HTTP fetch; may produce 0 or 1 persisted row per logical key **per revision**. |
| **Replay lineage**    | `replay_job_id` / metadata on row distinguishing replay path.                                     |


### 5.2 Doctrine (no destructive overwrite of raw rows)

- **Raw table is append-only evidence.** Never **UPDATE** a prior `raw_ingestion_record` to “fix” content (except operational bug fixes out of band — not normal path).

### 5.3 When logical id + payload changes

**Option A (recommended):** **Revision idempotency key** includes **content version** from provider when available:

- GitHub: `updated_at`, `node_id` + `updatedAt`, or **ETag** digest.  
- Slack: `edited.ts` if present — key `channel:ts:edited_ts` or **hash of message body** from API.  
- Linear: `updatedAt` on issue.

Idempotency key = `logical_base:rev:{provider_revision_token}`.  
**Same** revision refetched → **no new row**. **New** revision → **new row** (execution evolution preserved).

**Option B:** Single key per logical id, **always append** on every fetch — **high duplication**; **reject** for high-volume streams unless content-hash dedupe at insert.

### 5.4 When provider does not expose revision token

Use **payload hash** (`payload_hash` already computed) as **advisory**; idempotency key may use `hash_short` for **dedupe of identical refetch** only — **new** ambiguous edit without ts → **new row** risk; **mitigate** with periodic **compact** policy in Phase 02, not Phase 01 inference.

### 5.5 Replay corruption

Replay **must not** rewrite live rows. Replay rows carry **replay metadata**; comparators in verification compare **live tail** vs **replay job** in isolation.

---

## Step 6 — Live vs replay lanes (doctrine)


| Aspect          | Live lane                                                        | Replay lane                                                                                                                            |
| --------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Checkpoint**  | `scope_key = default` (or live incremental scope)                | `scope_key = replay:<job_id>`                                                                                                          |
| **Idempotency** | Stable **logical** key (§4) + no `run_id` in key for hot streams | `(replay_job_id, idempotency_key)` unique partial index                                                                                |
| **Writes**      | **New raw rows** for new logical revisions                       | **New raw rows** in same table with replay fields set — **not** “metadata only” unless re-fetch skipped (prefer re-fetch for fidelity) |
| **Fake events** | Forbidden — only API-backed payloads                             | Same — replay is **re-execution of fetch**, not synthesis                                                                              |


**Clarification:** Replay **does** create **additional rows** compared to historical live capture **if** replay job runs against same APIs again — that is **audit replay**, not duplicate logical events **within** the same lane; operators filter by `replay_job_id IS NULL` for “live corpus.”

---

## Step 7 — Checkpoint evolution proposal

### 7.1 Required cursor dimensions (conceptual)

Per connector, checkpoint state SHOULD support:

- **Per-stream** incremental watermark(s).  
- **Per-stream** backfill pointer(s) where dual-mode.  
- **Per-scope** shards: Slack `channels.{id}`, GitHub `repos.{full_name}`, Linear `issues_cursor`, Notion `database.{id}`.

### 7.2 Storage shape


| Approach                                        | Pros                                                      | Cons                                                  |
| ----------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| **Nested JSON in `connector_sync_state.state`** | Single row per (tenant, connection, connector, scope_key) | Large JSON; merge complexity; corruption blast radius |
| **Separate `ingestion_stream_cursor` table**    | Normalized; easier partial update; less merge risk        | New migration; more joins                             |


**Recommendation:** **Phase 01 implementation:** start with **nested JSON** under **versioned schema** (`checkpoint_schema_version`) + **deep merge** rules for known paths (Step 7 tracker). **If** JSON exceeds **~100KB** compressed or merge bugs recur → **migrate hot cursors** to side table **without** changing raw row semantics.

### 7.3 Corruption recovery

- **Version** checkpoint schema; validate on read; reject unknown fields or fail closed to repair mode (1.4).  
- **Backup** last good checkpoint in **separate** JSON blob on major transitions (optional).

---

## Step 8 — Duplication prevention model & failure modes

### 8.1 How duplication happens


| Failure mode             | Mechanism                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| Overlapping sync windows | Watermark behind; re-fetch same page                                                             |
| Replay overlap           | Same replay job retried without idempotency                                                      |
| Retry overlap            | Worker retry after **partial** commit                                                            |
| Cursor corruption        | Reset to earlier page                                                                            |
| Pagination restart       | Same `page=1` re-run without cursor                                                              |
| Edited payload re-fetch  | Same logical key without revision suffix                                                         |
| Clock skew               | Rare for id-based keys; **watermark** keys vulnerable — prefer **provider ids** over client time |


### 8.2 Prevention hierarchy

1. **Stable logical idempotency keys** (§4) + **revision suffix** when content can change (§5).
2. **Checkpoint after successful batch commit** (or transactional ordering).
3. **Single active writer** per `(tenant, connector, stream_scope)` chunk per tick (avoid two Beat tasks same scope).
4. **Replay:** DB constraint on `(replay_job_id, idempotency_key)`.
5. **Monitoring:** alert on **sudden row count spike** vs incremental delta for stream.

---

## Step 9 — Operational scheduling model

**Queues:**

- `**cortex_live`:** incremental continuation + **small** backfill budget (optional) each run.  
- `**cortex_replay`:** replay jobs only.  
- `**cortex_backfill` (recommended addition):** optional low-priority queue for deep historical walkers so Beat never blocks on 6-hour Slack crawl.

**Per tick (live connector):**

1. Run **incremental** for all streams (bounded time).
2. If `incremental_ready`, spend **remaining budget** on **backfill** ring-advance (Slack channel N, GitHub repo M, …).
3. Record **mode** in run `stats` (`incremental_msgs`, `backfill_msgs`) for observability.

**Fairness:** round-robin **channel** / **repo** for backfill.  
**Stalled stream:** if incremental **fails**, do not advance watermark; **exponential backoff** on connector; **alert**.

---

## Step 10 — Continuity model summary (post-Step 16 hardening lock)

**Empty workspace → deep, replay-safe organizational exhaust:**

1. **Connect** → first **incremental** possible for tail; **parallel** **initial backfill** per Step 2 windows using **backfill cursors** (Step 3).
2. **Persist** only **API-backed** rows with **logical idempotency** (§4) and **revision-aware** keys for mutating objects (§5).
3. **Advance** **incremental** watermarks **after** successful writes; **advance** **backfill** pointers **separately** toward policy horizon.
4. **Converge** history via **low-priority** rolling walkers (Step 9) without blocking **freshness**.
5. **Replay** uses **isolated** checkpoints + **replay idempotency**; does not **mutate** live rows; may **coexist** for audit.
6. **Repair** uses **re-fetch + idempotency**, not silent deletes.
7. **Checkpoints** evolve to **per-scope cursors**; **side table** if JSON unmaintainable (§7).

---

## FINAL OUTPUT (numbered)

### 1. Formal ingestion mode doctrine

Steps **1.1–1.5**: Historical backfill, incremental continuation, replay, recovery/repair, targeted re-sync — each with purpose, trigger, cursor, checkpoint, ordering, retry, duplication risks, constraints. **§1** also separates **historical convergence** vs **near-real-time continuation**.

### 2. Historical backfill strategy

**§2:** Policy bands per connector; **fast initial value**; backfill **alongside** incremental; `incremental_ready` vs `backfill_complete` handoff.

### 3. Incremental continuation strategy

**§1.2** + **§9:** Watermark-based tail sync every Beat; checkpoint **after** commit; bounded work per tick.

### 4. Logical idempotency doctrine

**§4:** Stable keys by provider identity; `**run_id` excluded** from logical identity; examples; retries, overlap, replay, edits.

### 5. Replay vs live-lane doctrine

**§6:** Isolated checkpoint scope; replay rows with lineage; re-fetch not synthesis; coexistence with live corpus.

### 6. Raw revision / evolution doctrine

**§5:** Append-only raw; revision-aware idempotency; terms: logical identity vs payload revision vs ingestion attempt vs replay lineage.

### 7. Checkpoint evolution proposal

**§7:** Per-stream/per-scope cursors; nested JSON + schema version + deep merge first; **optional** `ingestion_stream_cursor` table if scale demands.

### 8. Duplication prevention model

**§8:** Failure modes + prevention hierarchy (keys, commit order, single writer, replay constraint, monitoring).

### 9. Historical convergence model

**§3:** Dual cursors, rolling backfill, fairness, P0/P1/P2 priorities, convergence metric.

### 10. Operational scheduling model

**§9:** Live vs optional backfill queue; per-tick ordering; fairness; stalled-stream handling.

### 11. Open risks / unresolved tradeoffs


| Risk / tradeoff                 | Notes                                                                                                                                    |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Live unique constraint**      | Implemented as connection-scoped live uniqueness `(tenant, connection, connector, resource, identity, revision)` for `replay_job_id IS NULL`. |
| **Revision token gaps**         | Some APIs weak on edit detection → occasional duplicate or missed revision — document; Phase 02 compaction optional.                     |
| **Checkpoint JSON size**        | May force side table mid-Phase-01 — plan migration path.                                                                                 |
| **Dual-mode cursor bugs**       | Highest engineering risk — **require** integration tests for interleaving incremental + backfill.                                        |
| **Replay vs live row volume**   | Audit replay doubles storage — **retention policy** Phase 02+.                                                                           |
| **ETag / conditional requests** | GitHub — reduce bandwidth; **optional** optimization; cursor still source of truth.                                                      |


---

## Document control


| Document                                    | Relationship                                                       |
| ------------------------------------------- | ------------------------------------------------------------------ |
| `phase-01-raw-persistence-doctrine.md`      | **What** is stored per row                                         |
| **This doc**                                | **How** ingestion progresses, converges, and dedupes logically     |
| `phase-01-live-idempotency-doctrine.md`     | Live-lane identity/revision/hash/insertion closure requirements    |
| `phase-01-runtime-correctness-hardening-doctrine.md` | Runtime correctness invariants + connection scope doctrine |
| `organizational-exhaust-execution-track.md` | Implementation sequencing; update §F if continuity defaults change |


**Lock:** Changing §4–§6 or dual-cursor model requires **ADR** or explicit amendment to this file.