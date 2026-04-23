# V0 Action system — technical specification (Slack → report)

**Status:** implementation-ready V0 spec.  
**Audience:** backend engineers.  
**Normative companion:** [`action_system.md`](./action_system.md) — **global** Action rules (`ActionContext`, `ActionSpec`, executor, permissions, `input_model`/`output_model`, composability) **apply in full** unless this document explicitly **narrows** V0 behavior.

This document defines **only** the V0 product slice: **Slack commands → Actions → user report**, with **live external data** and **a single LLM step** at the end.

---

## 0. Core principle

V0 implements a **pure Action-based** pipeline:

- **Deterministic** except the single registered **`type="llm"`** Action.
- **Composable:** only **`execute_action`** chains child Actions.
- **Explicitly typed:** Pydantic `input_model` / `output_model` per [`action_system.md`](./action_system.md) §2.
- **Callable from:** Slack (V0 adapter) and, unchanged, an LLM tool adapter (future).

---

## 1. V0 constraints (non-negotiable)

| # | Rule |
|---|------|
| 1 | **No ingestion or persistence of report pipeline data** — do not write report payloads, raw fetches, embeddings, or `UserReportContext` to DB tables for this flow. Existing DB use for **auth**, **tenant/membership**, and **connector tokens/config** is allowed only where the product already requires it; those reads are not “report storage.” |
| 2 | **No Celery** (or other async job runners) **for this V0 report flow** — work runs **in the same API process** after Slack is acknowledged (see **§3.5**). No separate job queue. |
| 3 | **No embeddings / vector DB** for V0 report. |
| 4 | **No long-term memory** (no conversational state machine; no RAG store for this flow). |
| 5 | **All report-source data is fetched live** via external APIs (Slack, Linear, GitHub, Notion, peer-review source, etc.) inside **`type="data"`** Actions only. |
| 6 | **Slack slash commands** MUST **acknowledge immediately** (<1s) and MUST **not** block on `report.user`. The report pipeline runs **after** that acknowledgment **in-process** (e.g. FastAPI `BackgroundTasks`); the **user-visible** result is sent via Slack **`response_url`** (see **§3.5**). Connector fetches remain subject to per-source timeouts (§6.1.3). |
| 7 | **One LLM Action** per successful `report.user` invocation: only **`report.generate_user_summary`** performs model inference. That Action **MAY** perform **at most one** additional model call for **format repair** only (§9.0). No LLM in **`data`** or **`aggregation`** handlers (call the registered **`llm`** Action via executor if needed — already the case for summary). |

**Clarification:** `db: Session` may appear in handlers per global Action signature; V0 forbids **using Session to persist report artifacts**, not the presence of Session for ORM-backed identity/connector config already in the codebase.

### 1.1 Normative override (time window)

**V0 uses ONLY `window_days`** on `ReportUserInput` / `UserReportContext` (and related payloads). This **overrides** any conflicting illustrative examples elsewhere (including date-based `window_start` / `window_end` in [`action_system.md`](./action_system.md) §9). Implementations and tests MUST follow **`window_days`** for the shipped V0 Slack → report path.

---

## 2. High-level flow

```
Slack slash request
  → verify Slack auth / signing
  → parse body → { action_name, raw_inputs, response_url }
  → return immediate HTTP 200 + Slack JSON acknowledgment (<1s)  ← §3.5
  → (after response is sent, same worker process)
        → open DB session / resolve tenant_id, actor_user_id → build ActionContext (source="slack", request_id=…)
        → execute_action(db, ctx, action_name, raw_inputs)
             → (if report.user) child execute_action calls …
        → POST final payload to Slack response_url (markdown or structured post)
```

**No business logic** in Slack routes: auth, parse, immediate ACK, schedule work, `ActionContext` + `execute_action` only in the post-ACK job (§3.5). Formatting stays adapter-side.

---

## 3. Slack command layer (V0)

### 3.1 Format

```text
/do <action_name> <key>=<value> [<key>=<value> ...]
```

### 3.2 Example

```text
/do report.user user_id=550e8400-e29b-41d4-a716-446655440000 window_days=30
```

`user_id` MUST be a UUID string accepted by Pydantic `UUID` parsing.

### 3.3 Rules

- `action_name` MUST match registry **`name`** exactly (e.g. `report.user`).
- **Key=value pairs only** (ASCII `=`). No free-form natural language in the command tail.
- **Strict validation:** unknown keys, missing required keys, or type coercion failure → **hard error** to user (no partial run).
- **`ActionContext`** fields (`tenant_id`, `actor_user_id`, `request_id`, `source`) are **not** parsed from the command line; Slack adapter supplies them per [`action_system.md`](./action_system.md) §2.2.

### 3.4 Adapter responsibilities

| Allowed | Forbidden |
|---------|-----------|
| Slack signature / auth verification | Business rules, scoring, merging sources |
| Map Slack workspace + caller → `tenant_id`, `actor_user_id` | Direct HTTP to Linear/GitHub from route |
| Generate `request_id`, set `source="slack"` | Skipping `execute_action` |
| Parse `key=value` → `dict` | Natural language parsing |
| Call **`execute_action`** (in the **post-ACK** job, not before Slack ACK) | Embedding domain invariants inline |
| Schedule post-ACK execution + **`response_url`** delivery | Returning the final report in the initial slash-command HTTP body as the only path |

### 3.5 Slack execution model (normative)

