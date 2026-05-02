# Manager Insights — VO → Coordination Transition & Implementation Plan

## Which document to follow (progression)


| If you are…                                                                                      | Follow this file                                                                                                                                    |
| ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deciding **product intent** and report vocabulary (language safety, gap types, signal meaning)   | [manager_insights_vo.md](manager_insights_vo.md) — **reference**, not the execution checklist.                                                      |
| Auditing **what the V0 report pipeline already shipped** (steps 0–8, admin fetch-debug, tests)   | [manager_insights_implementation_plan.md](manager_insights_implementation_plan.md) — **§ Implementation status (living)** table + admin milestones. |
| Designing **where the product is going** (decisions, actions, graph, outcomes, no LLM in Decide) | [manager_insights_coordination_plan.md](manager_insights_coordination_plan.md) — **target architecture**.                                           |
| **Executing the next engineering work** from current `main` → coordination                       | **This file** — **§6** (`S01`–`S13`) + **§8** (admin after each step). Update **Status** cells here as you ship.                                    |


**Important:** [manager_insights_implementation_plan.md](manager_insights_implementation_plan.md) describes **Step 7 = Interpretations** and **Step 8 = Insights** as core runtime steps. [manager_insights_coordination_plan.md](manager_insights_coordination_plan.md) reuses numbers differently (**Step 7 = Decision engine**, **Step 8 = Action layer**). When planning coordination work, **ignore step numbers in the old implementation plan** for “what comes next”; use **this file’s `S01`–`S13`** and the coordination plan’s glossary instead.

---

**Canonical references**


| Document                                                                                         | Role                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [manager_insights_vo.md](manager_insights_vo.md)                                                 | Original **user-report** shape: `UserReportContext`, `SignalsV0`, evidence kinds, gap types, optional `InterpretationsV0` / `InsightsV0` / `ReportV0`, Slack report narrative, coaching, “one priority”. |
| [manager_insights_implementation_plan.md](manager_insights_implementation_plan.md)               | **V0 report pipeline** plan + **living status** (through admin Step 8 today); remaining items **Step 9+** (rendering, Slack delivery, arbitration, orchestration, persisted snapshots per that doc).     |
| [manager_insights_coordination_plan.md](manager_insights_coordination_plan.md)                   | Target **coordination** system: **Perceive → … → Act → Learn**, `DecisionItem`, Action Layer, ephemeral `ExecutionGraph`, `OutcomeItem`, no LLM in Decide/Act.                                           |
| [manager_insights_master_implementation_plan.md](manager_insights_master_implementation_plan.md) | **Single execution checklist** (`M-001`–`M-026`): API + admin + DB per narrow step; merges VO + coordination + transition + baseline.                                                                    |


**Status column (for this file):** use `—` until shipped; set to `done` or a short `missing: …` note. Update in place; do not duplicate the coordination plan’s full spec here.

**Admin:** The [coordination plan](manager_insights_coordination_plan.md) did not originally spell out **admin** surfaces. **§8** below is the **intended** way to try each build step: extend the same **debug** API and **Manager insight** admin page (or add small companion routes) so every slice is shippable and **manually verifiable** before Slack/prod.

---

## 1. Direction: what is changing

- **From:** a **report-first** product (ingest → deterministic facts → **optional** LLM narrative insights → Slack report sections).
- **To:** a **decision-first** product (same ingest + richer **perception** + same deterministic **detect** layer → **DecisionItem** → **human-in-the-loop act** → **outcomes**; narrative reports **optional** / secondary).

The [coordination plan](manager_insights_coordination_plan.md) is the **target architecture**. This file is the **migration and build order** from the VO mental model and existing code paths.

---

## 2. What to keep (conceptual + technical)


