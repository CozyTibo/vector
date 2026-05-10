# Phase 04 — Control Plane Doctrine (Execution Continuity Operator Console)

**Status:** normative — **authoritative** for Phase 04 operator/admin surfaces, information architecture (logical only), API inventory, aggregate contracts, and operator-console verification gates (**G-P04-21–G-P04-26**).  
**Audience:** architects, implementers, verification authors, frontend admin authors.  
**Non-goals:** product UX for Phase 09, end-user workflows, graph traversal products, AI narration, org-chart cognition.

**Upstream:** Phase 01–03 admin patterns (ingestion + canonical: sparse, table-first, receipts), `phase-03-canonical-control-plane-doctrine.md` (philosophy alignment), Phase 3.5 continuity references, `phase-04-implementation-plan.md` (stages **P04-17**, **P04-18**). **Fixture stress:** `phase-04-mock-data-strategy.md` — hostile mock seed **`nexora_p04_hostile_baseline`** should **populate** non-trivial dashboard/queue states during Phase 04 development (§15 expected population).

---

## 1) Purpose

Phase 04 is **operationally dangerous** in the same *class* as canonicalization: silent merges, invisible candidate/authoritative confusion, replay drift, and opaque linkage destroy trust faster than missing charts.

This doctrine defines the **Execution Continuity Operator Console** — a **minimal, highly inspectable** substrate for answering continuity questions **without** opening raw JSON unless deliberately drilling down.

The console is **Phase 04 scope only**: organizational continuity, handles, ledger, merges, ambiguity, primitives, replay/regeneration, and **handoff validation** for Phase 05 projections — **not** a graph product.

---

## 2) Operator philosophy (aligned with Cortex admin)

1. **Tables + inspectors + receipts first** — list views are dense with **typed columns**; detail panes show **structured** evidence, rule ids, hashes, intervals — not narrative.
2. **Evidence-first** — every row answers: *what evidence*, *which rule version*, *which replay job*, *which bundle / equivalence context*.
3. **Replay/debug focused** — candidate regen vs authoritative replay, drift classes, receipts, and freshness labels are **first-class** navigation targets.
4. **Deterministic** — counts, hashes, and classifications come from **stored** or **verifiably recomputed** artifacts; no ML-derived “confidence UI.”
5. **Fast to understand** — operators scan **cards → queue depth → filtered table → row inspector**; default path avoids JSON blobs.
6. **Raw + canonical + continuity visibility** — inspectors link outward to **raw record** drilldown (Phase 01/02 patterns) and **canonical** object inspectors (Phase 03) **without** conflating them with org meaning.

---

## 3) Hard rule: no graph visualization theater

**Forbidden in Phase 04 admin:**

- Force-directed, node–link, or any **interactive graph layout** of org meaning.
- Org chart rendering, tree-of-teams cognition, or “relationship maps.”
- Traversal UX (click-to-expand neighborhood, path finding, “explore graph”).
- Phase 05 **consumption** UI (stored graph indexes, bounded traversals) — belongs in Phase 05+.

**Allowed:**

- **Tables** of handles, links, merges, primitives, jobs, ambiguities.
- **Structured inspectors** (property lists, timelines, receipt lists).
- **Graph export preview** (§10): **metadata only** — schema version, node/edge **counts**, edge **class** histogram, projection hash, timestamp, replay source — to validate Phase 05 **handoff**, not to explore meaning visually.

---

## 4) Anti-goals (operator UI specific)

Phase 04 operator surfaces MUST NOT become:

| Anti-goal | Rationale |
| --------- | --------- |
| Phase **09** product UI | No workflows, onboarding, or “customer success” dashboards. |
| **Graph theater** | Violates §3; poisons operator mental model before Phase 05. |
| **AI visualization** | No LLM summaries, embeddings maps, or “smart” clustering UI. |
| **Cognition / retrieval UX** | No ranking, search relevance, or “signals” — Phase 07+. |
| **Semantic dashboards** | No “insights,” themes, or interpreted org performance. |
| **Silent collapse UX** | No bulk “accept all matches”; merges stay **policy-gated** and visible. |
| **Raw JSON as default** | JSON only in **advanced** accordion or copy-export — not the primary list row. |

