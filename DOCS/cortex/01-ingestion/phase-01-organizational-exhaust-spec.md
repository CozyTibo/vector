# Phase 01 — Organizational Exhaust Ingestion (Authoritative Spec)

**Status:** normative for what “Phase 01 complete” means for **exhaust** (distinct from substrate steps 0–6).  
**Non-normative:** product positioning; this file is **implementation and exit-criteria** only.

**Related:** `real-ingestion-definition.md` (short form), **`phase-01-raw-persistence-doctrine.md`** (locked unit model: threads, PRs, activity, blocks), **`phase-01-ingestion-continuity-doctrine.md`** (modes, idempotency, live vs replay, convergence, checkpoints), **`phase-01-live-idempotency-doctrine.md`** (mandatory Step 15 correctness gate), **`phase-01-runtime-correctness-hardening-doctrine.md`** (mandatory Step 16 runtime-correctness gate), `../implementation/organizational-exhaust-execution-track.md` (gap map + roadmap), `../connectors/connector-exhaust-matrix.md`, `../MASTER_TRACKER.md` §2.5.

---

## 1. Phase 01 goal (single sentence)

**Absorb and persist the complete raw operational exhaust of the organization** from every connected tool Vector supports, such that **organizational history can be reconstructed from `raw_ingestion_records` alone** (no canonicalization, inference, or graph required in Phase 01).

---

## 2. Exhaust-first philosophy (operational, not narrative)

| In scope for Phase 01 | Out of scope (later phases) |
| --------------------- | --------------------------- |
| HTTP/API fetch, pagination, cursoring | Canonicalization, normalization beyond envelope validation |
| Checkpointed backfill + incremental continuation | Execution graphs, risk signals, embeddings |
| Append-first raw rows + replay-safe keys + stable live logical idempotency | Global semantic dedupe, “smart” merging of meaning |
| Rate-limit handling, retries, workload chunking | Summarization, scoring, copilots |

**Forbidden ambiguity:** “Connector works,” “sync completed,” “admin shows green,” or “scope_ping exists” **do not** imply Phase 01 exhaust progress. Only **volume, breadth, and continuity of real resource streams** (messages, PR reviews, issue comments, blocks, transcripts, etc.) count.

---

## 3. Required ingestion depth (global rules)

Every **declared** organizational stream for a connector MUST eventually meet ALL of:

1. **Pagination:** follow provider pagination (`cursor`, `page`, `Link` header, GraphQL `pageInfo`) until the stream’s completion policy is met (see §8).
2. **Cursors in checkpoint:** `connector_sync_state.state` (or successor) stores **per-stream** continuation: e.g. Slack `latest`/`oldest` per channel, GitHub `since`/ETag/sha, Linear `updatedAt` + `after`, Notion `start_cursor` per list.
3. **Historical backfill:** first-time and catch-up passes walk **full available history** per policy (tenant/legal caps may bound *scope*, not silently default to “first page”).
4. **Incremental sync:** after backfill, same code paths advance only from checkpoint (no re-download of entire history every Beat tick unless policy says so).
5. **Replay:** replay jobs use **isolated checkpoint scope** and **idempotent raw inserts** for replay-scoped keys; behavior MUST be defined per stream (see §7).
6. **Raw resource types:** one row (or one batch row policy, if explicitly documented) per API response unit; `resource_type` MUST identify the stream (e.g. `slack.message`, `github.pull_request_review`).

**Shallow fetch** = any stream that stops at “first page,” “latest N without cursor,” or “sample channels” **without** a documented checkpoint path to completeness. Shallow fetch is **non-compliant** for Phase 01 exit unless explicitly deferred in §11 (open decisions).

---

## 4. What Phase 01 does NOT build

- Connector “maturity cards,” health dashboards, or integration scoring as **substitutes** for exhaust (admin may show **facts**: row counts, oldest/newest timestamps, cursor positions — not maturity narratives).
- `*.scope_ping` / `viewer_ping` as **evidence of ingestion depth** (allowed only as **error-path** or **explicit connectivity** when no token; must not be the dominant row mix).
- Canonical entities, linking, or derived execution intelligence.

---

## 5. Pagination requirements

| Requirement | Detail |
| ----------- | ------ |
| Completeness | For each stream, ingest **all pages** until provider end-of-list OR until an **explicit operator/tenant window** is documented and stored in checkpoint |
| Caps | Env caps (e.g. max pages per run) MUST implement **resume next run** via checkpoint, not silent truncation without resume |
| GraphQL | Use `pageInfo.hasNextPage` + `endCursor`; never rely on `first: n` alone without continuation |
| REST | Honor `next` links / `page` param / `since` where available |

---

## 6. Cursor requirements (checkpoint contract)

- **Per connector, per stream family:** checkpoint JSON MUST support resuming without reprocessing completed pages (e.g. `channels.{id}.history_cursor`, `repos.{full_name}.pr_list_cursor`).
- **Monotonic merge:** existing monotonic fields (`last_incremental_at`, numeric max hints) MUST be extended deliberately; partial merges MUST NOT erase finer-grained cursors.
- **Replay scope:** live checkpoint keys vs `replay:<job_id>` scope MUST remain isolated; document which cursors are copied vs blank on replay start.