The Slack adapter **MUST** treat platform timeouts as blocking for the **initial** HTTP response only.

| Step | Requirement |
|------|-------------|
| **Verify** | Verify Slack signing secret / request signature on the raw body before any heavy work. |
| **Acknowledge** | Return **HTTP 200** with a Slack-compatible JSON body **within \<1s** (e.g. ephemeral “Working on your report…”). This satisfies Slack’s slash-command interaction window. |
| **Execute** | Run `execute_action` **after** that response is returned, **in the same API process** (e.g. FastAPI `BackgroundTasks` — **not** Celery). |
| **Deliver** | POST the **final** user-visible payload to the `response_url` from the slash command payload. Use `response_type` appropriate for the product (often `in_channel` or `ephemeral` for errors). |
| **Errors** | On validation errors before ACK, return an error payload in the **initial** response if appropriate; on failures **after** ACK, POST an error message to `response_url` (do not leave the user with only the ACK). |

**DB session:** the post-ACK job **MAY** use a **new** DB session (e.g. `session_scope()`), independent of the request-scoped session used only for fast path / signing verification if any.

---

## 4. Action system (V0 profile)

### 4.1 Structure

Every Action **MUST** satisfy **`ActionSpec`** in [`action_system.md`](./action_system.md) §2.3, including:

- `permissions`, `idempotent`, `idempotency_note`, `side_effects`, `errors`, `llm_exposed`
- `handler(db, ctx, payload)` signature
- `input_model` / `output_model` as **`type[BaseModel]`** with `extra="forbid"` on inputs per global spec

**V0 omits `cost_hint` and `latency_hint` as product/runtime policy.** If the shared `ActionSpec` type in code still carries these fields for forward compatibility with the global doc, V0 registrations **SHOULD** leave them at implementation defaults; **no** V0 code path **MUST** branch on them (routing, quotas, “slow” rejection, etc.).

### 4.2 Action types (V0 semantics)

#### 4.2.1 `data` — live fetch only

- **May:** call external HTTP APIs via existing **connectors** / domain clients.
- **V0 — no DB in `data.fetch_*`:** handlers for **`data.fetch_*` MUST NOT** perform **any** ORM / `Session` database access (queries, flushes, writes). Connector tokens and workspace configuration **MUST** be resolved **before** the parallel fetch phase (e.g. in `report.user` preflight or the Slack post-ACK job) using a DB session, then passed into fetches via **in-memory** connector clients, DTOs, or **request-scoped wiring** (e.g. context keyed by `ctx.request_id`) populated only by that preflight — **not** via user-visible slash-command payloads. Handlers keep the global `db` parameter but **MUST NOT** use it in V0 fetch Actions.
- **Must not:** call LLM clients; persist report payloads; enqueue Celery for this flow.
- **Output:** normalized **slice** models (typed) consumed only by aggregation.

#### 4.2.2 `aggregation` — structure only

- **May:** call **`execute_action`** on other Actions when composing (see `report.user`). **`report.build_user_context`** in the preferred V0 pattern **does not** call `execute_action` on `data.*` again: `report.user` runs all `data.*` fetches first, then passes slices as **`report.build_user_context`’s `input_model`** (single merge step, no duplicate HTTP).
- **Must not:** perform direct external HTTP in aggregation handlers (all live IO only in **`data.*`**).
- **Must not:** call LLM libraries directly in aggregation handlers. The only LLM step is the registered Action **`report.generate_user_summary`**, invoked via **`execute_action`** from **`report.user`** (or manually in tests).

#### 4.2.3 `llm` — generation only

- **Input:** structured model only (e.g. `UserReportContext`).
- **Output:** markdown string per **`output_model`** (wrap in a Pydantic type, e.g. `UserSummaryMarkdown`).
- **Must not:** perform external data fetch, mutate business state, or call non-LLM side-effecting APIs.

---

## 5. V0 required action set (registry)

These **`name`** values **MUST** exist in V0 (additional internal Actions are allowed if `llm_exposed=False` and not part of the public report contract).

### 5.1 Data Actions

| `name` | Purpose |
|--------|---------|
| `data.fetch_slack_activity` | Live Slack API: recent messages / activity signals for subject user / window. |
| `data.fetch_linear_activity` | Live Linear API: issues, cycles, urgency for window. |
| `data.fetch_github_activity` | Live GitHub API: PRs, reviews, commits for window. |
| `data.fetch_notion_content` | Live Notion API: linked pages / databases snippets for window. |
| `data.fetch_peer_reviews` | Live API for peer review source (e.g. Google Docs / other connector) — structured snippets only. |

### 5.2 Aggregation Actions

| `name` | Purpose |
|--------|---------|
| `report.build_user_context` | Merge all `data.*` slices into **`UserReportContext`**; filter noise; deterministic transforms only. |

### 5.3 LLM Actions

| `name` | Purpose |
|--------|---------|
| `report.generate_user_summary` | Single LLM call: narrative + coaching from **`UserReportContext`**. |

### 5.4 Composed Action

| `name` | `type` | Purpose |
|--------|--------|---------|
| `report.user` | **`aggregation`** (required per [`action_system.md`](./action_system.md) §5.4) | Entrypoint: orchestrate fetches → context → LLM summary → final packaged output. |

---

## 6. Execution logic: `report.user`

**Entrypoint:** `report.user`.

**`input_model` (minimum):**