Full phase anti-goals remain in `phase-04-architecture-identity-linking-doctrine.md` and `phase-04-implementation-plan.md` §3.7.

---

## 5) Performance and paging constraints

| Constraint | Normative expectation |
| ---------- | --------------------- |
| **List endpoints** | Cursor or offset pagination with **hard caps**; default sort **deterministic** (e.g. `handle_id`, `link_id`, `created_at`, `temporal_ordering_key`). |
| **Aggregates** | Dashboard cards served from **precomputed** or **bounded** queries; must not full-scan unbounded joins on request path for large tenants. |
| **Inspectors** | Detail fetches **bounded** evidence lists (e.g. first N raw ids + “+M more” with explicit follow-up fetch). |
| **Exports** | Full projection download may be **async job** + file receipt (same pattern as certification pack) if size exceeds threshold. |
| **Staleness** | Cards expose `computed_at` + `freshness_label` where recomputation is expensive (**G-P04-18** alignment). |

---

## 6) Recommended admin information architecture (logical)

Naming is product-level; **obligations** below are normative. Suggested hierarchy under **Admin → Tenant → Cortex → Identity & continuity** (or **Execution continuity**):

| Nav item | Maps to console section | Primary question |
| -------- | ------------------------ | ---------------- |
| **Overview (dashboard)** | §7 Identity Dashboard | “What is the shape of continuity health?” |
| **Handles** | §8 Org Handles Explorer | “What org handles exist?” |
| **Links** | §9 Link Ledger Explorer | “What linked / failed / drifted / candidate-only?” |
| **Merges** | §10 Merge Queue | “What is proposed / approved / risky?” |
| **Ambiguities** | §11 Ambiguity Queue | “What does Cortex still not know?” |
| **Primitives** | §12 Primitive Explorer | “What org-shaped episodes exist?” |
| **Replay** | §13 Replay / Regeneration Console | “What replayed / regen’d / drifted?” |
| **Export preview** | §14 Graph export preview | “Is Phase 05 handoff structurally sane?” |

Cross-links in UI copy to **Ingestion** and **Canonical** tabs for raw/canonical drilldown — not duplicated here.

---

## 7) Surface 1 — Identity Dashboard (aggregate cards)

**Purpose:** one screen to answer continuity **volume and pressure** without tables.

**Required cards** (each card = `{ value, computed_at, freshness_label?, drilldown_route }`):

| Card | Operational meaning | Drilldown |
| ---- | -------------------- | --------- |
| **Org handles** | Count of active org entities (excl. tombstone policy per doctrine) | Handles explorer |
| **Persona bindings** | Count of active temporal bindings (persona → handle) | Handles + inspector filter |
| **Authoritative links** | Count in `cortex_org_link` (non-revoked / valid-now per doctrine) | Links explorer (`authoritative_only`) |
| **Candidate links** | Count from candidate store / last regen job summary | Links explorer (`candidate_only`) + Replay |
| **Ambiguous identities** | Count of open org-scoped ambiguity records | Ambiguity queue |
| **Pending merges** | Count of merge proposals awaiting decision | Merge queue |
| **Replay drift classes** | Histogram or top-N drift codes from last regen/replay jobs | Replay console |
| **Bundle equivalence gaps** | Count of unresolved / missing declarations blocking cross-bundle edges | Equivalence sub-panel or filtered Links |
| **Primitive instances** | Count by lifecycle state | Primitive explorer |
| **Orphaned references** | Count of normalized refs (Phase 3.5) with **no** qualifying org link / binding per doctrine | Dedicated filter or Ambiguity-derived |

**Verification:** **G-P04-21** — `GET .../identity/control-plane` payload includes **all** cards above with non-null contract fields defined in **Appendix A** (`identity_control_plane_v1`).

---

## 8) Surface 2 — Org Handles Explorer

**Primary question:** “What org handles exist, and what state are they in?”

