# Phase 04 — Identity & Linking: Full Implementation Program

**Status:** implementation-grade sequencing (doctrine + architecture freeze).  
**Purpose:** define the **complete** Phase 04 execution program: stages, doctrines, persistence, replay, verification, admin minimums, closure, and boundaries—**without** implementing runtime in this document.

**Normative architecture shell:** `phase-04-architecture-identity-linking-doctrine.md`  
**Normative index / doctrine registry:** `phase-04-normative-index.md`  
**Hostile continuity mock data (dev/CI):** `phase-04-mock-data-strategy.md`  
**Upstream substrate:** Phases 01–03 + Phase 3.5 (`vector.domains.cortex.continuity`).

**Anti-drift principle (same as Phase 03):** each numbered stage maps to **one primary runtime responsibility**. Stages may not be merged without tracker amendment.

---

## 1) Executive verdict

**GO** to execute Phase 04 as the **organizational continuity layer**—**after** doctrine freeze (§5) and schema sketches for §7 are accepted.  

**NO-GO** to runtime coding if: merge/hint/candidate/authoritative classes are not frozen; if topology-vs-meaning boundary is not a **verification-enforced** invariant; if cross-bundle equivalence is unspecified.

Phase 04 **must not** subsume Phase 05 (graph storage/traversal), Phase 06 (causal semantics), Phase 07 (retrieval ranking), or Phase 08 (synthesis).

---

## 2) Architectural critique (why this program is shaped this way)

1. **Canonical materialization is bundle-scoped and provider-shaped**—correct for Phase 03. Organizational cognition requires **org handles** and **meaning links** that are **not** `CanonicalObjectKind` rewrites.
2. **Normalized references (3.5) are join keys, not identities.** Phase 04 must never treat `canonical_form` equality as “same human.”
3. **Replay/materialization topology (Phase 03) must not become organizational meaning.** If Phase 04 does not hard-separate, Phase 06 will attach causality to ingestion convenience.
4. **“Lightweight same-user” is a failure mode.** Phase 04 is intentionally heavy on **governance, ledger, and replay** to avoid irreversible merges.

---

## 3) Final Phase 04 end goal (expanded)

### 3.1 Organizational continuity (definition)

**Organizational continuity** is the property that, for a tenant, Cortex can name and maintain **stable org-scoped handles** for actors and subjects, and **evidence-bound, temporally valid links** between handles and between handles and substrate pointers—such that **replay** reproduces the same **authoritative** continuity state modulo explicit, audited policy changes.

### 3.2 What becomes reconstructable after Phase 04

- **Who** (org-scoped actor handles) participated in **which work artifacts** (via links to canonical pointers / raw ids / primitives).
- **Ownership / accountability windows** as evidence-bound intervals (not HR truth).
- **Work episodes** and **delivery attempts** as org-first spans anchored in raw + canonical evidence.
- **Cross-tool joins** at the **reference plane** + **link ledger** (not by collapsing canonical rows).

### 3.3 What later phases consume

| Consumer | Consumes from Phase 04 |
| -------- | ---------------------- |
| Phase 05 | Org nodes + **meaning edge set** (projection input), not raw topology |
| Phase 06 | Stable endpoints + temporal validity + supersession for causal attachment |
| Phase 07 | Org handle + link confidence for grounded retrieval |
| Phase 08 | Merge/ambiguity surfaces + provenance for safe synthesis |

### 3.4 What remains impossible after Phase 04 (explicit)

- Authoritative **causal** claims (“A blocked B”) unless defined elsewhere as event typing (Phase 06).
- **Semantic ranking** of people or teams.
- **Embeddings-default** identity resolution.
- **Silent** cross-provider human merge.

### 3.5 Success criteria (closure)

1. **Replay parity:** candidate regeneration deterministic; authoritative ledger replay reproduces org continuity state.
2. **Invariant suite:** all **G-P04-*** gates green on certified slice.
3. **Operator proof:** unresolved multiplicity and merge audit trails are visible and actionable (minimum surfaces).
4. **Boundary proof:** no verification path conflates Phase 03 topology with Phase 04 meaning edges.

### 3.6 Closure gates (high level)

- Doctrine set §5 complete + normative index entry.
- Stages **P04-01–P04-22** exit criteria met (per-stage tables below).
- Phase 04 **certification pack extension** (or parallel pack) archived (mirror Phase 03 Step 18 pattern).

### 3.7 Anti-goals

Graph engine, causal engine, retrieval ranking, NL summaries, inferred org chart as authority, embedding merge, “smart dedupe” without ledger.

### 3.8 Existential requirements

- Persisted **org_entity** (handle registry).
- Persisted **link_record** (ledger).
- Persisted **merge_record** (governed equivalence).
- **link_rule_version** + candidate engine.
- **Two-layer replay** (candidates vs authoritative).

---

## 4) Full ordered step-by-step implementation plan (stages P04-01 — P04-22)

