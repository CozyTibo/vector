# Cortex semantic execution intelligence — phase plan

**Status:** Implementation roadmap (semantic / intelligence track)  
**Date:** 2026-05-23  
**Tenant reference:** `c08ef32b-f89a-40f6-9566-e19b5329436f` (Fizzer)  
**Scope:** Graph truth → identity continuity → retrieval semantics → synthesis usefulness → operator simplification  

**This is NOT:** a continuity/runtime/FSM plan, an ontology expansion, or a new platform architecture.  
**This IS:** the shortest honest path from **moving substrate** to **truthful useful execution intelligence** using what already exists.

**Hard evidence (read first, do not relitigate):**

| Audit | Use for |
|-------|---------|
| [`cortex_graph_truth_and_intelligence_quality_audit.md`](cortex_graph_truth_and_intelligence_quality_audit.md) | Primary semantic prod truth (2026-05-23T12:06Z) |
| [`cortex_final_reality_state_audit.md`](cortex_final_reality_state_audit.md) | Runtime vs intelligence split; fake-green inventory |
| [`cortex_runtime_continuity_stabilization_audit.md`](cortex_runtime_continuity_stabilization_audit.md) | What continuity track already fixed (R1–R6) — **do not duplicate** |
| [`cortex_autonomous_execution_continuity_audit.md`](cortex_autonomous_execution_continuity_audit.md) | Continuity invariants vs substrate capability |
| [`cortex_execution_reality_model_v0.md`](../architecture/cortex_execution_reality_model_v0.md) | Normative vocabulary (substrate vs reality vs fake-green) |

**Repro baseline:** `python backend/scripts/graph_truth_audit_snapshot.py` → [`baselines/graph_truth_fizzer_wave_s0_baseline.json`](baselines/graph_truth_fizzer_wave_s0_baseline.json)  
**Ops runbook:** [`cortex_semantic_ops_runbook.md`](cortex_semantic_ops_runbook.md)

---

## Non-negotiable constraints (all waves)

1. **Retrieval is the primary product substrate** — execution-state index + published epochs ground synthesis. Graph density is supporting, not the product.
2. **No new `link_type`** without: prod evidence, expected edge count, retrieval use-case, synthesis use-case (documented in PR).
3. **Delete before add** — fewer admin panels, fewer health “states,” fewer counters, fewer orchestration concepts after this phase.
4. **Graph progress = unique semantic pairs** (`unique_auth_pairs`, `dup_factor`), never raw `cortex_org_links` row count alone.
5. **Synthesis stays fail-loud** — weak retrieval → FAILED with SD codes, not empty green completion.

---

## Wave S0 — Truth baseline (COMPLETE)

| Step | Status | Artifact |
|------|--------|----------|
| S0.1 Measurement | Done | `semantic_readiness_v1.py`, `graph_truth_audit_snapshot.py` |
| S0.2 Admin truth metrics | Done | Semantic readiness card, `GET …/semantic-readiness`, graph page |
| S0.3 Baseline + runbook | Done | `graph_truth_fizzer_wave_s0_baseline.json`, `cortex_semantic_ops_runbook.md` |

---

## 0. The phase transition (read this once)

### FROM (largely done or owned elsewhere)

- Substrate continuity, worker/runtime stability, phase recurrence
- Anti-fake-green **runtime** gates (AA panel tightening, dual-lane, topology_wait starvation fixes)
- Execution islands as **graph components** + registry
- Retrieval/synthesis **heartbeat** (epochs publish; phase 07 completes; phase 08 fail-loud)

### TO (this plan)

- **Semantic execution intelligence** — execution reality that is **legible and useful**
- **Truthful graph continuity** — unique topology, real edge types, no row inflation
- **Cross-system identity** — Slack/GitHub/Notion/email in **promoted** graph, not just anchors
- **Meaningful retrieval** — execution-state index, not org_link mirror
- **Useful synthesis** — non-empty, evidence-backed claims or explicit lawful omission

### The question changed

| Old question | New question |
|--------------|--------------|
| Can the FSM move? | Does the graph **represent execution reality** strongly enough to support useful intelligence? |
| Are phases recurring? | Does recurrence **change what retrieval and synthesis mean**? |
| How many auth links? | How many **unique semantic pairs** and **cross-system bridges**? |

### Runtime continuity ≠ semantic usefulness

| Dimension | Runtime continuity (separate track) | Semantic usefulness (this plan) |
|-----------|-------------------------------------|----------------------------------|
| Success signal | Slice transitions, epoch publish, walk rows | Unique graph pairs, retrieval mix, synthesis claims |
| Prod today | Improved (walks 86/24h, ECS aligned, phase 07 COMPLETED) | **Failed** (98% org_link retrieval, 0 useful synthesis) |
| Failure mode | Stuck FSM, queued phases | **Lying metrics**, wrong index semantics |
| Fix style | Scheduling, lease, sweeps | **Dedupe, promotion rules, index materialization order** |

