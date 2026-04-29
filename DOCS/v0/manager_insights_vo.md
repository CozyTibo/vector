## The flow

1. You run a simple Slack command (no prompts, just fields).
2. Slack immediately replies: *“Working on it…”*
3. In the background, Vector:
    - pulls data from tools
    - merges everything into one view
    - generates a report
4. A few seconds later, the full report shows up in Slack.

---

## `FetchActivity`

For each run, Vector pulls fresh data (nothing precomputed):

- **Slack** `data.fetch_slack_activity`
  **We pull:**
  - Last **N days messages authored by the user**
  - Thread participation (replies vs root messages)
  - Channels they’re active in
  - Mentions (`@user`) and replies received
  - Reaction counts (basic signal of engagement)
  **We keep (after filtering + caps):**
  - `message_samples` (max ~30–50)
    - short cleaned snippets (no full dumps)
  - `activity_counts`
    - messages_sent
    - threads_participated
    - replies_received
  - `notable_interactions`
    - e.g. “resolved incident thread”, “active in #project-x”
    **What this becomes in the report:**
    
    - **Execution Signals**
        - responsiveness
        - collaboration intensity
    - **Raw highlights**
        - key conversations
    - **Coaching Questions**
        - communication gaps / overload / silence
- **Linear** `data.fetch_github_activity`
  **We pull:**
  - Issues assigned to the user
  - Issues completed in window
  - Priority / urgent issues
  - Cycle info (if exists)
  - Last updated timestamps
  **We keep:**
  - `issues_completed` (count)
  - `open_urgent_items` (count)
  - `active_projects` (derived from issue grouping)
  - lightweight issue summaries (titles only)
  **What this becomes in the report:**
  - **Delivery Pulse**
    - core output signal
  - **Open Action Items**
    - aging or stuck issues
  - **Recent Wins**
    - completed meaningful work
- **GitHub** → `data.fetch_github_activity`
    
    ### We pull
    
    - PRs **opened** by the user
    - PRs **merged**
    - PRs **still open**
    - PRs **reviewed** (comments + approvals)
    - Commits (lightweight metadata only)
    - PR timestamps (created, updated, merged)
    
    ---
    
    ### We keep (after caps)
    
    - `prs_opened_count`
    - `prs_merged_count`
    - `prs_reviewed_count`
    - `open_prs` (titles + age)
    - `merged_pr_titles` (top N)
    - `review_activity` (count + short notes)
    
    ---
    
    ### What this becomes in the report
    
    - **Delivery Pulse**
        - shipping velocity (merged PRs)
    - **Execution Signals**
        - review participation
        - merge consistency
    - **Open Action Items**
        - stale PRs
    - **Raw highlights**
        - “Merged PR: X”
        - “Reviewed critical change in Y”
- **Gemini**  `data.fetch_call_activity`
  (*Assuming Google Meet / transcripts / call summaries*)
  ### We pull
  - Calls attended in window
  - Call titles / context
  - Transcript summaries (NOT full transcripts)
  - Speaking participation (if available)
  - Action items extracted (if structured)
  ---
  ### We keep
  - `call_count`
  - `meeting_types` (1:1, team sync, incident, etc.)
  - `key_discussions` (short summaries)
  - `action_items` (if clearly extracted)
  ---
  ### What this becomes in the report
  - **Execution Signals**
    - involvement in coordination / leadership
  - **Key Achievements**
    - “Led incident review call”
  - **Open Action Items**
    - follow-ups from meetings
  - **Raw highlights**
    - “Discussed rollout strategy for X”
- **Notion** `data.fetch_notion_content`
  **We pull:**
  - Pages owned or edited by user
  - Relevant project docs (linked to work)
  - Last edited timestamps
  **We keep:**
  - Page titles
  - Short extracted summaries (first lines / headings)
  - Edit activity counts
  **What this becomes in the report:**
  - **Recent Wins**
    - docs shipped, specs written
  - **Execution Signals**
    - documentation hygiene
  - **Raw highlights**
    - “wrote spec for X”

It only looks at a **recent time window** (e.g. last 30 days)

- Slack: ~50 messages
- GitHub: ~30 PRs
- Linear: ~50 issues
- Notion: ~20 pages
- Calls: ~20 meetings

👉 Prevents explosion + keeps LLM grounded

---

# `UserReportContext`

This is what the LLM receives.

Everything is **grounded, cited, and uncertainty-aware**.

---

## 1. Delivery Metrics (Facts)

