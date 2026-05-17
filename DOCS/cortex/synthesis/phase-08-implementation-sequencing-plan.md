# Phase 08 — Implementation sequencing plan (Steps 01–35)

**Status:** normative handoff.  
**Runtime package:** `vector.domains.cortex.synthesis` (to be created).  
**Prerequisite:** Phase **07** runtime closure ([`../retrieval/PHASE07_RUNTIME_CLOSURE.md`](../retrieval/PHASE07_RUNTIME_CLOSURE.md)).

---

## Sequencing waves

| Wave | Steps | Outcome |
| ---- | ----- | ------- |
| **0** | 01–03 | Doctrine frozen in repo |
| **1** | 04–09 | Contracts + ingress + replay identity (no DB) |
| **2** | 10–14 | FSM core without LLM (deterministic shell) |
| **3** | 15–18 | Bindings + replay proofs + degradation |
| **4** | 19–23 | Completeness + observability + admin catalog |
| **5** | 24–28 | Verification + golden vectors + eval |
| **6** | 29–30 | Sequencing meta + program closure |
| **7** | 31–35 | Pipeline integration + E2E + persistence |

---

## Critical path

```text
anti_goals → job_contract → ingress → retrieval_plan → orchestrator_shell
  → llm_adapter → artifact_store → replay_gate → pipeline_phase_08 → admin → close
```

---

## Step 01 — Normative index + program freeze

| Field | Content |
| ----- | ------- |
| **Objective** | Ship constitutional index, freeze version, FF bundles |
| **Architectural purpose** | Single entry point for all implementers |
| **Contracts** | `PHASE08_PROGRAM_FREEZE_VERSION=1` |
| **Runtime** | `normative.py`, `build_phase08_normative_program_document_v1()` |
| **Persistence** | None |
| **Celery** | None |
| **Admin** | `GET /admin/catalog/cortex/synthesis/program` (`doctrine_catalog`) |
| **Replay** | Defines replay laws by reference |
| **Degradation** | SD registry pointer |
| **Testing** | `test_phase08_step01_normative_freeze.py` |
| **Certification** | Criterion 1 |
| **Dependencies** | Phase **07** docs complete |
| **Risks** | Doc/code version skew |
| **Deliverables** | Index + changelog + tracker rows |

## Step 02 — Anti-goals + forbidden cognition

| Field | Content |
| ----- | ------- |
| **Objective** | Static enforcement of forbidden keys and imports |
| **Architectural purpose** | Prevent chat/RAG drift at compile time |
| **Contracts** | `SYNTHESIS_FORBIDDEN_*` constants |
| **Runtime** | `anti_goals.py`, `enforce_synthesis_job_envelope_anti_goals_v1` |
| **Persistence** | None |
| **Celery** | None |
| **Admin** | Catalog forbidden keys (`doctrine_catalog`) |
| **Replay** | N/A |
| **Degradation** | N/A |
| **Testing** | G-P08-ANTI-01, G-P08-ANTI-02 |
| **Certification** | Criterion 3 partial |
| **Dependencies** | Step 01 |
| **Risks** | Incomplete denylist |
| **Deliverables** | `anti_goals.py` + tests |

## Step 03 — Phase boundaries (07 / 09 / 10)

| Field | Content |
| ----- | ------- |
| **Objective** | Runtime boundary validators |
| **Architectural purpose** | Acyclic enforcement SYN-BND-* |
| **Contracts** | `phase_boundaries.py` |
| **Runtime** | `validate_synthesis_ingress_from_retrieval_v1` |
| **Persistence** | None |
| **Celery** | None |
| **Admin** | Boundary catalog endpoint |
| **Replay** | Reject exploration retrieval for authoritative jobs |
| **Degradation** | Map RD→SD at boundary |
| **Testing** | `test_phase08_step03_phase_boundaries.py` |
| **Certification** | Cross-phase review |
| **Dependencies** | Step 02 |
| **Risks** | Bypass via raw ORM |
| **Deliverables** | `phase_boundaries.py` |

## Step 04 — Retrieval ingress law