Each row: **Stage | Objective | Why | Deliverables | Doctrine | Runtime module | DB | Replay | Verification | Tests | Admin min | Downstream**

### Stage P04-01 — Normative index + program freeze

| Field | Content |
| ----- | ------- |
| **Objective** | Freeze Phase 04 normative index; anti-goals; vocabulary. |
| **Why** | Prevents split-brain semantics across modules. |
| **Deliverables** | `phase-04-normative-index.md`; glossary § |
| **Doctrine** | New index file |
| **Runtime** | — |
| **DB** | — |
| **Replay** | N/A |
| **Verification** | Doc lint / peer review gate |
| **Tests** | — |
| **Admin** | — |
| **Downstream** | Unlocks all stages |

### Stage P04-02 — Topology vs meaning boundary (verification-first)

| Field | Content |
| ----- | ------- |
| **Objective** | Make “materialization DAG edge” vs “org meaning link” disjoint types at **type system + verification** level. |
| **Why** | Prevents graph/causal poisoning. |
| **Deliverables** | `phase-04-topology-vs-meaning-doctrine.md`; invariant IDs `INV-P04-TOPO-01..` |
| **Doctrine** | New |
| **Runtime** | `identity.boundary_checks` (pure validators) |
| **DB** | — |
| **Replay** | N/A |
| **Verification** | **G-P04-TOPO-01** forbidden cross-import in link payloads |
| **Tests** | Negative: topology edge shape rejected by org link validator |
| **Admin** | Doc link in operator handbook |
| **Downstream** | P05, P06 safe |

### Stage P04-03 — Org handle + org entity doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Define org handle identity: ids, kinds, lifecycle, tombstones. |
| **Why** | Canonical ids cannot serve this role. |
| **Deliverables** | `phase-04-org-entity-and-handle-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.org_entities` (schemas only → then impl) |
| **DB** | `cortex_org_entity` (name indicative) |
| **Replay** | Handles stable; tombstone via supersession row |
| **Verification** | **G-P04-ORG-01** handle id deterministic for same evidence seed (where applicable) |
| **Tests** | UUIDv5/name rules unit tests |
| **Admin** | Read-only list + detail (sparse) |
| **Downstream** | All linking |

### Stage P04-04 — Link ledger doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Typed links, temporal validity, provenance, confidence, supersession. |
| **Why** | Core ledger for Phase 05. |
| **Deliverables** | `phase-04-link-ledger-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.link_ledger` |
| **DB** | `cortex_org_link` |
| **Replay** | Regenerate candidates; replay authoritative from ledger |
| **Verification** | **G-P04-LINK-01** no link without evidence refs or explicit rule id |
| **Tests** | Property: temporal intervals non-overlap for authoritative same-type edges where doctrine requires |
| **Admin** | Link inspector (raw ids, rule, confidence) |
| **Downstream** | P05 |

### Stage P04-05 — Candidate vs authoritative linkage doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Formal two-layer model: candidates recomputed; authoritative from auditable writes. |
| **Why** | Replay safety + operator governance. |
| **Deliverables** | `phase-04-candidate-vs-authoritative-linkage-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.candidate_generation`, `identity.authoritative_writer` |
| **DB** | `cortex_org_link_candidate` (optional table) **or** ephemeral job output + hash; **authoritative** in `cortex_org_link` |
| **Replay** | Job: `regenerate_link_candidates`; job: `replay_authoritative_links` |
| **Verification** | **G-P04-CAND-01** candidates cannot promote without policy record |
| **Tests** | Replay hash of candidate set |
| **Admin** | “Candidate queue” sparse view |
| **Downstream** | P06 trust |

### Stage P04-06 — Merge governance doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Human merge, team merge, service split; forbidden merges; audit. |
| **Why** | Irreversible damage if wrong. |
| **Deliverables** | `phase-04-merge-governance-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.merge_policy`, `identity.merge_record` |
| **DB** | `cortex_org_merge` |
| **Replay** | Merge ledger append-only; rollback via compensating merge (no delete) |
| **Verification** | **G-P04-MRG-01** no human merge without two persona evidence + operator/policy record where required |
| **Tests** | Negative: email-only merge rejected |
| **Admin** | Merge approval workflow (minimal) |
| **Downstream** | P08 safety |

### Stage P04-07 — Hint / inferred / prohibited link classes

| Field | Content |
| ----- | ------- |
| **Objective** | Encode non-authoritative hints; prohibit classes. |
| **Why** | Prevents “maybe” becoming “is.” |
| **Deliverables** | `phase-04-hint-and-prohibited-link-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.link_classes` enums + validators |
| **DB** | `link_class` enum column |
| **Replay** | Hints regenerated or stored with explicit non-authority flag |
| **Verification** | **G-P04-HINT-01** hints excluded from merge closure |
| **Tests** | Closure algorithm tests |
| **Admin** | Hint bucket (read-only) |
| **Downstream** | P07 optional retrieval |