Deterministic, non-interpreted:

- `issues_completed`
- `prs_merged_count`
- `active_projects`
- `open_urgent_items`

👉 Used as baseline only (never conclusions on their own)

---

## 2. Work Items (Atomic Units)

No “topics” as truth.

Only **observable artifacts**.

```
work_item:
  id: "issue_123"
  type: "issue" | "pr" | "doc" | "call"

  title: "Billing retry fails under load"

  timestamps:
    created_at:
    updated_at:
    closed_at:

  status:
    open | in_progress | merged | closed

  project: "billing"

  text_content:
    summary: "...normalized short text..."

  source: linear | github | notion | call
```

---

## 3. Semantic Links (Best-effort, NOT truth)

Work items may be linked if similarity is high.

```
link:
  from: "call_3"
  to: "issue_123"

  type: "semantic_match"

  confidence: high | medium | low

  evidence:
    - "retry logic failing under load" (call)
    - "billing retry fails under load" (issue)
```

---

### Rules

- Only `high` confidence links are safe for reasoning
- `medium` → allowed but must be hedged
- `low` → ignored

---

## 4. Extracted Evidence (Citation-based ONLY)

No free-form extraction.

---

### a. Action Items

```
action_item:
  text: "fix retry logic"

  source: "call_3"

  evidence: "we should fix retry logic this week"

  linked_work_items: ["issue_123"]  // optional

  confidence: high | medium
```

---

### b. Blockers

```
blocker:
  text: "retry fails under load"

  source: "call_3"

  evidence: "it still breaks under load"

  linked_work_items: []

  confidence: medium
```

---

### c. Decisions

```
decision:
  text: "prioritize billing fixes"

  source: "call_2"

  evidence: "we’ll prioritize billing this week"

  confidence: high
```

---

👉 If no evidence span → **discarded**

---

## 5. Expected vs Actual Work

Core abstraction replacing “topics”.

---

### Expected Work (from discussions & docs)

```
expected_work:
  - action_item_id
  - linked_work_items (if any)
```

---

### Actual Work (from systems)

```
actual_work:
  issues: [...]
  prs: [...]
```

---

### Derived Gaps (computed BEFORE LLM)

```
gap:
  type: "expected_not_executed"

  description: "action item has no linked issue or PR"

  evidence:
    action_item: ...
    linked_items: []
```

Other gap types:

- `discussed_not_linked_to_work`
- `blocker_not_tracked`
- `doc_not_connected_to_execution`

---

👉 These are **structured observations**, not judgments

---

## 6. Key Achievements (Strict)

Only when:

- issue closed OR PR merged
AND
- optionally reinforced by:
    - doc
    - call confirmation (with evidence)

---

## 7. Raw Highlights (Facts Only)

Examples:

- “Billing retry mentioned in 3 calls”
- “No linked PR found for that discussion (high-confidence match)”
- “Spec written for onboarding flow”

---

# `SignalsV0` (Deterministic + Structured)

Signals are **state summaries**, not opinions.

---

## Signal 1 — Delivery Strength

From metrics only:

```
low / moderate / high
```

---

## Signal 2 — Urgent Pressure

From `open_urgent_items`

---

## Signal 3 — Expectation Coverage

Do expected items map to actual work?

```
high / partial / low
```

---

## Signal 4 — Follow-through

Do action items → tracked work?

```
strong / partial / weak
```

---

## Signal 5 — Blocker Visibility

Are blockers linked to tracked work?

```
visible / partial / not_visible
```

---

## Signal 6 — Repeated Discussion (Evidence-based)

```
present if:
  same semantic cluster (high confidence)
  appears in ≥2 calls
  AND no linked closed work
```

---

## Signal 7 — Execution Momentum

From PR / issue timestamps:

```
accelerating / steady / slowing
```

---

## Signal 8 — Documentation Linkage

Do docs connect to work?

```
linked / partially_linked / not_linked
```

---

## Signal 9 — Focus

From projects + clusters:

```
focused / moderate / fragmented
```

---

## Signal 10 — Collaboration Intensity

```
low / moderate / high
```

Based on:

- number of interactions
- diversity of participants

---

## Signal 11 — Support Pattern

```
- gives_help
- asks_for_help
- balanced
```

Based on:

- help_request vs help_given events

---

### Signal 12 — Feedback Reception

```
- proactive
- neutral
- defensive (only if clearly evidenced)
```

Based on:

- review comments + responses

⚠️ Default to neutral unless strong evidence

---