| Item                                  | Notes                                                                                                                                                                               |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Connectors + caps + time window**   | VO’s `FetchActivity` scope (Slack, GitHub, Linear, Notion, calls) stays; tenant-scoped fetches as implemented.                                                                      |
| `**WorkItem` as atom**                | id, type, text, status, project, source—VO §2; remains source of truth for graph nodes.                                                                                             |
| **Four base gap types**               | `expected_not_executed`, `discussed_not_linked_to_work`, `blocker_not_tracked`, `doc_not_connected_to_execution` (VO §5) — same predicates; may gain **traversal** helpers (graph). |
| **Semantic links**                    | VO §3; `high` / `medium` / `low` semantics feed links + 4.5 `references` reinforcement.                                                                                             |
| **Deterministic `SignalsV0` family**  | VO’s signal list (delivery, urgency, expectation, follow-through, etc.) **evolves** (new ambiguity/churn fields) but **stays** non-LLM, formula-driven.                             |
| **Key achievements + raw highlights** | VO §6–7; same steps (5.5 / 5.6) with possible inputs from new perception fields.                                                                                                    |
| **Evidence = grounded spans**         | VO: discard without evidence. Coordination: **tighten** with LLM perception + same validator idea.                                                                                  |
| **Language safety**                   | VO “not found in tracked systems” / avoid blame — keep in all user-facing copy (Slack, templates).                                                                                  |
| **Quote verification discipline**     | Existing manager-insights validation culture maps to [coordination plan §4](manager_insights_coordination_plan.md#4-validation-layer-step-3).                                       |


---

## 3. What to change (explicit deltas)


| VO / current                                           | Target (coordination plan)                                                                                                                                                           |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| “Evidence extraction” = regex-first                    | **Step 3: execution state perception** (LLM + validation): state, transitions, deps, commitment, **risk/ambiguity classes**, **ownership** only span-grounded.                       |
| Insights / interpretations = core delivery             | **Off-path by default**; do **not** block **Decision** pipeline.                                                                                                                     |
| `ReportV0` / `UserReportContext` as the shipped object | **Primary** shipped objects become `**DecisionItem`**, then optional **report** derived from same bundles.                                                                           |
| Slack = long report (sections)                         | Slack = **decision** messages (approve / modify / ignore) + **receipts**; [coordination plan §5](manager_insights_coordination_plan.md#5-slack--api-delivery).                       |
| Gaps only → text insights                              | Gaps + signals → **rule-mapped** `decision_type` (see [coordination plan §3](manager_insights_coordination_plan.md#3-gap--decision-mapping-base)).                                   |
| Stateless runs only                                    | **10.5** `DecisionItem` + **10.6** `OutcomeItem` for continuity and **deterministic** policy learning.                                                                               |
| Link-only geometry                                     | **4.5** in-memory **ExecutionGraph** (not persisted) for optional gap/decision **context** [coordination plan §2.3](manager_insights_coordination_plan.md).                          |
| Priority = narrative “one priority” in report          | **7.5** per-decision **rank** + `max_decisions_surfaced` (e.g. 3) — no decision clustering in V1.                                                                                    |
| N/A                                                    | `**HOLD_START` guards** (high ambiguity, no recent decision evidence in cluster, affected WI count above threshold) — [coordination plan §3](manager_insights_coordination_plan.md). |


---

## 4. What to remove or demote (product + code paths)


| Remove / demote                                                                  | Replacement                                                                                                       |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **LLM in the “insight is the product”** posture                                  | **Primary** value = **Decisions** + **outcomes**; keep insight LLM **behind flag** for narrative only.            |
| **ReportV0 as the must-build blocking milestone**                                | ship **Debug/API JSON** of decisions first; `ReportV0` later if still needed.                                     |
| **Interpreting “InsightsV0 examples 1–10” as a checklist to implement verbatim** | Map themes to **decision types** and **copy templates**; not one LLM card per example.                            |
| **Coaching questions + “One Priority” as required Slack fields**                 | Optional in narrative mode; not required in **decision** mode.                                                    |
| **Persistence of 4.5 graph** (if ever assumed)                                   | Explicit: **ephemeral** only until a future phase [coordination plan 4.5](manager_insights_coordination_plan.md). |
| **Decision grouping / clustering in V1**                                         | Explicitly out — [coordination plan 7.5](manager_insights_coordination_plan.md).                                  |


---

## 5. What to do (phased execution order)

Build **top-to-bottom** in this file’s **Step tracker**; each **Step** is one shippable slice (E2E verifiable) with a single “done when” so you can mark it **done** without cross-dependencies mid-slice.

**Dependency graph (simplified):**

`S01 → S02 → S03 → (S04 ∥ S05) → S06 → S07 → S08 → S09 → S10 → S11 → S12*`

*S12 can start after S08 if outcomes-only stub exists.*

---

## 6. Step-by-step implementation tracker (mark done here)

> **How to use:** set **Status** to `done` when **Done when** is satisfied. Add **Missing / next** (one line) if blocked. Pair each row with **§8.3** so **admin** and `**fetch-debug`** stay in sync with implementation.

> **Admin-complete:** same as §8.4 — you can validate the step from **Admin → Manager insight** (or listed companion routes) without Slack.


| Step    | Scope                                | Work (technical)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Done when                                                                                       | Status |
| ------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------ |
| **S01** | Contracts for coordination           | Add or extend Pydantic models: `DecisionItem` (v1), `DecisionBundle`, optional `OutcomeItem` stub, `decision_type` / status enums. Align names with [coordination plan 2.5](manager_insights_coordination_plan.md) without breaking existing `WorkItem` / `GapBundle` / `SignalsV0` contracts.                                                                                                                                                                                                                                                                                                | Types merge cleanly; `pytest` (contract tests) green; no runtime change to pipeline default.    | —      |
| **S02** | Step 3 schema (perception)           | Extend `EvidenceItem` (or parallel “perception row” type) for: `ambiguity_class`, optional `state_transition`, dependency refs, `risk` kind—**all** behind a **feature flag**; keep **regex** path for fallback.                                                                                                                                                                                                                                                                                                                                                                              | Flag off = current behavior; flag on = schema accepts new fields; validator strip invalid rows. | —      |
| **S03** | Perception LLM (minimal)             | Implement **one** LLM call path (batch WIs) producing JSON; wire **Step 3 validation** (schema + substring quote) from [coordination plan §4](manager_insights_coordination_plan.md). Perception output may **extend** `EvidenceItem` **or** be represented as a **parallel** validated structure (e.g. `PerceptionItem` rows) so core evidence types are not overloaded with state, dependencies, ambiguity classes, and transitions. **Steps 4–6 must consume only** a **normalized, validated** structure—never raw LLM JSON—keeping downstream independent of prompt/serialization shape. | E2E test: same fixture → validated rows; regex fallback on forced failure.                      | —      |
| **S04** | **Step 4.5** `ExecutionGraph`        | In-memory only: `ExecutionNode` / `ExecutionEdge` from Step 2 + 3 + 4; no DB; ** unit tests** for merge rules + priority. **Unresolved dependencies:** refs that cannot be resolved to existing `WorkItem` ids are stored as **unresolved references** only; they **must not** be turned into `ExecutionEdge`s that participate in deterministic graph traversal used by Steps **5–7** (prevents invalid edges and skewed gap/decision context).                                                                                                                                              | Graph built in `fetch-debug` or test harness; **not** persisted.                                | —      |
| **S05** | Gaps + graph (optional)              | **Light** use: where `compute_gaps` already uses neighbor logic, allow optional **1-hop** lookup via graph; **no** new gap types required to ship S05.                                                                                                                                                                                                                                                                                                                                                                                                                                        | Deterministic tests: with/without graph flag same for baseline gaps.                            | —      |
| **S06** | Signals extension                    | Add `scope_ambiguity` / `discussion_churn` / `contradiction_density` (or names in plan) as **code-owned** formulas from Step 3+6 inputs.                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `SignalsV0` (or debug bundle) includes new keys + `explain` strings.                            | —      |
| **S07** | **Step 7** Decision engine           | **Rule table only:** map `GapType` + pointers → `DecisionItem` (no `HOLD_START` until S08 unless stubbed). **Inputs:** **primary** = `GapBundle`; **supporting context** = `WorkItemBundle`, `LinkBundle`, validated perception output (normalized Step 3), and deterministic `SignalsV0`. **Optional (debug / admin only):** emit `decision_debug` per decision (`gap_id`, `matched_rule`, `conditions_met`) for `fetch-debug` and rule validation—not required for production Slack payloads.                                                                                               | `fetch-debug` (or admin route) returns `decisions: [...]` in JSON.                              | —      |
| **S08** | Extension decisions + **HOLD_START** | Implement [coordination plan §3](manager_insights_coordination_plan.md) **extension** rows: `HOLD_START` (with **all** three guards: ambiguity high, no recent decision **evidence** in cluster, **affected WI count** above configurable threshold), `CLARIFY_SPEC`, `RECENTER` / `PAUSE` as spec’d.                                                                                                                                                                                                                                                                                         | Integration test: threshold toggles emit/suppress `HOLD_START`.                                 | —      |
| **S09** | **Step 7.5** prioritization          | Sort **per decision**; apply `max_decisions_surfaced` (default **3**); **no** grouping/clusters. Outcome **tie-break** stub (pass-through) OK. Preserve optional `**decision_debug`** from S07 on ranked rows for admin visibility only (same non-production contract as S07).                                                                                                                                                                                                                                                                                                                | Order stable; cap enforced; tests.                                                              | —      |
| **S10** | **10.5** Persistence                 | DB tables (or existing store) for `DecisionItem` lifecycle, `run_id`, `tenant_id`, dedupe key; API **read** decisions.                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | After run, list decisions via API; survives process restart.                                    | —      |
| **S11** | **Step 8** Action (one connector)    | One **write** path: e.g. “post Slack thread / comment” or **one** of Linear create-issue—behind feature flag; idempotent.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | `Approve` in Slack → one external effect + `receipt` on decision row.                           | —      |
| **S12** | **10.6** Outcomes                    | `OutcomeItem` **write**; evaluation job: dismiss / `false_positive` / `ground_truth` booleans; **no** ML—**policy** counters only.                                                                                                                                                                                                                                                                                                                                                                                                                                                            | Dismiss flow increments suppression counter used in 7.5; doc’d formula.                         | —      |
| **S13** | Narrative (optional)                 | If still needed: wire **optional** `Interpretations` / `Insights` after Step 6 **only** for admin/report; **not** in default Slack path.                                                                                                                                                                                                                                                                                                                                                                                                                                                      | Feature flag; decisions unchanged when on/off.                                                  | —      |


---

## 7. Map: VO report sections → coordination artifacts


| VO / [manager_insights_vo.md](manager_insights_vo.md) | Coordination plan artifact                                                                               |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Delivery metrics                                      | Still **Step 0–2 + signals**; not the primary Slack payload.                                             |
| **Gaps (§5)**                                         | **Input** to **Step 7**; base table unchanged.                                                           |
| **Insights 1–10 (examples)**                          | Informs **template copy** for `DecisionItem.rationale` / `title` — not a 1:1 “insight step” in pipeline. |
| **Coaching questions / One priority**                 | **Demoted**; may appear in optional report or `CLARIFY_SPEC` follow-up copy.                             |
| `InterpretationsV0`                                   | Optional narrative; **not** the coordination loop.                                                       |
| `ReportV0` / LLM prompt at VO end                     | Optional **synthesis** over same bundles; **not** before **Decide**.                                     |


---

## 8. Admin & API verification (try each step)

### 8.1 What exists today


| Piece            | Location                                                                                                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **HTTP**         | `GET /admin/tenants/{tenant_id}/manager-insight/fetch-debug?window_days=…` (see `backend/.../routes/admin.py`).                                                             |
| **Orchestrator** | `run_manager_insights_fetch_debug` — runs Step **1 → 0.5 → 2 → 3 (regex evidence) → 4 → 5 → 5.5 → 5.6 → 6 → 7 (interpretations) → 8 (insights)**; returns one JSON payload. |
| **UI**           | `frontend/src/admin/AdminTenantManagerInsightPage.tsx` — “Run Step 1 → … → 8” button; renders sections for each bundle.                                                     |


There is **no** admin section yet for: **LLM perception**, **execution graph**, **DecisionItem**, **prioritization cap**, **persistence**, **apply**, or **outcomes**.

### 8.2 Rule for the transition

For each tracker step **S01–S13** that changes behavior or adds artifacts:

1. **Prefer** extending `**ManagerInsightFetchDebugResponse`** (and the admin page types) so **one run** still shows the full trace—new blocks appear as additional top-level keys or nested debug structs.
2. **Optional query params** (e.g. `include_graph=1`, `skip_insights=1`, `max_decisions=3`) are acceptable to keep payloads small and to match the **coordination** ordering when narrative steps are demoted.
3. **Persistence (S10+)**: add **dedicated admin GETs** (list decisions / outcomes for tenant) when state is no longer only in the debug response; the debug run can still return `**decision_ids`** or `**dry_run_decisions`** for correlation.

### 8.3 Step → backend → admin (expected delta)


| Step        | Backend (minimum)                                                                                                                                                                                                                                                                                             | Admin UI (minimum)                                                                                                         |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **S01**     | Pydantic models for `DecisionItem` / bundles; may be empty arrays in debug response.                                                                                                                                                                                                                          | Types updated; optional empty **Decisions** section.                                                                       |
| **S02–S03** | Replace or branch Step 3: perception output merged into `evidence` or `**perception`** + `**rejected_perception_rows`** in debug.                                                                                                                                                                             | Section **Step 3 — Perception**: show rejects count, toggle “regex vs LLM” if both exist.                                  |
| **S04**     | Build graph after links; attach `**execution_graph`** `{ nodes[], edges[] }` to debug response only. Traversable edges **exclude** unresolved dependency refs (those live outside the edge list or in an explicit `**unresolved_dependency_refs`** (or equivalent) debug field—never as fake WorkItem links). | Section **Step 4.5 — Execution graph** (table or JSON tree).                                                               |
| **S05**     | Optional `**gap_debug`** metadata (e.g. `graph_traversal_used`) if behavior differs.                                                                                                                                                                                                                          | One-line note under **Gaps** when flag on.                                                                                 |
| **S06**     | Extend `signals` object / `explain` for new keys.                                                                                                                                                                                                                                                             | Render new signal rows in existing **Signals** block.                                                                      |
| **S07**     | Append `**decisions`** `{ items: DecisionItem[], … }` from rule engine (no DB required). Optionally include `**decision_debug`** (`gap_id`, `matched_rule`, `conditions_met`) per item for admin rule tracing only.                                                                                           | **Decisions (Step 7)** section: table of `decision_type`, `gap_id`, `title`; optional expand row for `**decision_debug`**. |
| **S08**     | Same payload; `**HOLD_START`** rows appear only when guards pass; optional `**decision_emission_debug`** per row.                                                                                                                                                                                             | Filter or badge by type; expand row to show guard booleans.                                                                |
| **S09**     | Return `**decisions_prioritized`** (ordered list) + applied `**max_decisions_surfaced`**; expose cap via query param; carry through `**decision_debug`** when present (admin-only).                                                                                                                           | Show **rank** column + “cap = N” in header; optional `**decision_debug`** column or drill-down.                            |
| **S10**     | **New** `GET /admin/tenants/{id}/manager-insight/decisions` (list) + optional `POST` replay; debug run may **write** then return ids.                                                                                                                                                                         | **Persisted decisions** table + link from debug `run_id`.                                                                  |
| **S11**     | **New** `POST …/decisions/{id}/apply` (admin-only, gated) or Slack test hook; return receipt in response.                                                                                                                                                                                                     | Button **Apply (dry-run / live)** with confirmation + receipt panel.                                                       |
| **S12**     | **New** `GET …/outcomes` or embed recent outcomes on decision row; evaluation job writes rows.                                                                                                                                                                                                                | **Outcomes** tab: `false_positive`, `outcome_type`, timestamps.                                                            |
| **S13**     | `skip_interpretations=1` / `skip_insights=1` default or flag; narrative sections collapse.                                                                                                                                                                                                                    | Toggles to hide legacy Step 7/8 panels when coordination-only.                                                             |


### 8.4 “Done when” for admin

A tracker step is **admin-complete** when: a developer can **open the admin Manager insight page** (or the new list endpoints), perform the **primary action** for that step, and **see the expected structured output** without relying on Slack or production tenants-only flows.

---

## 9. Risks and mitigations (execution)


| Risk                             | Mitigation                                                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Scope creep** on graph         | **4.5** stays **in-memory** until S12+; no DB table for graph in S04–S10.                                                 |
| **Over-triggering** `HOLD_START` | [coordination plan](manager_insights_coordination_plan.md) **explicit emission rule**; integration tests with thresholds. |
| **LLM regression** on Step 3     | Feature flag + regex **fallback**; keep golden fixtures.                                                                  |
| **Slack report users confused**  | Product comms: **decisions** replace “report” as the default surface; long report = optional.                             |


### Quick checklist (mirror of §6)

- **S01** — Contracts (`DecisionItem`, bundles, enums)
- **S02** — Perception schema + flag + fallback compatibility
- **S03** — LLM perception path + quote validation
- **S04** — Ephemeral `ExecutionGraph` (4.5)
- **S05** — Gaps optionally use graph traversal (light)
- **S06** — Extended ambiguity/churn/contradiction signals
- **S07** — Decision engine (base gap → decision mapping)
- **S08** — Extension decisions + `HOLD_START` guards
- **S09** — Step 7.5 prioritization + cap (no clustering)
- **S10** — Decision persistence (10.5)
- **S11** — Action layer (one connector / Slack receipt)
- **S12** — Outcome tracking (10.6)
- **S13** — Optional narrative (insights/report) behind flag

---

## 10. Definition of “transition complete” (program-level)

- **Default** tenant path: fetch → **perception (validated)** → links → **graph (ephemeral)** → gaps → **signals (extended)** → **decisions (capped)** → **persisted** → Slack shows **decisions**, not a long `ReportV0` block.
- `Insights` / `ReportV0` / coaching **disabled by default** or feature-flagged without blocking the decision queue.
- **Outcome** path live for dismiss / `false_positive` and **7.5** nudge.
- [manager_insights_vo.md](manager_insights_vo.md) retained as **reference** for language and **optional** report shape; [manager_insights_coordination_plan.md](manager_insights_coordination_plan.md) is the **source of truth** for architecture.

---

*End of transition plan.*