---

## 7. Replay requirements

| Topic | Requirement |
| ----- | ----------- |
| Idempotency | Replay inserts: `ON CONFLICT DO NOTHING` on `(replay_job_id, idempotency_key)` for defined keys |
| Live lane | May append new rows per run; **prefer** stable idempotency keys per logical object revision where feasible to avoid unbounded duplicate raw rows (still raw — not semantic dedupe) |
| Evidence | Each raw row MUST remain sufficient to answer “which API response produced this” (endpoint, params, payload) |

---

## 8. Historical backfill vs incremental (expectations)

- **Backfill:** on first connect or after scope expansion, system walks history until checkpoint marks stream **caught up** (or hits documented tenant cap).
- **Incremental:** subsequent runs advance from last cursor / `updatedAt` / `since` only.
- **Reconciliation:** optional periodic full-diff is Phase 01 only if implemented as **additional raw fetches**, not interpretation.

---

## 9. Per-connector organizational exhaust scope (target)

Exact stream list and API mapping live in **`../implementation/organizational-exhaust-execution-track.md`** §2 (gap map) and **`../connectors/connector-exhaust-matrix.md`**. At minimum, Phase 01 **target** includes:

| Connector | Target exhaust (illustrative; not exhaustive) |
| --------- | --------------------------------------------- |
| **Slack** | Users, all conversation types policy allows, messages, threads/replies, reactions, files, pins/bookmarks where API permits, edits/deletes as events, membership changes where available |
| **GitHub** | Repos, branches/tags, PRs, reviews, review comments, issues, issue comments, commits, statuses/checks, Actions runs, deployments — with timelines where available |
| **Linear** | Issues, comments, labels, projects, cycles, attachments, relations, activity/history — with `updatedAt` incremental |
| **Notion** | Databases, pages, blocks (nested), comments/version where API permits |
| **Calls** | Transcripts, speakers, timestamps, meeting metadata, participants |

Until the gap map shows these streams **implemented with pagination + cursor**, Phase 01 exhaust is **incomplete**.

---

## 10. Admin / operator visibility (minimal bar)

Admin MUST allow operators to **verify exhaust reality**, not “sync success”:

- Browse `raw_ingestion_records` by connector with filters (`resource_type`, time range).
- See **row counts and time range** per `resource_type` (aggregates from DB).
- Optionally hide `*.scope_ping` rows from default view.

Admin MUST NOT be mistaken for Phase 01 completion: **row counts** prove absorption; **badges** do not.

---

## 11. Phase 01 exit criteria (organizational exhaust)

Phase 01 is **CLOSED for exhaust** only when ALL hold:

1. **Coverage:** Every row in `connector-exhaust-matrix.md` that is **required** for product Phase 01 (non-deferred) is **implemented** with pagination + checkpoint continuation — registry and matrix match code.
2. **Depth:** For each connector, raw store contains **dominant** real streams (e.g. `slack.message`, `github.pull_request_review`, `linear.comment`, `notion.block`) — not predominantly `scope_ping`.
3. **Temporal span:** Backfill has run or is resumable; **oldest** `fetched_at` / payload timestamps prove historical reach per policy.
4. **Incremental:** Beat/manual sync advances cursors without full re-backfill each time.
5. **Replay:** Documented replay behavior per stream; replay job reproduces raw captures without corrupting live checkpoints.
6. **Reconstruction drill:** Operationally agreed scenario (e.g. incident week) reconstructable from **raw rows alone** for each tool in scope.
7. **Documentation:** `organizational-exhaust-execution-track.md` gap map shows **no remaining “missing”** rows for in-scope streams, or explicitly lists **deferred** items with signed-off scope cut.
8. **Live-lane logical idempotency lock (Step 15):** stable live identity+revision keys, canonical payload hashing, deterministic conflict-ignore insertion, replay/live isolation visibility, and duplicate-prevention verification per `phase-01-live-idempotency-doctrine.md`.
9. **Runtime correctness lock (Step 16):** invariant suite + concurrency/retry/crash correctness validation, checkpoint/cursor correctness validation, replay/live overlap correctness, and finalized multi-connection scoping semantics per `phase-01-runtime-correctness-hardening-doctrine.md`.

**Substrate steps 0–6 complete** is necessary but **insufficient** for Phase 01 exhaust closure.

**Tracker alignment:** Organizational exhaust work is **`DOCS/cortex/MASTER_TRACKER.md` Phase 01 Steps 7–16** (substrate remains 0–6). Step **16** is the tracker exit gate for this section.

---

## 12. Explicit non-goals (again)

No canonicalization, no execution graph, no embeddings, no summarization, no cross-tool identity resolution in Phase 01.

---

## 13. Document control

| Change | Update together |
| ------ | ---------------- |
| New stream / resource_type | `connector-exhaust-matrix.md`, `exhaust_coverage_registry.py`, executor code, this file if exit criteria affected |
| Checkpoint shape | `checkpoint_contract` / merge rules, execution track roadmap step |
