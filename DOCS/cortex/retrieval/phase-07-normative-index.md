# Phase 07 — Normative index (lawful deterministic retrieval substrate)

**Status:** normative specification program — **PHASE07_PROGRAM_FREEZE_VERSION `0`** (pre-implementation architecture pass; target `1` at **FF‑P07‑5**).  
**Role:** constitutional entry for **Phase 07 Retrieval & Query Engine (LRE)** — lawful evidence access over replay-safe reconstruction, **not** synthesis, semantic search, or LLM cognition.  
**Normative tree:** `DOCS/cortex/retrieval/`.  
**Supersedes (intent only):** shallow `DOCS/cortex/08-retrieval/architecture.md` — that file remains a stub; **this tree** is authoritative for Phase 07.

**Changelog:** [`PHASE07_CONSTITUTIONAL_CHANGELOG.md`](./PHASE07_CONSTITUTIONAL_CHANGELOG.md).  
**Implementation contract (future):** [`phase-07-implementation-sequencing-plan.md`](./phase-07-implementation-sequencing-plan.md).  
**Gap discipline:** [`retrieval-spec-gap-matrix.md`](./retrieval-spec-gap-matrix.md).

---

## Constitutional sentence

**Phase 07** is the **lawful deterministic retrieval substrate**: operators and downstream phases MAY fetch **bounded, replay-addressable, provenance-complete evidence bundles** from organizational exhaust, canonical materializations, org graph continuity, OCTS traversal receipts, and TCRE reconstruction artifacts — under explicit **query legality classes**, **omission law**, and **anti-ranking** constraints. Phase 07 MUST NOT interpret, summarize, recommend, or rank by semantic relevance.

---

## Program freeze (P07-01)

| Field | Value |
| ----- | ----- |
| **PHASE07_PROGRAM_FREEZE_VERSION** | `0` (architecture); `1` at operator closure (**Step 30**). |
| **Scope** | Steps **1–30**; **FF‑P07‑0..5** bundles; vocabulary; CI gate catalog (**G‑P07‑***). |
| **Hard upstream gate** | Phase **06** TCRE doctrine **Frozen (doctrine)** Steps **1–30** + live **RUNTIME‑01/02** bounded slice; Phase **05** OCTS **Steps 19–23** minimum; Phase **04** authoritative graph export. |

**REPLAY REQUIREMENT:** Any retrieval response labeled **authoritative** MUST reproduce under pinned **`retrieval_query_replay_identity`** + upstream artifact digests per [`phase-07-replay-equivalence-retrieval-spec.md`](./phase-07-replay-equivalence-retrieval-spec.md).

---

## Freeze bundle registry (FF‑P07‑0..5)

| Bundle | Steps | Intent |
|--------|-------|--------|
| **FF‑P07‑0** | 1–3 | Index + anti-goals + phase boundaries |
| **FF‑P07‑1** | 1–9 | Query contracts + addressing + legality |
| **FF‑P07‑2** | 1–14 | Provenance + temporal + ranking + index law |
| **FF‑P07‑3** | 1–21 | Upstream bindings + replay + degradation + completeness |
| **FF‑P07‑4** | 1–26 | Observability + admin control plane + legality matrix |
| **FF‑P07‑5** | 1–30 | Verification harness + certification + closure |

---

## Step program ↔ primary doctrine (1:1)

