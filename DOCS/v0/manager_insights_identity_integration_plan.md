# Manager insights: identity as a first-class execution dimension (phased plan)

**Status:** planning only — **do not implement** until explicitly approved.  
**Goal:** extend the pipeline (do not rewrite) so execution modeling can use **stable `actor_id`** while **string `owner` / `participants` remain** for backward compatibility.

---

## Principles (non-negotiable)

1. **Dual-write:** new actor fields are **additive**; existing string fields **stay** and remain populated from current sources.
2. **Optional everywhere:** `owner_actor_id` / `participant_actor_ids` may be `null` / empty; contracts and APIs must treat them as optional.
3. **No LLM identity:** resolution is **deterministic** mapping `(tenant_id, connector, external_id)` → existing canonical tables / upsert rules — no fuzzy name matching.
4. **Artifact topology unchanged:** gaps, links, execution graph stay **work-item-id–centric** (per product decision).
5. **Explicit unknowns:** when resolution fails, downstream logic must use a **first-class UNKNOWN / unmapped** concept — **not** “pretend the string is a stable person key.”

---

## Phase map (incremental)


| Phase | Scope                                            | Primary verification                                            |
| ----- | ------------------------------------------------ | --------------------------------------------------------------- |
| P0    | Contracts + types + fixtures                     | Unit tests, JSON schema examples                                |
| P1    | Fetch sampling enrichment                        | Fetch-debug payload diff (new keys present)                     |
| P2    | Actor resolution hook + dual-write on `WorkItem` | Fetch-debug `work_items` include new fields; strings unchanged  |
| P3    | UNKNOWN semantics + signal migration             | Deterministic signal tests; golden snapshots                    |
| P4    | New execution situations                         | `detect_execution_situations` tests; debug-only surfacing first |
| P5    | Admin UI dedupe / display                        | UI manual + TS types; scope line counts                         |
| P6    | Hardening                                        | Load tests, demotion flags, rollout toggles                     |


Each phase should merge independently and keep **all existing tests green**.

---

## STEP 1 — Preserve identity at fetch layer (CRITICAL)

**Objective:** sampled connector payloads must carry **stable external ids** alongside today’s display strings — **additive fields only**.

### 1.1 Slack (`fetch_activity` mock + live paths)

- **Today:** sampled row uses `user` (mock: email from `user_email`; live: Slack member id).
- **Add:** e.g. `slack_user_id` (or `user_id`) when available from API; if mock only has email, set `slack_user_id: null` but **do not remove** `user`.
- **Verify:** fetch-debug `fetch.connectors.slack.payload.sampled_channel_messages[]` contains **both** `user` and new id field when live Slack returns `user`.

### 1.2 GitHub (`_fetch_github` / `_mock_github_result`)

- **Add:** `author_id` (numeric GitHub user id) next to existing `author` (login).
- **Verify:** PR/issue sampled rows include `author_id` when REST `user.id` exists.

### 1.3 Linear (`_fetch_linear` / `_mock_linear_result`)

- **Add:** `assignee_id` next to `assignee_name`.
- **Verify:** sampled issue rows include `assignee_id` when GraphQL `assignee.id` exists.

### 1.4 Notion (`_fetch_notion` / mock pages)

- **Add:** `last_edited_by_id` (or preserve full `last_edited_by` sub-object as read-only JSON) **in addition to** string `owner` already derived for `WorkItem`.
- **Verify:** `sampled_pages[]` exposes stable id without dropping `owner` string.

### 1.5 Calls (Google Calendar)

- **Add:** `organizer_id` (or equivalent from API) next to `organizer_email`.
- **Verify:** `sampled_events[]` includes organizer id when API provides it.

### 1.6 Non-goals for Step 1

- Do **not** change caps, windowing, or which rows are sampled (unless a field is impossible without an extra API call — document tradeoff).

**Exit criteria:** raw fetch payloads in fetch-debug show **new stable keys** populated where the upstream API/mock provides them; **zero removal** of existing keys used by `build_work_items` today.

---

## STEP 2 — Actor resolution in `build_work_items` (dual-write)

**Objective:** materialize **optional** actor linkage on each `WorkItem` while **keeping** string `owner` / `participants` identical to today’s behavior when resolution is off or fails.

### 2.1 Contract extension (`manager_insights_activity.WorkItem`)

- Add **optional** fields (names illustrative; finalize in implementation spec):
  - `owner_actor_id: UUID | None`
  - `participant_actor_ids: list[UUID]` (parallel list to `participants` **by index**, or document tuple pairing — choose one ordering contract and stick to it)
- Keep: `owner: str | None`, `participants: list[str]`, `source_ref: dict[str, str]`
- **JSON:** ensure OpenAPI / admin types / any codegen list new fields as optional with backward-compatible defaults.

