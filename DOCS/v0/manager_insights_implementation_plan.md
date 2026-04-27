# Manager insights — implementation plan (V0)

This document is the **step-by-step business + engineering plan** for implementing [Manager insights (V0)](./manager_insights_vo.md). It is meant to align with Vector’s direction: **frontier LLMs behind narrow interfaces**, a **structured work graph** (entities + relationships, not flat text dumps), **permissioned tool use** with least privilege, **RAG / retrieval grounded in real signals** with **citations back to sources**, **Slack-native human-in-the-loop** tone for user-visible output, and a **deterministic control plane** (typed APIs and pipelines; models only on scoped workflow stages).

---

# Execution Order (STRICT)

This pipeline has two types of steps:

* **Design-time steps (must exist before runtime)**
* **Runtime execution steps (executed per report)**

---

## Design-time (must be implemented first)

0. Step 0 — Contracts (Pydantic models, schemas)

---

## Runtime execution order (per report run)

1. Step 1 — FetchActivity
2. Step 0.5 — Data Reliability
3. Step 2 — WorkItems
4. Step 3 — Evidence
5. Step 4 — Links
6. Step 5 — Gaps
7. Step 5.5 — Key Achievements
8. Step 5.6 — Raw Highlights
9. Step 6 — Signals
10. Step 7 — Interpretations
11. Step 8 — Insights
12. Step 6.5 — Arbitration
13. Step 9 — Rendering
14. Step 10 — Slack Delivery
15. Step 11 — Assembly / Orchestration