**Rule:** Do not mark this phase done when the worker merely moves. Mark it done when **operators and engineers can trust graph/retrieval/synthesis metrics** and **at least one island produces a useful synthesis artifact**.

---

## 1. Executive truth

### What Cortex currently is (Fizzer prod, 2026-05-23)

Cortex is a **deterministic execution substrate warehouse** with:

- Ingest + canonical materialization at scale (33k raw, 21k mats, 21k anchors)
- A **recurring convergence worker** (dual-lane, dirty lease, hundreds of transitions/day)
- **Graph persistence** that runs (phase 04 `COMPLETED` repeatedly)
- **Partial island machinery** (257-entity component + registry row)
- **Retrieval epochs** that publish (latest `epoch-57147c1555c6`, 1,599 entries)
- **Fail-loud synthesis** (empty scope and pipeline failures surface as FAILED, not silent green)

### What Cortex is not

- An org-wide execution brain (96.5% of entities have **zero** authoritative edges)
- A cross-system identity system in prod (only `p04.candidate.exact_notion_user_id_v1` promotes)
- A retrieval layer over execution state (98.4% of rows are `org_link` mirrors)
- A synthesis product (1 artifact, `claims: []`, 1,043 failed jobs)
- A trustworthy graph metric surface (10,400 link rows = 2,000 unique pairs)

### What this phase tries to achieve

Build a **minimally sufficient, truthful execution graph** on **at least one real island** such that:

1. **Graph progress** is measured in **unique semantic topology**, not row inserts.
2. **Identity continuity** connects Slack/GitHub/Notion (and email where strict) in **promoted** edges.
3. **Retrieval** indexes **execution artifacts** (mats, walks, TCRE, causal chains) — org_link is supporting, not dominant.
4. **Synthesis** produces **≥1 published artifact per epoch** with **≥1 verifiable claim** tied to retrieval refs — or fails with explicit SD codes (keep fail-loud).
5. **Engineers** can debug end-to-end in &lt;30 minutes using SQL + receipts, without unlock scripts.

**Non-goals:** full company convergence, probabilistic traversal, embeddings platform, agent framework, new graph DB, ontology redesign.

---

## 2. Current semantic failure map

### 2.1 Graph truth failures

| ID | Failure | Prod evidence | Code locus |
|----|---------|---------------|------------|
| G1 | **5× authoritative duplication** | 10,400 rows / 2,000 unique pairs | `identity/link_ledger.py` promotion |
| G2 | **Single edge type in prod** | 100% `org.persona_belongs_to_handle` | `anchor_continuity_candidates.py` |
| G3 | **Single promotion rule in prod** | 100% `exact_notion_user_id_v1` | Same |
| G4 | **96.5% entities isolated** | 7,134 / 7,393 not in auth graph | `graph_orphan_continuity.py` |
| G5 | **Phase 04 “success” without topology delta** | `edge_count` 4,800→10,400, same 7,393 nodes | Phase 04 projection receipts |
| G6 | **Notion star, not execution cluster** | 9 personas → 257 handles | SQL persona/handle counts |
| G7 | **Registry edge count stale** | registry 2,398 vs 10,400 SQL | `execution_island_registry.py` |

### 2.2 Identity continuity failures

| ID | Failure | Prod evidence | Code locus |
|----|---------|---------------|------------|
| I1 | **Phase 03 COMPLETED_EMPTY** | Anchors/entities unchanged across runs | Phase 03 runner |
| I2 | **Slack/GitHub keys unused in graph** | 0 promotions for non-Notion rules | `build_anchor_continuity_candidate_rows` |
| I3 | **Anchor↔entity gap** | ~15,279 anchors without active entity match | Phase 03/04 boundary |
| I4 | **40k candidates / 2k pairs** | Batch inflation, 29,600 unpromoted | Candidate batch + promotion schedule |
| I5 | **Cross-system fragmentation** | Metadata hints (5k github-tagged entities) vs 9 personas in graph | Org entity `metadata_json` |

### 2.3 Retrieval semantic failures

| ID | Failure | Prod evidence | Code locus |
|----|---------|---------------|------------|
| R1 | **org_link mirror dominance** | 4,799 / 4,876 = 98.4% | `retrieval_graph_binding.py` `materialize_retrieval_index_from_graph_ref_v1` |
| R2 | **Under-indexed execution artifacts** | materialization 50, walk 26, causal 1 | `retrieval_octs_binding.py`, TCRE binders |
| R3 | **Scope law omits 96% of entities** | `outside_island_scope_entity_count: 7029` per row | Island scope law in materialize |
| R4 | **Epoch multiplicity without semantic gain** | 5 epochs, ~1,599 entries each, mostly links | `retrieval_publish_contract.py` |
| R5 | **Retrieval stopped advancing** | Last entry `2026-05-23T01:59Z` while graph churn continued | Phase 07 queued behind IDENTITY FSM |

