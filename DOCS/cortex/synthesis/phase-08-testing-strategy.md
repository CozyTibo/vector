# Phase 08 — Testing strategy

**Status:** normative.

---

## 1) Test layers

| Layer | Scope | Marker |
| ----- | ----- | ------ |
| **Unit** | law modules, replay identity, SD registry, anti-goals | default |
| **Integration** | FSM + DB + retrieval client mock | `@pytest.mark.integration` |
| **Golden** | corpus_manifest cases | integration + golden |
| **E2E** | full pipeline 02–08 | integration + e2e |
| **Admin HTTP** | route contracts | integration |
| **Static CI** | G-P08-ANTI-*, SCHEMA, imports | unit |

---

## 2) Gate catalog (G-P08-*)

| Gate | Type | Module |
| ---- | ---- | ------ |
| G-P08-ANTI-01 | static | anti_goals |
| G-P08-ANTI-02 | static | import boundary |
| G-P08-SCHEMA-01 | schema | job + artifact JSON schema tests |
| G-P08-INGRESS-01 | unit | synthesis_ingress |
| G-P08-REPLAY-01 | integration | synthesis_replay_equivalence |
| G-P08-REPLAY-02 | integration | synthesis_publication |
| G-P08-LEG-01 | unit | synthesis_legality_matrix |
| G-P08-CITE-01 | unit | synthesis_evidence_binding |
| G-P08-SEQ-01..05 | static | implementation waves |
| G-P08-TVER-01 | integration | tenant slice |
| G-P08-EVAL-01 | golden | evaluation harness |
| G-P08-CLOSE-01 | integration | certification pack |

---

## 3) Mocking rules

| Dependency | Mock strategy |
| ---------- | ------------- |
| LLM | `FakeLlmAdapter` returning fixture JSON |
| Retrieval | Recorded Phase **07** responses (vcr-style) |
| Celery | `CELERY_TASK_ALWAYS_EAGER` in integration |
| Pipeline | In-process `run_substrate_pipeline_sync_through_synthesis_v1` harness |

**Rule:** Golden tests MUST NOT call live LLM APIs in CI.

---

## 4) Per-step pytest mapping

Each implementation Step **N** ships `test_phase08_stepNN_*.py` mirroring Phase **07** convention.

---

## 5) Regression discipline

- Any new SD-* code → registry + semantics map + golden case  
- Any new workload → policy pack + schema enum + admin catalog  
- Policy pack change → digest bump + changelog entry  

---

## 6) CI placement

```
backend/tests/vector/domains/cortex/synthesis/
  test_phase08_step01_*.py
  ...
  e2e/
  synthesis_golden_vectors/v1/
```

Required for merge: all G-P08-* hard gates + no Active P0 in gap matrix.
