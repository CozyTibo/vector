# Cortex Execution Reality Model (v0)

**Status:** Foundational ontology — v0  
**Audience:** Core engineers, infra, agent/orchestration, retrieval/synthesis  
**Purpose:** Prevent architectural drift during Cortex unlock and operationalization  
**Aligns with:** FSM/substrate audits (`DOCS/audits/cortex_*`), unlock war-room plan, Vector execution-intelligence direction, `DOCS/cortex/**` phase doctrines

**This document is not:** an implementation plan, a product pitch, or an operator runbook.  
**This document is:** the execution-reality specification — what exists, what each layer means, and what downstream systems may legally assume.

---

## Terminology (stable)

| Term | Meaning |
|------|---------|
| **Operational exhaust** | Connector-native records ingested into `raw_ingestion_records` (Slack messages, GitHub PRs, Notion pages, etc.). Fragmented, incomplete, windowed. |
| **Execution substrate** | Deterministic, tenant-scoped structures derived from exhaust (canonical materializations, anchors, org entities, links, walks, TCRE artifacts). Source of truth for execution reasoning. |
| **Execution reality** | The reconstructed, evidence-anchored picture of who did what, in what dependency order, with what organizational continuity — at a point in time. |
| **Org handle** | `cortex_org_entity` — a stable identity object (typically `HUMAN_ACTOR` or service account), not a message or PR row. |
| **Meaning link** | `cortex_org_link` — a typed relationship between org handles with evidence record ids and authority class. |
| **Authoritative link** | `link_authority = 'authoritative'` — may be exported to graph traversal and retrieval binding. |
| **Candidate link** | `cortex_org_link_candidate` — deterministic continuity hypothesis; not traversable until promoted. |
| **RET-SKIP** | Canonical retrieval skip code when prerequisites are unmet (e.g. `RET-SKIP-GRAPH-DISCONNECTED`). |
| **Partial intelligence** | Lawful execution signals and narratives produced on incomplete substrate with explicit omission classes. |
| **Alive** | Substrate produces entities, authoritative edges, completed walks, and non-graph-skipped retrieval attempts — not admin card green. |

---

## 1. What Cortex Fundamentally Is

Cortex is **not**:

- a dashboard or reporting UI (admin surfaces observe substrate; they are not the product),
- a memory or note-taking system,
- an “AI manager” or copilot that calls SaaS APIs ad hoc,
- a semantic search index over Slack/GitHub text.

Cortex **is**:

> A **continuously reconstructed execution reality layer** for an organization — built from operational exhaust, held to deterministic substrate invariants, and exposed to humans and agents as evidence-backed execution state.

Reconstruction is **continuous** because exhaust keeps arriving; **execution** because the object of interest is work, ownership, dependency, and outcome — not document similarity; **reality layer** because downstream consumers (retrieval, synthesis, agents) must treat substrate as ground truth, not LLM invention.

The end-to-end execution chain (normative):

```text
raw operational exhaust
  → canonical execution substrate
  → identity continuity
  → organizational execution graph
  → execution traversal
  → evidence retrieval
  → deterministic signals
  → synthesis
  → execution intelligence
```

Each arrow is a **phase contract** with inputs, outputs, skip semantics, and receipts. Skipping or collapsing layers creates fake-green systems (see audits: graph blocked with zero entities, retrieval starved without walks).

---

## 2. The Organizational Execution Problem

Organizations coordinate through **distributed operational exhaust**: messages, PRs, reviews, deployments, tickets, docs. No single system holds “what is actually happening.”

Structural failures Cortex addresses:

| Failure mode | Example | Without execution reality |
|--------------|---------|-------------------------|
| **Coordination compression** | Leadership infers status from standups + DMs | Decisions lag actual execution state |
| **Management scaling** | Managers track 20+ streams manually | Context switching becomes the product |
| **Synchronization overhead** | “Who owns this?” repeated across tools | Hours lost to rediscovery |
| **Tool fragmentation** | Same person in Slack, GitHub, Notion with no stable id | No continuity of ownership |
| **Expectation vs execution gap** | Roadmap says X; exhaust shows Y blocked on dependency Z | Surprises at review time |
| **Unresolved execution loops** | Review requested → no review → re-ping → still open | Loops invisible across channels |