### 8.1 List table (required columns)

| Column | Content |
| ------ | ------- |
| **handle_id** | Stable org handle identifier |
| **kind** | `HumanActor`, `ServiceAccount`, `Team`, … per org-entity doctrine |
| **created_from** | Rule id + short evidence summary **or** `operator|backfill` provenance label |
| **persona_count** | Active bindings count (valid interval) |
| **active_links** | Count of authoritative links touching handle (non-revoked, valid-now) |
| **temporal_state** | e.g. `active` / `superseded` / `tombstoned` + `valid_to` if applicable |
| **merge_state** | `none` / `pending_inbound` / `merged_into` / `split` — derived from merge ledger |
| **last_replay** | Last job id + outcome chip affecting this handle’s links/bindings |
| **confidence_posture** | **Non-ranking** structural label from Phase 04 confidence doctrine (e.g. `evidence_complete` / `evidence_partial` / `contested`) |

### 8.2 Row drilldown (handle inspector)

Structured sections (no default JSON blob):

- Handle identity + kind + temporal bounds  
- **Persona bindings** table (provider, external ref, interval, evidence ids)  
- **Merge history** (append-only ledger refs)  
- **Related links** shortcut into Link explorer with `handle_id` filter  
- **Primitives** touching handle  
- **Ambiguity** tickets referencing handle  
- Links to **raw** / **canonical** inspectors (ids only in table; full fetch on panel)

**Routes:** §15.1 (`handles`, `handles/{id}`).

---

## 9) Surface 3 — Link Ledger Explorer (**main debugging surface**)

**Primary questions:** “What linked successfully? What failed? What is candidate-only? What drifted? Which rule? Which evidence?”

### 9.1 List table (required columns)

| Column | Content |
| ------ | ------- |
| **link_type** | Typed org meaning link (doctrine enum) |
| **source_handle** | Source org handle id |
| **target** | Handle id **or** typed target (canonical pointer, normalized ref, primitive id) — **display discriminator column** `target_kind` |
| **rule_version** | `cortex_link_rule_version` id + semantic version string |
| **candidate / authoritative** | Single column **badge** + storage row pointer |
| **validity_interval** | `[valid_from, valid_to]` display; open-ended semantics per temporal doctrine |
| **evidence_count** | Count of bound raw record ids (not blob) |
| **replay_state** | e.g. `clean` / `drift` / `pending_regen` / `replay_failed` |
| **drift_class** | `L*` or doctrine-defined code; `NONE` when clean |

### 9.2 Required filters (normative)

All filters composable where logically AND-safe; backend MUST document unsupported combinations.

| Filter key | Semantics |
| ---------- | --------- |
| `authoritative_only` | Authoritative ledger rows only |
| `candidate_only` | Candidate store only |
| `ambiguous` | Links in contested / ambiguous state per org ambiguity doctrine |
| `revoked` | `revoked_at` set or superseded link chain |
| `replay_drift` | `drift_class != NONE` or job-level drift |
| `rule_version` | Exact `link_rule_version_id` |
| `primitive_id` | Links attached to primitive instance |
| `handle_id` | Either endpoint touches handle |
| `time_valid_at` | Point-in-time validity slice (optional) |

**Verification:** **G-P04-22** — list endpoint implements **all** filters above; integration tests cover pairwise smoke.

**Routes:** §15.1 (`links`, `links/{id}`).

---

## 10) Surface 4 — Merge Queue

**Primary question:** “What organizational sameness is proposed, and is it safe to approve?”

### 10.1 List table (required columns)

| Column | Content |
| ------ | ------- |
| **proposed_merge** | `from_handle` → `to_handle` (ids + kinds) |
| **evidence_sources** | Count + top exemplar evidence ids |
| **why_generated** | Rule id **or** `operator_manual` / `policy_promotion` |
| **policy_satisfied** | Boolean + list of missing predicates if false |
| **candidate_age** | Time since proposal / first observation |
| **ambiguity_count** | Linked open ambiguity records |
| **risk_class** | Deterministic enum (`low`/`medium`/`high_blocked`) per merge governance doctrine |