### 2.4 Synthesis failures

| ID | Failure | Prod evidence | Code locus |
|----|---------|---------------|------------|
| S1 | **No useful artifacts** | 1× `degradation_brief`, `claims: []` | Synthesis orchestrator |
| S2 | **Per-island all scopes failed** | `synthesis_per_island_all_scopes_failed` | `synthesis_per_island.py` |
| S3 | **Empty scope with entries** | `phase08_empty_scope_with_retrieval_entries` | `phase08_empty_scope_truth_gate.py` |
| S4 | **1,043 failed jobs** | Job table hygiene / eligibility | `synthesis_job_lifecycle.py` |
| S5 | **Ingress not execution-shaped** | SD-SCOPE-EMPTY on completed job | Scope selection vs retrieval mix |

### 2.5 Fake-green metrics & surfaces

| Surface | Lie | Replace with |
|---------|-----|--------------|
| “Authoritative links” KPI | Row count | **unique_pairs**, **rule_id breakdown**, **dup_factor** |
| Phase 04 `edge_count` | Monotonic insert | **Δ unique_pairs**, **Δ components**, **new link_types** |
| Phase 03 `COMPLETED` | Sounds healthy | **`COMPLETED_EMPTY` visible**; delta anchors/merges |
| Candidate count | 40k noise | **distinct pairs**, **promotion rate per rule** |
| Retrieval row count | Mirrors graph | **index_kind mix**, **non-link %** |
| Raw − mat hero | Implies broken brain | **Deferral class breakdown** (reality model §3) |
| AA “alive” without synthesis claims | Continuity theater | **Semantic readiness panel** (new, small) |

### 2.6 Operational complexity / dead code

| Class | Examples | Action |
|-------|----------|--------|
| Duplicate proof scripts | 20+ `continuity_p0_phase_*_proof.py` | **SIMPLIFY** → one `continuity_audit_snapshot.py` for ops |
| Archived unlock scripts | `backend/scripts/archive/unlock/*` | **KEEP** archive only; ban from runbooks |
| Legacy coordinator | `substrate_pipeline/coordinator` | **DELETE** enqueue paths (partially done) |
| Unused promotion rules in UI | Rules never promoting in prod | **HIDE** until metric &gt; 0 |
| Wedge-era “alive” panels | Step 11/12 pass vs STALLED | **SIMPLIFY** labels; separate semantic panel |

---

## 3. Principles for this phase

1. **No new major infrastructure** — Postgres + existing phase runners + existing tables only.
2. **No second graph system** — `cortex_org_links` is the traversable graph; fix it, don’t wrap it.
3. **No probabilistic traversal** — deterministic components, deterministic promotion, deterministic retrieval replay ids.
4. **No “AI memory platform”** — retrieval rows point to **substrate artifacts**, not embedding stores.
5. **Delete before add** — remove duplicate links, dead scripts, and misleading KPIs before new index kinds.
6. **Retrieval = execution state index** — prioritize materializations, walks, TCRE, transitions; cap org_link share.
7. **Graph KPIs = unique semantic topology** — never ship a dashboard tile that grows with 5× duplication.
8. **Synthesis fails loud** — empty claims are worse than FAILED; do not weaken `phase08_empty_scope_truth_gate`.
9. **One island first** — prove usefulness on `d7e41b3c763d38e9` (257) before org-wide fantasies.
10. **Explainability over completeness** — every promoted edge and retrieval row must cite evidence record ids.

**Challenge test (apply to every PR):**  
*Does this make unique_pairs, retrieval mix, or synthesis claims more truthful without a new service?*  
If no → reject.

---

## 4. Graph truth plan

### 4.1 What should count as “graph progress”?

**Progress (allowed metrics):**

| Metric | Definition | Fizzer baseline | Target (phase end) |
|--------|------------|-------------------|---------------------|
| `unique_auth_pairs` | `COUNT(DISTINCT (source, target))` active authoritative | 2,000 | ≥2,500 **and** dup_factor ≤1.05 |
| `dup_factor` | `auth_edge_rows / unique_auth_pairs` | **5.2** | **≤1.05** |
| `entities_in_auth_graph_pct` | incident entities / active entities | 3.5% | ≥15% on island; document global omission |
| `promotion_rule_count` | distinct `rule_id` with ≥1 promoted edge | **1** | **≥3** (Notion + Slack + GitHub minimum) |
| `link_type_count` | distinct `link_type` with promoted edges | **1** | **≥2** (persona_handle + at least one execution bridge) |
| `component_count_ge2` | components with size ≥2 | 2 | ≥3 **or** largest component includes non-Notion bridge |