| Field | Content |
| ----- | ------- |
| **Objective** | Validate Phase **07** responses before synthesis |
| **Architectural purpose** | SYN-INGRESS-* gates |
| **Contracts** | `RetrievalEvidenceIngressV1` digest |
| **Runtime** | `synthesis_ingress.py` |
| **Persistence** | `retrieval_ingress_digest` column on jobs (future) |
| **Celery** | N/A |
| **Admin** | Ingress inspector on job detail |
| **Replay** | Require `retrieval_query_replay_identity` |
| **Degradation** | `SD-UPSTREAM-LEG` |
| **Testing** | G-P08-INGRESS-01 |
| **Dependencies** | Step 03, Phase **07** client |
| **Risks** | Algebra drift vs Phase **07** |
| **Deliverables** | Ingress module + tests |

## Step 05 — Workload + intent taxonomy

| Field | Content |
| ----- | ------- |
| **Objective** | Closed enums + validation |
| **Architectural purpose** | Replace free-text “use cases” |
| **Contracts** | `synthesis_job_contract.py` |
| **Runtime** | `validate_synthesis_workload_class_v1` |
| **Persistence** | N/A |
| **Admin** | Workload catalog (`doctrine_catalog`) |
| **Replay** | Workload in replay identity |
| **Degradation** | N/A |
| **Testing** | Schema enum tests |
| **Dependencies** | Step 04 |
| **Deliverables** | Contract module |

## Step 06 — Job envelope + FSM skeleton

| Field | Content |
| ----- | ------- |
| **Objective** | `SynthesisJobEnvelopeV1` + empty FSM phases |
| **Architectural purpose** | SYN-FSM-* scaffolding |
| **Contracts** | JSON schema job envelope |
| **Runtime** | `synthesis_orchestrator.py` stub `execute_synthesis_job_envelope_v1` |
| **Persistence** | Migration `cortex_synthesis_jobs` |
| **Celery** | Stub task |
| **Admin** | POST job/run returns trace |
| **Replay** | Trace only |
| **Degradation** | N/A |
| **Testing** | G-P08-SCHEMA-01 job |
| **Dependencies** | Step 05 |
| **Deliverables** | Schema + migration + stub FSM |

## Step 07 — Synthesis legality matrix

| Field | Content |
| ----- | ------- |
| **Objective** | S-LEG aggregation + fail-closed |
| **Architectural purpose** | Operator-trustworthy legality |
| **Contracts** | `synthesis_legality_class` enum |
| **Runtime** | `synthesis_legality_matrix.py` |
| **Persistence** | On artifact body |
| **Admin** | Legality explorer (derived) |
| **Replay** | Twin affects S-LEG-02 |
| **Degradation** | SD codes → floor |
| **Testing** | G-P08-LEG-01 |
| **Dependencies** | Step 06 |
| **Deliverables** | Legality module |

## Step 08 — Replay identity + receipt law

| Field | Content |
| ----- | ------- |
| **Objective** | `synthesis_job_replay_identity` computation |
| **Architectural purpose** | SYN-REP-01 |
| **Contracts** | Receipt shape |
| **Runtime** | `synthesis_replay_equivalence.py` |
| **Persistence** | `cortex_synthesis_job_receipts` |
| **Admin** | Replay explorer stub |
| **Replay** | G-P08-REPLAY-01 prep |
| **Degradation** | SD-REPLAY-* |
| **Testing** | Identity unit tests |
| **Dependencies** | Step 07 |
| **Deliverables** | Replay module |

## Step 09 — Cite-or-omit + citation binding

| Field | Content |
| ----- | ------- |
| **Objective** | `SynthesisCitationV1` + claim validation |
| **Architectural purpose** | Evidence-constrained intelligence |
| **Contracts** | Citation schema |
| **Runtime** | `synthesis_evidence_binding.py` |
| **Persistence** | Embedded in artifact JSON |
| **Admin** | Citation explorer |
| **Replay** | Citations in structural digest |
| **Degradation** | SD-CITE-GAP |
| **Testing** | G-P08-CITE-01 |
| **Dependencies** | Step 08 |
| **Deliverables** | Binding module |

## Step 10 — Deterministic orchestration (PLAN + RETRIEVE)