## Signal 13 — Coordination Role

```
- driving
- contributing
- peripheral
```

Based on:

- who initiates discussions
- who closes loops

---

## Signal 14 — Interaction Friction

```
present / unclear / absent
```

Triggered by:

- repeated clarification
- disagreement
- confusion signals

---

# `InterpretationsV0` (LLM but constrained + grounded)

Interpretations translate signals + evidence into meaning.

They are:

- grounded (must reference signals + evidence)
- probabilistic (confidence required)
- reusable (Insights are composed from them)

---

```jsx
interpretation:
id: string

type:
- ownership
- follow_through
- execution_friction
- prioritization
- collaboration_pattern
- autonomy
- support_dependency
- coordination_quality

description: string

based_on_signals:
- signal_id

evidence:
- "quoted span" (source_id)

confidence:
high | medium | low
```

Examples:

```
interpretation:
  type:"ownership"

  description:"Drives work end-to-end without external push"

  evidence:
    - merged PRs across same feature
    - initiated coordination threads

  confidence: medium
```

---

```
interpretation:
  type:"execution_friction"

  description:"Progress slowed by repeated clarification cycles"

  evidence:
    - repeated questions on same topic
    - same topic discussed across multiple calls

  confidence: high
```

---

```
interpretation:
  type:"leverage"

  description:"Reduces load on others through clear execution"

  evidence:
    - minimal follow-up in threads
    - clean PR merges without rework

  confidence: low/medium
```

---

# 🔥 `InsightsV0` (FINAL)

Each insight is:

- grounded in signals + interpretations
- prioritized
- decision-oriented
- **entity-grounded (V0 hard shape):** non-empty `primary_work_item_ids` (Step-2 work item ids), `supporting_work_item_ids` (optional list of Step-2 ids), non-empty `evidence_ids` (Step-3 action_item / blocker / decision ids — not only free-text quotes), and non-empty `primary_entities` (`{ name, kind }` with `kind` ∈ `project` \| `feature` \| `system`). The **`observation` must name the work** (include each primary work item id and each primary entity `name` as literal substrings) so copy cannot collapse into vague generalities.
- **Copy bar:** avoid team-level vagueness — e.g. ❌ “The team is blocked on external dependencies.” Prefer ✅ concrete anchors like “NEX-105 and NEX-77 are blocked on InfoSec approval with no owner assigned” when those ids exist in the underlying graph.

---

## Insight 1 — Gap Between Discussion and Execution

**Priority:** 🔴 critical

**Observation**

Some items discussed are not reflected in tracked work.

**Interpretation**

Follow-through from discussion → execution is inconsistent.

**Implication**

Work may be happening informally or getting dropped, reducing execution reliability.

**Evidence**

- “fix retry logic” (call_3)
- no linked issue or PR found

**Based on Interpretations**

- `follow_through: weak`
- `coordination_quality: partial`

**Confidence:** high

---

## Insight 2 — Repeated Unresolved Topic

**Priority:** 🔴 critical

**Observation**

The same topic appears across multiple discussions without closure.

**Interpretation**

A persistent issue lacks clear ownership or resolution path.

**Implication**

Creates execution drag and repeated coordination overhead.

**Evidence**

- Billing retry mentioned in 3 calls (call_1, call_3, call_5)
- No linked closed issue or PR

**Based on Interpretations**

- `execution_friction: high`
- `ownership: unclear`

**Confidence:** high

---

## Insight 3 — Ongoing Execution Pressure

**Priority:** 🟠 high

**Observation**

Multiple urgent items remain open.

**Interpretation**

High-priority work is accumulating alongside delivery.

**Implication**

Risk of reduced predictability if urgent work is not resolved quickly.

**Evidence**

- 3 open urgent items

**Based on Signals**

- `urgent_pressure: high`

**Confidence:** high

---

## Insight 4 — Weak Follow-through on Action Items

**Priority:** 🟠 high

**Observation**

Action items exist without linked tracked work.

**Interpretation**

Conversion from decisions → execution is partial.

**Implication**

Execution reliability degrades, especially on cross-team work.

**Evidence**

- 2 action items without linked issues or PRs

**Based on Interpretations**

- `follow_through: weak`

**Confidence:** medium-high

---

## Insight 5 — Limited Blocker Visibility

**Priority:** 🟠 high

**Observation**

Blockers are mentioned but not tracked.

**Interpretation**

Blockers are not externalized into the system.

**Implication**

Limits visibility, escalation, and team-level coordination.