**Not progress:**

- Raw `COUNT(*)` from `cortex_org_links`
- Phase 04 `edge_count` without dedupe
- Candidate batch insert volume

### 4.2 Authoritative link dedupe (Wave S1 — MUST)

**Problem:** Same `(tenant, source, target, link_type)` promoted multiple times (up to 10× observed).

**Implementation (minimal):**

1. **DB constraint** (preferred): unique partial index on active authoritative links  
   `(tenant_id, source_entity_id, target_entity_id, link_type) WHERE revoked_at IS NULL AND link_authority = 'authoritative'`
2. **Promotion idempotency** in `link_ledger.py`: `INSERT … ON CONFLICT DO NOTHING` or revoke+supersede pattern already in model — **enforce at write site**, not only in reports.
3. **One-time prod cleanup script** (operator-run, receipted): revoke duplicates keeping newest `promoted_from_candidate_id` / `created_at`.

**Validation SQL:**

```sql
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT (source_entity_id, target_entity_id)) AS uniq_pairs,
       ROUND(COUNT(*)::numeric / NULLIF(COUNT(DISTINCT (source_entity_id, target_entity_id)), 0), 2) AS dup_factor
FROM cortex_org_links
WHERE tenant_id = :tenant AND link_authority = 'authoritative' AND revoked_at IS NULL;
-- Accept: dup_factor <= 1.05
```

**Rollback:** Drop unique index if blocking legitimate multi-edge types (then narrow unique key per `link_type` only).

### 4.3 Idempotent promotion & promotion receipts

- Every promotion batch writes **`cortex_org_link_replay_job_receipts`** (already exists) with: `rule_id`, `candidates_in`, `promoted_new`, `promoted_skipped_dup`, `revoked_superseded`.
- Phase 04 receipt must include **`unique_pairs_delta`** not only `edge_count`.

**Code:** `identity/org_link_replay_runtime.py`, phase 04 runner output_json.

### 4.4 Edge-type truthfulness (Wave S2 — minimal new types)

**Do not invent 20 edge types.** Add **at most 2–3** execution-meaningful types, only with evidence:

| `link_type` (example) | Meaning | Evidence |
|-----------------------|---------|----------|
| `org.persona_belongs_to_handle` | **KEEP** — identity handle binding | Notion/Slack/GitHub user keys |
| `org.actor_authored_artifact` | Human/service → mat/walk anchor | `evidence_raw_record_ids` |
| `org.artifact_in_repository` | PR/issue → repo | GitHub payload refs |

**Challenge:** If a type cannot be populated from **existing** anchors with &gt;100 edges in prod, **defer** it.

### 4.5 Graph density truthfulness

- **Stop** reporting “density” as edges/entities without dedupe.
- Report **`mean_degree`** and **`component_size_distribution`** on **unique pairs** graph.
- Admin graph card: show **dup_factor** in red when &gt;1.1.

### 4.6 Remove fake graph metrics

| Remove / relabel | Where |
|------------------|-------|
| Raw auth link count as primary | Admin overview, continuity panel |
| “Graph COMPLETED” without Δ unique pairs | Phase cards |
| Candidate total without distinct pairs | Identity admin |

---

## 5. Identity continuity plan

### 5.1 Minimal useful cross-system continuity (definition)

**Minimal bar (prod-verifiable):**

> For at least **50** `human_actor` entities, the authoritative graph shows **≥2 connector classes** (e.g. GitHub login + Slack user + Notion user) connected via promoted `org.persona_belongs_to_handle` or a single merged persona entity with multiple handles — **not** merely metadata substrings.

**Stretch (phase end):**

- **`promotion_rule_count` ≥ 3** with non-zero promotions each
- **`unique_auth_pairs`** grows from **cross-system** rules, not 5× Notion batch replay

### 5.2 Rules already in code — enable in prod order

From `anchor_continuity_candidates.py` (do **not** add new rules until these promote):

| Priority | `rule_id` | Join key | Why first |
|----------|-----------|----------|-----------|
| P0 | `p04.candidate.exact_notion_user_id_v1` | notion_user_id | Already works — **fix dedupe first** |
| P1 | `p04.candidate.exact_github_login_v1` | github_login | Highest anchor volume (4,722 github refs) |
| P2 | `p04.candidate.exact_slack_user_id_v1` | slack_user_id | Coordination exhaust |
| P3 | `p04.candidate.exact_email_localpart_domain_v1` | strict email triple | Low false-positive if strict |
| Defer | fixture / cluster rules | — | Test-only until prod metrics clean |

**Likely bottleneck (investigate, don’t guess):**