### Stage P04-08 — Temporal validity + revocation doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Intervals, open-ended links, revocation events, supersession chain. |
| **Why** | Continuity over time + provider renames. |
| **Deliverables** | `phase-04-temporal-validity-and-revocation-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.temporal` |
| **DB** | `valid_from`, `valid_to`, `revoked_at`, `supersedes_link_id` |
| **Replay** | Regen respects validity windows |
| **Verification** | **G-P04-TMP-01** no overlapping authoritative merges for mutually exclusive classes |
| **Tests** | Interval logic battery |
| **Admin** | Timeline strip (sparse) |
| **Downstream** | P06 |

### Stage P04-09 — Bundle + cross-bundle equivalence doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Cross-bundle canonical pointers on edges require explicit equivalence declarations. |
| **Why** | Prevent forked universes. |
| **Deliverables** | `phase-04-cross-bundle-equivalence-doctrine.md`; extend `bundle_continuity_semantics` narrative |
| **Doctrine** | New |
| **Runtime** | `identity.bundle_equivalence` |
| **DB** | `cortex_bundle_equivalence_declaration` |
| **Replay** | Replay declarations before link replay |
| **Verification** | **G-P04-BNDL-01** |
| **Tests** | Cross-bundle negative tests |
| **Admin** | Equivalence audit |
| **Downstream** | P05 |

### Stage P04-10 — Continuity replay + regeneration doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Orchestrate jobs; drift classes; receipts (mirror C0–C5 style for links). |
| **Why** | Same bar as canonical replay. |
| **Deliverables** | `phase-04-continuity-replay-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.replay_jobs`, receipts tables |
| **DB** | `cortex_org_link_replay_job`, `cortex_org_link_replay_receipt` (indicative) |
| **Replay** | First-class |
| **Verification** | **G-P04-RPL-01** candidate regeneration deterministic hash |
| **Tests** | Job integration tests |
| **Admin** | Job list minimal |
| **Downstream** | Ops trust |

### Stage P04-11 — Linkage rule engine + versioning

| Field | Content |
| ----- | ------- |
| **Objective** | Deterministic rules emitting candidates from raw + 3.5 refs + canonical pointers. |
| **Why** | Avoid ad-hoc SQL in five places. |
| **Deliverables** | `phase-04-linkage-rule-engine-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.linkage_rules` |
| **DB** | `cortex_link_rule_version` |
| **Replay** | Version pinned per job |
| **Verification** | **G-P04-RULE-01** |
| **Tests** | Golden vectors per rule |
| **Admin** | Rule version readout |
| **Downstream** | Determinism |

### Stage P04-12 — Execution primitive persistence doctrine

| Field | Content |
| ----- | ------- |
| **Objective** | Bind Phase 3.5 primitive envelopes to org handles + evidence; persistence rules. |
| **Why** | Prevents Phase 05 provider-shaped graph. |
| **Deliverables** | `phase-04-execution-primitive-persistence-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.execution_primitives` |
| **DB** | `cortex_org_primitive_instance` |
| **Replay** | Rebuild primitives from evidence + rule versions |
| **Verification** | **G-P04-PRIM-01** no primitive without evidence_raw_ids |
| **Tests** | Fixture per primitive kind |
| **Admin** | Primitive inspector |
| **Downstream** | P05 org-shaped nodes |

### Stage P04-13 — Graph boundary doctrine (outputs for Phase 05)

| Field | Content |
| ----- | ------- |
| **Objective** | Define export contract: **OrgGraphProjectionV1** JSON schema (nodes/edges) from ledger—not a DB. |
| **Why** | Phase 05 ingests a frozen contract. |
| **Deliverables** | `phase-04-graph-projection-export-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.projection_export` |
| **DB** | — (export is view/query) |
| **Replay** | Export reproducible |
| **Verification** | **G-P04-EXP-01** export stable hash |
| **Tests** | Snapshot tests |
| **Admin** | Download export (gated) |
| **Downstream** | P05 |

### Stage P04-14 — Ambiguity + multiplicity surfaces (org scope)

| Field | Content |
| ----- | ------- |
| **Objective** | Org-level ambiguity records (distinct from Phase 03 ambiguity where needed) OR extend Phase 03 with org scope—**decide in doctrine** before impl. |
| **Why** | Unresolved multiplicity is healthy, not a bug. |
| **Deliverables** | `phase-04-ambiguity-multiple-persona-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.ambiguity` |
| **DB** | `cortex_org_ambiguity_record` (if separate) |
| **Replay** | Replay ambiguity transitions |
| **Verification** | **G-P04-AMB-01** |
| **Tests** | Multiplicity scenarios |
| **Admin** | “Unresolved actors” queue |
| **Downstream** | P08 |

### Stage P04-15 — Identity verification engine extension