### 10.2 Actions (policy-gated, audited)

| Action | Effect (normative intent) |
| ------ | --------------------------- |
| **Approve** | Writes governed merge / promotion per `phase-04-merge-governance-doctrine.md` |
| **Reject** | Terminal negative decision + audit |
| **Defer** | Snooze / backlog without truth change |
| **Split** | Governance path for undoing mistaken collapse direction (compensating merge / split record) |

**Verification:** **G-P04-23** — every action emits durable audit row; **G-P04-15** (authorization) enforced on all **POST**s.

**Routes:** §15.1 (`merge-queue`, `merge-queue/{id}/…`).

---

## 11) Surface 5 — Ambiguity Queue (**“what Cortex still does not know”**)

**Philosophy:** unresolved multiplicity is **healthy visibility**, not a bug to hide. The queue is the honest surface for **unknowns**.

### 11.1 Required row classes (minimum)

| Class | Operator-facing label (example) |
| ----- | -------------------------------- |
| **Unresolved personas** | Multiple provider personas → incomplete binding to human handle |
| **Conflicting refs** | Same normalized ref family suggests incompatible handles |
| **Duplicate humans** | Evidence supports multiple human handles without merge |
| **Ownership contention** | Overlapping ownership windows / conflicting assignment |
| **Primitive contention** | Same evidence supports competing primitive instances |
| **Cross-tool collisions** | Connector-shaped evidence collision at continuity layer |

Each row: `{ ambiguity_id, class, severity, created_at, exemplar_handle_ids[], exemplar_link_ids[], evidence_sample_ids[], drilldown_route }`.

**Verification:** **G-P04-24** — when org ambiguity backlog count is non-zero, queue API returns at least one row **or** explicit `backlog_mismatch` diagnostic code on verification run (fail-closed for operator honesty).

**Routes:** §15.1 (`ambiguity-queue`, `ambiguity-queue/{id}`).

---

## 12) Surface 6 — Primitive Explorer

**First org-shaped inspection surface** — binds Phase 3.5 envelopes to org handles.

### 12.1 List table (required columns)

| Column | Content |
| ------ | ------- |
| **primitive_kind** | e.g. `WorkEpisode`, `DeliveryAttempt`, … |
| **linked_org_handles** | Count + abbreviated list |
| **evidence_refs** | Count of raw ids |
| **canonical_refs** | Count of canonical pointers |
| **temporal_bounds** | start/end or doctrine-specific window |
| **replay_lineage** | Last regen job id + hash fragment |
| **export_participation** | Included in last `OrgGraphProjectionV1`? + projection hash id |

**Verification:** **G-P04-26** — default list response returns **structured** fields; raw payload optional via `?include_raw_envelope=false` default.

**Routes:** §15.1 (`primitives`, `primitives/{id}`).

---

## 13) Surface 7 — Replay / Regeneration Console

**Primary question:** “What replayed, what regen’d, what drifted, with what receipts?”

### 13.1 Required panels / tables

| Panel | Content |
| ----- | ------- |
| **Candidate regen jobs** | Job id, status, started/completed, `link_rule_version`, input manifest hash, output candidate hash |
| **Authoritative replay jobs** | Job id, status, ledger slice, output hash |
| **Replay hashes** | Side-by-side candidate vs authoritative when applicable |
| **Drift classes** | Per-job and per-receipt breakdown |
| **Receipts** | Table of receipt ids + class + target entity |
| **Failed regenerations** | Failures with failure case linkage |
| **Rule versions used** | Pinned version per job |
| **Replay freshness** | `fresh` / `stale` + `computed_at` (**G-P04-18**) |

**Routes:** §15.1 (`replay-jobs`, `replay-jobs/{id}`, `POST …/replay-jobs/run`).

---

## 14) Surface 8 — Graph export preview (Phase 05 handoff only)

**NOT** graph traversal UI. **NOT** adjacency export in preview.

**Required preview fields:**