| Field | Content |
| ----- | ------- |
| **Objective** | Retrieval fan-out without LLM |
| **Architectural purpose** | Prove Phase **07** integration |
| **Contracts** | `build_synthesis_retrieval_plan_v1` |
| **Runtime** | FSM phases PLAN, RETRIEVE |
| **Persistence** | Store sub-query receipts on job |
| **Celery** | Job worker executes through RETRIEVE |
| **Admin** | Job debugger shows sub-queries |
| **Replay** | Sub-query identities in replay hash |
| **Degradation** | SD-CAP-RETRIEVAL |
| **Testing** | Integration with `execute_retrieval_query_envelope_v1` |
| **Dependencies** | Step 09, Phase **07** |
| **Risks** | Retrieval fail-closed in pipeline |
| **Deliverables** | Working RETRIEVE path |

## Step 11 — LLM authority + adapter isolation

| Field | Content |
| ----- | ------- |
| **Objective** | `adapters/llm` with FakeLlmAdapter |
| **Architectural purpose** | SYN-AI-* enforcement |
| **Contracts** | `model_route` registry in policy pack |
| **Runtime** | `llm_router.py` |
| **Persistence** | `llm_trace_refs` on artifact |
| **Admin** | Model route catalog |
| **Replay** | Model pins in replay identity |
| **Degradation** | SD-LLM-* |
| **Testing** | Adapter unit tests |
| **Dependencies** | Step 10 |
| **Deliverables** | LLM adapter package |

## Step 12 — Prompt assembly law

| Field | Content |
| ----- | ------- |
| **Objective** | Template registry + prompt_hash |
| **Architectural purpose** | SYN-PRM-* |
| **Contracts** | `prompt_template_id` + version |
| **Runtime** | `prompt_assembly.py` |
| **Persistence** | Hashes on receipt |
| **Admin** | Template catalog (doctrine) |
| **Replay** | prompt_hashes in identity |
| **Degradation** | N/A |
| **Testing** | Hash stability tests |
| **Dependencies** | Step 11 |
| **Deliverables** | Prompt module + 1 template |

## Step 13 — Bounded caps + SD registry

| Field | Content |
| ----- | ------- |
| **Objective** | SD-* registry like RD-* |
| **Architectural purpose** | Omission law |
| **Contracts** | `SynthesisPolicyPackV1` caps |
| **Runtime** | `synthesis_bounded_caps.py` |
| **Persistence** | Omission rows on artifact |
| **Admin** | SD explorer |
| **Replay** | SD multiset in twin |
| **Degradation** | Full taxonomy |
| **Testing** | Registry completeness test |
| **Dependencies** | Step 12 |
| **Deliverables** | Caps module + fixture |

## Step 14 — Artifact materialization

| Field | Content |
| ----- | ------- |
| **Objective** | Persist `SynthesisIntelligenceArtifactV1` |
| **Architectural purpose** | Durable intelligence output |
| **Contracts** | Artifact JSON schema |
| **Runtime** | `synthesis_artifact_materialization.py` + FSM LLM, CLASSIFY |
| **Persistence** | `cortex_synthesis_artifacts` |
| **Celery** | Full job completion |
| **Admin** | Artifact explorer |
| **Replay** | artifact_digest |
| **Degradation** | Rollup on artifact |
| **Testing** | G-P08-SCHEMA-01 artifact |
| **Dependencies** | Steps 11–13 |
| **Deliverables** | End-to-end job (no publish) |

## Step 15 — Retrieval/TCRE binding copy

| Field | Content |
| ----- | ------- |
| **Objective** | Copy binding envelopes to artifact header |
| **Architectural purpose** | Explainability without re-derive |
| **Contracts** | Binding fields on artifact |
| **Runtime** | `synthesis_bindings.py` |
| **Persistence** | In body_json |
| **Admin** | Binding panels on artifact page |
| **Replay** | Bindings in structural digest |
| **Degradation** | SD-UPSTREAM-RD |
| **Testing** | Binding copy tests |
| **Dependencies** | Step 14 |
| **Deliverables** | Bindings module |

## Step 16 — Lineage on artifacts

