# Phase 04 — Architecture & Doctrine: Identity & Linking

**Status:** normative target for Phase 04 runtime and specifications.  
**Audience:** architects, implementers, verification authors.  
**Non-goal:** This document does not specify UI polish or connector breadth expansion.

**Upstream:** Phase 01 raw memory, Phase 02 trust/replay semantics, Phase 03 canonicalization + identity anchors (provider-scoped), Phase 3.5 continuity foundation (normalized references, edge envelopes, execution primitive envelopes, bundle semantics).

**Related (same folder):** `phase-04-implementation-plan.md` (22-stage program, gates, persistence/runtime tables), `phase-04-normative-index.md` (doctrine registry + vocabulary), `phase-04-control-plane-doctrine.md` (Execution Continuity Operator Console — admin surfaces, routes, operator gates **G-P04-21–G-P04-26**), `phase-04-mock-data-strategy.md` (hostile deterministic mock data for continuity stress in dev/CI).

---

## Executive verdict (normative summary)

**GO** to enter Phase 04 **runtime implementation only after** the doctrine set listed in §14 ships and **closure gates** for identity corruption are drafted (see §13). **NO-GO** if implementation begins while: (a) human vs provider identity boundaries remain ambiguous, (b) merge vs link vs hint semantics are conflated, (c) cross-bundle equivalence is implicit, or (d) inferred/probabilistic equality is allowed without an explicit later-phase charter.

Phase 04 is **structurally necessary** between canonical materialization and organizational graph: skipping it forces Phase 05 to smuggle identity decisions into graph edges—**semantic corruption** and **non-replayable authority**.

---

## 1) Phase 04 end goal

### 1.1 What Phase 04 achieves

Phase 04 establishes **organizational continuity of actors and work subjects** as **first-class, evidence-bound, replay-regenerable linkage** over the existing substrate:

- **Stable organizational handles** for entities that exist across tools and time (humans, teams, org units, initiatives, repositories-as-org-assets, key execution artifacts).
- **Typed links** between those handles and between handles and **bundle-scoped canonical pointers** / **normalized references** / **raw record ids**, with explicit **confidence**, **temporal validity**, **provenance**, and **supersession/revocation** semantics.
- **Explicit non-merge** defaults: the system may **acknowledge** candidate co-reference; it may not **collapse** identity without governed merge records.

### 1.2 What becomes possible after Phase 04

- Phase **05** can project a **faithful organizational graph** (nodes = org handles + canonical pointers; edges = Phase 04 link ledger) without inferring “sameness.”
- Phase **06** can attach **temporal and causal** reasoning to **stable endpoints** (org handles) rather than to volatile provider ids.
- Phase **07** can retrieve **cross-tool** evidence chains keyed by org handles + normalized references.
- Phase **08** can ground synthesis in **link confidence + provenance**, not in hidden merges.

### 1.3 What MUST remain impossible in Phase 04

- **Semantic causality** (“A caused B”) as authoritative graph facts.
- **Probabilistic identity equality** as authoritative (ML “same person” merge).
- **Silent collapse** of two provider personas into one org handle.
- **Retroactive rewrite** of raw or canonical truth.
- **Bundle-agnostic canonical logical key mutation** (Phase 03 boundary preserved).

### 1.4 Success criteria (closure-oriented)

1. **Replay regeneration:** given the same raw corpus + same linkage rule versions + same merge ledger inputs, the **org handle set** and **authoritative link set** are identical (within declared tolerance for explicit stochastic policies—default: **zero** stochastic policies).
2. **Corruption resistance:** every authoritative merge or equivalence has a **durable audit record** citing evidence ids and operator/policy context where applicable.
3. **Cross-tool joins:** normalized references from Phase 3.5 are consumed as **inputs** to links, not as automatic identities.
4. **Separation of concerns:** replay/materialization topology (Phase 03) is never mistaken for organizational meaning edges (Phase 04+).

### 1.5 Anti-goals

- Dashboards-as-success, “green” verification without linkage invariants, connector exhaust expansion as Phase 04 work, embeddings-first identity.

### 1.6 Existential requirements

- A **link ledger** data model (append-only or event-sourced) distinct from `cortex_canonical_transform_materialization`.
- A **merge contract** distinct from “hint edge.”
- **Versioned linkage rules** (deterministic transforms analogue) with replay job semantics for regeneration.