```python
class ReportUserInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    window_days: int = Field(ge=1, le=90)
```

**Ordered steps (logical):**

1. **Fetch** — `report.user` invokes each required **`data.fetch_*`** via **`execute_action`** (only here; not inside `report.build_user_context` in the preferred pattern). See **§6.1** (failure + parallelism + timeouts).
2. **Aggregate** — `execute_action(..., "report.build_user_context", <payload containing all slices + `user_id` + `window_days`>)` → **`UserReportContext`** (see §8.1; every slice field is `Slice | None`).
3. **LLM** — `execute_action(..., "report.generate_user_summary", {"context": <UserReportContext>})` → markdown satisfying §10, using system prompt **§9.1**.
4. **Return** — `report.user` **`output_model`** MUST expose final markdown for Slack (e.g. field `markdown: str`); optional echo of `UserReportContext` for admin/debug only behind explicit flags (default off).

**`side_effects` on `report.user`:** MUST list `invokes <name>` for every child Action actually called (all fetches + `report.build_user_context` + `report.generate_user_summary`).

### 6.0 Declared `side_effects` / `invokes` (V0)

In V0, `side_effects` entries (including `invokes <action.name>`) are **informational** for humans and static review. The executor **does not** validate that runtime `execute_action` calls match the declared list.

**Optional (recommended):** the executor **SHOULD** emit a structured log field (or trace attribute) listing each child `name` as `execute_action` runs, for drift detection and ops dashboards.

### 6.1 Fetch failure, parallelism, and executor (normative)

#### 6.1.1 Failure of a `data.fetch_*` Action

When any **`data.fetch_*`** invocation fails (timeout, HTTP 5xx after retry policy, auth error, rate limit exhaustion, validation error from connector, etc.):

| Rule | Requirement |
|------|-------------|
| **Continue** | `report.user` **MUST** continue execution; it **MUST NOT** abort the whole pipeline solely because one source failed (unless **all** sources failed — product MAY then return a dedicated error; if at least one slice succeeds, continue). |
| **Slice binding** | The corresponding slice argument for **`report.build_user_context`** **MUST** be set to **`None`** (Python `None` / JSON `null` in the merged payload). |
| **Logging** | Each failure **MUST** be logged at **warning** or **error** with: `action` name, `ctx.request_id`, `ctx.tenant_id`, source key (e.g. `slack`), and a **non-secret** error code or message. |
| **No fabrication** | Downstream **`report.build_user_context`** and the **LLM** **MUST NOT** invent metrics, achievements, signals, or action items for that missing source (see §8, §9.2, §10). |

#### 6.1.2 Parallelism and executor

- **`data.fetch_*` Actions SHOULD** be executed **in parallel** when they are **independent** (no shared mutable prefetch state; same read-only `ctx`).
- The **executor** (or a thin V0 orchestration helper used **only** from `report.user`) **MAY** use **`asyncio.gather`** (async) or a **bounded thread pool** to run child `execute_action` calls concurrently, provided each child still runs: validate input → permissions → handler → validate output per [`action_system.md`](./action_system.md).
- **DB session safety:** parallel child Actions **MUST NOT** share one `Session` for ORM work. Combined with **§4.2.1** (no DB in `data.fetch_*`), the default V0 pattern is: **preflight** connector/config reads on **one** session (sequential), then run fetches **without** DB access in parallel threads/tasks.
- **Ordering** of results before **`report.build_user_context`** MUST be deterministic (e.g. sort by fixed source name order) so tests and logs are stable.

#### 6.1.3 Per-source timeouts (fetch phase)

Each **`data.fetch_*`** call from `report.user` **MUST** enforce a **hard wall-clock timeout** in the range **3–5 seconds per source** (pick a single constant per source in code, document in settings). On timeout, treat as **§6.1.1 failure** (`None` slice + log).

---

## 7. Data fetching rules

Each **`data.fetch_*`** handler:

1. Uses **tenant-scoped** connector credentials supplied **in memory** after preflight (§4.2.1); never raw tokens in the Slack-visible Action payload.
2. Calls **external APIs** and normalizes into a **fixed Pydantic `output_model`** for that Action (slice).
3. **Does not** INSERT/UPDATE report tables; does not enqueue background jobs for report materialization; **does not** use `Session` for ORM access in V0 (§4.2.1).

### 7.1 Bounds and selection (MUST — every `data.fetch_*`)

Each **`data.fetch_*`** implementation **MUST** enforce all of the following:

| Rule | Requirement |
|------|-------------|
| **Bounded time window** | All queries **MUST** be scoped to a window derived from **`window_days`** (and optional clock “as of” = request time unless otherwise specified). Do not fetch unbounded history. |
| **Maximum items** | Each slice **MUST** define and enforce a **maximum count** per list field (e.g. messages, issues, PRs, doc blocks, review snippets). Constants **MUST** be documented next to the Action in code (e.g. `MAX_SLACK_MESSAGES = 50`). |
| **Prioritization** | When truncating, items **MUST** be ordered **most relevant first** (documented rule per connector: e.g. Slack by recency + thread engagement; Linear by updated-at + priority; GitHub by updated-at + review state). |
| **One retry** | On **transient** failure (timeouts, connection reset, HTTP **429** with `Retry-After`, HTTP **5xx**), the handler **MUST** perform **exactly one** retry (two attempts total including the first). Non-transient errors (4xx except retryable 429) **MUST NOT** retry. |
| **Rate limits** | Handlers **MUST** respect provider rate limits (backoff, respect `Retry-After`, token bucket if already in connector). |
| **Wall timeout** | Obey **§6.1.3** (3–5s per source) in addition to any finer client timeouts. |