Cortex does not replace tools. It **compresses organizational synchronization cost** by maintaining a **single deterministic execution substrate** that humans and agents query instead of re-scanning raw APIs.

---

## 3. Execution Reality vs Raw Data

| Dimension | Raw operational exhaust | Execution reality |
|-----------|-------------------------|-----------------|
| **Form** | Connector payloads, external ids, timestamps | Materialized objects, org handles, authoritative links, walks |
| **Completeness** | Intentionally partial (ingest windows, caps) | Partial with **declared omission classes** |
| **Identity** | Opaque user ids, logins scattered in JSON | Stable org handles + primitive fingerprints |
| **Relationships** | Implicit (thread parent, PR number) | Explicit meaning links with evidence |
| **Truth contract** | “What the API returned” | “What the substrate proves with receipts” |
| **LLM role** | Must not be primary interpreter | Interprets **only** bounded synthesis inputs |

**Rule:** Raw rows are **evidence inputs**, not the execution brain. Agents must not reason over “Slack/GitHub chaos” directly when Cortex substrate exists for the tenant.

**Corollary (operational):** `raw_total - mat_total` is **not** a measure of execution-reality quality. Deferral-blocked rows may be unmaterialized while 71%+ of exhaust is already sufficient for partial intelligence (proved: ~11.8k org entities from existing anchors).

---

## 4. Canonical Execution Substrate

**Canonical substrate** is the deterministic transformation of routable raw rows into **materializations** and **identity anchors** under an approved mapping bundle.

Properties:

- **Deterministic:** Same raw + bundle + engine ref → same materialization and anchor ids (replay-stable).
- **Topology-respecting:** Parent/child dependencies (PR before timeline event, deployment before status) are enforced via materialization order and deferrals — not guessed at synthesis time.
- **Incomplete by nature:** Ingest is windowed; some parents never arrive; some deferrals become **permanent orphans**. Substrate records this honestly (`topology_wait`, `permanent_orphan`, deferral queues).

Canonical substrate is **not** “all rows transformed.” It is “all **routable** rows either materialized, deferral-classified, or omission-documented.”

**Invariant:** Synthesis and traversal never repair missing canonical parents. Ingest or canonical drain must.

**Known failure class (v0 ops):** Topology orphans stored with `missing_parent_ref` must release when the parent node materializes — otherwise execution reality freezes despite existing parents (audit: deferral release deadlock).

---

## 5. Identity Continuity

**Identity** answers: *which organizational actors exist as stable execution participants?*

| Object | Role |
|--------|------|
| `cortex_canonical_identity_anchor` | Stable canonical entity per materialized work object / person object |
| `cortex_org_entity` (org handle) | Execution participant: `HUMAN_ACTOR`, service account, etc. |
| `cortex_org_primitive_instance` | Connector-native primitive (Slack `U…`, GitHub login) bound to an org handle |
| Identity primitive projection | Extracts actors from payloads (`slack_user`, `github_user`, `notion_user`) — not every message becomes a handle |

**Work objects** (messages, PRs, threads) **do not** by default become org handles. They **cite** handles via primitives. Collapsing “every message = person” is an architectural error.

**Continuity** is cross-source collapse onto handles via **deterministic rules** (same Slack user id, same GitHub login, email evidence, fixture keys in tests) — producing **candidate** links, not automatic truth.

**Identity continuity rebuild** is the operator/autonomous path to refresh handles + candidates; it is not a semantic clustering engine.

---

## 6. Organizational Execution Graph

The **organizational execution graph** is the **exported** structure used for phase 05 (traversal) handoff:

- **Nodes:** `org_entity` (+ optional `org_primitive` instances).
- **Edges:** **Only** `cortex_org_links` where `link_authority = 'authoritative'`.

Phase 04 graph export (`build_org_graph_projection_v1`) is **read-only**. It does not discover relationships from embeddings or co-occurrence.

| Graph export has | Graph export does not have |
|------------------|----------------------------|
| Sorted nodes/edges, stable hash | Semantic similarity edges |
| Evidence record ids on edges | LLM-inferred relationships |
| Link types from linkage rules | Canonical topology inside export (forbidden leakage) |