Each runtime step **extends** the tenant **Admin → Manager insight** tab and persisted run snapshots per the [milestone checklist](#admin-per-step-milestones-required-checklist).

---

## Implementation status (living)

Update this table only when a step is truly complete against its own checklist and acceptance criteria.

| Step | Status | Completion gate |
| --- | --- | --- |
| Step 0 — Contracts | `completed` | Canonical Step-0 contract tree (`UserReportContext`, `SignalsV0`, `InterpretationV0`, `InsightV0`, `InsightArbitrationResult`, `ReportV0`, links/gaps/evidence bundles) exists in code with strict validation (`extra=forbid`) and round-trip JSON tests. |
| Step 1 — FetchActivity | `completed` | All target connectors implemented to the agreed V0 scope, metadata present, tests passing, and Admin tab checklist row fully satisfied. |
| Step 0.5 — Data reliability | `completed` | Deterministic tiers + reason codes + overall confidence aligned with defaults/config, tests passing, and Admin tab checklist row fully satisfied. |
| Step 2 — Normalization → WorkItems | `completed` | Deterministic `raw_* -> WorkItem` mapping from Step 1 payloads, stable IDs + timestamps + source/type fields, tests passing, and Manager insight tab renders Step 2 artifacts for QA. |
| Step 3 — Evidence extraction | `completed` | Deterministic extraction of `action_items` / `blockers` / `decisions` with strict non-empty evidence quotes, source references, and explicit discard tracking; Step 3 artifacts visible in Manager insight tab for QA. |
| Step 4 — Links | `completed` | Deterministic token-Jaccard (+ cross-source nudge + shared issue keys + optional Step-3 text hits) work-item `Link` edges with `confidence` + `evidence`; `high` only at/above published thresholds; tests; Manager insight tab shows Step 4. |
| Step 5 — Gaps | `completed` | Deterministic `Gap` computation from Step 2/3/4 artifacts (`expected_not_executed`, `discussed_not_linked_to_work`, `blocker_not_tracked`, `doc_not_connected_to_execution`) with evidence pointers; tests; Manager insight tab shows Step 5 artifacts. |
| Step 5.5 — Key achievements | `completed` | Deterministic closed/merged execution wins from `WorkItem` + optional doc/call reinforcement via medium+ `Link`s; `KeyAchievementItem` / `KeyAchievementsBundleDebug`; tests; admin tab section. |
| Step 5.6 — Raw highlights | `completed` | Deterministic factual highlight lines (repeated call/Slack terms, closed PRs, gap-backed lines) with `sources[]`; `RawHighlightItem` / `RawHighlightsBundleDebug`; tests; admin tab section. |
| Step 6 — Signals | `completed` | Deterministic `SignalsV0`-aligned computation (`delivery_strength`, `urgent_pressure`, coverage/follow-through/blocker visibility, repeated discussion flag, momentum, doc linkage, focus, collaboration/support/feedback/coordination/friction) with `explain` reasons; tests; admin tab section. |
| Step 7+ | `not_started` | Mark one-by-one as each step meets its own checklist and acceptance criteria. |

**Current note (2026-04-28):**

- Step 1 + Step 0.5 are wired in backend + admin surfaces, including tenant OAuth connect links for all five connectors (Slack, GitHub, Linear, Notion, Calls/Gemini).
- Step 1 now performs bounded-window activity probes per connector (Slack channel history samples, GitHub repo/PR/issue samples, Linear issues/projects window query, Notion edited-page search + users/me probe, Calls calendar + events samples) and emits `fetched_at`, window bounds, caps, errors, coverage stats, completeness stats, and payload summaries.
- Step 0.5 now consumes explicit per-connector coverage/completeness counters and applies deterministic threshold policy: coverage (>=80 / >=50 / <50), freshness (<24h / <72h / stale), critical-source gating, completeness downgrades, and exact overall confidence rule (critical-low override, >50% low override, >=80% high for overall-high).
- Step 1 + Step 0.5 tests are passing in `backend/tests/vector/domains/manager_insights/test_fetch_activity.py` and `backend/tests/vector/domains/manager_insights/test_data_reliability.py`.
- Step 2 is now implemented in `vector/domains/manager_insights/build_work_items.py` and exposed via the same admin debug endpoint/UI (`Manager insight` tab): each normalized work item is visible with source/type/status/timestamps and full JSON payload for QA.
- Step 2 tests are passing in `backend/tests/vector/domains/manager_insights/test_build_work_items.py`.
- Step 3 is now implemented in `vector/domains/manager_insights/extract_evidence.py` and exposed via the same admin debug endpoint/UI: extracted action items, blockers, and decisions are displayed with quote evidence and source work-item references.
- Step 3 tests are passing in `backend/tests/vector/domains/manager_insights/test_extract_evidence.py`.
- **Step 4 (semantic links)** is implemented in `vector/domains/manager_insights/link_work_items.py` (inputs: `WorkItemBundle` + optional `EvidenceBundle`). It produces `WorkItemLink` / `LinkBundle` in `vector/contracts/manager_insights_activity.py` with Jaccard thresholds `high≥0.40`, `medium≥0.24`, `low≥0.14` (plus a small cross-source bonus, shared ticket-key path `NEX-…` → `link_type=shared_reference`, and optional token hits from Step-3 snippets against the *other* work item). Pairs are bounded by sorting and at most 120 work items. Admin debug `GET /admin/tenants/…/manager-insight/fetch-debug` and **Manager insight** tab run **Step 1 → 0.5 → 2 → 3 → 4**; UI section **Semantic links (Step 4)**.
- Step 4 tests: `backend/tests/vector/domains/manager_insights/test_link_work_items.py`.
- **Step 0 canonical pass** is now implemented in `vector/contracts/manager_insights.py`: strict (`extra=forbid`) Pydantic models for `WorkItem`, `Link`, `ActionItem`/`Blocker`/`Decision`, `ExpectedWork`/`ActualWork`/`Gap`, `DeliveryMetrics`, `KeyAchievement`/`RawHighlight` bundles, full `SignalsV0` enums, `InterpretationV0`, `InsightV0`, `InsightArbitrationResult`, `ReportV0`, and `UserReportContext`; covered by `backend/tests/vector/contracts/test_manager_insights_contracts.py` (round-trip + unknown-field rejection + report cap check).
- **Step 5 (gaps)** is implemented in `vector/domains/manager_insights/compute_gaps.py` and wired into the debug pipeline and response contracts (`GapItem` / `GapBundle` in `vector/contracts/manager_insights_activity.py`). Current deterministic rules use medium/high links and Step-3 evidence to emit:
  - `expected_not_executed` (action item has no linked closed issue / merged PR),
  - `discussed_not_linked_to_work` (discussion evidence with no linked issue/PR),
  - `blocker_not_tracked` (blocker evidence with no linked issue/PR),
  - `doc_not_connected_to_execution` (document work item without medium/high issue/PR links).
  Each gap carries evidence pointers resolvable to Step 2–4 ids. Admin debug `GET /admin/tenants/…/manager-insight/fetch-debug` and Manager insight tab now run and render **Step 1 → 0.5 → 2 → 3 → 4 → 5** including a dedicated **Gaps (Step 5)** section.
- Step 5 tests: `backend/tests/vector/domains/manager_insights/test_compute_gaps.py`.
- **Step 5.5 (key achievements)** is implemented in `vector/domains/manager_insights/build_key_achievements.py`: includes **closed Linear issues** and **merged/closed GitHub PRs** (by `closed_at` and/or terminal `status`) only; sorted by close time; evidence lists `work_item:…` plus optional `reinforced_by_link:…` when a **medium/high** `WorkItemLink` connects the achievement to a `document` / `call` / `message_thread`. Response field `key_achievements` on admin fetch-debug; UI **Key achievements (Step 5.5)**.
- Step 5.5 tests: `backend/tests/vector/domains/manager_insights/test_build_key_achievements.py`.
- **Step 5.6 (raw highlights)** is implemented in `vector/domains/manager_insights/build_raw_highlights.py`: (1) repeated **4+ char tokens** across distinct **calls/Slack** work items, (2) one line per **closed** pull request (notable list, capped), (3) one line per **gap** with sources from `evidence_pointers`; light banned-token sanitizer. Response field `raw_highlights`; UI **Raw highlights (Step 5.6)**. Admin run label **1 → 0.5 → 2 → 3 → 4 → 5 → 5.5 → 5.6**.
- Step 5.6 tests: `backend/tests/vector/domains/manager_insights/test_build_raw_highlights.py`.
- **Step 6 (signals)** is implemented in `vector/domains/manager_insights/compute_signals.py`: deterministic state-vector computation from Steps 2–5.6 with no LLM, explicit fallback defaults for sparse fields, and `explain` strings for operator QA. Response field `signals` (`SignalsV0Debug`) on admin fetch-debug; UI section **Signals (Step 6)**; admin run label **1 → 0.5 → 2 → 3 → 4 → 5 → 5.5 → 5.6 → 6**.
- Step 6 tests: `backend/tests/vector/domains/manager_insights/test_compute_signals.py`.
- Remaining work after Step 6: **Step 7 (Interpretations)**. Runtime prerequisites unchanged (tenant OAuth, connector access).

---

## Responsibility Split

* **Step 10 — Slack Layer**

  * Handles Slack input/output
  * Sends ACK
  * Triggers async job
  * Posts final message

* **Step 11 — Pipeline Orchestration**

  * Runs the **runtime pipeline through Step 9 (Rendering)** in the strict order above (includes 0.5, 5.5, 5.6, 6.5)
  * Builds `UserReportContext`
  * Applies config, retries, logging
  * Returns final structured result to Step 10

👉 This removes ambiguity completely.

---

## Admin: Manager insight tab (per tenant)

**Goal:** From **Step 1 onward**, every implementation step ships **visible, tenant-scoped admin UI** so operators can **see intermediate artifacts**, **confirm the step behaves**, and **debug** before moving on. This is intentionally **parallel to Slack**: Slack is the manager surface; **admin is the operator/debug surface**. (Product label: **“Manager insight”** on the tab.)

### Where it lives (frontend)

- Add a new tenant tab **“Manager insight”** in the admin tenant nav (alongside Workspace, Integrations, Data pipeline, etc.). Today that nav lives in **`frontend/src/admin/AdminTenantLayout.tsx`** — add a `NavLink` to e.g. **`/admin/tenants/:tenantId/manager-insight`**.
- Implement the page in a dedicated component (suggested): **`frontend/src/admin/AdminTenantManagerInsightPage.tsx`** (route wired next to other tenant admin routes).

### What the backend must support

- **Tenant-scoped, admin-authenticated JSON APIs** (read-first; optional **“Run dry pipeline”** later) that return the **latest successful snapshot per step** for a tenant (and optionally a chosen **pipeline `run_id`**).
- **Persist pipeline runs** for debugging: at minimum `run_id`, `tenant_id`, **subject user**, **window**, timestamps, **per-step status** (`pending | ok | failed | skipped`), **duration**, and **bounded JSON** (or object-store pointer) for each step’s output (`fetch_bundle`, `data_reliability`, `work_items`, …). Apply **size caps** + redaction rules for secrets; never store raw OAuth tokens in these blobs.
- **Correlation:** reuse the same **`job_id` / `run_id`** string you log in Step 10/11 so Slack failures and admin views line up.

### Operator workflow (how you “gate” steps)

1. Implement backend step **N** + persist its snapshot.
2. Extend **Manager insight** tab with a section for step **N** (collapsible JSON viewer + human summary counts + copy/download).
3. **Manually verify** on a real or fixture-driven run before starting step **N+1**.

The **canonical checklist** of what each step must surface in the tab is in **[Admin: Per-step milestones](#admin-per-step-milestones-required-checklist)** below.

### Guardrails

- **RBAC:** admin-only; never expose this data on public or tenant-user routes.
- **PII / content:** default to **truncated previews** in UI; full JSON behind “expand” / download with audit logging if required by policy.
- **Deterministic steps:** admin should show **the same inputs** you would feed golden tests (or link to `run_id` used in CI).

### Tenant-identical command runs (admin)

**Product goal:** At the end of the flow (and once the pipeline is wired), an operator can **trigger the same Manager Insights command** they would use in Slack **from the tenant Admin → Manager insight tab**, and see **exactly what that tenant’s manager would see** if they ran it in Slack—the **same markdown body** (post–Step 9, post–compression/lint), the **same partial-data banners**, and the **same structured context** (for the debug panels above).

**Technical rules (non-negotiable for parity):**

1. **Single pipeline entrypoint** — Admin actions **must not** fork a second “admin-only” report implementation. They call the **same Step 11 orchestration** (runtime order **1 → 0.5 → … → 9**) with the **same arguments** Slack would resolve: `tenant_id`, **subject user** (Slack user id / internal user key—define one canonical id in Step 0), **`window`**, caps, feature flags.
2. **Explicit `invocation_source`** — `slack | admin` (or `delivery_channel`) is allowed **only** for outer I/O: Slack path still does **3s ACK + chat.postMessage/chat.update**; admin path does **HTTP response / SSE or poll** + renders in-page. **Downstream of Step 1, both paths must execute identical code** (same functions, same renderer output string).
3. **Same output artifact** — Persist and return the **exact `final_markdown`** string that Step 10 would post to Slack (byte-identical for the same inputs and config). Admin UI shows it in a **Slack-flavored markdown preview** (or the same renderer component the product uses for previews) so formatting matches what Slack displays.
4. **Audit** — Log `admin_user_id`, tenant, subject, `run_id`, and `invocation_source=admin` for every admin-triggered run.
5. **No secret side doors** — Admin runs use **live tenant connectors** by default (same as Slack). Optional **fixture-only** runs stay restricted to **non-prod** (already suggested for Step 11).

**UI sketch (Manager insight tab, bottom “Run” region):**

- Fields mirroring the slash command: e.g. **subject** (`@user` picker mapped to Slack member / internal id), **window** (preset days), optional overrides only if product-approved.
- Buttons: **“Run report (same as Slack)”** → starts job → poll until complete → show **Final report** tab with markdown identical to tenant view.
- Show **`run_id`**, per-step timeline (reuse Step 11 data), and link “open this run’s step debug” above.

---

## How this relates to the product spec


| Spec concept                       | Implementation role                                                      |
| ---------------------------------- | ------------------------------------------------------------------------ |
| `FetchActivity`                    | Raw connector reads + caps + time window (no “intelligence”)             |
| `UserReportContext`                | Single **merge artifact** passed to later LLM stages; everything cited   |
| Work items, links, evidence, gaps  | **Graph nodes/edges + annotations**; gaps are **computed**, not narrated |
| `SignalsV0`                        | **Deterministic** layer over metrics + graph                             |
| `InterpretationsV0` / `InsightsV0` | **Scoped LLM** stages with strict I/O contracts                          |
| Report sections                    | **Renderer** maps context → fixed markdown sections                      |


---

## Stack reality check (important)

The repo’s backend is **Python** with **Pydantic** contracts under `backend/src/vector/contracts/` (e.g. connectors, onboarding). The step outline you suggested uses **TypeScript** filenames (`types.ts`, `fetchActivity.ts`, …).

**Recommendation (challenge to “TS-only Step 0”):**

- **Lock contracts in Python first** (`vector/contracts/manager_insights.py` or split modules), mirroring the spec **field-for-field**. This matches today’s architecture and keeps the API boundary honest.
- If the product later needs **shared TS types** (e.g. admin UI or a Node worker), generate them from **OpenAPI / JSON Schema** emitted from the same Pydantic models—do not maintain a second handwritten `types.ts` unless you accept drift.

Below, **“Output”** names are **logical**; map them to `vector/contracts/…`, `vector/domains/manager_insights/…`, etc., as you implement.

---

## North-star constraints (carry through every step)

1. **No invention** beyond what the context object allows; uncertainty must be explicit.
2. **Evidence-first**: anything that looks like an action item, blocker, or decision **without a quotable span** is discarded (per spec).
3. **Links are hypotheses**: confidence `high | medium | low`; only `high` is “safe” for strong downstream reasoning; `low` ignored for conclusions.
4. **Deterministic before LLM**: metrics, work items shape, gaps, and signals must be **replayable** from the same inputs.
5. **LLM is narrow**: interpretations and insights are **functions** `(UserReportContext | slice, schema) → validated JSON`, not free chat.
6. **Orchestration is not the model**: multi-step flows, retries, and tool calls live in **application code** (future: explicit tool registry with permissions).
7. **Admin Manager insight tab ships with every step from Step 1:** each step’s PR **extends** the tenant **Manager insight** tab and the **persisted run snapshot** so the team can **validate and debug** that step before the next step merges (see [Admin: Manager insight tab](#admin-manager-insight-tab-per-tenant) and the [milestone checklist](#admin-per-step-milestones-required-checklist)).
8. **Slack vs admin parity:** the **final user-visible report string** is produced **once** by the shared pipeline; Slack posting and admin preview are **thin adapters** over that result (see [Tenant-identical command runs](#tenant-identical-command-runs-admin)).

---

## Step 0 — Lock contracts (CRITICAL)

**Business goal:** One source of truth so product, prompts, and tests do not drift.

**Technical goal:** Frozen **JSON-serializable** types for the entire pipeline, matching [UserReportContext](./manager_insights_vo.md) sections 1–7, plus `SignalsV0`, `InterpretationsV0`, `InsightsV0`, and the **report DTO** (sections 1–7 + summary + key risks).

**Define (minimum set from spec):**

- `WorkItem`, `WorkItemType`, `WorkItemStatus`, `SourceSystem`
- `Link`, `LinkType`, `LinkConfidence`, evidence strings
- `ActionItem`, `Blocker`, `Decision` (each with `source`, `evidence`, optional `linked_work_items`, `confidence` where applicable)
- `ExpectedWork`, `ActualWork`, `Gap`, `GapType`
- `DeliveryMetrics` (the fact bundle: issues completed, PRs merged, etc.)
- `KeyAchievement`, `RawHighlight` (strict rules from spec)
- `SignalsV0` (all signal enums / structures exactly as spec)
- `InterpretationV0`, `InsightsV0` (insight shape: observation, interpretation, implication, evidence, confidence, priority)
- `UserReportContext` root type composing the above
- `ReportV0` or `RenderedReportSections` for the **fixed** markdown section contract

**Extended (required for downstream steps in this plan):**

- `DataReliabilityReport` — per-connector `high | medium | low` for coverage, freshness, completeness; plus `overall_confidence: high | medium | low` (see Step 0.5).
- `KeyAchievementsBundle` — ordered list of `KeyAchievement` records produced by Step 5.5 (deterministic); same `KeyAchievement` type as spec, bundled for merge into `UserReportContext`.
- `RawHighlightsBundle` — ordered list of `RawHighlight`-shaped records produced by Step 5.6 (deterministic); factual strings + `sources[]` only; merged into `UserReportContext` (see Step 5.6).
- `InsightArbitrationResult` — exactly one primary `InsightV0` reference, at most two supporting `InsightV0` references, and `dropped_insights` with deterministic `drop_reason` + `evidence_pointers` each (see Step 6.5).

**STRICT RULES:**

- No fetch logic, no similarity, no LLM prompts in this step.
- Optional: JSON Schema export for docs/tests.

**Output (suggested):** `vector/contracts/manager_insights.py` (or `manager_insights/context.py`, `…/signals.py` if you prefer smaller files).

**Why first:** Prevents rework; prompts and golden tests can target stable shapes.

**Challenge:** If you skip `ExpectedWork` / `ActualWork` / `KeyAchievement` / `RawHighlight` here, Steps 5–9 will invent fields under pressure—add them in Step 0.

**Validation:**

- **Proceed only if** every pipeline stage’s inputs/outputs named in Steps 0.5–5.6, 6–11 have a corresponding Pydantic model (or nested model) and round-trip JSON fixtures load without unknown fields.
- **FAIL** if any later step introduces a field not present in Step 0 models (add to Step 0 first).

---

## Step 0.5 — Data reliability layer

**Document order vs runtime order:** This section is placed **immediately after Step 0** (contracts). **Implementation must run Step 0.5 after Step 1** (`FetchActivity`), because tiers are computed from fetch payloads and metadata. The mermaid diagram reflects **runtime** order (`S1 → S0.5 → S2`).

**Business goal:** Quantify **how much we actually know** per connector so the product never sounds more certain than the data allows.

**Technical goal:** After `FetchActivity` artifacts exist (Step 1 output) and **before** gap/signal logic treats data as authoritative, compute a **deterministic** `DataReliabilityReport`:

- **Coverage per connector** — did we get *expected* slices (e.g. channels configured, repos linked, Linear teams in scope)? Map to `high | medium | low` using explicit thresholds (e.g. % of configured sources with a successful fetch, zero vs partial vs full errors). **V0 default percentages and freshness bounds:** see **Default Thresholds (V0)** appendix (Data Reliability).
- **Freshness** — age of newest vs oldest successful fetch per connector vs report window; staleness beyond SLA downgrades tier.
- **Completeness** — within each connector payload, did we hit caps / truncation / empty sets where non-empty was expected? Downgrade when caps dominate the story.

**STRICT RULES:**

- **MUST be deterministic** — same fetch snapshot + same config → same reliability report.
- **MUST NOT use an LLM.**
- **MUST** feed forward into `UserReportContext` (or parallel merge) so Steps 6 (Signals), 7–8 (tone/hedging in prompts or post-validation), and Step 9 (renderer) can **tone-match confidence** (e.g. avoid definitive language when `overall_confidence` is `low`).

**Output (shape):**

```yaml
data_reliability:
  slack: high | medium | low      # coverage + freshness + completeness rolled up per connector
  github: high | medium | low
  linear: high | medium | low
  notion: high | medium | low
  calls: high | medium | low
overall_confidence: high | medium | low
```

**Implementation fit:** `vector/domains/manager_insights/data_reliability.py`; inputs = Step 1 raw fetch DTOs + fetch metadata (timestamps, errors, caps applied flags). Unit tests: golden fetch fixtures → expected tier per connector.

**Why here:** Prevents overconfident conclusions in Signals and Insights when connectors are partial or stale.

**Validation:**

- **Proceed only if** every connector listed in the report window appears in `data_reliability` with a tier (or explicit `not_configured` mapped into `low` per policy documented in code).
- **FAIL** if any tier is produced without a recorded reason code in structured logs / `DataReliabilityReport` debug fields (auditable downgrade trail).

---

## Step 1 — FetchActivity (raw connectors only)

**Business goal:** Prove “live signals in a bounded window” for one engineer report run.

**Technical goal:** One orchestrated **fetch** stage per connector, returning **connector-native** structures + metadata (fetched_at, window, caps applied). Align naming with spec: Slack, Linear, GitHub, Notion, calls (Gemini / Meet-style).

**STRICT RULES:**

- No cross-connector merging, no semantic links, no “topics.”
- Apply **caps** and **time window** exactly as spec (message samples, PR counts, etc.).
- Normalize only **transport concerns** (dates as UTC, IDs as strings)—not business normalization (that is Step 2).

**Implementation fit:** Place behind existing connector/auth patterns (`vector/domains/connectors/…`), returning typed DTOs that are **not** `WorkItem` yet (e.g. `SlackActivityRaw`, `LinearIssuesRaw`, …) defined in contracts or adjacent `raw_fetch.py` models.

**Output (suggested):** `vector/domains/manager_insights/fetch_activity.py` (+ per-connector helpers). Mock external APIs in tests only.

**Goal:** Data in the door, bounded and attributable.

**Challenge:** Spec lists `data.fetch_github_activity` for Linear—treat as **doc typo**; implement **Linear** and **GitHub** as separate modules to avoid coupling.

**Validation:**

- **Proceed only if** each connector returns `fetched_at`, window bounds, and explicit `caps_applied` / `errors` metadata usable by Step 0.5.
- **FAIL** if any connector silently returns empty without an error when credentials or config expect data (must distinguish “empty world” vs “failed fetch”).

---

## Step 2 — Normalization → WorkItems

**Business goal:** A single **work graph** vocabulary: every ticket, PR, doc, call is one node with comparable fields.

**Technical goal:** Deterministic `raw_* → WorkItem` mapping:

- One `WorkItem` per issue, PR, doc, call (per spec).
- Titles + **short summaries** (normalize text for dedup/embeddings later; still not “meaning”).
- Timestamps, status, `source`, `project` when available.

**DO NOT (yet):**

- Create `Link` rows.
- Run LLM summarization that is not strictly **extractive** from provided text (prefer deterministic truncation + cleaning for V0).

**Output (suggested):** `vector/domains/manager_insights/build_work_items.py`

**This is your first real system:** Everything downstream consumes `WorkItem`, not five connector shapes.

**Challenge / future:** When you move to a **stored work graph**, this step becomes “projection into graph tables”; the contract should stay stable.

**Validation:**

- **Proceed only if** every `WorkItem` has stable `id`, `source`, `type`, and timestamps within the report window policy.
- **FAIL** if duplicates of the same logical entity appear without a deterministic dedup key (define merge rules in code + tests).

---

## Step 3 — Evidence extraction (hard constraint layer)

**Business goal:** Only **citable** claims enter the context object.

**Technical goal:** Extract `action_items`, `blockers`, `decisions` from **calls / Slack snippets / Notion excerpts** (whatever inputs you defined in Step 1–2), each with:

- `evidence`: **exact quote** from source text (spec: no quote → discard).
- `source` reference (e.g. call id, message id).
- Optional `linked_work_items` only when **deterministic** string match or later when Step 4 runs (choose one policy and stick to it—**recommended:** extraction here only sets text; Step 4 attaches IDs).

**STRICT RULES:**

- No “helpful” paraphrase without the quote stored alongside.
- Confidence only where spec allows; otherwise omit or use a single conservative tier.

**Output (suggested):** `vector/domains/manager_insights/extract_evidence.py`  
Implementation may use an LLM **only if** output is schema-validated and quotes are **substring-verified** against source text.

**Why systems fail here:** Teams allow summarization without citations—don’t.

**Validation:**

- **Proceed only if** every retained `ActionItem` / `Blocker` / `Decision` has a non-empty `evidence` string that **substring-verifies** against the referenced source payload (byte-normalized per policy).
- **FAIL** if any item lacks quotes or verification fails (discard path must be explicit, not silent).

---

## Step 4 — Semantic linking (isolated problem)

**Business goal:** Hypothesis edges between work items for cross-source reasoning **without** pretending they are ground truth.

**Technical goal:** `linkWorkItems`-style module:

- Inputs: `WorkItem` list + optional evidence snippets.
- Simple similarity first (normalized string overlap, token Jaccard, or cheap embeddings).
- Output: `Link` with `confidence` + **evidence** string pairs as spec.

**DO NOT:**

- Feed links into narrative generation until Steps 6–8 apply the spec’s confidence rules.

**Output (suggested):** `vector/domains/manager_insights/link_work_items.py`

**Keep it isolated:** Unit tests with fixed strings; golden cases for “billing retry” ↔ issue title.

**Challenge:** This is where **graph-backed context** starts—later, persist links as edges with provenance and decay stale links.

**Validation:**

- **Proceed only if** every `Link` has `confidence` and evidence fields populated per Step 0 contract.
- **FAIL** if `high`-confidence links are emitted without meeting documented thresholds (tests must lock thresholds).

---

## Step 5 — Gaps (deterministic layer)

**Business goal:** Encode “discussion vs execution” and related patterns as **structured observations**, not prose.

**Technical goal:** Compute `Gap` list from **only** `work_items`, `links`, `extracted evidence`, and **ExpectedWork / ActualWork** construction rules in the spec:

- `expected_not_executed`
- `discussed_not_linked_to_work`
- `blocker_not_tracked`
- `doc_not_connected_to_execution`

**STRICT RULES:**

- **No LLM.**
- Each gap carries **evidence** pointers (which action item, which work items were searched, etc.).

**Output (suggested):** `vector/domains/manager_insights/compute_gaps.py`

**Truth engine:** Downstream copy should say “not found in tracked systems,” not “they didn’t do it”—gaps encode the former.

**Validation:**

- **Proceed only if** each `Gap` references evidence pointers resolvable to Step 2–4 artifacts.
- **FAIL** if a gap type is emitted with no evidence pointer schema field populated.

---

## Step 5.5 — Key achievements builder

**Business goal:** Surface **closed, attributable wins** so the report balances risks with **verified delivery**, without LLM invention.

**Technical goal:** Deterministic extraction of `key_achievements` from graph + fetch facts:

**Input:**

- Closed issues (Linear / equivalent), merged PRs (GitHub), within the report window and attribution rules in spec.
- Optionally: linked docs (Notion) or calls that **reinforce** an achievement only when **deterministic** link exists (Step 4 `high` or spec-approved deterministic doc/PR linkage—**no LLM** for core inclusion).

**STRICT RULES:**

- **MUST** be closed/merged work only (states enumerated in code + tests).
- **NO LLM** for inclusion/eligibility; optional reinforcement means **extra linked evidence items** appended when deterministic rules match, not paraphrase.
- Order achievements by **merge/close time** or spec-defined priority (deterministic sort key).

**Output (shape):**

```yaml
key_achievements:
  - title: string
    linked_items: [work_item_id, ...]
    evidence: [{ type, id, quote_or_ref }, ...]
```

**Output (suggested):** `vector/domains/manager_insights/build_key_achievements.py` → `KeyAchievementsBundle` merged into `UserReportContext`.

**Validation:**

- **Proceed only if** every achievement has ≥1 `linked_items` entry resolvable to `WorkItem` ids from Step 2.
- **FAIL** if any achievement references open/in-progress items or lacks evidence pointers.

---

## Step 6 — Signals (pure computation)

**Business goal:** A compact, manager-legible **state vector** over the period.

**Technical goal:** Implement **all** `SignalsV0` fields in the spec from deterministic inputs (metrics + graph features + gaps). Each signal should be **explainable** (“because open_urgent_items = 3”, “because repeated cluster X with no closed work”, …).

**STRICT RULES:**

- No LLM.
- If a signal cannot be computed honestly from current data, return **explicit unknown / neutral** per spec guidance (e.g. feedback reception defaults to neutral).

**Output (suggested):** `vector/domains/manager_insights/compute_signals.py`

**Challenge:** Spec’s Signal 12–14 need **review/Slack** features—if Step 1 did not capture them, either narrow the signal to “insufficient data” or extend Step 1 before claiming the signal.

**Validation:**

- **Proceed only if** every `SignalsV0` field is either a computed value or an explicit `unknown`/neutral sentinel defined in Step 0.
- **FAIL** if any signal is computed using fields absent from Steps 2–5.6 outputs (no hidden globals).

---

## Step 5.6 — Raw highlights builder (deterministic)

**Business goal:** Surface factual, high-signal observations **without interpretation** so the report and downstream prompts have “what happened” texture beyond achievements alone.

**Technical goal:** Build `raw_highlights` (as `RawHighlightsBundle` / `RawHighlight[]` per Step 0) from deterministic graph + fetch inputs:

* **Repeated mentions** (calls, Slack) — same normalized topic/entity string appears ≥ configured threshold across distinct source ids.
* **Notable events** — merged PRs, large threads, or other **enumerated** event types from `WorkItem` + fetch metadata (rules in code, not prose).
* **Missing links** — discussion surfaced in evidence/gaps as “discussion without execution” patterns (e.g. gap-backed **discussed_not_linked_to_work** with stable source ids).

**STRICT RULES:**

* **MUST** be **pure facts** (counts, presence, absence, ids)—no “seems”, “likely”, “concern”.
* **MUST** reference **source ids** on every highlight (`sources: [...]`).
* **NO LLM.**
* **NO interpretation language** — template-generated or concatenated factual strings only; lint for banned inference tokens.

**Output (shape):**

```yaml
raw_highlights:
  - text: "Billing retry mentioned in 3 calls"
    sources: ["call_1", "call_3", "call_5"]

  - text: "No linked PR found for retry discussion"
    sources: ["call_3"]
```

**Output (suggested):** `vector/domains/manager_insights/build_raw_highlights.py` → merged into `UserReportContext`.

**Validation:**

* **FAIL** if any highlight contains inferred / evaluative language (deterministic lint list + tests).
* **FAIL** if any highlight has empty `sources` or ids not resolvable to Step 1–2 artifacts.

---

## Step 6.5 — Insight arbitration engine (CRITICAL)

**Business goal:** Turn **many candidate insights** into a **small, decision-ready set** so managers get one clear primary focus and limited supporting context—**no LLM overreach**, no wall of text.

**Technical goal:** Deterministic **`InsightArbitrationResult`** from structured inputs. This step **does not generate prose**; it **selects and ranks** insights already produced in Step 8 using evidence-backed rules.

**Pipeline placement (CRITICAL):** Step 6.5 **MUST run after Step 8** in code (it requires `InsightsV0[]`). The numeric label `6.5` reflects its role in the **Execution Brain** (decision layer sitting on top of **state** from Step 6 and **meaning** from Steps 7–8), not “between Step 6 and Step 7” in the runtime graph.

**Input:**

- `SignalsV0` (Step 6)
- `Gap[]` (Step 5)
- `InsightsV0[]` (Step 8) — full candidate set from LLM with schema validation already applied

**Output (shape):**

```yaml
arbitration:
  primary_issue: Insight            # exactly one Insight reference (id + snapshot ref per contract)
  supporting_issues: [Insight, Insight]   # length 0–2 only
  dropped_insights: [{ insight_id, drop_reason, evidence_pointers }, ...]
```

**STRICT RULES:**

- **MUST select EXACTLY 1** `primary_issue` from the candidate list (if candidates empty, emit explicit **no-primary** sentinel defined in Step 0 contract—renderer must handle).
- **MUST select at most 2** `supporting_issues`; order is deterministic (secondary score, then insight id lexicographic tie-break).
- **MUST discard** all other candidates with a **deterministic** `drop_reason` enum and `evidence_pointers` (signal ids, gap ids, achievement ids, quotes already on the insight).
- **MUST NOT use an LLM** for selection or ranking. Optional: **strictly constrained** templated string for internal debug logs only—never for selection logic.
- **MUST** justify selection using **only** fields already on insights + gaps + signals (e.g. map each insight to gap types / signal thresholds in code).

**Priority order (STRICT — implement as ordered tie-break after computing a per-insight score vector):**

1. **Expectation vs execution gap** — insights tied to `GapType` / evidence classes matching “expected not executed” / “discussed not linked” / spec’s expectation-vs-execution family win first.
2. **Repeated unresolved topic** — insights backed by recurrence features in signals + evidence clusters (thresholded in code).
3. **Blocker visibility** — insights tied to `blocker_not_tracked` and blocker-related signal patterns.
4. **Urgent pressure** — insights tied to urgency/open-urgent style signals per spec.
5. **Everything else** — deterministic score from remaining insight `priority` + confidence + evidence strength fields; tie-break lexicographically by `insight_id`.

**V0 numeric score components (weights + tie-breaker):** implement exactly as documented in **Default Thresholds (V0)** appendix (Arbitration); the ordered priority list above remains the **strict dominance** order—numeric scores resolve ties **within** a band.

**Implementation fit:** `vector/domains/manager_insights/arbitrate_insights.py`; exhaustive unit tests: fixture candidates → expected primary + supporting + dropped reasons.

**Validation:**

- **Proceed only if** Step 8 output passed schema validation and every candidate insight has stable `insight_id`.
- **FAIL** if primary count ≠ 1 when candidates non-empty, or supporting count > 2, or any selection uses free-text model output not present on the structured insight objects.

---

## Step 7 — Interpretations (LLM layer 1)

**Business goal:** Translate signals + evidence into **reusable**, hedged meanings for composition.

**Technical goal:** `generateInterpretations`:

- Input: `SignalsV0`, evidence subset, **high** links only for strong claims (medium only hedged).
- Output: `InterpretationV0[]` matching spec schema (`type`, `description`, `based_on_signals`, `evidence`, `confidence`).

**STRICT RULES:**

- Must reference **signal ids** and **evidence quotes**; validate output against Step 0 schema.
- Temperature low; refusal/short output if context insufficient.

**Output (suggested):** `vector/domains/manager_insights/generate_interpretations.py`

**Controlled LLM usage:** Wrap with timeouts, token budgets, and structured logging (no model on raw HTTP request path—invoke from job/worker).

**Validation:**

- **Proceed only if** each interpretation references valid signal ids present in Step 6 output and evidence quotes that verify against input corpora.
- **FAIL** schema validation or “new quote” check (quotes not found in allowed text).

---

## Step 8 — Insights (LLM layer 2)

**Business goal:** Prioritized, decision-oriented **insight cards** managers actually read.

**Technical goal:** `generateInsights`:

- Input: interpretations + signals + key gaps/evidence.
- Output: `InsightsV0[]` with observation, interpretation, implication, evidence, confidence, **priority** (per spec).

**STRICT RULES:**

- No new facts; only recombination and emphasis of grounded inputs.
- Priority ordering should reflect spec’s **One Priority** selection order where possible.

**Output (suggested):** `vector/domains/manager_insights/generate_insights.py`

**Wow layer:** Keep it honest—wow should come from **clarity**, not hallucination.

**Validation:**

- **Proceed only if** JSON validates and **no new facts** check passes (all cited strings exist in allowed corpora / structured fields).
- **FAIL** if insight count exceeds configured max for cost control **or** if any insight lacks evidence fields required by Step 0.

---

## Step 9 — Report rendering

**Business goal:** Slack-ready markdown that matches the **fixed** report contract (Summary, Key Risks, sections 1–7, language rules).

**Technical goal:** Pure `UserReportContext` (+ optional style flags) → markdown string; **no** model in this step.

**STRICT RULES:**

- Follow [Report Mapping](./manager_insights_vo.md) and the **language rule** (no “untracked work”; use spec’s approved phrasing).
- Include “from discussions (not found in tracked systems)” style labels where spec requires.

**Report compression rules (CRITICAL — enforce in renderer + pre-render validation):**

- **Max 3 insights shown** in the manager-facing narrative — these **MUST** be exactly the `primary_issue` + up to 2 `supporting_issues` from **`InsightArbitrationResult`** (Step 6.5). No additional insight bullets in the compressed view; other material may appear only in appendix/debug channels if explicitly product-approved.
- **Max 5 development signals** — enumerate at most five signal-derived bullets in the “signals / delivery” summary region; pick top five by deterministic ordering keyed to spec weights (document the ordering function in `render_report.py` tests).
- **Max 4 coaching questions** — cap generated or template-expanded coaching prompts at four total in the compressed report.
- **Exactly 1 “One Priority”** block — must correspond to `arbitration.primary_issue` (or explicit empty-state copy if arbitration says no-primary); **never** zero, **never** more than one in the compressed report.
- **No verbosity** — hard character budgets per section (define constants; **V0 default: max 500 characters per major section** — see **Default Thresholds (V0)** appendix); renderer **truncates deterministically** with ellipsis markers rather than spilling.
- **No duplication** — if the same fact appears in achievements and signals, include once (deterministic precedence: achievements win in “wins” region, signals win in “state” region).
- **No generic statements** — post-render lint pass (deterministic regex / template checks): reject lines matching banned generic patterns (maintain list in code); **FAIL CI** if golden fixtures trip lint.

**Output (suggested):** `vector/domains/manager_insights/render_report.py`

**Optional:** Template engine or literal section builders; snapshot tests on golden `UserReportContext`.

**Validation:**

- **Proceed only if** `InsightArbitrationResult`, `DataReliabilityReport`, `KeyAchievementsBundle`, and `RawHighlightsBundle` are present on the context object passed to render (or explicit V0 “feature off” flags documented—default ON).
- **FAIL** compression / lint checks: wrong insight count, >5 signal bullets, >4 coaching questions, ≠1 One Priority block, or banned generic phrases detected.

---

## Step 10 — Slack orchestration layer

**Business goal:** **Slack-native** entry and exit: a manager runs a command, gets an immediate acknowledgement, and receives a **single updated** final message with the rendered report—reliable under timeouts, partial data, and transient Slack/API failures.

**Admin parity (same step, different adapter):** **Step 10** is the **Slack I/O adapter** only. **Admin “run same as Slack”** does **not** duplicate the pipeline: it calls **Step 11** with `invocation_source=admin` and displays the **same `final_markdown`** returned by the shared orchestration (see [Tenant-identical command runs](#tenant-identical-command-runs-admin)).

**Technical goal:** Application-level orchestration (not LLM):

1. **Slash command handler** — e.g. `/vector report @user` (exact command string product-defined); parse args, resolve `tenant`, `subject_user`, `window`, idempotency key.
2. **Immediate ACK response** — ephemeral or channel message: **“Working on it…”** (or product copy) within Slack’s **3-second** interaction window; include a `job_id` / link if product provides status UI.
3. **Async job execution** — enqueue Celery (or equivalent) job that invokes **Step 11 (Pipeline Orchestration)** to run the full runtime chain **1 → 0.5 → 2 → 3 → 4 → 5 → 5.5 → 5.6 → 6 → 7 → 8 → 6.5 → 9** with tracing and `invocation_source=slack`; **never** block the ACK path on LLM or connectors.
4. **Final message update** — post or **update** the Slack message (same `ts` if using chat.update pattern) with Step 9 markdown; respect Slack markdown limits (split deterministically into thread replies if over limit—document behavior).

**Retry logic:**

- **Connector retries** — bounded exponential backoff per connector in Step 1; record outcomes in `DataReliabilityReport`.
- **Slack post retries** — idempotent post/update with dedupe on `job_id`; respect `429` Retry-After.
- **LLM retries** — only for transient HTTP errors; **never** retry validation failures with “hope it works” temperature changes.

**Timeout handling:**

- Hard wall-clock per job tier; on timeout: post **partial** final message (see below) + `job_status=timeout` in logs.

**Partial data behavior:**

- If `overall_confidence` is `low` or specific connectors `low`, final Slack copy **MUST** include a short deterministic banner (e.g. “Partial data: GitHub unavailable for this run”) from `DataReliabilityReport`; renderer + Slack template share the same string builder.
- Arbitration + compression still run; **never** silently omit the partial-data banner when tiers are low.

**Output example:**

```
Slack Flow:
1. /vector report @user
2. immediate ACK (“Working on it…” + job reference)
3. async pipeline execution (Step 11: runtime items 1–13 — includes 0.5, 5.5, 5.6, 6.5)
4. final report posted or message updated in Slack
```

**Output (suggested):** `vector/domains/manager_insights/slack_orchestration.py` + worker task module; reuse existing Slack signing secret / interaction patterns from product infra.

**Validation:**

- **Proceed only if** interaction ACK returns within Slack’s required latency budget (monitor in staging).
- **FAIL** e2e tests if final message is missing when job succeeded, or if ACK is missing on command receipt, or if partial-data banner omitted when fixture forces `overall_confidence=low`.

---

## Step 11 — Assembly / pipeline orchestration (glue you should plan explicitly)

**Responsibility (see Execution Order → Responsibility Split):** Step 11 is the **worker-side pipeline**: it runs the **runtime items 1–13** in strict order, assembles `UserReportContext`, and returns the structured result + rendered markdown to **Step 10** for Slack delivery. Step 10 **does not** re-implement fetch/signal/LLM logic—it **triggers** this layer and **displays** the outcome.

**Same entrypoint for admin:** **Step 11** is also invoked by the **Admin → Manager insight** “Run report (same as Slack)” action with `invocation_source=admin`. Return payload **must** include the same `final_markdown` (and structured `UserReportContext` / `run_id`) that Slack delivery would use so the admin UI can prove **tenant-identical** output ([Tenant-identical command runs](#tenant-identical-command-runs-admin)).

The original 0–9 list implied a linear file chain; in production you also need:

1. **`build_user_report_context`** — merges metrics, work items, links, evidence, gaps, **key achievements (5.5)**, **raw highlights (5.6)**, **data reliability (0.5)**, signals, interpretations, insights, **arbitration (6.5)** into the final `UserReportContext` object (spec: “what the LLM receives”) in a **documented field order** so Steps 7–9 see a stable shape.
2. **Worker entrypoint** — invoked by **Step 10** after ACK **or** by **admin run** (HTTP → job): run pipeline stages in strict order with tracing, idempotency key per `(tenant, subject_user, window, invocation_source)`.
3. **Configuration** — `window_days`, caps, feature flags per connector; thresholds for Step 0.5 tiers (see appendix) and Step 6.5 scoring (see appendix) versioned in config with tests.
4. **Observability** — per-stage latency, token usage, validation failures; correlate Slack `job_id` across spans.
5. **Admin snapshots** — after **each** runtime step completes, **persist** the step output (or bounded pointer) on the **`ManagerInsightPipelineRun`** record so the tenant [Manager insight](#admin-manager-insight-tab-per-tenant) tab can render the [milestone checklist](#admin-per-step-milestones-required-checklist) without re-running the pipeline.

This aligns with **deterministic control plane**: orchestration stays in Python services; LLM calls are **boxed** in Steps 7–8; **Step 6.5 and Step 9 compression** remain deterministic code paths.

**Validation:**

- **Proceed only if** a single integration test can run `build_user_report_context` from golden fixtures through **Step 8** (with **5.5 / 5.6** bundles merged on the context) and produce a valid object for Step 6.5 + Step 9.
- **FAIL** if merge order introduces nondeterminism (unordered dict iteration for lists exposed to LLM—use sorted keys / declared list order).

---

## Execution brain (architecture clarification)

This section names how **state**, **meaning**, **observations**, and **decision** compose—so engineers do not conflate LLM creativity with product judgment.


| Layer               | Step(s)                 | Role                                                                                                                                                                  |
| ------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Signals**         | Step 6                  | **State** — a compact, deterministic vector describing what the graph + metrics say happened (and unknowns).                                                          |
| **Interpretations** | Step 7                  | **Meaning** — LLM turns state + evidence into hedged, reusable interpretations **tied to signal ids and quotes**.                                                     |
| **Insights**        | Step 8                  | **Observations** — LLM composes interpretation + gaps into prioritized insight cards **without new facts**.                                                           |
| **Arbitration**     | Step 6.5 (runs after 8) | **Decision** — deterministic policy picks **one** primary and **≤2** supporting insights for the human-facing report; everything else is dropped with logged reasons. |


**Flow mnemonic:** Measure → (LLM) explain → (LLM) propose → **(code) decide** → **(code) compress & render** → **(Slack) deliver**.

---

## Mapping to Vector’s AI / platform direction


| Direction                       | How this plan supports it                                                                                                                          |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontier LLMs via API           | Steps 7–8 behind stable interfaces; swap models without changing deterministic + render + orchestration stages **0, 0.5, 1–6, 5.5, 5.6, 6.5, 9–11** (prompt/versioning only on 7–8). |
| Graph-backed execution context  | Steps 2–5 define nodes (`WorkItem`), edges (`Link`), annotations (evidence, gaps)—persist later without rewriting semantics.                       |
| Tool use / orchestration        | Future: each connector becomes a **permissioned tool**; same contracts, callable from agents **or** batch jobs.                                    |
| RAG over connectors + artifacts | Step 1 outputs become **retrieval chunks** with stable IDs; Steps 3–4 attach citations; renderer links back.                                       |
| Conversational Slack layer      | **Step 10** owns ACK + async + final message; Step 9 output is the payload; tone remains manager-grade in prompts (Steps 7–8), not in determinism. |
| Deterministic APIs              | Steps 0, 0.5, 5, 5.5, 5.6, 6, 6.5, 9 compression/lint, 11 orchestration are pure code; contract tests guard regressions.                             |


---

## Sequencing and dependencies (summary)

```mermaid
flowchart LR
  S0[Step 0 Contracts]
  S1[Step 1 Fetch]
  S05[Step 0.5 Data reliability]
  S2[Step 2 WorkItems]
  S3[Step 3 Evidence]
  S4[Step 4 Links]
  S5[Step 5 Gaps]
  S55[Step 5.5 Key achievements]
  S56[Step 5.6 Raw highlights]
  S6[Step 6 Signals]
  S7[Step 7 Interpretations]
  S8[Step 8 Insights]
  S65[Step 6.5 Arbitration]
  S9[Step 9 Render]
  S10[Step 10 Slack]
  S11[Step 11 Assembly]
  S0 --> S1 --> S05 --> S2 --> S3 --> S4 --> S5 --> S55 --> S56 --> S6 --> S7 --> S8 --> S65 --> S9 --> S10
  S11 -.->|build_user_report_context + config + observability| S0
```

**Note:** Step **0.5** is numbered for **contract adjacency** to Step 0; **runtime** is always `S1 → S0.5 → S2 → … → S55 → S56 → S6 → …` as in the diagram. Encode that order in `build_user_report_context` + worker; add a CI test that fails if Step 0.5 runs before fetch completes.

**Parallelism note:** After Step 2, **Step 3 (evidence)** and **partial link hints** can be engineered in parallel **only** if you keep evidence extraction free of link side effects until Step 4.

---

## Acceptance criteria (V0 “done enough”)

- **Admin Manager insight tab:** for each merged step **≥ Step 1**, the tenant tab exposes the artifacts listed in the [milestone checklist](#admin-per-step-milestones-required-checklist); **CI or reviewer checklist** blocks the next step if the tab/snapshots lag.
- Golden fixture: raw fetch snapshots → deterministic `WorkItem` + `Gap` + `SignalsV0` (byte-stable or field-stable).
- **Data reliability:** golden fetch with simulated partial outage → `data_reliability` tiers + `overall_confidence` match expected; Slack banner appears when low.
- **Key achievements:** only closed/merged items; each has `linked_items` + evidence; no LLM in builder tests.
- **Raw highlights (5.6):** factual strings only; every highlight has non-empty `sources`; lint rejects inference language; no LLM.
- **Arbitration:** golden `InsightsV0[]` + gaps + signals → exactly one primary, ≤2 supporting, deterministic `dropped_insights` reasons.
- Evidence tests: every `ActionItem`/`Blocker`/`Decision` in fixtures includes a verifiable substring of source text.
- LLM stages: JSON schema validation + “no new quotes” check (quotes must appear in input corpora).
- Renderer: snapshot tests enforce **compression rules** (≤3 arbitrated insights, ≤5 dev signals, ≤4 coaching questions, exactly one One Priority, **≤500 chars per major section** per V0 appendix defaults).
- **Slack path:** interaction ACK within timeout; job completes; final message contains report; forced failure exercises retries / partial banner; end-to-end dry run with mocked connectors in CI.
- **Admin / Slack parity:** for the same `(tenant, subject_user, window, config)`, an **admin-triggered** run and a **Slack-triggered** run produce the **same `final_markdown`** (golden test or pairwise CI check); admin-only **fixture** runs exempted when flagged `fixture=true`.

---

## Explicit challenges to the original step list

1. **Step 0 as TS-only** — likely wrong for this repo; **Pydantic first**, codegen second.
2. **Single `fetchActivity.ts` file** — will not scale; use **per-connector modules** + one orchestrator.
3. **Evidence extraction before WorkItems** — weaker than **WorkItems first** (you need stable IDs to attach evidence).
4. **Semantic linking before gaps** — acceptable, but policy must define whether gaps use only `high` links or also `medium` (spec: medium hedged—encode explicitly).
5. **Skipping Key achievements / Raw highlights** — report will feel empty; **Step 5.5** owns achievements; **Step 5.6** owns raw highlights; keep both aligned with [manager_insights_vo.md](./manager_insights_vo.md).
6. **Step 0.5 runtime order** — document explicitly: reliability is computed **from fetch outputs** (recommended **S1 → S0.5 → S2** in code even though the section sits after Step 0 for contract reasons).
7. **Step 6.5 runtime order** — must run **after Step 8**, never between 6 and 7.

---

## Admin: Per-step milestones (required checklist)

Each row is **acceptance for the admin “Manager insight” tab** for that step: the tab **must** show the listed data for the **latest run** (or selected `run_id`) before the team treats the step as “done” and starts the next.

| Step | Admin tab must show (minimum) | Debug helpers (minimum) |
| ---- | ------------------------------- | ------------------------- |
| **Step 0** — Contracts | Schema / contract **version** string; list of registered Pydantic model names (or OpenAPI link if exported). | “Contracts OK” badge from a health endpoint that imports models. |
| **Step 1** — FetchActivity | **New tab appears** here. Per connector: **status**, `fetched_at`, window, **`caps_applied`**, **`errors`**, row/sample **counts**; expandable **truncated** raw JSON per connector. | `run_id`, **Copy JSON** (per connector + full bundle), **Download run** (bounded zip/json). |
| **Step 0.5** — Data reliability | `DataReliabilityReport` tiers + **`overall_confidence`**; **reason codes** / downgrade trail per connector. | Filter “show only low tiers”; copy full report JSON. |
| **Step 2** — WorkItems | `WorkItem` count by `source`/`type`; table preview (id, title, status, timestamps); validation errors if any. | Copy full `work_items[]` JSON (size-capped server-side if huge). |
| **Step 3** — Evidence | Counts of `ActionItem` / `Blocker` / `Decision` kept vs discarded; list kept items with **evidence preview** + source id. | Highlight **failed substring-verification** rejects in a separate sub-panel. |
| **Step 4** — Links | Link count by `confidence`; sample edges (`from` → `to`) with evidence snippets. | Copy `links[]` JSON. |
| **Step 5** — Gaps | `Gap` list with `type`, short description, **evidence pointers** resolved to links (click → highlight work item / evidence). | Copy `gaps[]` JSON. |
| **Step 5.5** — Key achievements | `KeyAchievementsBundle` list with linked `WorkItem` ids + evidence refs. | Empty-state copy when none (deterministic). |
| **Step 5.6** — Raw highlights | `RawHighlightsBundle` entries + `sources[]`. | Copy bundle JSON. |
| **Step 6** — Signals | Full **`SignalsV0`** as structured fields + “why” tooltips populated from **deterministic explain strings** you attach in code (recommended). | Copy signals JSON. |
| **Step 7** — Interpretations | `InterpretationV0[]` with types, confidences, **signal ids referenced**, evidence quotes (preview). | Token/latency metadata for the call (if applicable). |
| **Step 8** — Insights | `InsightsV0[]` cards (priority, confidence, evidence preview). | Copy insights JSON. |
| **Step 6.5** — Arbitration | `InsightArbitrationResult`: **primary** + **supporting** + **`dropped_insights`** with reasons. | Side-by-side “before/after counts” vs Step 8. |
| **Step 9** — Rendering | Final **markdown preview** (same string as would go to Slack) + **lint/compression** pass result (`ok` / `failed` + reasons). | Copy markdown; download `.md`. |
| **Step 10** — Slack | Recent **`job_id`s**, ACK timestamp, final post/update **status**, Slack API errors. | Deep link to Slack message if `ts`/channel available. |
| **Step 10b** — Admin run (parity) | **“Run report (same as Slack)”** UI: form fields match slash command; on success show **`final_markdown`** preview **identical** to what Slack would receive; show `run_id` + link to step panels. | Side-by-side optional: **open same `run_id` in Slack** if a Slack run was used (N/A for admin-only runs—label clearly). |
| **Step 11** — Orchestration | End-to-end **timeline** (waterfall): per-step duration, status, **retry count**; link to raw logs; show **`invocation_source`** (`slack` / `admin`) per run. | Buttons: **“Run with fixture”** (optional, **non-prod** only) **and** **“Run report (same as Slack)”** (prod-allowed when RBAC + audit OK) — both call **this same** orchestration entrypoint. |

**Definition of done (process):** merging step **N+1** without the admin tab section for step **N** complete is a **process FAIL** (CI policy or reviewer checklist), not just a missing nice-to-have.

---

# Default Thresholds (V0)

Canonical defaults for implementers; **override only via versioned config** + tests.

## Data Reliability (Step 0.5)

* **high**

  * ≥80% of configured sources for that connector fetched successfully in the run
  * freshest successful data for that connector **< 24h** old vs `report_as_of` (or window end)

* **medium**

  * ≥50% of configured sources successful
  * freshness **< 72h** for the stalest successful slice (per policy: use worst-of or p90—**pick one in code and document**)

* **low**

  * **<50%** successful **or** any **critical** configured source missing/failed (define “critical” per connector in config: e.g. primary repo, primary Linear team, mandatory Slack channel)

`overall_confidence` = **low** if any critical connector is **low**; else **low** if >50% of connectors are **low**; else **high** only if ≥80% of connectors are **high**; else **medium**.

---

## Arbitration (Step 6.5)

**Insight score components** (sum after mapping insight → gap/signal buckets per strict priority bands above):

* `gap_match` (expectation vs execution family): **+3**
* `repeated_topic`: **+2**
* `blocker_visibility`: **+2**
* `urgent_pressure`: **+1**
* `confidence` on insight: **high +2**, **medium +1**, **low +0**

**Tie-breaker (within same priority band):** highest numeric score → then **lexicographic `insight_id`**.

The **ordered list** in Step 6.5 (expectation gap beats repeated topic, etc.) remains **dominance**: a higher-band insight beats a lower band regardless of numeric tie unless you explicitly define “co-win” (V0: **no co-win**).

---

## Compression (Step 9)

* max insights: **3** (from arbitration only)
* max signals: **5**
* max coaching questions: **4**
* max chars per major section: **500**

---

## Current vs Target Structure

**Current:**

- `vector/domains/connectors/`
- `vector/contracts/`

**Target (example — extend as files land):**

- `frontend/src/admin/AdminTenantLayout.tsx` — add **Manager insight** tab link
- `frontend/src/admin/AdminTenantManagerInsightPage.tsx` — tab UI (per-step panels + JSON viewers)
- `frontend/src/admin/adminRedirects.tsx` (or router module used elsewhere) — register `manager-insight` route
- `backend/.../api/` + `vector/contracts/` — admin JSON routes for pipeline runs / step snapshots **and** `POST …/manager-insight/run` (or equivalent) that enqueues the **same Step 11 job** as Slack with `invocation_source=admin` (exact path follows repo API layout)
- `vector/domains/manager_insights/`
  - `fetch_activity.py`
  - `data_reliability.py`
  - `build_work_items.py`
  - `extract_evidence.py`
  - `link_work_items.py`
  - `compute_gaps.py`
  - `build_key_achievements.py`
  - `build_raw_highlights.py`
  - `compute_signals.py`
  - `arbitrate_insights.py`
  - `generate_interpretations.py`
  - `generate_insights.py`
  - `render_report.py`
  - `slack_orchestration.py`
  - `pipeline_orchestration.py` (or `worker.py` — name to match repo conventions)

👉 Helps onboarding; not critical for correctness.

---

## Related document

- Product and schema source: [manager_insights_vo.md](./manager_insights_vo.md)