| Field | Content |
| ----- | ------- |
| **Objective** | Add Phase 04 gate suite to verification runner (tenant + CI). |
| **Why** | Prevent regression. |
| **Deliverables** | `phase-04-verification-gates-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.verification` |
| **DB** | optional `cortex_org_verification_run` |
| **Replay** | N/A |
| **Verification** | **G-P04-01–G-P04-26** (§12.1); incl. operator console gates **G-P04-21–G-P04-26** from `phase-04-control-plane-doctrine.md` §18 |
| **Tests** | Gate fixtures; **CI slices** from `phase-04-mock-data-strategy.md` §§16–17 (`nexora_p04_ci_slice_*`) |
| **Admin** | Verification panel extension (surface console gate failures with drilldown hints) |
| **Downstream** | Closure |

### Stage P04-16 — Failure + remediation (org scope)

| Field | Content |
| ----- | ------- |
| **Objective** | Classify org linkage failures; remediation paths (replay regen, revoke link, split merge). |
| **Why** | Operational safety. |
| **Deliverables** | `phase-04-failure-remediation-doctrine.md` |
| **Doctrine** | New |
| **Runtime** | `identity.failure_remediation` |
| **DB** | `cortex_org_failure_case` |
| **Replay** | Regen after repair |
| **Verification** | gates tied to failure sync |
| **Tests** | remediation flows |
| **Admin** | repair actions |
| **Downstream** | ops |

### Stage P04-17 — Control plane aggregate (org continuity)

| Field | Content |
| ----- | ------- |
| **Objective** | Ship the **Execution Continuity Operator Console** aggregate: **Identity Dashboard** cards (handles, persona bindings, authoritative/candidate links, ambiguities, pending merges, replay drift histogram, bundle-equivalence gaps, primitive instances, orphaned refs) + freshness pointers — per `phase-04-control-plane-doctrine.md` §§5–7, **Appendix A**, aggregate contract `identity_control_plane_v1`. |
| **Why** | Operators must answer continuity health **without** JSON or graph theater; parity with Ingestion/Canonical **sparse proof** style. |
| **Deliverables** | `phase-04-control-plane-doctrine.md` (normative IA, surfaces §7–14, performance §5, anti-goals §4); aggregate builder `identity.control_plane`. |
| **Doctrine** | `phase-04-control-plane-doctrine.md` (**authoritative** for operator IA + card contracts) |
| **Runtime** | `identity.control_plane` (deterministic aggregations + drilldown route hints) |
| **DB** | read models / materialized views optional; indexes to meet §5 paging/cost bars |
| **Replay** | `freshness_label` on cards; last candidate regen + authoritative replay job pointers (**G-P04-18**) |
| **Verification** | **G-P04-21** (dashboard card contract); **G-P04-18** (replay freshness); control-plane section on org verification run |
| **Tests** | Contract tests on `identity_control_plane_v1` JSON shape + snapshot exemplar tenant |
| **Admin** | **Identity → Overview** dashboard route wired to aggregate API |
| **Downstream** | P04-18 UI tables consume same freshness semantics |

### Stage P04-18 — API routes (internal/admin)

| Field | Content |
| ----- | ------- |
| **Objective** | Implement **all** read + gated write routes in `phase-04-control-plane-doctrine.md` **§15** (handles explorer, **link ledger explorer** with §9.2 filters, merge queue + actions, ambiguity queue, primitive explorer, replay/regeneration console listings, bundle-equivalence list, **projection preview** §14). Tables-first list/detail JSON; dangerous POSTs idempotent where required. |
| **Why** | Without routes, the console is fiction; **Link Ledger Explorer** is the primary debugging surface. |
| **Deliverables** | OpenAPI-style appendix in control plane doctrine (§15 kept canonical path inventory); `vector.api.http.routes` identity module implementing §15.1–§15.2. |
| **Doctrine** | `phase-04-control-plane-doctrine.md` §§8–16 + §15 |
| **Runtime** | `vector.api.http.routes.identity_*` (+ list row serializers per §16.2) |
| **DB** | uses org tables; list queries respect §5 caps |
| **Replay** | `POST .../replay-jobs/run` triggers jobs; job list/detail feed Replay console |
| **Verification** | **G-P04-22** (filter parity); **G-P04-23** (merge POST audit + RBAC **G-P04-15**); **G-P04-24**–**G-P04-26** as applicable; authz integration tests |
| **Tests** | HTTP integration per resource; filter matrix tests for links |
| **Admin** | Frontend routes for **Identity** IA §6: Overview, Handles, **Links**, Merges, **Ambiguities**, Primitives, **Replay**, **Export preview** |
| **Downstream** | P04-19 jobs UI; P04-15 verification payloads |

### Stage P04-19 — Celery / worker jobs

| Field | Content |
| ----- | ------- |
| **Objective** | Async candidate regen, authoritative replay, export build. |
| **Why** | Large tenants |
| **Deliverables** | task modules |
| **Doctrine** | replay doc |
| **Runtime** | `app.tasks.cortex_identity_*` |
| **DB** | job tables |
| **Replay** | core |
| **Verification** | job receipts |
| **Tests** | celery integration optional |
| **Admin** | Job status surfaces in **Replay / Regeneration Console** (`phase-04-control-plane-doctrine.md` §13) |
| **Downstream** | scale |