### 2.2 Dependency injection (no global state)

- Introduce a narrow protocol / interface, e.g. `ResolveActorFn(tenant_id, connector, external_id, fallback_label) -> UUID | None`.
- **Default no-op implementation** for tests and for “resolution disabled”: returns `None` for all calls; strings still filled as today.
- **Production implementation** wraps canonical upsert / lookup (`Actor` / `ActorExternalIdentity`) under tenant scope — **deterministic**, idempotent.

### 2.3 Mapping table (per connector)

Document exact precedence for **external_id** string stored in `ActorExternalIdentity.external_id`, e.g.:

- Slack: `slack_user_id` (`U…`) preferred; if only email in mock, **do not invent** an id — leave `owner_actor_id` null.
- GitHub: `github_user:{numeric_id}` or documented stable key format (must match canonical ingestion if shared).
- Linear: `linear_user:{assignee_id}` (example — align with canonical).
- Notion: `notion_user:{uuid}`.
- Calls: `google_user:{organizer_id}` or email-backed actor only if that is the canonical policy (document explicitly).

### 2.4 `build_work_items` changes

- After constructing each `WorkItem` **as today**, call resolver for:
  - owner external id (from new fetch fields)
  - each participant external id (Slack may need policy: thread row only has one `user` today — document limitation)
- Set `owner_actor_id` / `participant_actor_ids` from resolver results.
- **Do not** alter `id`, `title`, `source_ref` keys used by graph/gaps.

**Exit criteria:** with resolver **disabled**, output is **byte-identical** to current behavior except for presence of new null/empty fields; with resolver **enabled**, fetch-debug shows **same strings** + **non-null actor ids** where mapping exists.

---

## STEP 3 — UNKNOWN actor handling (no silent string fallback)

**Objective:** downstream logic must not treat “missing actor” as “same as string token.”

### 3.1 Define UNKNOWN explicitly

- Introduce an internal sentinel or parallel classification, e.g. `UNRESOLVED_ACTOR` bucket keyed by `(connector, raw_string)` **only for analytics that must count unresolved** — **not** as a fake UUID.
- Rule: **signals that claim to measure people** must report:
  - **mapped actor counts** separately from
  - **unmapped participant counts** (see `unknown_actor_ratio` in Step 4).

### 3.2 Policy when `actor_id` is null

- **Do not** silently substitute string equality for actor equality in new logic.
- **Do** keep legacy string-based paths **only** behind explicit flags or “legacy mode” sections until Step 4 replaces them.

**Exit criteria:** with 100% unmapped users, new signals report high `unknown_actor_ratio` and **do not** claim low `actor_fragmentation` based on strings alone.

---

## STEP 4 — Upgrade `compute_signals` (core change)

**Objective:** actor-aware, deterministic signals; **string fallback only where explicitly allowed** (see Step 3).

### 4.1 Refactor participant aggregation (internal)

- Build **two** parallel representations from `WorkItem` list:
  1. `actors: set[UUID]` from non-null `owner_actor_id` and `participant_actor_ids`
  2. `unmapped: structured counters` for items with null actor but non-empty strings

### 4.2 New signals (all deterministic, no LLM)

1. `**actor_fragmentation`** — count distinct mapped `actor_id` across selected work items / discussion neighborhood (define exact window: same inputs as current collaboration metric uses today — document side-by-side).
2. `**actor_load**` — distribution: e.g. max / p95 of “open-ish” work items per `actor_id` (define “open-ish” using existing `WorkItem.status` / `closed_at` rules already in codebase for execution types).
3. `**actor_consistency**` — boolean or enum: same `actor_id` appears in ≥2 of: discussion-derived items, execution items (issue/PR), ownership fields (define precise sets from existing work item types).
4. `**unknown_actor_ratio**` — `unmapped_participant_events / total_participant_events` (define denominator from `participants` list length + owner presence).

### 4.3 Backward compatibility for signals

- Keep existing signal fields **unchanged in meaning** for one release where possible.
- Add **new keys** under `SignalsV0Debug.explain` or new top-level optional fields (contract decision) — document migration for consumers.

**Exit criteria:** golden tests: given fixture with **same human** mapped to one actor across tools, `actor_fragmentation` **drops** vs string-based cardinality; with unmapped fixtures, `unknown_actor_ratio` rises.

---

## STEP 5 — Upgrade `detect_execution_situations` (additive rules)

**Objective:** new situations driven by actor signals; **existing situations remain**.

### 5.1 New situation types (names from prompt; finalize enums in contracts)