| Step | Title | Primary normative file(s) |
| ---- | ----- | ------------------------- |
| 1 | Normative index + program freeze | **This file** |
| 2 | Anti-goals + forbidden cognition | [`phase-07-anti-goals-doctrine.md`](./phase-07-anti-goals-doctrine.md) |
| 3 | Phase boundaries (06 / 08 / 09) | [`phase-07-phase-boundaries-doctrine.md`](./phase-07-phase-boundaries-doctrine.md) |
| 4 | Upstream ingress + observed vs derived | [`phase-07-query-contract-doctrine.md`](./phase-07-query-contract-doctrine.md) §Ingress |
| 5 | Query workload classes + intent taxonomy | [`phase-07-query-contract-doctrine.md`](./phase-07-query-contract-doctrine.md) §1–2 |
| 6 | Lawful query envelope + execution contract | [`phase-07-query-contract-doctrine.md`](./phase-07-query-contract-doctrine.md) §3–4 |
| 7 | Query legality classes + degradation semantics | [`retrieval-legality-matrix.md`](./retrieval-legality-matrix.md); [`phase-07-query-contract-doctrine.md`](./phase-07-query-contract-doctrine.md) §5 |
| 8 | Query replay identity + provenance envelope | [`phase-07-replay-equivalence-retrieval-spec.md`](./phase-07-replay-equivalence-retrieval-spec.md); [`phase-07-retrieval-provenance-evidence-doctrine.md`](./phase-07-retrieval-provenance-evidence-doctrine.md) §Replay |
| 9 | Retrieval addressing model | [`phase-07-retrieval-addressing-model.md`](./phase-07-retrieval-addressing-model.md) |
| 10 | Evidence retrieval envelope | [`phase-07-retrieval-provenance-evidence-doctrine.md`](./phase-07-retrieval-provenance-evidence-doctrine.md) |
| 11 | Temporal retrieval model | [`phase-07-temporal-retrieval-doctrine.md`](./phase-07-temporal-retrieval-doctrine.md) |
| 12 | Deterministic ranking + selection | [`phase-07-retrieval-ranking-selection-doctrine.md`](./phase-07-retrieval-ranking-selection-doctrine.md) |
| 13 | Bounded caps + omission law | [`phase-07-query-contract-doctrine.md`](./phase-07-query-contract-doctrine.md) §6; [`phase-07-retrieval-degradation-taxonomy.md`](./phase-07-retrieval-degradation-taxonomy.md) |
| 14 | Retrieval index materialization contract | [`phase-07-retrieval-runtime-architecture.md`](./phase-07-retrieval-runtime-architecture.md) §Index |
| 15 | TCRE / chronology / edge bindings | [`phase-07-retrieval-runtime-architecture.md`](./phase-07-retrieval-runtime-architecture.md) §TCRE |
| 16 | OCTS walk + traversal lineage bindings | [`phase-07-retrieval-runtime-architecture.md`](./phase-07-retrieval-runtime-architecture.md) §OCTS |
| 17 | Graph / identity / canonical bindings | [`phase-07-retrieval-runtime-architecture.md`](./phase-07-retrieval-runtime-architecture.md) §Graph |
| 18 | Retrieval replay equivalence proofs | [`phase-07-replay-equivalence-retrieval-spec.md`](./phase-07-replay-equivalence-retrieval-spec.md) |
| 19 | Degradation taxonomy + propagation | [`phase-07-retrieval-degradation-taxonomy.md`](./phase-07-retrieval-degradation-taxonomy.md) |
| 20 | Substrate completeness integration | [`phase-07-retrieval-completeness-doctrine.md`](./phase-07-retrieval-completeness-doctrine.md); [`phase-07-substrate-overview-integration.md`](./phase-07-substrate-overview-integration.md) |
| 21 | Artifact lineage retrieval substrate | [`phase-07-retrieval-runtime-architecture.md`](./phase-07-retrieval-runtime-architecture.md) §Lineage |
| 22 | Observability + health model | [`phase-07-retrieval-observability-doctrine.md`](./phase-07-retrieval-observability-doctrine.md) |
| 23 | Retrieval control plane catalog | [`phase-07-retrieval-admin-control-plane-spec.md`](./phase-07-retrieval-admin-control-plane-spec.md) |
| 24 | Operator workflows + debuggers | [`phase-07-retrieval-admin-control-plane-spec.md`](./phase-07-retrieval-admin-control-plane-spec.md) §Workflows |
| 25 | Tenant verification slice + readiness economics | [`phase-07-verification-harness-spec.md`](./phase-07-verification-harness-spec.md) §Tenant slice |
| 26 | Runtime legality matrix | [`phase-07-retrieval-runtime-legality-matrix.md`](./phase-07-retrieval-runtime-legality-matrix.md) |
| 27 | **G‑P07‑*** verification harness | [`phase-07-verification-harness-spec.md`](./phase-07-verification-harness-spec.md) |
| 28 | Golden vectors + certification pack law | [`phase-07-closure-gates-doctrine.md`](./phase-07-closure-gates-doctrine.md) |
| 29 | Implementation sequencing + runtime handoff | [`phase-07-implementation-sequencing-plan.md`](./phase-07-implementation-sequencing-plan.md) |
| 30 | Closure + admin program freeze (**G‑P07‑CLOSE‑01**) | [`phase-07-closure-gates-doctrine.md`](./phase-07-closure-gates-doctrine.md) |

---

## Vocabulary (closed)

| Term | Meaning |
| ---- | ------- |
| **LRE** | Lawful Retrieval Engine — Phase 07 runtime name (package TBD: `vector.domains.cortex.retrieval`). |
| **Query** | A **declared, validated** `RetrievalQueryEnvelopeV1` — not free-text search. |
| **Hit** | One addressed evidence row returned inside a bounded result set — always carries provenance. |
| **Omission** | Lawful non-return with **`retrieval_omission_class`** — never silent drop. |
| **Authoritative retrieval** | Response legality ∈ {`retrieval_replay_safe`, `retrieval_degraded`} with complete provenance envelope. |
| **Exploration retrieval** | Partition-isolated queries (mirror OCTS exploration_mode) — MUST NOT feed Phase 08 authoritative synthesis. |

---

## Pipeline position (substrate overview)

```text
Raw → Canonical → Identity → Graph → Traversal → TCRE → Retrieval → (Phase 08 Synthesis)
```

Retrieval completeness is **downstream of** TCRE reconstruction coverage and OCTS walk durability but **MUST NOT** collapse TCRE gaps into silent retrieval success.
