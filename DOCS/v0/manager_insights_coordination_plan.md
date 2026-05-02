# Manager Insights — Coordination System Implementation Plan

**Product intent:** Manager Insights is a **system that keeps execution moving**—it surfaces when work is stuck, unclear, or not tied to trackable output, and drives **verifiable next steps** (human-approved first). Analysis exists to **unblock flow**, not to deliver commentary for its own sake.

The engine is **hybrid**: a **perception** stage interprets language into **validated structure**; everything downstream—linking, gaps, signals, decisions, actions, learning—is **deterministic and auditable**.

---

## Execution loop

End-to-end behavior: **Perceive → Structure → Detect → Decide → Act → Learn.**


| Stage         | Meaning                                                                                                                                                  | System locus                   |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **Perceive**  | Turn raw work-item text and thread context into **grounded** execution state and intent (states, dependencies, strength of commitment, risk, ambiguity). | Step 3 + validation            |
| **Structure** | Build comparable objects: work items, perceived rows, **links**, and an **ephemeral execution graph** for reasoning.                                     | Steps 2, 3 (validated), 4, 4.5 |
| **Detect**    | Apply fixed predicates: **gaps**, **achievements**, **highlights**, **signals** (incl. churn/contradiction aggregates).                                  | Steps 5, 5.5, 5.6, 6           |
| **Decide**    | Map gaps/signals to **decision items**; rank and cap.                                                                                                    | Steps 7, 7.5                   |
| **Act**       | Execute approved changes via connectors; record receipts.                                                                                                | Step 8                         |
| **Learn**     | Record **outcomes**; adjust **rule weights, caps, and suppressions** from observed success/false positives—**without** model retraining.                 | Step 10.6                      |


**Invariant:** only **Perceive** uses an LLM proposal path; **Decide** and **Learn** stay rule- and data-driven.

---

## 1. Architecture layers

### Execution model (Steps 0–6)

- **0–2, 0.5:** Connectors, reliability, `WorkItemBundle`.
- **3 — Execution state perception (LLM-assisted):** Reconstructs **what is happening in execution** from messy language, not a keyword bag (see §2.1). Output = validated rows + optional state/dependency/ownership fields, all quote-grounded.
- **4–4.5, 5–6:** Deterministic. No model calls; inputs = validated Step 3 output + work items + links (+ **4.5** graph from those artifacts).

**Boundary:** *Perception* proposes; *validation* defines what the rest of the system may use.

### Perception validation (within Step 3)

- Schema, substring verification, rejection list, optional regex fallback. Invalid rows **never** reach Step 4.

### Decision (Steps 7, 7.5)

- **No LLM.** Gaps + deterministic signals + rule tables → `DecisionItem` fields; prioritization is code + stored policy, not model logits.

### Action (Step 8)

- **No LLM.** Slack/API in → adapter out → receipt on `DecisionItem`.

### Delivery (Slack / API)

- Surface **decisions** and **outcomes** notifications where policy requires; no dashboard-first UX.

### Outcome & learning (Step 10.6)

- **No ML training.** Consumes `OutcomeItem` rows + persistence; updates **versioned, deterministic** knobs (see §2.2).

---

## 2. Step pipeline (canonical)

### 2.0 Steps 0–2, 0.5


| Step | Output (summary)              |
| ---- | ----------------------------- |
| 0    | Tenant, window, feature flags |
| 1    | `FetchActivityBundle`         |
| 0.5  | Data reliability report       |
| 2    | `WorkItemBundle`              |


### 2.1 Step 3 — **Execution state perception (LLM-assisted)** 【CRITICAL】

**Objective:** **Execution state reconstruction**, not “evidence extraction” as an end in itself. The model infers **what is happening in the work**—progress, blockers, commitments, ownership, and ambiguity—from messy natural language; validated structure feeds Steps 4–6.

**Why this is not “keyword extraction”**

- Coordination uses **implicature, timeline, and negation** (blocked vs venting), **shifting ownership**, and **soft vs hard** commitments. The LLM **proposes** an interpretation of **execution intent and state**; only **substring-grounded** fields become facts downstream.

**Structured outputs (extend `EvidenceItem` and related types)**