---

## 2) Architectural role of Phase 04

### 2.1 Position in the stack

```
Raw (P1–2) → Canonical projection (P3, bundle-scoped) → ORG HANDLES + LINKS (P4) → Graph projection (P5) → Temporal/causal (P6) → Retrieval (P7) → Synthesis (P8)
```

- **Phase 03** answers: “What structural object is this raw row under this bundle pin?”
- **Phase 04** answers: “**Which organizational actor or subject** does that object participate in, **linked how**, **with what evidence**, **valid when**, **superseded when**?”
- **Phase 05** answers: “What is the optimized **traversable** representation for operator and machine paths?”

### 2.2 What breaks if Phase 04 is skipped

Graph becomes the **identity oracle** by default: edges imply sameness, ML fills gaps, replay cannot explain why two nodes merged, causal reasoning attaches to **wrong endpoints**, synthesis hallucinates continuity.

### 2.3 Challenge: is Phase 03 canonical model sufficient?

**No** for organizational cognition; **yes** for its charter. Canonical kinds remain **provider-shaped artifacts**. Phase 04 must introduce **org-shaped handles** that are **not** `CanonicalObjectKind` renames—either new persisted `OrgEntityKind` or a parallel registry. Risk if skipped: Phase 05 encodes org semantics in graph node labels.

### 2.4 Challenge: are Phase 3.5 continuity contracts sufficient?

**Necessary, not sufficient.**

- `NormalizedReference` gives **join keys**; it does not assert **co-reference**.
- `ContinuityEdgeContract` is an **envelope**; Phase 04 must add **ledger semantics**: validity interval, revocation, rule version, merge lineage.
- `ExecutionPrimitiveEnvelope` is **sparse**; Phase 04 must decide which primitives get **persisted org nodes** vs remain derived views.

---

## 3) Identity theory (doctrine)

### 3.1 What “identity” means in Cortex

Three **non-interchangeable** layers:

| Layer | Meaning | Authority |
| ----- | ------- | --------- |
| **Provider identity** | Provider-stable id tuple | Provider + raw |
| **Canonical identity** | `canonical_entity_id` / logical keys under bundle | Phase 03 rules |
| **Organizational identity** | Org handle representing continuity across tools/time | Phase 04 governance |

**Hard rule:** `canonical_entity_id` equality **does not** imply organizational equality.

### 3.2 Kinds of identities (org handle taxonomy — illustrative minimum)

- **HumanActor** — never merged by email alone.
- **ServiceIdentity** — bots, integrations; never merged with HumanActor by default.
- **TeamOrGroup** — Slack team, GitHub org team, Linear team; merge only with explicit org policy record.
- **RepositoryAsset** — distinct from `git.repo` reference string: may map 1↔1 but org handle carries **org ownership** semantics.
- **ProjectOrInitiative** — cross-tool initiative windows.
- **OrgUnit** — employer / division boundary (often absent early—**unknown** is valid).

### 3.3 What MUST NOT be merged

- HumanActor ⟷ HumanActor by **email/username similarity** without deterministic provider merge event + governance.
- HumanActor ⟷ ServiceIdentity.
- Cross-bundle canonical rows **without** explicit migration equivalence record.

### 3.4 Deterministic vs probabilistic boundaries

| Operation | Allowed in P04? |
| --------- | --------------- |
| Deterministic link from provider merge event payload | Yes (evidence-grade E0/E1 per rule) |
| Deterministic link from normalized ref equality | Only as **candidate** unless rule explicitly promotes |
| Probabilistic merge | **No** as authoritative |
| Probabilistic hint | **Yes** only if stored as **non-authoritative** with explicit `hint` class and **zero** downstream merge force unless promoted by policy job |

### 3.5 Replay-safe identity evolution

- Org handles are **stable ids** (UUIDv5 or monotonic id + namespace rules).
- **Supersession:** merge/split emits new records; old relationships remain queryable under tombstone rules.
- **Regeneration:** linkage rules are versioned; replay recomputes **candidate** sets; **authoritative** merges replay from merge ledger, not from heuristics.

### 3.6 Bundle-aware continuity