### 7.2 Example contract shape (`data.fetch_slack_activity` output — illustrative fields)

```python
class SlackActivitySlice(BaseModel):
    message_samples: list[str] = Field(default_factory=list)
    activity_counts: dict[str, int] = Field(default_factory=dict)
    notable_interactions: list[str] = Field(default_factory=list)
```

Other `data.*` slices MUST be typed similarly; **`report.build_user_context`** is the **only** place slices merge into **`UserReportContext`**.

---

## 8. Aggregation: `report.build_user_context`

**Role:** single choke point for **deterministic** merge/filter/signal extraction.

**Input model:** MUST accept **`user_id`**, **`window_days`**, and **one optional field per `data.*` slice** (e.g. `slack: SlackActivitySlice | None`, `linear: LinearActivitySlice | None`, …). **`None`** means that source **failed or was skipped** (see §6.1.1). **Recommended:** explicit optional fields per source (no union soup).

**Output model:** **`UserReportContext`** — exact sections below. **`user_id`** and **`window_days`** on the context **MUST** match the request (for LLM section titles and “Last *N* days” copy).

### 8.1 `UserReportContext` (normative schema)

All sub-objects use Pydantic models with `extra="forbid"` unless noted. Lists default to empty.

```python
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeliveryMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues_completed: int = Field(ge=0)
    estimated_points: float = Field(ge=0)
    active_projects: int = Field(ge=0)
    open_urgent_items: int = Field(ge=0)


class KeyAchievement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    impact: str


class ExecutionSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    trend: Literal["up", "down", "stable"]


class OpenActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    status: Literal["open", "done", "stale"]
    age_days: int = Field(ge=0)


class PeerFeedbackSignals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summarized_insights: str
    notable_quotes: list[str] = Field(default_factory=list)


class UserReportContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Subject and window (MUST mirror ReportUserInput / build step inputs)
    user_id: UUID
    window_days: int = Field(ge=1, le=90)

    # Which upstream fetches produced None (for LLM uncertainty copy)
    unavailable_sources: list[str] = Field(
        default_factory=list,
        description='Stable source keys, e.g. "slack", "linear", "github", "notion", "peer_reviews"',
    )

    # 1. Delivery metrics
    delivery_metrics: DeliveryMetrics

    # 2. Key achievements (recent wins)
    key_achievements: list[KeyAchievement] = Field(default_factory=list)

    # 3. Execution signals
    execution_signals: list[ExecutionSignal] = Field(default_factory=list)

    # 4. Open action items
    open_action_items: list[OpenActionItem] = Field(default_factory=list)

    # 5. Peer feedback signals
    peer_feedback: PeerFeedbackSignals

    # 6. Raw highlights (optional, for LLM grounding — curated, not full API dumps)
    raw_highlights: list[str] = Field(default_factory=list)
```

**Rules:**

- **No raw API dumps** in `raw_highlights` — only short, curated strings (IDs + human label, key event one-liners).
- Missing source data: use **zero / empty / explicit “unknown”** fields per field semantics; **do not fabricate** numbers or events. Populate **`unavailable_sources`** with stable keys for every slice that was **`None`** at aggregation input (including after timeout).
- **`user_id`** and **`window_days`** **MUST** be set on every **`UserReportContext`** so the LLM can render **“Last {window_days} days”** without guessing.

---

## 9. LLM layer: `report.generate_user_summary`

**`input_model`:** wraps `UserReportContext` (e.g. `GenerateUserSummaryInput(context: UserReportContext)`).

**`output_model`:** e.g. `UserSummaryMarkdown(markdown: str)` where **`markdown`** conforms to §10.

**Responsibilities:**

- Transform structured context into **narrative**, **insights**, and **coaching recommendations** per §10 section headings, under the **system prompt in §9.1** (normative).

**Forbidden:**

- Network fetch, connector calls, DB writes, mutation of tenant state, calling **`execute_action`** from inside this handler (leaf LLM Action).

**`side_effects`:** MUST document LLM inference API usage; **no** other side effects.

### 9.0 Markdown format validation and retry (normative)

Strict H2 heading validation (§10) can fail on otherwise acceptable model output. **`report.generate_user_summary` MUST** implement:

1. **Generate** markdown from the model using system prompt §9.1 (first attempt).
2. **Validate** headings per §10 (order, spelling, level-2).
3. **If invalid:** issue **exactly one** retry call to the model with a **user** (or secondary system) instruction whose sole purpose is format repair, e.g. *“Fix Markdown structure only: keep factual content identical. Ensure all six H2 headings from §10 appear once, in order, with exact titles.”* Do **not** supply new facts or JSON beyond what the first pass already had.
4. **If still invalid after retry:** return a **structured error** to the caller (do not POST raw broken markdown to Slack as the final `response_url` payload).

This yields **at most two** LLM generations for the summary step (one primary + one format-repair). It does **not** violate §1 item 7 (“single LLM step”) — that rule refers to **one logical summarization Action**, not retry-for-format within that Action.

**Implementation note:** Python may centralize steps 1–4 in `vector.domains.actions.user_report_markdown.user_summary_markdown_with_heading_retry`, passing a `format_fix` callable whose model call includes `FORMAT_FIX_RETRY_USER_MESSAGE` (same module) as the repair instruction.