- Promotion policy not scheduling non-Notion batches
- Phase 03 `COMPLETED_EMPTY` skipping regen when anchors unchanged
- Candidate cap overflow dropping GitHub/Slack rows (check `accounting_out` in `build_anchor_continuity_candidate_rows`)

### 5.3 Anchor → entity continuity

**Problem:** 15,279 anchors without active org entity match.

**Fix (minimal):**

1. Phase 03/04 must write `metadata_json.canonical_entity_id` (or existing boundary hook) **deterministically** for every anchor used in promotion.
2. Admin identity slice: show **`anchors_without_entity_pct`** not just anchor count.

**Validation SQL:**

```sql
SELECT COUNT(*) AS anchors_missing_entity
FROM cortex_canonical_identity_anchors a
WHERE a.tenant_id = :tenant
  AND NOT EXISTS (
    SELECT 1 FROM cortex_org_entities e
    WHERE e.tenant_id = a.tenant_id
      AND e.tombstoned_at IS NULL
      AND e.metadata_json->>'canonical_entity_id' = a.canonical_entity_id::text
  );
-- Target: <5% of anchor count (not zero overnight)
```

### 5.4 Slack ↔ GitHub ↔ Notion verification metrics

```sql
-- Promotions by rule (weekly)
SELECT rule_id, COUNT(*) AS promoted_edges,
       COUNT(DISTINCT (source_entity_id, target_entity_id)) AS uniq_pairs
FROM cortex_org_links
WHERE tenant_id = :tenant AND link_authority = 'authoritative' AND revoked_at IS NULL
GROUP BY 1 ORDER BY 2 DESC;

-- Cross-connector personas (approx): sources with edges to targets whose metadata mentions another connector
-- (Refine in implementation with explicit connector tags on entities.)
```

### 5.5 What we will NOT build

- Global probabilistic entity resolution
- ML identity clustering
- New identity ontology tables
- “Person merge” UI without receipts

---

## 6. Retrieval semantic plan

### 6.1 Problem statement

Retrieval today is a **graph edge export**:

- 98.4% `org_link` (`retrieval_graph_binding.py`)
- Walks/TCRE/materializations exist in code but are **noise** in prod index

Synthesis cannot be useful if ingress is **topological**, not **executional**.

### 6.2 What SHOULD be indexed (priority order)

| Priority | `index_kind` | Source | Execution meaning |
|----------|--------------|--------|-------------------|
| 1 | `materialization` | Canonical mats in island scope | What work objects exist |
| 2 | `walk` | OCTS durable walks | Ordered execution traversal |
| 3 | `causal_chain` / TCRE outputs | TCRE jobs | Reconstructed dependency chains |
| 4 | `org_entity` | Handles in scope | Identity nodes (sparse) |
| 5 | `org_link` | Auth edges | **Supporting** topology only |

**Optional later (same tables):** `execution_transition` from `cortex_execution_transition_log` if bounded — **no new bus**.

### 6.3 What should NOT dominate

| Kind | Cap (published epoch) | Rationale |
|------|----------------------|-----------|
| `org_link` | **≤30%** of entries | Prevent mirror loops |
| `org_entity` | **≤10%** | Avoid handle spam |
| `materialization` + `walk` + causal/TCRE | **≥60%** | Execution state body |

### 6.4 Target retrieval composition

**Baseline (Fizzer published epoch `epoch-57147c1555c6`):**

| kind | count | % |
|------|-------|---|
| org_link | 1,599 | ~100% of published set |
| materialization | 50 | trace |
| walk | 26 | trace |

**Phase-end target (same island scope):**

| kind | min % | min count (island) |
|------|-------|-------------------|
| materialization | 35% | 400 |
| walk | 15% | 150 |
| causal/TCRE | 10% | 100 |
| org_link | ≤30% | ≤500 |
| org_entity | ≤10% | ≤150 |

### 6.5 Retrieval truth laws (implement as code gates, not docs)

1. **L1 — Mix gate:** After phase 07 build, if `org_link_pct > 0.30` → phase outcome `FAILED` with `retrieval_semantic_mix_violation` (fail-loud).
2. **L2 — Non-empty execution:** Published epoch must have `materialization + walk ≥ 1` per island scope worked.
3. **L3 — Evidence:** Every row’s `artifact_ref_json` must resolve to a real row id (mat, walk, link).
4. **L4 — Omission honesty:** `omission_summary` required when scope law excludes &gt;50% entities (already partial).
5. **L5 — No duplicate replay:** Same `retrieval_lookup_id` cannot appear twice in an epoch (dedupe).

**Code touchpoints:**