| Field | Purpose |
| ----- | ------- |
| `projection_schema_version` | `OrgGraphProjectionV1` version |
| `node_counts` | By node class bucket |
| `edge_counts` | Total + by edge class |
| `edge_class_histogram` | Map class → count |
| `projection_hash` | Stable hash of export payload rules per export doctrine |
| `generated_at` | Timestamp |
| `replay_source` | Job ids + rule versions that fed this export |

**Forbidden in preview:** neighbor lists, paths, force-directed coordinates, downloadable full edge list **unless** explicitly async “full export” job (then still not visualization — file download).

**Verification:** **G-P04-25** — preview response schema excludes large adjacency arrays; static test asserts max payload shape / keys allowlist.

**Routes:** §15.1 (`projection-preview`).

---

## 15) Admin HTTP route inventory (indicative)

All under tenant scope: `/admin/tenants/{tenant_id}/cortex/identity/…`  
(Exact router module: `vector.api.http.routes` — names indicative.)

### 15.1 Read surfaces

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `.../identity/control-plane` | Dashboard aggregate (**Appendix A**) |
| GET | `.../identity/handles` | Handles explorer list |
| GET | `.../identity/handles/{handle_id}` | Handle inspector |
| GET | `.../identity/links` | Link ledger explorer (**§9 filters**) |
| GET | `.../identity/links/{link_id}` | Link inspector |
| GET | `.../identity/merge-queue` | Merge proposals |
| GET | `.../identity/merge-queue/{merge_proposal_id}` | Merge proposal detail |
| GET | `.../identity/ambiguity-queue` | Ambiguity rows |
| GET | `.../identity/ambiguity-queue/{ambiguity_id}` | Ambiguity detail |
| GET | `.../identity/primitives` | Primitive explorer |
| GET | `.../identity/primitives/{primitive_id}` | Primitive inspector |
| GET | `.../identity/replay-jobs` | Job list (query: `job_kind`, `status`) |
| GET | `.../identity/replay-jobs/{job_id}` | Job + receipts |
| GET | `.../identity/projection-preview` | Graph export preview (**§14**) |
| GET | `.../identity/bundle-equivalence` | Declarations list (supports P04-09 card drilldown) |

### 15.2 Action surfaces (dangerous / gated)

| Method | Path | Purpose |
| ------ | ---- | ------- |
| POST | `.../identity/merge-queue/{id}/approve` | Approve merge (**§10**) |
| POST | `.../identity/merge-queue/{id}/reject` | Reject |
| POST | `.../identity/merge-queue/{id}/defer` | Defer |
| POST | `.../identity/merge-queue/{id}/split` | Split / compensating path |
| POST | `.../identity/links/{id}/revoke` | Revoke link (policy) |
| POST | `.../identity/replay-jobs/run` | Start candidate regen or authoritative replay |
| POST | `.../identity/projection-export/run` | Optional async full export job (if size threshold) |

POST bodies MUST be idempotent where doctrine requires (e.g. optional client `command_id`).

---

## 16) Backend aggregate and query contracts

### 16.1 Control-plane aggregate (`identity_control_plane_v1`)

Single JSON document returned by `GET .../identity/control-plane`.

**Minimal shape (normative keys — values typed per implementation):**

```json
{
  "schema_version": "identity_control_plane_v1",
  "tenant_id": "uuid",
  "computed_at": "iso8601",
  "freshness_label": "fresh|stale",
  "cards": {
    "org_handles": { "value": 0, "drilldown": "/…/handles" },
    "persona_bindings": {},
    "authoritative_links": {},
    "candidate_links": {},
    "ambiguous_identities": {},
    "pending_merges": {},
    "replay_drift": { "histogram": {} },
    "bundle_equivalence_gaps": {},
    "primitive_instances": {},
    "orphaned_references": {}
  },
  "last_authoritative_replay_job": null,
  "last_candidate_regen_job": null,
  "verification_pointer": { "last_org_verification_run_id": null }
}
```

### 16.2 List row contracts (minimal columns)