| Field | Content |
| ----- | ------- |
| **Objective** | `lineage_chain_digest` + persist edges |
| **Architectural purpose** | Traceability to retrieval |
| **Contracts** | Reuse Phase **07** lineage helpers |
| **Runtime** | `synthesis_lineage.py` |
| **Persistence** | Lineage edges table or reuse graph |
| **Admin** | Lineage panel on artifact |
| **Replay** | Digest in replay identity optional |
| **Degradation** | SD-LINEAGE-GAP if truncated |
| **Testing** | Lineage integration test |
| **Dependencies** | Step 15 |
| **Deliverables** | Lineage wiring |

## Step 17 — Replay equivalence proofs

| Field | Content |
| ----- | ------- |
| **Objective** | Structural twin for `prove` intent |
| **Architectural purpose** | G-P08-REPLAY-01 |
| **Contracts** | Twin diff object |
| **Runtime** | Extend `synthesis_replay_equivalence.py` |
| **Persistence** | Twin results on receipt |
| **Admin** | Replay explorer full |
| **Replay** | Core step |
| **Degradation** | SD-REPLAY-TWIN |
| **Testing** | `test_phase08_step17_replay_equivalence.py` |
| **Dependencies** | Step 16 |
| **Deliverables** | Twin harness |

## Step 18 — Degradation taxonomy propagation

| Field | Content |
| ----- | ------- |
| **Objective** | `apply_synthesis_degradation_taxonomy_v1` |
| **Architectural purpose** | No silent gaps |
| **Contracts** | RD→SD map |
| **Runtime** | `synthesis_degradation.py` |
| **Persistence** | Rollup fields |
| **Admin** | Degradation topology view |
| **Replay** | SD multiset in twin |
| **Degradation** | Core step |
| **Testing** | Propagation matrix tests |
| **Dependencies** | Step 13, 17 |
| **Deliverables** | Degradation module |

## Step 19 — Substrate completeness projection

| Field | Content |
| ----- | ------- |
| **Objective** | Overview `synthesis` stage metrics |
| **Architectural purpose** | Operator truth in overview |
| **Contracts** | Completeness shape |
| **Runtime** | `synthesis_completeness_projection.py` |
| **Persistence** | Read artifacts + epochs |
| **Admin** | Overview integration |
| **Replay** | N/A |
| **Degradation** | health_state |
| **Testing** | Projection unit tests |
| **Dependencies** | Step 14 |
| **Deliverables** | Completeness module |

## Step 20 — Artifact lineage retrieval substrate

| Field | Content |
| ----- | ------- |
| **Objective** | Query artifacts by lookup id / epoch |
| **Architectural purpose** | Phase **09** read path prep |
| **Contracts** | List/get APIs |
| **Runtime** | `synthesis_artifact_query.py` |
| **Persistence** | Indexes on tenant+lookup+epoch |
| **Admin** | Artifact list filters |
| **Replay** | N/A |
| **Degradation** | N/A |
| **Testing** | API tests |
| **Dependencies** | Step 16 |
| **Deliverables** | Query helpers |

## Step 21 — Observability + health

| Field | Content |
| ----- | ------- |
| **Objective** | Metrics + health snapshot |
| **Architectural purpose** | SLO monitoring |
| **Contracts** | Metric names |
| **Runtime** | `synthesis_observability.py` |
| **Persistence** | Optional metrics table |
| **Admin** | Health strip data |
| **Replay** | N/A |
| **Degradation** | Alert on critical SD |
| **Testing** | Metric increment tests |
| **Dependencies** | Step 14 |
| **Deliverables** | Observability module |

## Step 22 — Control plane catalog

| Field | Content |
| ----- | ------- |
| **Objective** | Aggregate API |
| **Architectural purpose** | Single operator entry |
| **Contracts** | Control plane schema v1 |
| **Runtime** | `synthesis_control_plane.py` |
| **Persistence** | Reads only |
| **Admin** | GET control-plane |
| **Replay** | N/A |
| **Degradation** | Posture in aggregate |
| **Testing** | Admin HTTP test |
| **Dependencies** | Steps 19–21 |
| **Deliverables** | Control plane endpoint |