### Stage P04-20 — Migration + backfill strategy

| Field | Content |
| ----- | ------- |
| **Objective** | Backfill org handles from existing canonical anchors **as candidates** only. |
| **Why** | Avoid mass auto-merge. |
| **Deliverables** | `phase-04-backfill-doctrine.md`; mock implementation of **`phase-04-mock-data-strategy.md`** (personas, scenario keys, `continuity_fixture` sidecar, generator overlay wiring). |
| **Doctrine** | New + mock strategy (**Shipped**) |
| **Runtime** | `identity.backfill` |
| **DB** | migrations |
| **Replay** | reproducible backfill hash |
| **Verification** | **G-P04-BF-01** no authoritative merge from backfill |
| **Tests** | backfill fixtures; hostile mock validation (`validate_mock_dataset.py` extensions per mock strategy §6.4) |
| **Admin** | run backfill job |
| **Downstream** | adoption |

### Stage P04-21 — Stabilization + economics pass

| Field | Content |
| ----- | ------- |
| **Objective** | Load tests on regen; storage estimates; explosion thresholds. |
| **Why** | Prevent Phase 04 from becoming cost sink. |
| **Deliverables** | readiness audit update |
| **Doctrine** | `phase-04-readiness-audit.md` |
| **Runtime** | probes |
| **DB** | indexes |
| **Replay** | budget |
| **Verification** | perf gates optional |
| **Tests** | perf smoke; regen/replay cost on **`nexora_p04_hostile_baseline`** (mock strategy §17) |
| **Admin** | warnings |
| **Downstream** | cost |

### Stage P04-22 — Closure + certification pack (Phase 04)

| Field | Content |
| ----- | ------- |
| **Objective** | Archive certification artifacts; **G-P04-01–G-P04-26** all pass; sign-off. |
| **Why** | Same institutional pattern as Phase 03 Step 18. |
| **Deliverables** | `phase-04-closure-gates-doctrine.md`; pack builder |
| **Doctrine** | New |
| **Runtime** | `identity.certification_pack` |
| **DB** | `cortex_org_certification_archive` |
| **Replay** | pack includes regen hashes |
| **Verification** | **G-P04-CLOSE-01** |
| **Tests** | pack contract tests |
| **Admin** | download pack |
| **Downstream** | Phase 05 kickoff |

---

## 5) Required foundational doctrines (complete list + challenges)

**Must exist before runtime (minimum):**

1. `phase-04-normative-index.md`
2. `phase-04-topology-vs-meaning-doctrine.md`
3. `phase-04-org-entity-and-handle-doctrine.md`
4. `phase-04-link-ledger-doctrine.md`
5. `phase-04-merge-governance-doctrine.md`
6. `phase-04-candidate-vs-authoritative-linkage-doctrine.md`
7. `phase-04-temporal-validity-and-revocation-doctrine.md`
8. `phase-04-cross-bundle-equivalence-doctrine.md`
9. `phase-04-continuity-replay-doctrine.md`
10. `phase-04-linkage-rule-engine-doctrine.md`
11. `phase-04-execution-primitive-persistence-doctrine.md`
12. `phase-04-graph-projection-export-doctrine.md`
13. `phase-04-hint-and-prohibited-link-doctrine.md`
14. `phase-04-ambiguity-multiple-persona-doctrine.md`
15. `phase-04-verification-gates-doctrine.md`
16. `phase-04-failure-remediation-doctrine.md`
17. `phase-04-control-plane-doctrine.md` (**Shipped** — Execution Continuity Operator Console: §§3–18, route inventory §15, **G-P04-21–G-P04-26**)
18. `phase-04-backfill-doctrine.md`
19. `phase-04-readiness-audit.md`
20. `phase-04-closure-gates-doctrine.md`
21. `phase-04-anti-goals-doctrine.md` (may merge into index)
22. `phase-04-graph-boundary-doctrine.md` (explicit “no traversal engine in P04”)
23. `phase-04-mock-data-strategy.md` (**Shipped** — hostile deterministic mock/fixture program for identity stress; **not** a runtime doctrine file but **normative** for `backend/mock_connectors/` Phase 04 work)

**Likely additional (challenge: add if not redundant):**

- `phase-04-privacy-and-data-minimization-doctrine.md` (human identity sensitive)
- `phase-04-authorization-model-doctrine.md` (who may approve merges)
- `phase-04-tenant-isolation-doctrine.md` (cross-tenant leak forbidden patterns)

---

## 6) Organizational entity model (all classes)

Legend: **Instantiate** = may create handle from evidence. **Forbidden** = must not create without governance record.