- `retrieval/retrieval_publish_contract.py` — post-build validator
- `retrieval/retrieval_graph_binding.py` — **cap** `materialize_retrieval_index_from_graph_ref_v1` batch size per epoch
- `retrieval/retrieval_octs_binding.py` — **ensure** walk materialize runs **before** link sweep in phase 07 orchestration

### 6.6 Rollout sequencing

| Step | Change | Risk |
|------|--------|------|
| S3.1 | Reorder phase 07: walks → TCRE → mats → **bounded** org_link | Low |
| S3.2 | Add mix gate (fail epoch) | Medium — may fail until mats indexed |
| S3.3 | Backfill one epoch on island `d7e41b3c763d38e9` | Operator script |
| S3.4 | Wire freshness metric (see §9) | Low |

### 6.7 Validation SQL (copy/paste)

```sql
-- Retrieval mix for published epoch
WITH published AS (
  SELECT index_epoch FROM cortex_retrieval_index_epochs
  WHERE tenant_id = :tenant AND published_at IS NOT NULL
  ORDER BY published_at DESC LIMIT 1
)
SELECT index_kind, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM cortex_retrieval_index_entries e
JOIN published p ON e.index_epoch = p.index_epoch
WHERE e.tenant_id = :tenant
GROUP BY 1 ORDER BY n DESC;

-- Freshness
SELECT MAX(created_at) AS last_retrieval_row,
       EXTRACT(EPOCH FROM (NOW() - MAX(created_at)))/60 AS minutes_stale
FROM cortex_retrieval_index_entries WHERE tenant_id = :tenant;
```

**Accept:** `org_link_pct ≤ 30` AND `materialization+walk ≥ 60%` AND `minutes_stale < 120` during active ingest (when continuity track is healthy).

---

## 7. Synthesis stabilization plan

### 7.1 Non-negotiables

- **Do not weaken** `evaluate_phase08_empty_scope_truth_v1` (`phase08_empty_scope_truth_gate.py`).
- **Empty synthesis is better than hallucination.**
- **FAILED with SD codes** is success for honesty; **COMPLETED with `claims: []`** is not.

### 7.2 Minimum useful synthesis artifact

**Definition (phase contract):**

| Field | Requirement |
|-------|-------------|
| `published` | `true` |
| `artifact_kind` | `execution_brief` or `island_brief` (not `degradation_brief` unless `synthesis_legality_class` demands degradation) |
| `body_json.claims` | **≥1** claim |
| Each claim | `claim_text` + `evidence_refs[]` pointing to **retrieval_lookup_id** or raw record id |
| Omissions | Explicit `omission_classes[]` when scope incomplete |
| Receipt | No `SD-SCOPE-EMPTY` unless retrieval mix gate failed first |

### 7.3 Fix order (inputs before model)

1. **Retrieval mix gate** (§6) — synthesis should fail until retrieval is execution-shaped.
2. **Scope eligibility** — `synthesis_per_island.py` `list_retrieval_entries_for_island_v1` must use **published epoch** + island tags consistent with phase 07 receipt (`epoch-57147c1555c6` mismatch class of bugs).
3. **Job table hygiene** — reconcile 1,043 `failed` jobs; stop enqueue storms.
4. **Ingress digest** — ensure `retrieval_ingress_digest` changes when epoch mix changes (replay safety).
5. **Only then** tune prompts/templates for claim extraction.

### 7.4 Synthesis quality gates (add, don’t remove)

| Gate | Condition | Outcome |
|------|-----------|---------|
| Q1 | Published epoch `org_link_pct > 0.30` | FAIL phase 08 `retrieval_not_semantic` |
| Q2 | `retrieval_entries_in_scope == 0` | FAIL `phase08_empty_scope_with_retrieval_entries` (existing) |
| Q3 | Completed job with `claims.length == 0` | FAIL `synthesis_empty_claims` |
| Q4 | All island scopes failed | FAIL `synthesis_per_island_all_scopes_failed` (existing) |

### 7.5 Truthful omissions

- Prefer **explicit omission classes** in artifact body over silent empty claims.
- Degradation briefs only when **SD-*** codes prove substrate degradation — not default path.

---

## 8. Runtime simplification / dead-code cleanup

**This section deletes theater, not runtime continuity fixes.**

### DELETE (or finish deletion)

| Item | Path / note |
|------|-------------|
| Legacy substrate coordinator enqueue | `substrate_pipeline/coordinator`, `scheduling.py` guards |
| Duplicate per-step proof runners as **operational requirement** | Keep CI gates, delete from operator runbooks |
| Misleading “alive 6/6” as intelligence sign-off | `continuity_proof_panel.py` — split semantic panel |
| Raw auth link KPI | Admin overview metrics |
| `prod_substrate_proof_queries.py` as primary | Deprecated — use `continuity_audit_snapshot.py` + `graph_truth_audit_snapshot.py` |

### SIMPLIFY