## Step 23 — Operator workflows + debuggers

| Field | Content |
| ----- | ------- |
| **Objective** | SPA routes W1–W4 |
| **Architectural purpose** | Terminal step admin slice |
| **Contracts** | UI ↔ API mapping |
| **Runtime** | N/A (frontend) |
| **Admin** | Full debugger surfaces |
| **Replay** | Replay UI |
| **Degradation** | SD explorer UI |
| **Testing** | Admin E2E optional |
| **Dependencies** | Step 22 |
| **Deliverables** | SPA synthesis section |

## Step 24 — Tenant verification + economics

| Field | Content |
| ----- | ------- |
| **Objective** | G-P08-TVER-01 + economics receipt |
| **Architectural purpose** | CI tenant slice |
| **Contracts** | verification block shape |
| **Runtime** | `synthesis_tenant_verification.py`, economics |
| **Persistence** | Proof runs table |
| **Admin** | Verification tab extension |
| **Replay** | Sample twin in slice |
| **Degradation** | Fail verification on critical |
| **Testing** | G-P08-TVER-01 |
| **Dependencies** | Step 17 |
| **Deliverables** | Verification slice |

## Step 25 — Runtime legality matrix enforcement

| Field | Content |
| ----- | ------- |
| **Objective** | PROD-SYN-01 enforcement hooks |
| **Architectural purpose** | Production guardrails |
| **Contracts** | Matrix catalog |
| **Runtime** | `assert_synthesis_production_lawful_v1` |
| **Persistence** | N/A |
| **Admin** | Matrix view |
| **Replay** | N/A |
| **Degradation** | Block publish |
| **Testing** | Matrix tests |
| **Dependencies** | Step 07 |
| **Deliverables** | Enforcement hooks |

## Step 26 — G-P08-* verification harness

| Field | Content |
| ----- | ------- |
| **Objective** | Single harness runner |
| **Architectural purpose** | CI aggregation |
| **Contracts** | Harness receipt |
| **Runtime** | `synthesis_verification_harness.py` |
| **Persistence** | Run ledger |
| **Admin** | Harness API |
| **Replay** | Runs REPLAY gates |
| **Degradation** | N/A |
| **Testing** | Self-test |
| **Dependencies** | Steps 02–25 |
| **Deliverables** | Harness module |

## Step 27 — Golden vectors + policy fixture

| Field | Content |
| ----- | ------- |
| **Objective** | Corpus + `SynthesisPolicyPackV1_Default.json` |
| **Architectural purpose** | Regression anchors |
| **Contracts** | Fixture digest in normative |
| **Runtime** | `synthesis_golden_vectors_v1_root()` |
| **Persistence** | N/A |
| **Admin** | Catalog pointer |
| **Replay** | Golden REPLAY-01 |
| **Degradation** | Golden degraded case |
| **Testing** | Corpus pytest |
| **Dependencies** | Step 17 |
| **Deliverables** | `tests/.../synthesis_golden_vectors/v1/` |

## Step 28 — Evaluation harness

| Field | Content |
| ----- | ------- |
| **Objective** | G-P08-EVAL-01/02 |
| **Architectural purpose** | Quality governance |
| **Contracts** | Evaluation receipt |
| **Runtime** | `synthesis_evaluation.py` |
| **Persistence** | Eval runs |
| **Admin** | Evaluation explorer |
| **Replay** | EVAL-02 non-blocking |
| **Degradation** | N/A |
| **Testing** | Eval tests |
| **Dependencies** | Step 27 |
| **Deliverables** | Eval module |

## Step 29 — Implementation sequencing meta

| Field | Content |
| ----- | ------- |
| **Objective** | `synthesis_implementation_sequencing.py` wave evaluators |
| **Architectural purpose** | G-P08-SEQ-* gates |
| **Contracts** | Wave definitions |
| **Runtime** | Wave status builders |
| **Admin** | Sequencing catalog |
| **Testing** | `test_phase08_step29_implementation_sequencing.py` |
| **Dependencies** | Steps 01–28 docs |
| **Deliverables** | Sequencing module |