| Class | Why exists | May instantiate from | Must NOT instantiate from | Replay | Temporal | Merge | Continuity | Provenance |
| ----- | ---------- | ---------------------- | --------------------------- | ------ | -------- | ----- | ---------- | ---------- |
| **HumanActor** | Cross-tool person continuity | Provider user objects + explicit merge ledger | Email equality alone | Stable handle id; merges append-only | validity on persona bindings | governed merge only | multi-persona explicit | raw ids per binding |
| **ServiceAccount** | Bots/integrations | provider bot flags | human heuristics | stable | service rename events | no merge into human | drift visible | evidence |
| **Team** | Org groupings | provider team objects | message co-occurrence | stable | membership intervals | merge w/ policy | continuity via membership links | evidence |
| **RepositoryAsset** | Org-owned repo | repo records + org policy | inferred from stars | stable | rename/ref moves | link to org unit | ref normalization | evidence |
| **Initiative** / **Workstream** | initiative continuity | explicit provider objects or declared org initiative | inferred from chatter | stable | windows | merge rare | links to work | evidence |
| **WorkEpisode** | org-shaped work span | primitive envelope + evidence | single message | rebuild from evidence+rules | start/end | split/merge via ledger | links to delivery | raw+canonical |
| **DeliveryAttempt** | ship attempts | deploy/workflow evidence | green CI alone | rebuild | attempt window | no auto merge | episode linkage | evidence |
| **CoordinationThread** | escalation/discussion spine | slack thread + ticket refs | sentiment | rebuild | active intervals | merge cautious | links to episode | evidence |
| **OwnershipWindow** | accountability | explicit role assignments | inferred blame | rebuild | intervals | transfer events | supersession | evidence |
| **DecisionWindow** | decision periods | explicit decision artifacts (if any) | inferred | rebuild | bounded | no auto merge | links | evidence |
| **IncidentWindow** | incident intervals | incident provider objects or manual declare | inferred outages | rebuild | interval | merge policy | links deploy | evidence |
| **BlockageEpisode** | blocked execution | explicit blocked state in tools | inferred “slow” | rebuild | interval | no merge | links issue/PR | evidence |
| **ReviewCycle** | review phases | review objects + time bounds | single comment | rebuild | cycles | rare merge | link PR | evidence |
| **EscalationChain** | escalation path | thread/ticket linkage evidence | org chart guess | rebuild | chain version | no auto merge | coord thread | evidence |

---

## 7) Link / merge / hint theory (governance model)

### 7.1 Classes

| Class | Authority | Replay | Promotion |
| ----- | --------- | ------ | --------- |
| **Deterministic link** | E0/E1 from provider-structural fields | regen from rules | automatic candidate → authoritative only if rule declares |
| **Candidate link** | recomputed | always regen | never authoritative until promotion |
| **Inferred link** | **default PROHIBITED authoritative** | if allowed at all: candidate only | requires future policy (post-P04) |
| **Hint** | non-authoritative | regen ok | **must not** affect merge closure |
| **Authoritative link** | ledger row | replay from ledger | operator/policy |
| **Prohibited** | never stored authoritative | — | — |

### 7.2 Merge semantics

Merge is **only** via `merge_record` with: `from_handle`, `to_handle`, `evidence`, `policy_ref`, `operator_ref?`, `supersedes?`. **Undo** = compensating merge, not delete.

### 7.3 Revocation / supersession

Links support `revoked_at` + `supersedes_link_id`. **Temporal validity** mandatory for authoritative “same_as” family.

### 7.4 “Might be related” vs “same entity”

- **Might be related:** `hint` link class + **excluded** from merge closure algorithms.
- **Same entity:** only `merge_record` + canonical **equivalence** rules for org handles (not refs).

---

## 8) Temporal continuity (survival requirements)

Identity/org evolution must survive: replay, rematerialization, bundle changes, connector churn, renames, deleted accounts, split identities.

**Mechanisms:**

- **Append-only** merges and links (compensating events).
- **Validity intervals** on persona bindings.
- **Rename continuity** via new provider id link superseding old (not in-place rewrite).
- **Deleted accounts** → tombstone handle + preserved historical links read-only after `valid_to`.
- **Split identities** → split merge record + new handles; never silent.

---

## 9) Replay + regeneration (adequacy challenge)

**Current Phase 03 replay is sufficient for canonical rows, not for org continuity.** Phase 04 must add:

- **Candidate regen job** pinned to `link_rule_version` + raw snapshot id / raw hash manifest.
- **Authoritative replay** from append-only merge/link ledger.
- **Drift classes** for link regen (mirror C-classes): e.g. `L1` rule hash mismatch, `L2` evidence missing, `L3` forbidden promotion attempt.

**Challenge conclusion:** extend replay doctrine; do not reuse canonical replay job as sole mechanism.

---

## 10) Execution primitives (doctrine-level)

Each primitive: **representation**, **evidence**, **cannot**, **deterministic boundaries**, **temporal**, **replay**, **provenance**, **graph implication (P05)**.