| Resource | Contract name | Required keys per row |
| -------- | --------------- | --------------------- |
| Handle list | `org_handle_list_row_v1` | `handle_id`, `kind`, `created_from`, `persona_count`, `active_links`, `temporal_state`, `merge_state`, `last_replay`, `confidence_posture` |
| Link list | `org_link_list_row_v1` | `link_id`, `link_type`, `source_handle_id`, `target`, `target_kind`, `rule_version`, `link_layer`, `valid_from`, `valid_to`, `evidence_count`, `replay_state`, `drift_class` |
| Merge queue | `org_merge_queue_row_v1` | `proposal_id`, `from_handle_id`, `to_handle_id`, `evidence_sources`, `why_generated`, `policy_satisfied`, `candidate_age`, `ambiguity_count`, `risk_class` |
| Ambiguity | `org_ambiguity_queue_row_v1` | `ambiguity_id`, `class`, `severity`, `exemplar_handle_ids`, `evidence_sample_ids` |
| Primitive | `org_primitive_list_row_v1` | `primitive_id`, `primitive_kind`, `handle_count`, `evidence_count`, `canonical_ref_count`, `temporal_bounds`, `replay_lineage`, `export_participation` |
| Replay job | `org_replay_job_list_row_v1` | `job_id`, `job_kind`, `status`, `rule_version`, `started_at`, `completed_at`, `input_hash`, `output_hash`, `drift_summary` |

Implementations MAY add keys; verification gates test **required** keys.

---

## 17) Co-evolution with stages

| Stage | Responsibility |
| ----- | ---------------- |
| **P04-17** | Aggregate builder + card semantics + freshness; links to explorers. |
| **P04-18** | HTTP routes + authz + request validation for all §15 routes; OpenAPI appendix. |
| **P04-19** | Worker job visibility wired into Replay console. |
| **P04-15** | Verification engine includes **G-P04-21–G-P04-26** in org verification payload sections. |

---

## 18) Verification gates (operator console)

| Gate | Statement |
| ---- | --------- |
| **G-P04-21** | Control-plane payload matches §7 cards + **Appendix A** required keys. |
| **G-P04-22** | Link ledger list supports **all** §9.2 filters. |
| **G-P04-23** | Merge queue mutations are RBAC-gated + audited (**G-P04-15** overlap). |
| **G-P04-24** | Ambiguity backlog honesty contract (**§11.1**). |
| **G-P04-25** | Projection preview is metadata-only (**§14**). |
| **G-P04-26** | Primitive default list is structured without raw blob (**§12**). |

**G-P04-18** (control plane freshness for org replay jobs) remains the **freshness** bar; **G-P04-21** is **shape/completeness** of the aggregate.

---

## Appendix A — `identity_control_plane_v1` card key checklist

Normative card keys under `cards` (each value object includes at least `value` numeric or structured histogram where specified, `computed_at`, `drilldown` path or route name):

1. `org_handles`  
2. `persona_bindings`  
3. `authoritative_links`  
4. `candidate_links`  
5. `ambiguous_identities`  
6. `pending_merges`  
7. `replay_drift` (includes `histogram`)  
8. `bundle_equivalence_gaps`  
9. `primitive_instances`  
10. `orphaned_references`

---

## Appendix B — OpenAPI (implementation placeholder)

When routes ship (**P04-18**), the generated or hand-authored **OpenAPI 3** description SHOULD live beside this doctrine (repo convention TBD: e.g. `04-identity/openapi/identity_admin.yaml`) and **must** enumerate every path in **§15** with request/response schemas derived from **§16** contracts.

---

## References

- `phase-04-implementation-plan.md` — P04-17, P04-18, §12 gates, §13 admin minimums  
- `phase-04-mock-data-strategy.md` — scenarios that **should** fill queues/cards in dev/CI  
- `phase-04-normative-index.md`  
- `phase-03-canonical-control-plane-doctrine.md` — precedent philosophy  
- `10-admin/phase-visualization-model.md`, `dangerous-action-safety-model.md`, `admin-permissions-model.md` — safety/RBAC patterns  