- **Kinds (evidence row tags):** `action_item`, `blocker`, `decision`, `risk`, `ambiguity`, and optional `ownership_hint`.
- **State / transitions:** attach **execution state** labels with quotes: `not_started` | `in_progress` | `blocked` | `waiting` | `done` (synonyms like **started** map to `in_progress` in schema normalization). Optional `**state_transition`** objects `{ from_state?, to_state, quote }` when the text explicitly indicates movement (e.g. “unblocked now,” “handed off to …”)—each leg **quote-backed**; validator drops underspecified transitions.
- **Dependencies:** `waits_on` / `blocked_by` — each edge **to a string mention** in source text (e.g. “waiting on @legal”) or to a resolvable in-text reference; no silent graph to external owners without span.
- **Commitment strength:** `weak` | `medium` | `strong` (or numeric bucket promoted in Step 6) — from hedging, deadlines, and assignee clarity in the same quoted neighborhood; still **dropped** if not grounded; **never** fed to decision rules as raw model score unless mapped through Step 6 **tiers** by fixed thresholds.
- **Ambiguity (expanded):** each `ambiguity` row carries `ambiguity_class` ∈ { `unclear_scope`, `discussion_loop`, `contradiction` } (extensible), each with a **separate** verbatim quote.  
  - **unclear scope:** in/out, boundaries, or success criteria unset.  
  - **discussion_loop:** topic recurs without closure (may combine with **deterministic** reply-count/age in Step 6 for tiering).  
  - **contradiction:** two stances in same work item (or thread slice) with conflicting commitments/owners/ship dates—**two** quotes + machine-checkable `contradiction_pair_id`.
- **Ownership:** **inference** is allowed in output **only** when the model **maps an inferred role to a substring** (name, @handle, team) present in the same work item. Validator rejects “owner = Alice” with no “Alice” span. *Explicit mentions* + *role + quoted span* live in one structured field (e.g. `ownership_inferred: { text_span, role_guess? }`).

**Strict constraints (unchanged in spirit)**

1. Every semantic claim used downstream must have a **contiguous** quote in parent work item text (normalization as defined in validator).
2. Rejections logged; no rows leak to Step 4 without passing.
3. **No** invented ticket numbers, dates, or external ids.

**Implementation:** Batched LLM calls, JSON schema, merge/dedupe, optional **regex** as hints. Fallback policy may strip `risk` / `ambiguity` / dependency columns if the model is unavailable.

### 2.2 Step 10.6 — **Outcome tracking** (after persistence)

**Purpose:** Close the **Learn** part of the loop: record what happened when humans acted (or ignored) a decision, and feed **non-ML** policy updates.

`**OutcomeItem` (v1)**