| Item | Action |
|------|--------|
| 20+ `continuity_p0_phase_*_proof.py` | One **CI matrix** doc; operators run **2 scripts** only |
| Island registry display | Show `registry_snapshot_at` + SQL live edge count |
| Phase 03 label | Show `COMPLETED_EMPTY` verbatim |
| Candidate admin | Show distinct pairs + unpromoted, not 40k total |
| Unlock archive | `backend/scripts/archive/unlock/README.md` — recovery only |

### KEEP

| Item | Why |
|------|-----|
| `continuity_audit_snapshot.py` | Unified ops JSON |
| `graph_truth_audit_snapshot.py` | Semantic baseline |
| `dual_lane_worker.py` | Runtime (other track) but needed for 05–08 |
| Fail-loud synthesis gates | Honesty |
| `cortex_execution_reality_model_v0.md` | Vocabulary |

### DEFER

| Item | Why |
|------|-----|
| Probabilistic traversal | Out of scope |
| Embeddings / vector DB | Out of scope |
| New agent orchestration | Out of scope |
| Full deferral drain (11k) | Canonical track — only bound if blocking island mats |

---

## 9. Operational truth model

### What operators should care about now

**Semantic readiness panel (new, small)** — 6 numbers, no charts theater:

| # | Metric | SQL / source | Green threshold |
|---|--------|--------------|-----------------|
| 1 | `unique_auth_pairs` | §4.2 SQL | ↑ week-over-week; dup≤1.05 |
| 2 | `promotion_rule_count` | §5.4 SQL | ≥3 |
| 3 | `retrieval_org_link_pct` | §6.7 SQL | ≤30% |
| 4 | `retrieval_execution_pct` | mat+walk+causal | ≥60% |
| 5 | `synthesis_published_claims_7d` | artifacts with claims | ≥1 |
| 6 | `retrieval_freshness_minutes` | §6.7 SQL | &lt;120 when ingest active |

### Continuity metrics (separate tab — do not merge)

- FSM transitions, lease dirty, phase recurrence, walk count/24h  
- Owned by continuity track; link from admin but **don’t conflate** with semantic panel.

### STOP showing as primary

- Raw authoritative link rows  
- Raw candidate rows  
- Phase 04 `edge_count` without dedupe  
- `raw − mat` alone  

---

## 10. Detailed implementation roadmap

### Wave S0 — Truth baseline (3–5 days)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| S0.1 | Ship `graph_truth_audit_snapshot.py` fixes (components, ECS) | JSON reproducible |
| S0.2 | Admin + panel: `unique_pairs`, `dup_factor`, `rule_id` table | Fizzer shows 2000/5.2/1-rule |
| S0.3 | Document operator runbook (2 scripts) | This plan §Appendix |

**Rollback:** UI-only flags hide new metrics.

### Wave S1 — Graph dedupe & idempotent promotion (1 week)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| S1.1 | Unique constraint + promotion upsert | `dup_factor ≤ 1.05` |
| S1.2 | One-time duplicate revoke script + receipt | 10,400→~2,000 rows |
| S1.3 | Phase 04 receipt `unique_pairs_delta` | Receipt JSON in prod |
| S1.4 | Stop IDENTITY/03–04 spin when Δ=0 | No 8,800 link burst without new pairs |

**Validation:** §4.2 SQL after deploy.

**Rollback:** Drop constraint; restore from backup if revoke script wrong (dry-run mandatory).

### Wave S2 — Identity continuity (1–2 weeks)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| S2.1 | Fix promotion scheduling for GitHub + Slack rules | `promotion_rule_count ≥ 3` |
| S2.2 | Cap candidate batch inflation (distinct pair dedupe) | candidates/unique_pairs &lt; 3× |
| S2.3 | Anchor→entity boundary write | anchors_missing_entity −50% |
| S2.4 | Optional: second `link_type` for actor→artifact (if evidence exists) | ≥100 edges |

**Validation:** §5.4 SQL weekly.

### Wave S3 — Retrieval semantics (1–2 weeks)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| S3.1 | Phase 07 materialization order + caps | Published epoch mix passes L1 |
| S3.2 | Mix gate in publish contract | Fail-loud on violation |
| S3.3 | Island backfill for `d7e41b3c763d38e9` | One epoch passes §6 targets |
| S3.4 | Freshness metric on admin | &lt;120 min when worker healthy |

**Rollback:** Feature flag `cortex_retrieval_semantic_mix_gate_enabled=false` for emergency.

### Wave S4 — Synthesis usefulness (1 week, after S3)

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| S4.1 | Epoch/scope alignment fixes | `retrieval_entries_in_scope > 0` |
| S4.2 | Reconcile failed jobs | failed count stable near 0 post-epoch |
| S4.3 | Q3 empty-claims gate | No published empty claims |
| S4.4 | First **published** `execution_brief` with ≥1 claim | Prod artifact id recorded |