## Step 30 — Program closure + G-P08-CLOSE-01

| Field | Content |
| ----- | ------- |
| **Objective** | SYNTHESIS-CERT-PACK-1 + closure UI |
| **Architectural purpose** | Phase sign-off |
| **Contracts** | 10 criteria |
| **Runtime** | `synthesis_certification_pack.py` |
| **Persistence** | `cortex_synthesis_certification_archives` |
| **Admin** | Certification routes |
| **Testing** | CLOSE-01 integration |
| **Dependencies** | Steps 01–29 |
| **Deliverables** | Closure pack (pre-pipeline) |

## Step 31 — Substrate pipeline phase 08

| Field | Content |
| ----- | ------- |
| **Objective** | `PHASE_08_SYNTHESIS` in orchestrator |
| **Architectural purpose** | Automatic synthesis after retrieval |
| **Contracts** | Phase receipt schema |
| **Runtime** | `run_substrate_phase_08_synthesis_v1`, Celery task |
| **Persistence** | phase_runs output receipt |
| **Celery** | Chain after phase 07 |
| **Admin** | Pipeline panel phase 08 |
| **Replay** | Pin index epoch from 07 receipt |
| **Degradation** | SD-PIPELINE-GAP |
| **Testing** | Pipeline integration test |
| **Dependencies** | Step 14, Phase **07** pipeline |
| **Risks** | Celery chord complexity |
| **Deliverables** | `substrate_pipeline` extension |

## Step 32 — Publication barrier

| Field | Content |
| ----- | ------- |
| **Objective** | `publish_synthesis_epoch_v1` |
| **Architectural purpose** | G-P08-REPLAY-02 |
| **Contracts** | Epoch monotonic law |
| **Runtime** | `synthesis_publication.py` |
| **Persistence** | `cortex_synthesis_publication_epochs` |
| **Admin** | Publish status on control plane |
| **Replay** | Epoch in artifact |
| **Degradation** | SD-PUBLISH-BLOCKED |
| **Testing** | Monotonicity tests |
| **Dependencies** | Step 31 |
| **Deliverables** | Publish module |

## Step 33 — Durable store hardening

| Field | Content |
| ----- | ------- |
| **Objective** | Indexes, idempotency, retention |
| **Architectural purpose** | Production scale |
| **Contracts** | Retention policy |
| **Runtime** | Repository layer |
| **Persistence** | Migrations + indexes |
| **Admin** | Retention dangerous action |
| **Replay** | Idempotent jobs |
| **Testing** | Load smoke tests |
| **Dependencies** | Steps 06, 14, 32 |
| **Deliverables** | Repository + migrations |

## Step 34 — E2E operational certification

| Field | Content |
| ----- | ------- |
| **Objective** | Automate scenarios A–D |
| **Architectural purpose** | Prove ingest→intelligence |
| **Contracts** | E2E harness |
| **Runtime** | `synthesis/testing/e2e_*.py` |
| **Persistence** | Uses test DB |
| **Testing** | `tests/.../synthesis/e2e/` |
| **Dependencies** | Step 31–32 |
| **Deliverables** | E2E suite |

## Step 35 — Constitutional freeze sign-off

| Field | Content |
| ----- | ------- |
| **Objective** | P08-FINAL-FREEZE changelog entry |
| **Architectural purpose** | Lock doctrine + implementation parity |
| **Contracts** | Freeze version bump if needed |
| **Runtime** | Normative document match |
| **Admin** | Program freeze banner |
| **Certification** | All 10 criteria |
| **Dependencies** | Steps 01–34 |
| **Deliverables** | `PHASE08_CONSTITUTIONAL_CHANGELOG.md` final + tracker **Frozen** |

---

## Parallel tracks

| Track | After step |
| ----- | ---------- |
| Frontend admin | 22 |
| Golden vectors | 17 |
| Pipeline | 14 (stub), 31 (full) |
| LLM vendor real adapter | 11 (behind flag) |

---

## Phase 09 readiness (post-35)

- [ ] Artifacts queryable by `artifact_id` + `synthesis_publication_epoch`  
- [ ] Phase **09** boundary tests green  
- [ ] Operator certification archived  