- `OWNERSHIP_FRAGMENTED` — driven by `actor_fragmentation` threshold + existing gap context.
- `NO_ACCOUNTABLE_OWNER` — no mapped owner actor on execution-type items in cluster (define “execution items” = existing `_EXEC_TYPES` logic).
- `KEY_PERSON_BOTTLENECK` — `actor_load` concentration threshold (e.g. one actor > X% of load).
- `DECISION_NOT_CONNECTED_TO_OWNER` — decision evidence neighborhood lacks execution-owner `actor_id` (requires tying “decision” evidence to work items — document dependency on evidence kinds).
- `UNKNOWN_OWNERSHIP` — `unknown_actor_ratio` high **and** ownership pressure signals present.

### 5.2 Ordering / caps

- Reuse existing merge/cap/narrative pipeline; new situations must participate in **same** `MIN_SITUATIONS` / `MAX_SITUATIONS_RETURNED` discipline.
- Add tests: when actor data absent, **new situations do not fire** (or fire only `UNKNOWN_OWNERSHIP` per policy — document).

**Exit criteria:** fetch-debug shows **new situation types** in engine output when fixtures map actors; with resolver off, output **matches** pre-change situation sets.

---

## STEP 6 — Keep gaps and graph unchanged

**Explicit invariants:**

- `compute_gaps`, `link_work_items`, `build_execution_graph`: **no behavioral changes** except consuming **unchanged** `WorkItem.id` graph.
- No requirement that gaps reference `actor_id`.

**Optional later (out of scope for this doc):** “ownerless gap” copy may **reference** actor display for human text — still not a graph change.

---

## STEP 7 — Admin UI (minimal)

**Objective:** people chips / scope / collaboration displays prefer actor-backed labels when present.

### 7.1 Dedupe

- Primary set key: `actor_id` when present on the underlying work items in scope.
- Fallback: existing `ownerFirstToken` string dedupe **only** for entries with `actor_id == null` (must be visually distinguishable in debug if needed).

### 7.2 Display

- Prefer `Actor.display_name` (from lightweight join in API response **or** embed `owner_display` snapshot on `WorkItem` if fetch-debug must stay self-contained — decision recorded in implementation).
- Fallback to string `owner` / `participants` values.

**Exit criteria:** same multi-tool user appears **once** in UI counts when mapped; unmapped path identical to current UI.

---

## STEP 8 — Backward compatibility checklist

- All existing pytest suites green without updating assertions (except snapshots explicitly renewed).
- `WorkItem` JSON: old clients **ignore** new fields; new clients read optional fields.
- `DecisionBundle` / `compute_decisions` outputs unchanged when actor resolver disabled (feature flag env default **off** in prod until validated).
- Fetch-debug response size regression documented (new payload keys).

---

## STEP 9 — Explicit non-goals

- No LLM-based identity matching.
- No fuzzy / Levenshtein name merge.
- No removal of `owner` / `participants` / string `source_ref`.
- No wholesale pipeline rewrite — only additive modules + localized edits in named steps.

---

## Rollout flags (recommended)

- `VECTOR_MANAGER_INSIGHTS_ACTOR_RESOLUTION=0|1` — Step 2+
- `VECTOR_MANAGER_INSIGHTS_ACTOR_SIGNALS=0|1` — Step 4+
- `VECTOR_MANAGER_INSIGHTS_ACTOR_SITUATIONS=0|1` — Step 5+

Defaults **off** until each phase is verified in fetch-debug on internal tenants.

---

## Success criteria (acceptance)

1. **Same human, multiple tools → one `actor_id`** in `WorkItem` fields when external ids exist and canonical mapping succeeds.
2. **Signals:** cross-tool double counting **eliminated** in actor-based metrics; legacy string metrics remain available or frozen per policy.
3. **Situations:** new actor-backed situations appear in **fetch-debug** (`decisions` / `decision_debug`) under flag.
4. **Zero behavior change** when actor fields are absent **and** flags off.

---

## Verification playbook (after each phase)

1. Run fetch-debug for a tenant with mock connectors + one real tenant class.
2. Diff `fetch.*.payload.sampled_`* for Step 1.
3. Diff `work_items.items[]` for new optional fields (Step 2).
4. Assert `signals.explain` (or chosen location) for new keys (Step 4).
5. Assert `execution_situation` cardinality / new types (Step 5).
6. Spot-check admin scope line participant count (Step 7).

---

## Open decisions (record before coding)

1. **Participant / actor list alignment:** index-locked parallel lists vs array of `{label, actor_id|null}` objects — affects contract stability.
2. **Canonical key format:** must match `ActorExternalIdentity` upsert used elsewhere to avoid duplicate actors.
3. **Slack thread model:** single `participants` entry today — whether Step 1 needs extra API to enumerate thread authors (likely **out of initial scope**).
4. **Where resolver runs in serverless / worker contexts:** DB session availability in `build_work_items` call chain (fetch-debug vs batch jobs).

---

## Document history

- **2026-05-03:** Initial phased plan from product prompt (planning only).