(Detailed per-primitive matrices live in `phase-04-execution-primitive-persistence-doctrine.md`—must expand to one subsection each before coding.)

**Graph implication:** primitives become **first-class nodes** in `OrgGraphProjectionV1`; provider artifacts attach as **typed attachments**, not as the only nodes.

---

## 11) Graph-ready semantics (pre-Phase 05)

**Minimum authoritative meaning edges before P05:**

- `PersonaBelongsToHuman` (provider persona → org handle) — evidence-backed.
- `ArtifactParticipatesInWorkEpisode` (canonical pointer → primitive) — many-to-many allowed with evidence.
- `OrgHandleEquatesToNormalizedReference` (join alignment) — non-merge, reference plane only.
- `OwnershipHeldInWindow` (handle → interval) — interval table or link attrs.

**Hard separation:** export **only** org projection; never export materialization DAG as “org graph.”

---

## 12) Verification + closure

### 12.1 Gate list (draft numbering)

- **G-P04-01** No authoritative human merge without merge_record + dual evidence policy satisfied.
- **G-P04-02** Hints excluded from merge closure (static analysis over code paths).
- **G-P04-03** Cross-bundle canonical endpoints forbidden without equivalence declaration.
- **G-P04-04** Candidate regen deterministic hash stable on frozen inputs.
- **G-P04-05** Authoritative replay reproduces link set hash.
- **G-P04-06** No link without `evidence_raw_record_ids` OR explicit `rule_id` with fixture vector.
- **G-P04-07** ServiceAccount cannot merge HumanActor (default).
- **G-P04-08** Topology edge types cannot appear in org link table (schema or validator).
- **G-P04-09** Primitive instances require evidence set.
- **G-P04-10** Export projection stable hash.
- **G-P04-11** Tombstone rules: deleted provider accounts do not delete historical links.
- **G-P04-12** Ambiguity pressure thresholds (explosion warn) like Phase 03.
- **G-P04-13** Merge rollback only via compensating merge (detect illegal deletes).
- **G-P04-14** Bundle equivalence replay ordering declared.
- **G-P04-15** Authorization: merge actions require role gate.
- **G-P04-16** Privacy: PII minimization on exports.
- **G-P04-17** Org verification run green on certified slice.
- **G-P04-18** Control plane freshness for org replay jobs.
- **G-P04-19** Failure registry sync completeness.
- **G-P04-20** Certification pack archived.
- **G-P04-21** Identity control-plane aggregate includes all dashboard cards and required keys (`identity_control_plane_v1`, `phase-04-control-plane-doctrine.md` §7 + Appendix A).
- **G-P04-22** Link ledger list endpoint supports all normative filters (authoritative-only, candidate-only, ambiguous, revoked, replay drift, rule version, primitive scope, handle scope, optional time-validity).
- **G-P04-23** Merge queue actions (approve / reject / defer / split) are RBAC-gated and emit durable audit records (**G-P04-15** overlap).
- **G-P04-24** Ambiguity queue honesty: non-zero org ambiguity backlog implies visible rows or explicit `backlog_mismatch` diagnostic on verification.
- **G-P04-25** Graph export **preview** is metadata-only (no traversal / adjacency theater); allowlisted response shape.
- **G-P04-26** Primitive explorer default list rows are structured (`org_primitive_list_row_v1`); raw JSON blob not default.

### 12.2 Closure criteria

All gates **G-P04-01–G-P04-26** (incl. operator console **G-P04-21–G-P04-26**) + Stage P04-22 pack + operator sign-off on merge policy defaults.

### 12.3 Stabilization / certification

Mirror Phase 03-17/18: org stabilization proof + org certification archive.

---

## 13) Admin / control plane minimums (sparse, escalation-oriented)

**Authoritative operator spec:** `phase-04-control-plane-doctrine.md` — **Execution Continuity Operator Console** (Identity Dashboard, Org Handles Explorer, **Link Ledger Explorer** as primary debug surface, Merge Queue, **Ambiguity Queue**, Primitive Explorer, Replay/Regeneration Console, **Graph export preview** for P05 handoff only). Philosophy: **tables + inspectors + receipts first**; **no graph visualization theater** (§3 of doctrine).

**Must inspect (workflow):** dashboard cards → unresolved multiplicity (**Ambiguity Queue**) → pending merges → link regen drift (**Replay console** + ledger **replay_drift** filter) → bundle equivalence gaps → orphaned refs card → primitive counts.

**Must approve:** human merge, cross-bundle equivalence, promotion candidate→authoritative where policy demands (**Merge Queue** actions).

**Must repair:** revoke bad link, compensating merge, rerun regen job (from Link inspector / Replay console).

**Must replay:** authoritative link replay job, candidate regen job (**Replay console**).

**Must understand:** topology-vs-meaning doc, merge governance, “hints are not truth” (`phase-04-topology-vs-meaning-doctrine.md`, merge + hint doctrines).