- Default: links attach **canonical pointers** as `(tenant_id, bundle_id, kind, logical_key_hash)` **or** raw ids + normalized refs.
- **Cross-bundle:** requires `BundleEquivalenceDeclaration` (name illustrative) — explicit, audited, versioned.

### 3.7 Doctrine: humans vs bots vs teams

- **Humans:** multiple provider personas remain distinct handles until merge ledger says otherwise; **ambiguity** surfaces as **multiplicity**, not silent pick.
- **Bots:** separate namespace; never auto-linked to humans.
- **Teams/repos/projects:** may link to org units with policy; must not silently absorb humans.

---

## 4) Linking theory (doctrine)

### 4.1 What a link is

A **LinkRecord** is an auditable assertion: `(source_ref, target_ref, link_kind, validity, confidence, evidence[], rule_id, created_at, superseded_by?)`.

Refs may be: `OrgHandleRef`, `CanonicalPointer`, `NormalizedReference`, `RawRecordRef`.

### 4.2 Link kinds (minimum taxonomy)

- **Structural evidence links** (deterministic): raw field says parent/child.
- **Provider merge links** (deterministic): provider declares account merge.
- **Reference equality links** (deterministic with guardrails): same normalized ref family—**still** not “same human” unless family is human-safe.
- **Hints** (non-authoritative): similarity, co-occurrence—**must not** affect merge closure.
- **Prohibited:** inferred causal “blocked” from message tone; inferred “same person” from embeddings default.

### 4.3 Confidence & provenance

Reuse Phase 03 grades where possible; add **link-specific** metadata: `evidence_raw_ids`, `evidence_rule_version`, `operator_id` (if any).

### 4.4 Temporal validity

Every authoritative link has `[valid_from, valid_to)` or open-ended with explicit revocation event.

### 4.5 Replay semantics

Two-layer replay:

1. **Candidate regeneration** from rules + raw (may create candidates).
2. **Authoritative replay** from merge ledger + supersession (must reproduce).

### 4.6 Challenge: are Phase 3.5 edge contracts sufficient?

**No.** They lack: validity interval, revocation, authoritative vs candidate, rule versioning, merge lineage, operator policy binding. Phase 04 should **extend** (not replace) those contracts into a **persistence-grade LinkRecord**.

---

## 5) Cross-tool continuity (org semantics, not connector joins)

### 5.1 Contracts required

- **ActorContinuityRecord:** org handle + provider persona bindings + validity.
- **WorkContinuityRecord:** binds primitives (`WorkEpisode`, etc.) to org handles and canonical pointers.
- **OwnershipContinuityRecord:** role/holder changes over time (no HR semantics required early).
- **EscalationContinuityRecord:** thread-level escalation chains with evidence.

### 5.2 Challenge: substrate enough?

**Enough to start** if Phase 3.5 reference plane is populated at materialization boundaries; **not enough** for quality if ingest still misses actors and timestamps—Phase 04 will **surface pain** as unresolved multiplicity (which is correct behavior).

---

## 6) Organizational execution primitives

### 6.1 Are they required before graph?

**Minimum required:** `WorkEpisode` (or equivalent) as **evidence-bounded span** and `OwnershipWindow` for accountability continuity. Others (ReviewCycle, BlockageEpisode, …) can be phased but **without** a work span, graph becomes a bag of provider objects.

### 6.2 Challenge: connector ontology enough?

**No** for end vision; **yes** for Phase 03. Phase 04 must add **parallel org-shaped registry** without flattening canonical kinds prematurely.

---

## 7) Graph-ready edge model (pre-Phase 05)

### 7.1 Edges that MUST exist before Phase 05 (minimum)

- `PersonaBelongsToOrgHandle` (provider persona → org handle) — evidence-backed.
- `CanonicalPointerParticipatesInOrgHandle` (artifact → org handle role).
- `OrgHandleLinkedToNormalizedReference` (join key alignment).
- `WorkEpisodeComposedOfCanonicalPointers` / raw ids.

### 7.2 Separation: topology vs meaning

| Edge class | Source layer | Must never |
| ---------- | -------------- | ---------- |
| Materialization topology | Phase 03 replay DAG | Imply org ownership |
| Organizational meaning | Phase 04 link ledger | Drive materialization order |