### 9.1 System prompt (normative — MUST use verbatim except `{…}` injection)

The implementation **MUST** send a **system** message equivalent to the following (placeholders filled with **serialized `UserReportContext` JSON** only; no extra scraped text):

```text
You are an experienced engineering manager writing an internal execution report about ONE team member (the report subject). The reader is the subject’s manager (or skip-level) who needs a clear, honest picture of delivery and behaviors over a fixed time window.

You will receive a single JSON object: the UserReportContext. It always includes:
- user_id, window_days, unavailable_sources
- delivery_metrics, key_achievements, execution_signals, open_action_items, peer_feedback, raw_highlights

Rules (violation = incorrect output):

1. FACTUALITY: You may ONLY attribute facts, numbers, trends, achievements, signals, and action items that are DIRECTLY supported by fields inside the JSON. If a section of the report would require data that is missing, empty, or you are not fully certain about, you MUST write explicit uncertainty (e.g. “Not enough data in this window to assess X.” or “Source unavailable: Slack.”). You MUST NOT invent metrics, achievements, execution signals, or action items.

2. MISSING SOURCES: If `unavailable_sources` is non-empty, you MUST mention which sources were unavailable (use the exact strings from the list) and you MUST NOT fill gaps with guesses.

3. TONE: Professional, direct, constructive. No flattery. No blame theater. Prefer specific behaviors and outcomes over adjectives.

4. MANAGER LENS: Frame insights as what a good EM would notice: delivery predictability, follow-through, collaboration, quality, escalation, focus, and growth. When data is thin, say so and suggest what to observe next — without inventing past behavior.

5. MARKDOWN STRUCTURE: Your entire reply MUST be GitHub-flavored Markdown and MUST contain EXACTLY these level-2 headings, in this order, with this spelling and numbering:

## 1. Delivery Pulse (Last X Days)
## 2. Recent Wins
## 3. Development Signals
## 4. Open Action Items
## 5. Coaching Questions
## 6. One Priority

6. WINDOW LABEL: Keep the §10 heading text exactly (`## 1. Delivery Pulse (Last X Days)`). In the first sentence of that section’s body, state the real window using `window_days` (e.g. “Reporting period: last **30** days per UserReportContext.”).

7. COACHING QUESTIONS: Section 5 MUST contain 3–7 concrete questions the manager could ask in a 1:1, grounded ONLY in the JSON. If data is insufficient, ask meta-questions about how to gather signal — do not invent incidents.

8. ONE PRIORITY: Section 6 MUST give exactly ONE primary recommendation: what to do next and why it matters, grounded in the JSON. If the JSON does not support a strong recommendation, recommend a discovery step (e.g. clarify scope with IC) and state why certainty is low.

UserReportContext JSON follows:
{USER_REPORT_CONTEXT_JSON}
```

**Injection note:** `{USER_REPORT_CONTEXT_JSON}` is the **canonical JSON** serialization of the validated **`UserReportContext`** (compact, UTF-8). No additional user message is required for V0; if a user message is used, it **MUST** be empty or a fixed string with no extra facts.

### 9.2 LLM anti-fabrication (hard requirements)

The model output **MUST NOT**:

- Invent **metrics** not supported by `delivery_metrics` and related lists.
- Invent **achievements** not supported by `key_achievements` (if empty, say there were no captured wins in context).
- Invent **execution signals** not supported by `execution_signals`.
- Invent **open action items** not supported by `open_action_items`.

When any of those structures are empty or ambiguous, the markdown **MUST** include an **explicit uncertainty** statement in the relevant section (and reference **`unavailable_sources`** when applicable).

---

## 10. Report output format (mandatory markdown)

The string returned by **`report.generate_user_summary`** (and echoed in `report.user` output) **MUST** be valid markdown and **MUST** contain **exactly** these **H2 headings** in **this order** (titles and casing as written):

```markdown
## 1. Delivery Pulse (Last X Days)

## 2. Recent Wins

## 3. Development Signals

## 4. Open Action Items

## 5. Coaching Questions