### 13.1 Hostile mock dataset (implementation co-requisite)

Local mock data must **not** stay “clean Nexora only” during Phase 04 coding. **`phase-04-mock-data-strategy.md`** defines:

- **Scenario families** (`P04MD-*`) covering human/persona, temporal, cross-tool, primitive, ambiguity, replay-drift, and bundle-equivalence stress.
- **Deterministic personas** (e.g. `tibo_fracture`, two-Alex collision, deleted Dana, shared-email pair).
- **L-class replay drift** injectors (**L0–L7**) tied to explainable fixture changes.
- **CI slices** vs full **`nexora_p04_hostile_baseline`** for economics and verification.

Runtime + verification authors MUST treat hostile mock scenarios as **first-class** inputs alongside unit vectors.

---

## 14) Phase boundary audit

| Concern | Phase 04 | Phase 05 | Phase 3.5 |
| ------- | -------- | -------- | --------- |
| Org handles + merges | **yes** | no | refs only |
| Graph storage/index/traversal | **no** | yes | no |
| Causal semantics | **no** | no | no |
| Reference normalization | consume | consume | **yes** if new family needed |
| Execution primitive envelopes | persist/bind | consume | define |

**Challenge:** any remaining “reference family” gaps → **3.5 extension PR**, not sneaked into P04 merge logic.

---

## 15) Long-term failure modes

Identity corruption; irreversible merges; graph poisoning via topology; causal hallucination downstream; continuity fragmentation across bundles; replay nondeterminism in candidates; probabilistic contamination; connector-shaped graph because primitives skipped; semantic drift via ambiguous link types; economic collapse from regen cost.

---

## 16) Required runtime components (modules)

- `vector.domains.cortex.identity.org_entities`
- `vector.domains.cortex.identity.link_ledger`
- `vector.domains.cortex.identity.merge_governance`
- `vector.domains.cortex.identity.candidate_generation`
- `vector.domains.cortex.identity.authoritative_replay`
- `vector.domains.cortex.identity.bundle_equivalence`
- `vector.domains.cortex.identity.execution_primitives`
- `vector.domains.cortex.identity.projection_export`
- `vector.domains.cortex.identity.verification`
- `vector.domains.cortex.identity.failure_remediation`
- `vector.domains.cortex.identity.control_plane`
- `vector.domains.cortex.identity.replay_jobs` (+ receipts)
- `vector.api.http.routes.identity_*` (names indicative)

---

## 17) Required persistence models (tables — indicative)

- `cortex_org_entity` (handle registry)
- `cortex_org_persona_binding` (provider persona → handle, temporal)
- `cortex_org_link` (authoritative links)
- `cortex_org_link_candidate` (optional persisted candidates)
- `cortex_org_merge` (merge ledger)
- `cortex_bundle_equivalence_declaration`
- `cortex_link_rule_version`
- `cortex_org_primitive_instance`
- `cortex_org_link_replay_job` / `cortex_org_link_replay_receipt`
- `cortex_org_failure_case` / `cortex_org_remediation_validation` (mirror pattern)
- `cortex_org_verification_run` (optional)
- `cortex_org_certification_archive`

Indexes: tenant_id + temporal queries; handle id; link type + validity; evidence json GIN optional.

---

## 18) Future-phase compatibility guarantees (contractual)

- **P05** consumes only `OrgGraphProjectionV1` + append-only org tables **read** APIs; no write-back from graph engine.
- **P06** may only attach causal annotations referencing **org handle ids** or **link ids**, not raw guesses.
- **P07** retrieval must cite **link id / merge id / evidence raw ids**.
- **P08** synthesis forbidden unless **confidence + evidence** fields present.

---

## 19) Hard blockers before Phase 05

1. Org entity + link tables + migrations shipped.
2. Topology-vs-meaning enforced in schema/validators + **G-P04-08**.
3. Merge vs hint separation proven by tests (**G-P04-02**).
4. `OrgGraphProjectionV1` export stable (**G-P04-10**).
5. Two-layer replay working (**G-P04-04/05**).

---

## 20) Final GO / NO-GO for runtime implementation

| **GO** | Stages **P04-01–P04-13** doctrines written + reviewed; **schemas** for §17 agreed; gate list §12 frozen. |
| **NO-GO** | Any merge semantics still “TBD”; hint can promote; cross-bundle unspecified. |

---

## References

- `phase-04-architecture-identity-linking-doctrine.md`
- `phase-04-control-plane-doctrine.md` (operator console, routes §15, gates **G-P04-21–G-P04-26**)
- `phase-04-mock-data-strategy.md` (hostile continuity mock/fixtures)
- `phase-04-normative-index.md`
- `phase-03-identity-continuity-doctrine.md` (Phase 03 boundary)
- `phase-35-organizational-continuity-foundation.md` (Phase 3.5)
- `MASTER_TRACKER.md` (Phase 04 section references this program)