---

## 8) Phase 04 failure modes (aggressive)

1. **Identity fragmentation:** multiple org handles for same human because merge policy is too strict vs too loose—**worse than** unresolved multiplicity.
2. **Fake causality later:** if Phase 04 links are interpreted as causal without event typing—Phase 06 invents causality.
3. **Graph corruption:** Phase 05 imports topology edges as org edges—semantic collapse.
4. **Bundle fork universes:** cross-bundle pins without equivalence declarations—irreconcilable graphs.
5. **Probabilistic corruption:** “embedding neighbor” promoted to merge—**non-replayable authority**.
6. **Operational greenwash:** verification passes while merge invariants absent.

---

## 9) Implementation plan (runtime sequencing — post-doctrine)

### Step A — Doctrine freeze set (see §14)

### Step B — Data model: `org_entity`, `link_record`, `merge_record`, `link_rule_version`, optional `primitive_instance`

### Step C — Deterministic rule engine: candidate generation from raw + 3.5 refs + canonical pointers

### Step D — Ledger writes: authoritative merges only via governed paths

### Step E — Replay jobs: regenerate candidates + reconcile ledger

### Step F — Verification gates: no silent merge, bundle coherence, replay parity

### Step G — Admin/control plane minimum: ambiguity-style surfaces for “unresolved multiplicity” + safe actions

### Step H — Tests: property tests for replay parity, negative tests forbidding email-merge

---

## 10) Hard blockers before Phase 05

- [ ] Org handle registry schema + API contract frozen.
- [ ] LinkRecord persistence + temporal validity + supersession semantics frozen.
- [ ] Explicit **topology ≠ meaning** enforcement in docs + verification.
- [ ] Cross-bundle equivalence doctrine + migration record type.
- [ ] Candidate vs authoritative link classes frozen.

---

## 11) Long-term risks if ignored

Semantic drift, irreversible merges, non-replayable “AI said so,” graph queries that return socially wrong ownership, causal engines that optimize narratives.

---

## 12) Boundary challenges (explicit)

- **Some work belongs in Phase 3.5 still** if reference families are missing—feed forward, not back.
- **Some work belongs in Phase 05** if it is purely index/traversal optimization—do not bloat Phase 04.
- **Risk:** Phase 04 becomes “graph lite”—reject by keeping **no native traversal engine** in P04.

---

## 13) Verification gates (draft names)

- **G-P04-01** No authoritative human merge without merge ledger record + evidence.
- **G-P04-02** Replay regeneration parity for link candidates given frozen rules.
- **G-P04-03** Cross-bundle canonical pointers forbidden on single authoritative edge without equivalence declaration.
- **G-P04-04** Hints cannot change merge closure.
- **G-P04-05** ServiceIdentity cannot merge into HumanActor by default.

---

## 14) Required companion doctrine files (new)

1. `phase-04-org-entity-and-handle-doctrine.md`
2. `phase-04-link-ledger-and-merge-contract-doctrine.md`
3. `phase-04-temporal-validity-and-revocation-doctrine.md`
4. `phase-04-replay-and-regeneration-doctrine.md`
5. `phase-04-cross-bundle-equivalence-doctrine.md`
6. `phase-04-execution-primitive-persistence-doctrine.md` (binds 3.5 envelopes to org handles)
7. `phase-04-verification-gates-doctrine.md`
8. `phase-04-admin-operator-surface-minimum.md` (policy-gated actions only)

---

## 15) Required runtime modules (names indicative)

- `vector.domains.cortex.identity.org_entities`
- `vector.domains.cortex.identity.link_ledger`
- `vector.domains.cortex.identity.merge_policy`
- `vector.domains.cortex.identity.candidate_generation`
- `vector.domains.cortex.identity.replay_regeneration`
- `vector.domains.cortex.identity.verification` (Phase 04 gates)

DB: new tables for org handles, links, merges, rule versions; **no** change to raw append-only invariants.

---

## Final GO / NO-GO (runtime)

| State | Condition |
| ----- | --------- |
| **GO** | §14 doctrine set drafted + §10 blockers have signed schemas + §13 gates have acceptance tests specified |
| **NO-GO** | Implementation starts before merge vs hint vs topology separation is normative |