**Empty graph** with thousands of materializations usually means **zero promoted authoritative links**, not a broken exporter.

---

## 7. Authoritative vs Non-Authoritative Relationships

| Class | Storage | May traverse? | May bind retrieval? |
|-------|---------|---------------|---------------------|
| **Authoritative** | `cortex_org_links.link_authority = 'authoritative'` | Yes | Yes (subject to legality/temporal gates) |
| **Candidate** | `cortex_org_link_candidates` | No | No |
| **Hint / inferred / prohibited** | Non-truth link classes | No | No |

**Promotion** is a **governed, deterministic** transition: candidate + `promotion_policy_id` → authoritative row (`promote_candidate_to_authoritative_link`). Not operator whim; not model confidence.

**Authoritative means:** “This relationship is part of execution reality for traversal and retrieval until revoked or superseded.”

**Non-authoritative means:** “Hypothesis or exploration only — must carry `non_authoritative` flags in walk/replay paths.”

Edges are **meaning links** (ownership continuity, same-person evidence, fixture-declared subjects) — **not** “these documents are similar.”

---

## 8. Traversal as Execution Continuity Reconstruction

**Traversal** (phase 05, OCTS) is **not** generic graph walking or PageRank.

It is **execution continuity reconstruction**: bounded, deterministic walks over the **authoritative** org graph to produce **walk results** (visited link ids, fingerprints, termination reason) persisted for replay and retrieval.

Properties:

- **Policy-bound:** `max_hops`, `max_frontier`, `hop_class_allowlist` (e.g. `org.handle_links_canonical`), tie-break rules.
- **Evidence-ordered:** Visit order is deterministic from policy, not LLM salience.
- **Exploration vs authoritative:** Exploration walks must be explicitly non-authoritative; silent promotion is forbidden (phase-05 replay doctrine).

Traversal without authoritative edges produces **disconnected walks** → `RET-SKIP-GRAPH-DISCONNECTED` / `RET-SKIP-WALK-INCOMPLETE`. That is **correct degradation**, not a bug.

**Example:** Two handles exist for the same human (Slack + GitHub) but no promoted link → traversal cannot connect them → synthesis must not claim unified ownership.

---

## 9. Retrieval as Evidence Recovery

**Retrieval** (phase 07) is **not** RAG over chunked Slack.

It is **evidence recovery** bound to substrate artifacts:

- OCTS walk results and graph refs,
- TCRE materializations (phase 06),
- Authoritative org links and entity resolution,
- Legality and temporal consistency checks.

When prerequisites fail, retrieval emits **RET-SKIP** codes (registry in `retrieval_skip_registry.py`) — e.g.:

| Code | Meaning |
|------|---------|
| `RET-SKIP-TCRE-MISSING` | Reconstruction artifact absent |
| `RET-SKIP-WALK-INCOMPLETE` | Walk did not complete under policy |
| `RET-SKIP-ORG-LINK-MISSING` | Required link not found |
| `RET-SKIP-IDENTITY-UNRESOLVED` | Handle not resolved |
| `RET-SKIP-GRAPH-DISCONNECTED` | Graph cannot support required continuity |
| `RET-SKIP-NO-CANDIDATES` | No bindable candidates |

Retrieval **binds** evidence to queries about execution — it does not **author** new facts.

---

## 10. Deterministic Signals

**Deterministic signals** are structured outputs computed from substrate + walks + retrieval bindings **without** LLM invention:

- Counts, hashes, stable ids, omission class tallies,
- Convergence receipts, phase outcomes (`topology_wait`, `partial_progress`),
- Graph density metrics, orphan classifications,
- RET-SKIP distributions, replay drift flags,
- Link promotion receipts (L0 class).

Signals are **replay-safe** and **tenant-scoped**. They feed admin completeness projections and agent tool responses.

**Rule:** If a fact cannot be traced to substrate rows + receipts, it is **not** a deterministic signal — it is synthesis output.

---

## 11. Synthesis Boundaries and Legal Inference