**Rollback:** Gates only — do not re-enable silent empty completion.

### Wave S5 — Cleanup (parallel, ongoing)

| Task | Deliverable |
|------|-------------|
| S5.1 | Delete coordinator paths |
| S5.2 | Collapse proof scripts in docs/CI |
| S5.3 | Remove fake KPIs from overview |

### Dependency graph

```text
S0 (metrics) → S1 (dedupe) → S2 (identity rules) → S3 (retrieval mix) → S4 (synthesis)
                     ↘ S5 (cleanup) parallel throughout
```

**Critical path:** S1 → S2 → S3 → S4. Without S1, graph metrics lie. Without S3, synthesis has nothing useful to say.

### Continuity track interface (minimal)

Only touch runtime when semantic work **requires** execution lane time:

- Ensure phase 07–08 are not permanently **queued** behind IDENTITY spin (FSM priority tweak — **small**, continuity-owned PR).
- Do **not** reopen dual-lane architecture.

---

## 11. Final target for this phase (concrete)

At phase end on Fizzer (minimum bar):

| Capability | Concrete outcome |
|------------|------------------|
| **Truthful graph** | `dup_factor ≤ 1.05`; ≥3 promotion rules with non-zero edges; no single-rule 100% graph |
| **Cross-system island** | Largest component includes handles linked under **≥2** of {Notion, GitHub, Slack} rules |
| **Meaningful retrieval** | Latest published epoch: `org_link ≤ 30%`, execution kinds ≥ 60%, ≥500 mat rows indexed |
| **Useful synthesis** | ≥1 **published** artifact / 7d with ≥1 claim + evidence refs to retrieval |
| **Freshness** | Retrieval rows &lt;2h stale during business-hours ingest |
| **Operator trust** | Semantic panel green without unlock scripts |
| **Engineer debug** | Single SQL pack explains graph+retrieval+synthesis for island scope |

**Explicitly NOT required at phase end:**

- Org-wide 95% entity graph participation
- Zero canonical deferrals
- Autonomous 48h AA clock pass (continuity track)
- Multi-tenant generalization beyond Fizzer proof

---

## Appendix A — Prod truths checklist (must remain visible)

- [ ] 96.5% graph-isolated entities (until identity+edges fix — track weekly)
- [ ] Only Notion rule promoted at baseline — **must change**
- [ ] 10,400 rows = 2,000 pairs — **must dedupe**
- [ ] Retrieval ~98% org_link — **must flip mix**
- [ ] Synthesis empty/failed — **must produce one useful artifact or stay failed loud**
- [ ] Slack/GitHub in anchors, not graph — **must promote**
- [ ] Runtime motion ≠ intelligence — **do not conflate in sign-off**

---

## Appendix B — Code map (implementation)

| Concern | Primary files |
|---------|----------------|
| Candidates | `identity/anchor_continuity_candidates.py` |
| Promotion | `identity/link_ledger.py`, `identity/org_link_replay_runtime.py` |
| Graph components | `operational_runtime/graph_orphan_continuity.py` |
| Phase 07 | `substrate_pipeline` phase 07 runner, `retrieval/retrieval_publish_contract.py` |
| Graph retrieval bind | `retrieval/retrieval_graph_binding.py` |
| Walk retrieval bind | `retrieval/retrieval_octs_binding.py` |
| Synthesis scope | `synthesis/synthesis_per_island.py` |
| Empty scope gate | `synthesis/phase08_empty_scope_truth_gate.py` |
| Admin metrics | `pipeline/continuity_overview_v1.py`, `pipeline/pipeline_admin_overview.py` |
| Ops snapshots | `scripts/continuity_audit_snapshot.py`, `scripts/graph_truth_audit_snapshot.py` |

---

## Appendix C — Skepticism log (assumptions challenged)

| Assumption | Challenge | Decision |
|------------|-----------|----------|
| “More auth links = progress” | 5× duplication | **Rejected** — unique pairs only |
| “Phase 04 COMPLETED = healthy graph” | Edge inflation | **Rejected** — delta metrics |
| “40k candidates = rich identity” | 2k distinct pairs | **Rejected** — cap batch noise |
| “Retrieval epochs = memory” | org_link mirror | **Rejected** — mix gates |
| “We need embeddings for synthesis” | Empty claims with 1,599 rows | **Rejected** — fix ingress |
| “We need new orchestration” | Worker already runs 05–08 | **Rejected** — reorder + gates |
| “Merge all humans globally” | 7k entities, deferrals | **Deferred** — island-first |

---

*End of plan. Do not treat this document as deployed work — it is the execution contract for the semantic/intelligence phase.*