**Evidence**

- “fails under load” (call_3)
- no linked issue

**Based on Interpretations**

- `execution_friction: present`
- `coordination_quality: partial`

**Confidence:** medium

---

## Insight 6 — Clarification-Driven Execution Friction

**Priority:** 🟡 medium

**Observation**

Repeated clarification cycles across Slack and calls.

**Interpretation**

Scope or ownership is not always clearly defined upfront.

**Implication**

Adds coordination overhead and slows progress.

**Evidence**

- repeated clarification questions
- same topics discussed multiple times

**Based on Interpretations**

- `execution_friction: high`

**Confidence:** medium

---

## Insight 7 — Fragmented Execution Focus

**Priority:** 🟡 medium

**Observation**

Work spans multiple projects.

**Interpretation**

Attention is distributed across domains.

**Implication**

Context switching may reduce efficiency.

**Evidence**

- active_projects ≥ 3

**Based on Signals**

- `focus: fragmented`

**Confidence:** medium

---

## Insight 8 — Documentation Not Driving Execution

**Priority:** 🟡 medium

**Observation**

Docs exist but are not linked to execution.

**Interpretation**

Documentation is not clearly used as a driver for delivery.

**Implication**

Effort may not translate into impact.

**Evidence**

- billing spec doc present
- no linked PRs or issues

**Based on Interpretations**

- `documentation_linkage: weak`

**Confidence:** medium

---

## Insight 9 — Active Collaboration with Limited Leverage

**Priority:** 🟡 medium

**Observation**

Regular participation in reviews and discussions.

**Interpretation**

Strong collaboration, but not always translating into execution outcomes.

**Implication**

Time spent collaborating may not fully convert into delivery impact.

**Evidence**

- PR reviews present
- Slack participation

**Based on Interpretations**

- `collaboration_pattern: active`
- `leverage: moderate`

**Confidence:** medium

---

## Insight 10 — Coordination Load is High

**Priority:** 🟡 medium

**Observation**

Progress often requires multiple discussions.

**Interpretation**

Execution depends on synchronous coordination.

**Implication**

Creates bottlenecks and limits scalability.

**Evidence**

- repeated discussions before execution
- delayed work linkage

**Based on Interpretations**

- `coordination_quality: heavy`

**Confidence:** medium

# Report Mapping

---

## Delivery Pulse

- Delivery Strength
- Urgent Pressure
- Momentum

---

## Recent Wins

- Only **closed / merged work**
- optionally supported by:
    - docs
    - calls (with evidence)

---

## Development Signals

Focus on:

- expectation vs execution gaps
- repeated unresolved discussions
- follow-through
- blocker visibility
- fragmentation

---

## Open Action Items

ONLY:

- tracked work (issues / PRs)

PLUS:

- **Potential follow-ups from discussions**
(must be labeled clearly)

---

### Language rule

Never say:

❌ “untracked work”

Always say:

✅ “items mentioned in discussions not found in tracked systems”

---

## Coaching Questions

Derived from:

- gaps
- missing links
- unresolved discussions

---

## One Priority

Selection order:

1. expectation vs execution gap
2. repeated unresolved topic
3. hidden blockers
4. urgent pressure

---

# Example `ReportV0`

## Summary

Delivery is consistent, but execution gaps exist between discussions and tracked work.

Repeated unresolved topics and clarification loops suggest coordination friction.

Primary opportunity is improving follow-through from discussion to execution.

---

## Key Risks (Ranked)

1. Follow-through gap between discussions and execution

→ items discussed are not consistently tracked or executed

2. Repeated unresolved topic (billing retry)

→ discussed multiple times without visible progress

3. Blockers not clearly visible in tracked systems

→ limits escalation and resolution

---

## 1. Delivery Pulse (Last 30 Days)

- 18 issues completed
- 6 PRs merged
- 3 urgent items open

Delivery appears consistent, with steady output across multiple projects.

Urgent work remains present.

---

## 2. Recent Wins

- Refactored onboarding API (merged PR + issue)
- Improved caching layer (merged PR)
- Authored billing flow specification (Notion)

---

## 3. Collaboration & Ways of Working

### 1. Active Participation in Team Interactions

**Signal:** 🟢 positive

**Interaction Patterns**

- Regular Slack participation
- Active in PR reviews

**Interpretation**

- Consistently engaged in team communication and collaboration

**Impact**

- Supports alignment and shared understanding across the team

---

### 2. Frequent Clarification Loops