## 6. One Priority
```

### 10.1 Section content rules

| Section | Required content |
|---------|------------------|
| **1. Delivery Pulse (Last X Days)** | Use **`UserReportContext.window_days`** as **`X`** in prose (e.g. “Last **30** days …”). Bullet or compact list: issues completed (or equivalent), active projects, urgent items — **only** values justified by `UserReportContext.delivery_metrics` / related fields; if metrics are zeros due to missing sources, **state uncertainty** per §9.2. |
| **2. Recent Wins** | Bullet list; each bullet **title** + short **explanation** sourced from `key_achievements`. |
| **3. Development Signals** | For each signal: **title**, **explanation**, **trend** (`up` / `down` / `stable`) aligned with `execution_signals`. |
| **4. Open Action Items** | Group by urgency; **highlight stale** items (e.g. bold or subheading) using `status` + `age_days`. |
| **5. Coaching Questions** | Numbered or bulleted **actionable** questions for the manager, grounded in context. |
| **6. One Priority** | Exactly **one** primary recommendation: **what to do next** and **why it matters** (short paragraph). |

**Validation:** implement a **post-condition** per **§9.0** (validate → single format-retry → structured error if still invalid). Do not silently send broken markdown to Slack.

### 10.2 Partial data banner (user-facing)

Let **`V0_REPORT_SOURCE_KEYS`** be the canonical five sources: `slack`, `linear`, `github`, `notion`, `peer_reviews` (stable strings, aligned with `unavailable_sources` in §8.1).

When **all** of the following hold:

- `UserReportContext.unavailable_sources` is **non-empty**, and
- **at least 50%** of the five sources are unavailable (i.e. `len(unavailable_sources) >= 3` when using the full five-source set),

then the markdown delivered to Slack (`report.user` final output / `response_url`) **MUST** begin with the following **verbatim prefix line** (line break after), followed by the normal report body:

```text
⚠️ Partial data: some sources unavailable (Slack, GitHub, …)
```

Replace the parenthetical with a **comma-separated** list of **human-readable** source labels derived from the unavailable keys (e.g. `slack` → `Slack`), **all** sources that are unavailable for this run, not a literal ellipsis. Keep the leading warning emoji and wording through “unavailable ” consistent for searchability in support tooling.

---

## 11. Important rules (V0)

1. **No raw dumps to LLM** — only **`UserReportContext`** (curated `raw_highlights` max).
2. **No mega-actions** — keep `data.*` single-source; keep aggregation pure; keep one `llm` Action.
3. **No hidden inputs** — [`action_system.md`](./action_system.md) `ActionContext` + explicit payload only.
4. **No report persistence** — §1.
5. **LLM only in the summary Action** — §1 item 7 (including §9.0 format-retry cap).
6. **Partial fetch failure** — §6.1.1: continue, `None` slice, log, no fabrication.
7. **Bounded fetches** — §7.1: max items, window from `window_days`, prioritization, one retry, rate limits, per-source timeout.
8. **Partial data UX** — §10.2: ≥50% sources unavailable → mandatory warning prefix.
9. **LLM format recovery** — §9.0: one format-only retry before structured error.

### 11.1 Recommended structured log (end of `report.user`)

For observability (optional but **recommended**), when `report.user` completes (success or handled failure), emit **one** structured log line (JSON fields or logging `extra`) including at minimum:

```json
{
  "action": "report.user",
  "request_id": "...",
  "tenant_id": "...",
  "user_id": "...",
  "duration_ms": 0,
  "sources": {
    "slack": "ok|timeout|error",
    "github": "ok|timeout|error",
    "linear": "ok|timeout|error",
    "notion": "ok|timeout|error",
    "peer_reviews": "ok|timeout|error"
  },
  "status": "success|partial_success|fail"
}
```

- **`user_id`:** report subject (`ReportUserInput.user_id`), not necessarily `ctx.actor_user_id`.
- **`sources`:** map each canonical key to the outcome of that fetch phase (including `timeout` per §6.1.3).
- **`status`:** e.g. `partial_success` when the pipeline produced markdown but at least one source failed; `fail` when no usable output.

---

## 12. Integration with existing backend

| Layer | V0 responsibility |
|-------|-------------------|
| `vector/domains/actions/` | Action modules, registration bootstrap, **`execute_action`**, handlers calling domain/connectors. |
| `vector/domains/connectors/` (and related) | HTTP clients, OAuth token usage — invoked **from `data.*` handlers** (or thin domain services they call). |
| `vector/domains/*` | Business rules for “what to fetch,” rate limits, error translation — **not** skipped. |
| `vector/api/http/routes/` | Slack route: verify, parse, **immediate ACK**, schedule post-ACK **`execute_action`**, **`response_url`** delivery (§3.5). |

**Forbidden:** Actions that **bypass** domain connector rules or open arbitrary HTTP not covered by connector policy.

---

## 13. Future compatibility

A future LLM agent:

1. Selects **`name`** + JSON **`arguments`** matching `input_model`.
2. Builds **`ActionContext`** with `source="llm"` and appropriate `request_id`.
3. Calls the **same** **`execute_action`** as Slack.

**No change** to Action `name`, `input_model`, or handler orchestration required for that migration.

---

## 14. Reference checklist (implementation)

Use as **final sign-off** after completing **§15**. Each item MUST be true before calling V0 “done.”

- [ ] All actions in §5 registered with full `ActionSpec` per [`action_system.md`](./action_system.md) (V0 omits runtime use of `cost_hint` / `latency_hint`; §4.1).
- [ ] `report.user` is `type="aggregation"` with full `invokes …` `side_effects` (informational per §6.0).
- [ ] `report.build_user_context` output matches §8.1 schema (**includes `user_id`, `window_days`, `unavailable_sources`**).
- [ ] Fetch failures implement §6.1.1 (continue, `None`, structured log).
- [ ] Each `data.fetch_*` implements §7.1 + §6.1.3 (caps, window, ordering, retry, rate limit, timeout) and **no DB** in handler (§4.2.1).
- [ ] Parallel fetch orchestration per §6.1.2 where independent; **no shared `Session`** across parallel children (§6.1.2).
- [ ] `report.generate_user_summary` uses system prompt **§9.1**, output validated against §10 headings, **§9.0** retry path covered in tests.
- [ ] Post-generation check enforces §9.2 (no invented lists beyond JSON support — spot-check in tests).
- [ ] Slack adapter: **§3.5** immediate ACK + post-ACK `execute_action` + **`response_url`** delivery; zero domain branching beyond parse + map identity.
- [ ] §10.2 partial-data banner when ≥50% sources unavailable.
- [ ] No Celery enqueue on `report.user` path; no report tables written.

---

## 15. Phased implementation plan

**Rules for using this plan**

- Complete phases **in order** unless a later phase only adds an **optional** connector and you explicitly stub it.
- Each phase has a **small scope**, a **deliverable**, and **exit criteria** so you can merge and demo without carrying the whole V0.
- Stop at any phase boundary: the system should still **run** (possibly with stubs or fewer live sources).

---

### Phase 1 — Action skeleton (no Slack, no external IO)

**Scope:** Global Action plumbing only.

**Tasks**

- Add `vector/contracts/actions/context.py` with **`ActionContext`** per [`action_system.md`](./action_system.md).
- Add `vector/domains/actions/types.py`, `registry.py`, `bootstrap.py`, `executor.py` per global spec: validate in → permissions hook → log → handler → validate out.
- `enforce_permissions`: implement **deny-by-default** or a temporary **allow-list** for dev only (document); must accept full **`ctx`**.

**Deliverable:** `execute_action` callable from a unit test with **one** dummy Action (`name="debug.echo"`, `type="aggregation"`, round-trip payload).

**Exit criteria**

- Unknown action name → stable error.
- Invalid payload → validation error before handler.
- Handler return wrong shape → output validation error.

---

### Phase 2 — Contracts only (Pydantic, no handlers)

**Scope:** All V0 **I/O models** in one place.

**Tasks**

- Define slice `output_model` types for each `data.fetch_*` (can be minimal fields first; expand later).
- Define `ReportUserInput`, `BuildUserContextInput`, `UserReportContext` (§8.1 including `user_id`, `window_days`, `unavailable_sources`), `GenerateUserSummaryInput`, `UserSummaryMarkdown`.
- Apply `ConfigDict(extra="forbid")` on all **input** models.

**Deliverable:** `vector/contracts/actions/v0_report.py` (or split files) importable with **no** circular deps.

**Exit criteria**

- `UserReportContext.model_json_schema()` usable for docs/tests.
- No handler code required to merge this PR.

---

### Phase 3 — `report.build_user_context` (deterministic only)

**Scope:** Aggregation that merges **optional** slices into **`UserReportContext`**; no HTTP.

**Tasks**

- Implement handler: copy `user_id` / `window_days`; fill `unavailable_sources` for each `None` slice; merge non-`None` slices into metrics / lists per §8 rules (initial merge logic can be **minimal** but **must not** invent data).
- Register Action with full `ActionSpec` (`permissions`, `side_effects`, etc.).

**Deliverable:** Unit tests with fixtures: all slices present, all `None`, mixed.

**Exit criteria**

- Output always validates as `UserReportContext`.
- `unavailable_sources` correct for every `None` input field.

---

### Phase 4 — Stub `data.fetch_*` + `report.user` orchestration

**Scope:** End-to-end **code path** with **fake** data (no real APIs yet).

**Tasks**

- Register all five `data.fetch_*` names; handlers return **empty but valid** slices (or tiny fixed fixtures).
- Implement `report.user`: parallel or sequential executor helper; **§6.1.1** behavior (force failure in one handler in test → `None` + log + continue).
- Call `report.build_user_context`, then a **stub** `report.generate_user_summary` that returns fixed markdown **matching §10 headings** (no real LLM).

**Deliverable:** Integration test: `execute_action(..., "report.user", …)` → markdown string.

**Exit criteria**

- No connector credentials required to run tests.
- Parallelism + failure semantics covered by tests.

---

### Phase 5 — Real LLM: `report.generate_user_summary`

**Scope:** Replace stub LLM Action only.

**Tasks**

- Wire real inference client in **`report.generate_user_summary`** handler.
- Inject system prompt **§9.1** verbatim (JSON placeholder).
- Post-validate markdown headings §10; map API failures to `errors` contract.

**Deliverable:** Test with **real** `UserReportContext` fixture (from Phase 3 fixtures) → assert headings present.

**Exit criteria**

- §9.2 enforced in prompt + manual or automated check on golden outputs.

---

### Phase 6 — Live `data.fetch_slack_activity`

**Scope:** **One** connector end-to-end.

**Tasks**

- Implement fetch via existing Slack connector patterns; §7.1 (window, caps, order, retry, rate limit); §6.1.3 timeout.
- Map errors to `None` + log at `report.user` level per §6.1.1 (handler may raise; orchestrator catches — pick **one** pattern and document).

**Deliverable:** Manual or integration test against sandbox Slack.

**Exit criteria**

- Slice validates; never exceeds documented max items; respects timeout.

---

### Phase 7 — Live `data.fetch_linear_activity`

Same pattern as Phase 6 for Linear only.

**Exit criteria:** §7.1 + §6.1.3 satisfied for Linear slice.

---

### Phase 8 — Live `data.fetch_github_activity`

Same pattern as Phase 6 for GitHub only.

**Exit criteria:** §7.1 + §6.1.3 satisfied for GitHub slice.

---

### Phase 9 — Live `data.fetch_notion_content`

Same pattern as Phase 6 for Notion only.

**Exit criteria:** §7.1 + §6.1.3 satisfied for Notion slice.

---

### Phase 10 — Live `data.fetch_peer_reviews`

Same pattern for peer-review connector (Google Docs or chosen backend).

**Exit criteria:** §7.1 + §6.1.3; clear behavior when connector not configured (`None` + `unavailable_sources`).

---

### Phase 11 — Slack `/do` adapter

**Scope:** Thin HTTP/Slack surface only.

**Tasks**

- Parse `/do` per §3; verify signing secret; return **immediate ACK** JSON \<1s (**§3.5**).
- In a post-ACK in-process task: open DB session as needed; build `ActionContext` (`source="slack"`, `request_id`); call `execute_action` for the parsed `action_name` (including `report.user` when registered).
- POST final markdown (or error text) to **`response_url`**; do not rely on the initial HTTP response for the full report.

**Deliverable:** Manual run from Slack staging workspace.

**Exit criteria**

- §3.4 + §3.5 satisfied; zero business logic in the route beyond parse / identity map / scheduling.
- §14 checklist fully satisfied for V0.

---

### Phase map (dependencies)

```text
Phase 1 (skeleton)
    → Phase 2 (contracts)
        → Phase 3 (build_user_context)
            → Phase 4 (stubs + report.user)
                → Phase 5 (real LLM)
                    → Phases 6–10 (live connectors; any order after Phase 5,
                      but sequential order reduces integration risk)
                        → Phase 11 (Slack)
```

**Optional split:** If Phase 4 is still large, split into **4a** (`report.user` + stubs only) and **4b** (parallelism + failure injection tests only).

---

## 16. Strategic Direction — RAG + Tool Orchestration (Post-V0)

### 16.1 Positioning

V0 is **not** a RAG system. V0 is a **deterministic Action-based execution layer**: live `data.*` fetches, deterministic `aggregation` (including `report.build_user_context`), and a **single logical LLM Action** for final narrative generation. There is **no retrieval** over a historical corpus, **no long-term conversational memory**, **no embeddings**, and **no vector database** on the V0 report path.

> V0 is intentionally designed so that RAG and LLM tool orchestration can be added later without refactoring the Action system.

### 16.2 Target architecture (V1 → V2)

Future stages extend the same primitives:

- **Tool orchestration:** an LLM runtime (or agent) **selects and chains** registered Actions via `execute_action`, using stable `name` values and Pydantic `input_model` / `output_model` as tool contracts.
- **RAG:** a **retrieval layer** supplies historical or indexed context as **structured inputs** to aggregation and, ultimately, to the `llm` Action—still through typed models and the executor, not ad hoc prompts.

**Target flow (conceptual):**

```text
LLM (orchestrator)
  → selects / chains Actions (tool calls → execute_action)
  → optionally invokes retrieval-backed data Actions
  → aggregation builds structured context (e.g. UserReportContext or successor models)
  → llm Action generates output from that context only
```

### 16.3 What V0 already establishes (foundation)

V0 is not an end state; it **locks in** the pieces required for both tools and RAG later:

1. **Action system (tools):** stable global `name`, typed I/O, registry, `execute_action`, permissions, logging, and composability rules per [`action_system.md`](./action_system.md).
2. **Structured context (`UserReportContext`):** deterministic, bounded, explicit fields suitable as the **only** payload shape for the summary LLM in V0—this pattern generalizes to richer context objects when retrieval exists.
3. **Strict separation of kinds:** `data` = IO, `aggregation` = deterministic merge/orchestration, `llm` = generation only—preserved so that new IO (including retrieval) remains in `data`, not in prompts.

These are **required primitives** for safe tool orchestration and for RAG that respects the same boundary discipline.

### 16.4 What is intentionally excluded from V0

The following are **out of scope** for the V0 Slack → report slice (see §1):

- embeddings
- vector DB
- semantic retrieval over a managed historical index
- long-term memory stores for this flow
- historical indexing / materialization of report pipeline data for retrieval

> These are deferred to avoid premature complexity and maintain deterministic behavior in V0.

### 16.5 RAG introduction path (future)

RAG becomes appropriate when the product needs **historical analysis**, **trend detection**, **multi-period reasoning**, or other capabilities that cannot be satisfied by live connector slices alone.

**Intended pattern:**

- Add retrieval as **new `data.*` Actions** (e.g. `data.retrieve_user_history` or domain-specific fetchers) that return **typed slice models**, not prose blobs.
- Feed retrieval outputs into **`report.build_user_context`** (or a successor aggregation Action) so merged context remains **structured and validated**.
- The **`llm`** Action continues to consume **only** structured context (Pydantic-validated), not raw index hits.

### 16.6 Critical invariant (must not be broken)

The LLM must **NEVER** receive raw unstructured retrieval output (full chunks, dump JSON from a search engine, unbounded hit lists, etc.).

**Always:**

```text
retrieval → structured context (validated models) → llm Action
```

**Never:**

```text
retrieval → raw dump → LLM
```

Violations break auditability, safety gates tied to `ActionContext`, and the single-source-of-truth schema model.

### 16.7 Migration path

| Stage | Description |
| ----- | ----------- |
| V0 | Deterministic Action pipeline for Slack → report; live external `data.*`; single summary `llm` Action; constraints in §1. |
| V1 | LLM tool runtime **selects and chains** Actions via the same executor and contracts; composition depth and policies expand; V0 Actions remain valid tools. |
| V2 | **RAG:** retrieval enters as additional **`data.*`** sources feeding aggregation; structured context only into `llm`. |
| V3 | Full **execution intelligence** platform: broader tool surface, retrieval, evaluation, and ops—still anchored on the Action system and typed context invariants above. |

---

*End of V0 specification.*