| Field              | Type            | Description                                                                                                                                               |
| ------------------ | --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`               | `uuid`          |                                                                                                                                                           |
| `decision_id`      | `string`        | Required link                                                                                                                                             |
| `tenant_id`        | `uuid`          |                                                                                                                                                           |
| `observed_at`      | `datetime`      | When evaluation ran                                                                                                                                       |
| `outcome_type`     | enum            | `applied_success` · `applied_partial` · `apply_failed` · `dismissed` · `ignored` · `superseded`                                                           |
| `user_attribution` | optional        | e.g. Slack user id for dismiss/dismissed reason code                                                                                                      |
| `receipt`          | optional object | External ids, HTTP status, connector error (from Action Layer)                                                                                            |
| `false_positive`   | `bool?`         | Set when user or rule marks decision as misfire                                                                                                           |
| `ground_truth`     | object          | **Deterministic** follow-up: e.g. `gap_id_absent_in_next_run`, `work_item_moved_to_done`, `link_created` (each boolean or id checks from subsequent runs) |


**Evaluation (deterministic rules)**

- **When:** on a schedule (e.g. daily), after **apply** + grace period, or on manual replay—same rules everywhere.
- **What:** load `DecisionItem` + subsequent pipeline runs + connector-visible state. Check booleans in `ground_truth`: gap absent on next run, link/issue created, target `WorkItem` status/closure, receipt success.
- **Emit:** `OutcomeItem` with `outcome_type` / `false_positive`; **no** embedding updates, **no** weight tensors—tabular counters and thresholds only.

**Use of outcomes (deterministic feedback; not ML training)**

- **False positives:** increment counters per `gap_type` + `ambiguity_class` (if any) + connector; if rate exceeds threshold, **deprioritize** or **suppress** that class for a **policy window** (stored row, not model weights).
- **Prioritization (Step 7.5):** nudge order using **trailing false-positive rate** and **time-to-resolve** for similar decisions (sliding window; formula in config).
- **Rule improvement:** when **same** `gap_id` family repeatedly **fails** apply, open **playbook** ticket in engineering queue; when outcomes are strong, **lower friction** (e.g. allow auto-apply policy for that `decision_type`) — all **versioned, revertible** table changes.

### 2.3 Steps 4–6 (deterministic; incl. 4.5)


| Step | Output                                                                                                                                                                          |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4    | `LinkBundle` (semantic + ref links) — uses text + **validated** evidence sentences                                                                                              |
| 4.5  | `ExecutionGraph` — ephemeral derived graph (see **Step 4.5** below)                                                                                                             |
| 5    | `GapBundle` — predicates over work items, links, evidence; **may use graph traversal** where applicable; may **extend** with ambiguity-driven gaps (optional Phase)             |
| 5.5  | `KeyAchievementsBundle`                                                                                                                                                         |
| 5.6  | `RawHighlightsBundle`                                                                                                                                                           |
| 6    | `SignalsV0` + **extended** metrics: `coordination_risk`, `scope_ambiguity`, `discussion_churn`, `contradiction_density`, etc., each with `level` + `explain` (threshold tables) |


#### Step 4.5 — Execution graph construction

An `**ExecutionGraph`** is assembled **per pipeline run** from:

- `**WorkItemBundle` (Step 2)** — canonical ids and connector types for nodes.
- **Validated perception output (Step 3)** — **semantic structure**: execution state on items, `waits_on` / `blocked_by` (and related spans) mapped to edges where resolvable to node ids; optional `**owner_hint`** on nodes from perception (same grounding rules as Step 3).
- `**LinkBundle` (Step 4)** — **link reinforcement**: semantic/ref edges strengthen or add `**references`** (and similar) relationships between existing work-item nodes.

`**ExecutionNode`**


| Field        | Description                                                                                                                         |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `id`         | `WorkItem.id`                                                                                                                       |
| `type`       | `issue`                                                                                                                             |
| `state`      | From Step 3 perception for that item when present; otherwise derived only from deterministic work-item fields already on `WorkItem` |
| `owner_hint` | Optional; from validated perception, attached to the node                                                                           |


`**ExecutionEdge**`


| Field  | Description  |
| ------ | ------------ |
| `from` | Node id      |
| `to`   | Node id      |
| `type` | `depends_on` |


Edge `**type**` is assigned deterministically from Step 3 dependency labels + Step 4 link types (fixed merge rules in code). Conflicts resolve by **priority table**, not LLM.

**CRITICAL — graph is not persisted**

- The execution graph is **computed per run**, **not stored in the database**, and exists only as a **derived structure for reasoning** inside the pipeline (and in-memory debug dumps if enabled).
- **Source of truth** remains persisted `**WorkItem`** records, `**EvidenceItem`** (perception output as stored per product policy), `**DecisionItem**`, and `**OutcomeItem**` / decision lifecycle—not the graph.
- Omitting DB persistence **avoids premature schema lock-in**, allows **rapid iteration** on node/edge construction rules, and keeps rollback cheap. **Persistence of the graph may be introduced later** once the representation is stable and justified by query patterns.

**Step 6 (ambiguity + churn) — examples**

- **unclear scope:** count of `ambiguity_class=unclear_scope` in cluster / window.
- **discussion loop:** `ambiguity_class=discussion_loop` count + optional **mechanical** boost from reply depth / age of thread (connector metadata when available) — all **formulas in code**, not the LLM.
- **contradiction:** count of `contradiction` pairs; high tier if **and** no subsequent `decision` evidence row in same work item (deterministic time order).

Step **7** consumes these tiers **only** via §3 rule tables (optional **new** gaps in Step 5, e.g. `work_expanded_under_unresolved_spec`, `repeated_thread_without_link`—pure predicates on validated evidence + metadata).

**Product mapping (deterministic):** scope/loop/contradiction signals drive **do-not-start** and **spec-clarification** decisions—see §3 extension rows (`HOLD_START`, `CLARIFY_SPEC`, `RECENTER` / `PAUSE_INVESTMENT`). **No LLM** in Step 7.

### 2.4 Deprecate (narrative)

**Step 8** = Action Layer only. Optional narrative “insights/interpretations” and **arbitration of prose** are separate; they **do not** drive `DecisionItem`.


| Artifact                                                | Role                                              |
| ------------------------------------------------------- | ------------------------------------------------- |
| Optional narrative LLM (interpretations, insight cards) | **Off** by default; never gates decisions         |
| Narrative arbitration (merge/dedupe copy)               | **Off-path**; never arbitrates the decision queue |


### 2.5 Steps 7, 7.5, 8, 10.5

- **7** — `DecisionItem[]` from rule tables; inputs: `GapBundle`, `LinkBundle`, `WorkItemBundle`, **validated** `EvidenceBundle`, **deterministic** `SignalsV0` (Step 6), optional in-memory `**ExecutionGraph` (4.5)** for **graph context** (e.g. neighboring nodes, `depends_on` / `blocks` hops) when enriching rationale or default payloads—**fixed templates only; no LLM.**
- **7.5** — **Per-decision** ordering: each candidate decision is scored and sorted **individually**; `**max_decisions_surfaced`** caps output (default **3**, configurable). **V1:** no clustering, batching, or grouping of decisions—only a sorted list truncated by the cap. May use **outcome** aggregates from **10.6** (e.g. suppressions, trailing false-positive rate by `gap_type`) as tie-break inputs.
- **8** — apply path; connector writes; **no LLM.**
- **10.5** — persist `DecisionItem` (`proposed` → `accepted` / `dismissed` / … → `completed` / `failed`), `run_id` / `tenant_id`, optional Slack `channel_id` / `message_ts`, idempotency keys, audit fields; then **10.6** appends/updates `OutcomeItem` and policy.

`**DecisionItem` (v1)**


| Field             | Type             | Notes                                                                         |
| ----------------- | ---------------- | ----------------------------------------------------------------------------- |
| `id`              | `string` or UUID | Stable id; DB id after save                                                   |
| `gap_id`          | `string`         | Set when row came from a gap; optional if signal-only extension               |
| `gap_type`        | enum             | Mirrors `GapType` when applicable                                             |
| `decision_type`   | enum             | From rule tables in §3                                                        |
| `title`           | `string`         | Template string                                                               |
| `rationale`       | `string`         | Filled from gap + pointers (deterministic)                                    |
| `default_action`  | `object`         | `kind`, optional `connector`, `payload_template` — executed only in Step 8    |
| `required_inputs` | `object`         | Human/API fields to complete before apply                                     |
| `evidence_refs`   | `string[]`       | `EvidenceItem` / work item ids as applicable                                  |
| `signal_refs`     | `string[]`       | `SignalsV0` key names that influenced ordering only (tiers, not model scores) |
| `created_at`      | `datetime`       |                                                                               |
| `run_id`          | `uuid`           |                                                                               |


---

## 3. Gap → decision mapping (base)


| Gap type                         | Decision type              | Default action                   | Required inputs                                     |
| -------------------------------- | -------------------------- | -------------------------------- | --------------------------------------------------- |
| `expected_not_executed`          | `LINK_OR_CLOSE_COMMITMENT` | Create/link issue or close loop  | Target issue fields, optional `assignee_id`         |
| `discussed_not_linked_to_work`   | `THREAD_TO_TRACKING_LINK`  | Link thread/call to execution    | `execution_work_item_id`, `discussion_work_item_id` |
| `blocker_not_tracked`            | `BLOCKER_ESCALATION`       | Tracked issue + blocked / notify | Owner routing, `blocking_statement`                 |
| `doc_not_connected_to_execution` | `DOC_EXECUTION_BRIDGE`     | Link doc to issue/PR             | Document + execution ids                            |


**Extension rows (when optional gaps/signals are enabled)**


| Trigger (deterministic)                                            | Decision type                   | User-facing intent                                                                       | Default action                                                                                  |
| ------------------------------------------------------------------ | ------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `scope_ambiguity` tier **high** + open execution in cluster (§2.3) | `HOLD_START`                    | **Do not start** expanding tracked work (no new issues/PRs in cluster until spec exists) | Policy: block auto-create templates; comment + label “needs spec”                               |
| Same + doc/issue template available                                | `CLARIFY_SPEC`                  | **Spec clarification**                                                                   | Open/fill spec section (Notion/Linear/Wiki), post checklist comment, or schedule clarify thread |
| `contradiction` + `discussion_churn` high                          | `RECENTER` / `PAUSE_INVESTMENT` | Stop parallel conflicting pushes                                                         | Reconcile in thread; pause new tickets; templated comment                                       |


`**HOLD_START` — explicit emission rule:** This decision is only emitted when `**ambiguity_signal` is high**, **no recent `decision` evidence** exists in the same work item cluster, and the **number of affected work items exceeds a configurable threshold**. That guards against **over-triggering** and **blocking teams too early**.

**No LLM** in mapping tables.

---

## 4. Validation layer (Step 3)

1. **Schema** — Pydantic on LLM JSON.
2. **Quote** — every derived field must cite a substring of parent `WorkItem` text.
3. **Consistency** — `source_work_item_id` exists; `ambiguity_class` allowed; `contradiction` rows come in **pairs** or single row with two quote refs, per schema.
4. **Dedupe** — `normalized_quote_hash` + kind.
5. `**rejected_perception_rows`** — for observability only.

**Fallback:** may narrow to `action_item` / `blocker` / `decision` if API fails; state/ambiguity/dependency fields empty.

---

## 5. Slack / API delivery

- **Block messages:** decision title, decision type, gap/label, rationale, default action, evidence links, decision id, run id.  
- **Interactions:** Approve (modal/confirm) · Modify · Ignore (with `false_positive` path feeding **10.6**).  
- **Outcome pings (optional):** “Was this useful?” or auto-eval notice — writes `**OutcomeItem`**, not model.

**Admin debug (implementation):** Extend the admin `**fetch-debug`** response and **Manager insight** page (or add list routes for persisted decisions/outcomes) whenever a pipeline stage ships, so each step is verifiable without Slack. See [manager_insights_vo_to_coordination_transition.md §8](manager_insights_vo_to_coordination_transition.md#8-admin--api-verification-try-each-step). **Narrow step checklist (API + admin + DB):** [manager_insights_master_implementation_plan.md](manager_insights_master_implementation_plan.md).

---

## 6. Roadmap


| Phase | Scope                                                                                                                                                                                            |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1** | Step 3 execution-state perception + validation; Steps 4–6 incl. **4.5 ephemeral `ExecutionGraph`**; 7, 7.5, 10.5; Slack read-only; **10.6** minimal (dismiss/ignore + `false_positive` capture). |
| **2** | Action Layer + Linear/GitHub; receipts → **10.6** `ground_truth` population.                                                                                                                     |
| **3** | Auto-apply for **low-regret** `decision_type`s; governed by **outcome**-informed policy from **10.6**.                                                                                           |
| **4** | New ambiguity-driven gaps; stronger churn/contradiction signals; prioritization levers from **outcome** tables.                                                                                  |


---

## 7. Not in scope (current)

- **LLM** in Decision or Action (including ranking via model).  
- **Model fine-tuning / online learning** from `OutcomeItem` (explicitly: **no** ML training; policy tables only).  
- **Unsupervised** multi-app orchestration without human or policy gate.  
- **Strategic** org planning.  
- **Invented** or unquoted spans in gap/decision path.

---

## 8. Principles

1. **LLM for perception, not decision** — only Step 3 proposes; Steps 4–8 apply rules.
2. **Deterministic system owns truth, action, and learning knobs** — quotes + runs + `OutcomeItem` feed **versioned** rules, not ad hoc model judgment.
3. **All LLM outputs must be verifiable** — or discarded.
4. The **Execution loop** at the top of this document is the only macro control flow.
5. **Keep execution moving** over narrating it — decisions and outcomes beat commentary.
6. **Action > analysis**; **Continuous > one-off reports** (persistence + outcomes).

---

*End of plan.*