**Signal:** 🔴 risk

**Interaction Patterns**

- Repeated clarification questions
    - “can you clarify expected response format?”
- Same topics discussed multiple times

**Interpretation**

- Scope or ownership may not be clearly defined upfront

**Impact**

- Introduces coordination overhead and slows execution

---

### 3. Support and Contribution to Others

**Signal:** 🟢 positive

**Interaction Patterns**

- Provides feedback in PR reviews
- Engages beyond own tasks

**Interpretation**

- Actively contributes to team success

**Impact**

- Improves code quality and team velocity

---

### 4. Limited Explicit Blocker Escalation

**Signal:** 🔴 risk

**Interaction Patterns**

- Blockers discussed but not formally tracked

**Interpretation**

- Blockers remain implicit or informal

**Impact**

- Reduces visibility and slows resolution

---

### 5. Dependency on Synchronous Coordination

**Signal:** 🟠 moderate risk

**Interaction Patterns**

- Progress depends on calls / discussions
- Limited async resolution

**Interpretation**

- Work requires external alignment before moving forward

**Impact**

- Can create bottlenecks in execution

---

### 6. Partial Collaboration Visibility

**Signal:** 🟡 neutral

**Interaction Patterns**

- Collaboration visible in Slack + PRs
- Limited visibility elsewhere

**Interpretation**

- Collaboration exists but is not fully captured

**Impact**

- Manager may not see full collaboration picture

---

## 4. Development Signals

- Consistent delivery and contribution across the period
- Active participation in code reviews
- Work spans multiple projects
- **Billing retry topic discussed in multiple calls without visible resolution**
    - Mentioned in 3 calls
    - No linked closed issue or merged PR
- **Some discussion items are not reflected in tracked work**
    - Example: “fix retry logic” (call_3)
    - No associated issue or PR found
- **Blockers mentioned in discussions are not clearly tracked**
    - Example: “fails under load” (call_3)
    - No linked issue

---

## 5. Open Action Items

**Stale**

- Billing retry bug — open for 9 days
- Cache invalidation issue — open for 7 days

**Active**

- API error handling improvements
- Auth token refresh fix

**From discussions (not found in tracked systems)**

- “fix retry logic” (call_3)
- “investigate edge cases under load” (call_3)

---

## 6. Coaching Questions

- Why is the billing retry topic repeatedly discussed without resolution?
- Are action items from discussions consistently converted into tracked work?
- Are blockers being explicitly captured and owned in the system?
- Is urgent work aligned with what is being discussed in planning?
- “Where do you feel you need more clarity before starting work?”
- “Are there areas where you rely heavily on others to unblock you?”
- “Do discussions usually translate into clear next steps?”

---

## 7. One Priority

**Improve follow-through between discussions and execution.**

Some items discussed in calls are not clearly reflected in tracked work, creating a gap between planning and delivery.

---

# LLM Prompt

```
You are an experienced Engineering Manager writing an execution report about ONE engineer.

You will receive a structured UserReportContext.

--------------------------------
CORE PRINCIPLE
--------------------------------
You are NOT producing truth.

You are producing:
- observations
- supported by evidence
- highlighting gaps

--------------------------------
STRICT RULES
--------------------------------

1. NO INVENTION
- Only use provided data
- If unclear, say so

2. EVIDENCE REQUIRED
- Every important claim MUST reference evidence
- Prefer quoting or referencing specific items

3. HANDLE UNCERTAINTY
- If links or matches are partial → use cautious language
- Never present uncertain data as fact

4. CROSS-SOURCE REASONING
Focus on:
- discussions (calls, docs)
- execution (issues, PRs)
- gaps between them

5. LANGUAGE SAFETY
DO NOT say:
- “this is not tracked”
- “this is missing”

INSTEAD say:
- “not found in available tracked systems”
- “no linked issue or PR found”

6. TONE
- Direct
- Factual
- Neutral
- No blame

--------------------------------
OUTPUT STRUCTURE (STRICT)
--------------------------------

## 1. Delivery Pulse (Last X Days)
## 2. Recent Wins
## 3. Development Signals
## 4. Open Action Items
## 5. Coaching Questions
## 6. One Priority

--------------------------------
SECTION RULES
--------------------------------

Development Signals MUST include:
- delivery consistency
- gaps between discussion and execution
- repeated unresolved topics (if any)
- follow-through
- blocker visibility

Open Action Items:
- include tracked work
- AND clearly labeled items from discussions

--------------------------------
END
```