**Synthesis** (phase 08) operates on **constrained inputs**: retrieval bundles, deterministic signals, explicit omission classes — not raw exhaust.

### Allowed

- Summarize **evidence-backed** execution state (“PR #142 blocked on review X per records [ids]”),
- Surface **gaps** declared by omission classes (“timeline events unmaterialized: topology deferral”),
- Relate **known** handles and links (“Actor A authored commits linked to PR B”),
- Propose **operator actions** labeled as recommendations, not facts.

### Forbidden

- Invent **causality** not supported by evidence (“because they were frustrated”),
- Invent **psychology** or intent not in payload,
- Merge identities **without** authoritative or candidate linkage,
- Treat **candidate** links as fact,
- Treat **semantic similarity** as organizational relationship,
- Fill topology holes with narrative glue,
- Override RET-SKIP with plausible prose.

**Legal inference** means: every sentence in an execution narrative must be reducible to a chain: `substrate object → evidence_raw_record_ids → displayed claim`. If reduction fails, the sentence is illegal.

LLMs are **interpretation layers** on bounded inputs — not substrate authors.

---

## 12. Partial Intelligence vs Full Convergence

| | **Partial intelligence** | **Full convergence** |
|---|-------------------------|----------------------|
| **Definition** | Lawful execution narratives on incomplete substrate | All routable exhaust materialized, deferrals resolved or classified, phases autonomously healthy |
| **Required?** | **No** — product must work here | **No** for v0 usefulness on real tenants |
| **Admin appearance** | May show degraded / blocked downstream cards | May show green completeness while intelligence empty |
| **Example** | 11k handles, 50 authoritative links, 1 walk, 1 retrieval binding | `raw == mat`, zero deferrals, all phases completed |

**Principle:** Cortex **must degrade gracefully**:

- Explicit RET-SKIP instead of hallucinated retrieval,
- `topology_wait` instead of fake materialization success,
- Disconnected graph components instead of invented edges,
- Omission classes in synthesis instead of silent gaps.

**Anti-pattern:** Blocking all intelligence until `raw_total == mat_total`. Real companies never reach that under windowed ingest.

---

## 13. What “Alive” Means

**Alive** is an **operational** predicate, not marketing health.

A tenant Cortex is **alive** when all hold:

| # | Criterion | Typical evidence |
|---|-----------|------------------|
| A1 | `cortex_org_entities` (active) > 0 | SQL / identity control plane |
| A2 | `cortex_org_links` authoritative (active) > 0 | SQL |
| A3 | `cortex_org_link_candidates` > 0 | SQL |
| A4 | Canonical drain `total_succeeded > 0` in recent window | CloudWatch / forward-progress |
| A5 | ≥1 completed OCTS walk with ≥1 visited authoritative edge | Phase 05 output / walk store |
| A6 | ≥1 retrieval attempt not dominated by `RET-SKIP-GRAPH-DISCONNECTED` | Retrieval diagnostics |

**Not alive:** ingestion runs, 24k raw rows, `canonical_continue` loops, pipeline overview “waiting” cards, or `raw−mat` decreasing alone.

**First intelligence milestone** (war-room): A1–A6 at minimal thresholds — not full synthesis, not zero deferrals.

---

## 14. Human + Agent Shared Execution Brain

Humans and agents (Claude MCP, Cursor, internal automation) share the **same substrate** — not duplicate integrations.

### Humans use Cortex to

- See execution continuity across tools,
- Inspect deferral/topology truth (`forward-progress`),
- Promote or revoke links under policy,
- Trigger reruns from named phases with receipts.

### Agents must consume from Cortex

| Consume | Do not consume (when substrate exists) |
|---------|--------------------------------------|
| Execution state (phase cursors, outcomes) | Raw Slack/GitHub API firehose |
| Org handles + primitive keys | Per-message guessing of actors |
| Authoritative links + link types | Embedding neighbors |
| Dependency topology (materialization/deferral) | Ad-hoc parent guessing |
| OCTS walk results | Unbounded thread scraping |
| Deterministic signals + RET-SKIP | Ignoring skip codes |
| Evidence-backed synthesis bundles | Free-form tool narration as fact |

**Agent API shape (conceptual):**

- `execution/inspect` — lease, FSM, phase status,
- `canonical/forward-progress` — deferrals, topology gaps,
- `identity/control-plane` — handles, candidates, ambiguities,
- Graph density / orphan continuity — disconnected components,
- Retrieval materialization diagnostics — skip reasons,
- Synthesis outputs — labeled, evidence-reducible.

Agents **must** propagate omission classes into plans (“cannot assert ownership — `RET-SKIP-IDENTITY-UNRESOLVED`”).

### Example: agent planning a code review follow-up

1. Query handle for GitHub login → org entity id.  
2. Query authoritative links → related PR/work entities.  
3. Check walk or TCRE binding for review state.  
4. If `RET-SKIP-WALK-INCOMPLETE`, report gap — do not invent review status.  
5. Synthesis layer drafts message citing `evidence_raw_record_ids`.

---

## 15. Long-Term Vision

**Execution brain** = the combination of:

- Continuous exhaust ingestion (imperfect),
- Deterministic substrate reconstruction,
- Governed identity and link promotion,
- Replay-safe traversal and retrieval,
- Bounded synthesis producing **execution intelligence** — narratives, signals, and agent-executable state that reduce organizational synchronization overhead.

### Directional properties (v0 → v1)

| Property | Intent |
|----------|--------|
| **Always-on reconstruction** | Convergence workers advance substrate without manual wedges (after deferral/gate fixes). |
| **Lawful partial intelligence by default** | Most tenants run incomplete; product remains useful. |
| **Agent-native contracts** | MCP/tools expose execution reality, not connector clones. |
| **Evidence courts** | Synthesis challenges trace to records or fail. |
| **No single-vendor lock-in** | Exhaust is multi-connector; reality is vendor-neutral handles. |

### Non-goals

- Perfect organizational knowledge graphs,
- Full historical replay of every SaaS object,
- Replacing HR systems of record,
- Autonomous management without human promotion/policy,
- LLM-authored substrate.

### Success criterion for the vision

Agents and humans **coordinate execution** with measurably less redundant status-seeking — because **execution reality** is queryable, deterministic, evidence-backed, and honestly incomplete where data is incomplete.

---

## Appendix A — Phase alignment (implementation map)

| Reality layer | Pipeline phase (typical) | Primary persistent objects |
|---------------|--------------------------|----------------------------|
| Canonical substrate | Phase 02 | `cortex_canonical_transform_materializations`, deferrals, anchors |
| Identity continuity | Phase 03 | `cortex_org_entities`, primitives, candidates |
| Org execution graph export | Phase 04 | Projection JSON + stable hash (not a separate graph DB) |
| Traversal | Phase 05 | OCTS walk records |
| TCRE / reconstruction | Phase 06 | TCRE jobs, materializations |
| Evidence retrieval | Phase 07 | Retrieval bindings, skip stats |
| Synthesis | Phase 08 | Synthesis artifacts (bounded) |

---

## Appendix B — Related documents

| Document | Role |
|----------|------|
| `DOCS/audits/cortex_execution_proofs.md` | Prod evidence, SQL, phase contracts |
| `DOCS/audits/cortex_execution_unlock_challenge.md` | Deadlock analysis |
| `DOCS/audits/cortex_execution_intelligence_unlock_master_plan.md` | War-room implementation order |
| `DOCS/cortex/**` phase doctrines | Normative phase invariants |
| `DOCS/audits/cortex_fsm_full_audit.md` | FSM substrate audit |

---

## Appendix C — Ontology consistency rules (for PR reviewers)

1. Never call candidates “links” in traversal/retrieval contexts — say **candidate** or promote first.  
2. Never call graph export “the graph database” — it is a **projection** of org handles + authoritative links.  
3. Never call retrieval “RAG” in architecture docs — **evidence recovery**.  
4. Never call synthesis “understanding the company” — **execution intelligence** with legal inference rules.  
5. Never use `raw−mat` as success metric — use **alive** criteria §13.  
6. Any new feature must declare: which layer it mutates, which RET-SKIP it may emit, and whether it is allowed to use LLMs.

---

*v0 — update only via explicit version bump (`v1`) when ontology changes.*
