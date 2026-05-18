# Phase 08 — Normative index (Synthesis & Intelligence Layer)

**Status:** **`Frozen (implementation)`** — **P08-FINAL-FREEZE-2026-05-17** (Steps **1–35** runtime shipped; **PHASE08_PROGRAM_FREEZE_VERSION `1`**).  
**Role:** constitutional entry for **Phase 08 Synthesis & Intelligence Layer (SIL)** — bounded, evidence-constrained execution intelligence over Phase **07** lawful retrieval envelopes — **not** chat, RAG, or unconstrained LLM cognition.  
**Normative tree:** `DOCS/cortex/synthesis/`.  
**Upstream:** Phase **07** retrieval closure ([`../retrieval/PHASE07_RUNTIME_CLOSURE.md`](../retrieval/PHASE07_RUNTIME_CLOSURE.md)); substrate pipeline phases **02–07** ([`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md)).  
**Downstream:** Phase **09** operational intelligence products; Phase **10** admin shell unifies navigation.

**Changelog:** [`PHASE08_CONSTITUTIONAL_CHANGELOG.md`](./PHASE08_CONSTITUTIONAL_CHANGELOG.md).  
**Implementation contract:** [`phase-08-implementation-sequencing-plan.md`](./phase-08-implementation-sequencing-plan.md).  
**Gap discipline:** [`synthesis-spec-gap-matrix.md`](./synthesis-spec-gap-matrix.md).  
**Future code package (reserved):** `vector.domains.cortex.synthesis`.

---

## Constitutional sentence

**Phase 08** is the **execution intelligence layer**: it transforms **lawful, replay-addressable retrieval evidence** into **bounded synthesis artifacts** (execution understanding, operational narratives, management intelligence surfaces) under explicit **synthesis legality**, **cite-or-omit law**, **replay identity**, and **AI authority limits**. Phase 08 MUST NOT fetch organizational memory directly, invent evidence, or present probabilistic model output as substrate truth.

---

## Program freeze (P08-01)

| Field | Value |
| ----- | ----- |
| **PHASE08_PROGRAM_FREEZE_VERSION** | `1` — MUST match future runtime constant `vector.domains.cortex.synthesis.normative.PHASE08_PROGRAM_FREEZE_VERSION`. |
| **Scope** | Steps **1–35**; **FF‑P08‑0..5** bundles; vocabulary; CI gate catalog (**G‑P08‑***). |
| **Hard upstream gate** | Phase **07** authoritative retrieval envelopes + published `index_epoch` + `retrieval_query_replay_identity`; Phase **06** TCRE receipts when synthesis workload requires causal context; substrate pipeline **phase_07_retrieval** completion receipt. |
| **Hard downstream contract** | Phase **09** MUST consume **`SynthesisIntelligenceArtifactV1`** + **`synthesis_job_receipt`** only through Phase **08** ingress — never raw retrieval rows. |

**REPLAY REQUIREMENT:** Any synthesis artifact labeled **authoritative** MUST reproduce under pinned **`synthesis_job_replay_identity`** + pinned retrieval query replay identity + synthesis policy pack digest per [`phase-08-replay-equivalence-spec.md`](./phase-08-replay-equivalence-spec.md).

---

## Freeze bundle registry (FF‑P08‑0..5)

| Bundle | Steps | Intent |
|--------|-------|--------|
| **FF‑P08‑0** | 1–3 | Index + anti-goals + phase boundaries |
| **FF‑P08‑1** | 1–9 | Job contracts + ingress + legality + replay identity |
| **FF‑P08‑2** | 1–14 | Orchestration substrate + LLM law + caps + artifact materialization |
| **FF‑P08‑3** | 1–21 | Bindings + replay proofs + degradation + completeness |
| **FF‑P08‑4** | 1–28 | Observability + admin control plane + evaluation harness |
| **FF‑P08‑5** | 1–35 | Pipeline integration + certification + closure |

---

## Step program ↔ primary doctrine (1:1)

| Step | Title | Primary normative file(s) |
| ---- | ----- | ------------------------- |
| 1 | Normative index + program freeze | **This file** |
| 2 | Anti-goals + forbidden cognition | [`phase-08-anti-goals-doctrine.md`](./phase-08-anti-goals-doctrine.md) |
| 3 | Phase boundaries (07 / 09 / 10) | [`phase-08-phase-boundaries-doctrine.md`](./phase-08-phase-boundaries-doctrine.md) |
| 4 | Retrieval ingress + evidence envelope law | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §Ingress |
| 5 | Synthesis workload classes + intent taxonomy | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §1–2 |
| 6 | Synthesis job envelope + execution FSM | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) §FSM |
| 7 | Synthesis legality classes + degradation semantics | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) §Legality |
| 8 | Synthesis replay identity + provenance envelope | [`phase-08-replay-equivalence-spec.md`](./phase-08-replay-equivalence-spec.md) |
| 9 | Evidence binding + cite-or-omit model | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §Citations |
| 10 | Deterministic orchestration substrate | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Orchestrator |
| 11 | LLM authority boundary + model routing law | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) §AI |
| 12 | Prompt assembly law (structured, pinned) | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) §Prompts |
| 13 | Bounded caps + omission law (**SD‑***) | [`phase-08-failure-degradation-taxonomy.md`](./phase-08-failure-degradation-taxonomy.md) |
| 14 | Intelligence artifact materialization contract | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §Artifacts |
| 15 | Retrieval / TCRE binding on synthesis inputs | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Bindings |
| 16 | Lineage + continuity propagation on artifacts | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Lineage |
| 17 | Synthesis replay equivalence proofs | [`phase-08-replay-equivalence-spec.md`](./phase-08-replay-equivalence-spec.md) §Twin |
| 18 | Degradation taxonomy + propagation | [`phase-08-failure-degradation-taxonomy.md`](./phase-08-failure-degradation-taxonomy.md) §Propagation |
| 19 | Substrate completeness integration | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Completeness |
| 20 | Artifact lineage on synthesis outputs | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Lineage |
| 21 | Observability + health model | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) §Observability |
| 22 | Synthesis control plane catalog | [`phase-08-admin-control-plane-spec.md`](./phase-08-admin-control-plane-spec.md) |
| 23 | Operator workflows + debuggers | [`phase-08-admin-control-plane-spec.md`](./phase-08-admin-control-plane-spec.md) §Workflows |
| 24 | Tenant verification slice + readiness economics | [`phase-08-evaluation-quality-governance.md`](./phase-08-evaluation-quality-governance.md) §Tenant |
| 25 | Runtime legality matrix | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) §Matrix |
| 26 | **G‑P08‑*** verification harness | [`phase-08-testing-strategy.md`](./phase-08-testing-strategy.md) |
| 27 | Golden vectors + policy fixture | [`fixtures/SynthesisPolicyPackV1_Default.json`](./fixtures/SynthesisPolicyPackV1_Default.json) |
| 28 | Evaluation harness + quality governance | [`phase-08-evaluation-quality-governance.md`](./phase-08-evaluation-quality-governance.md) |
| 29 | Implementation sequencing + runtime handoff | [`phase-08-implementation-sequencing-plan.md`](./phase-08-implementation-sequencing-plan.md) |
| 30 | Closure + admin program freeze (**G‑P08‑CLOSE‑01**) | [`phase-08-closure-gates-doctrine.md`](./phase-08-closure-gates-doctrine.md) |
| 31 | Substrate pipeline phase **08** integration | [`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md) |
| 32 | Publication barrier + synthesis epoch | [`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md) §Publish |
| 33 | Durable artifact store + receipts persistence | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md) §Persistence |
| 34 | E2E operational flow certification | [`phase-08-e2e-operational-flow.md`](./phase-08-e2e-operational-flow.md) |
| 35 | Constitutional changelog + doctrine freeze sign-off | [`PHASE08_CONSTITUTIONAL_CHANGELOG.md`](./PHASE08_CONSTITUTIONAL_CHANGELOG.md) |

---

## Vocabulary (closed)

| Term | Meaning |
| ---- | ------- |
| **SIL** | Synthesis & Intelligence Layer — Phase 08 runtime name (`vector.domains.cortex.synthesis`). |
| **Synthesis job** | A **declared, validated** `SynthesisJobEnvelopeV1` — not a chat session. |
| **Intelligence artifact** | Durable output row: structured claims + citations + legality + replay pins — not raw LLM text alone. |
| **Claim** | Atomic synthesized statement bound to ≥1 evidence citation or explicitly marked **omitted**. |
| **Citation** | Pointer to `RetrievalEvidenceHitV1` fields (lookup id, hit id, digest, omission class) — never free-form URL. |
| **Authoritative synthesis** | Artifact legality ∈ {`synthesis_replay_safe`, `synthesis_degraded`} with complete citation envelope. |
| **Exploration synthesis** | Partition-isolated jobs — MUST NOT feed Phase **09** production workflows without escalation. |
| **Deterministic shell** | Orchestration, caps, legality aggregation, replay identity, receipt hashing — **always** deterministic. |
| **Probabilistic core** | LLM token generation — **bounded**, **pinned**, **logged**, never authoritative for substrate facts. |

---

## Pipeline position (substrate overview)

```text
01 Ingest → 02 Raw → 03 Canonical → 04 Identity → 05 OCTS → 06 TCRE → 07 Retrieval → 08 Synthesis → 09 Products
```

Phase **08** executes **after** retrieval index publication for the same `substrate_pipeline_run_id` (or explicit manual synthesis trigger with pinned retrieval epoch). See [`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md).

---

## Document map (complete spec package)

| # | Deliverable | File |
| - | ----------- | ---- |
| 1 | Endgoal | [`phase-08-endgoal-doctrine.md`](./phase-08-endgoal-doctrine.md) |
| 2 | Architecture | [`phase-08-synthesis-runtime-architecture.md`](./phase-08-synthesis-runtime-architecture.md) |
| 3 | Runtime + E2E flow | [`phase-08-runtime-flow-e2e.md`](./phase-08-runtime-flow-e2e.md), [`phase-08-e2e-operational-flow.md`](./phase-08-e2e-operational-flow.md) |
| 4 | Data contracts | [`phase-08-data-contracts.md`](./phase-08-data-contracts.md), [`schemas/`](./schemas/) |
| 5 | Synthesis law | [`phase-08-synthesis-law-system.md`](./phase-08-synthesis-law-system.md) |
| 6 | Replay + equivalence | [`phase-08-replay-equivalence-spec.md`](./phase-08-replay-equivalence-spec.md) |
| 7 | Evaluation + quality | [`phase-08-evaluation-quality-governance.md`](./phase-08-evaluation-quality-governance.md) |
| 8 | Admin / control plane | [`phase-08-admin-control-plane-spec.md`](./phase-08-admin-control-plane-spec.md) |
| 9 | Pipeline orchestration | [`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md) |
| 10 | Implementation plan | [`phase-08-implementation-sequencing-plan.md`](./phase-08-implementation-sequencing-plan.md) |
| 11 | Certification / closure | [`phase-08-closure-gates-doctrine.md`](./phase-08-closure-gates-doctrine.md) |
| 12 | Failure / degradation | [`phase-08-failure-degradation-taxonomy.md`](./phase-08-failure-degradation-taxonomy.md) |
| 13 | Testing strategy | [`phase-08-testing-strategy.md`](./phase-08-testing-strategy.md) |
| 14 | E2E flow (operator) | [`phase-08-e2e-operational-flow.md`](./phase-08-e2e-operational-flow.md) |
| 15 | Ingestion pipeline integration | [`phase-08-pipeline-orchestration.md`](./phase-08-pipeline-orchestration.md) |

---

## surface_kind classification (all admin surfaces)

| surface_kind | Meaning |
| ------------ | ------- |
| **`runtime_backed`** | Reads durable synthesis jobs, artifacts, receipts, metrics — operator truth. |
| **`doctrine_catalog`** | Frozen policy packs, workload registries, gate catalogs — spec mirrors, not tenant truth. |
| **`derived_aggregate`** | Rollups computed from runtime tables (histograms, lag) — MUST cite source receipt ids. |
| **`verification_probe`** | Harness output (G-P08-*) — pass/fail with artifact pointers. |

Phase **08** admin MUST label every API response with `surface_kind` per [`phase-08-admin-control-plane-spec.md`](./phase-08-admin-control-plane-spec.md).
