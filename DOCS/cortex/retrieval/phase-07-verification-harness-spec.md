# Phase 07 — Verification harness (G-P07-*)

**Status:** normative.

---

## Gate catalog (minimum set)

| Gate ID | Severity | Stage | Predicate |
| ------- | -------- | ----- | --------- |
| **G-P07-ANTI-01** | hard_fail | A | No forbidden cognition imports |
| **G-P07-ANTI-02** | hard_fail | A | Ingress token rejection |
| **G-P07-SCHEMA-01** | hard_fail | A | Query envelope schema |
| **G-P07-ADDR-01** | hard_fail | B | Lookup id determinism golden |
| **G-P07-REPLAY-01** | hard_fail | C | Double-run equality |
| **G-P07-REPLAY-02** | hard_fail | C | Index permutation invariance |
| **G-P07-RANK-01** | hard_fail | B | No float scores in policy |
| **G-P07-PROV-01** | hard_fail | B | Provenance envelope required fields |
| **G-P07-DEG-01** | hard_fail | B | RD-* registry closed |
| **G-P07-CP-01** | hard_fail | D | Control plane OpenAPI RBAC |
| **G-P07-ECO-01** | hard_fail | E | Readiness economics receipt |
| **G-P07-TVER-01** | hard_fail | D | Tenant verification slice golden |
| **G-P07-CLOSE-01** | hard_fail | Z | RETRIEVAL-CERT-PACK-1 closure |

---

## CI staging (mirror Phase 05/06)

| Stage | Gates |
| ----- | ----- |
| A | Anti-goals, schema |
| B | Addressing, provenance, ranking, degradation |
| C | Replay |
| D | Control plane, tenant slice |
| E | Economics |
| Z | Certification pack |

---

## Golden vectors

Root: `backend/tests/vector/domains/cortex/retrieval/retrieval_golden_vectors/v1/`

Cases:

- `query/chronology_window_minimal_v1`  
- `query/causal_chain_minimal_v1`  
- `query/replay_equivalence_double_run_v1`  
- `index/publish_barrier_v1`  
- `tenant_verification/org_graph_retrieval_slice_good_v1.json`  

---

## Tenant verification slice

`build_org_graph_retrieval_verification_slice_v1`:

- `walk_index_depth`  
- `tcre_index_depth`  
- `index_epoch`  
- `retrieval_program_freeze_version`  
- `retrieval_slice_hash`  

Env: `VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE=1`

---

## PR blocking bundle

`run_retrieval_gp07_pr_blocking_static_stages_v1()` — stages A+B+C gates only.
