# Phase 07 — Retrieval runtime legality matrix

**Status:** normative.

---

## Production certification predicates

| ID | Name | Check |
| -- | ---- | ----- |
| **R-LEG-01** | Anti-goals enforced | G-P07-ANTI-01 pass |
| **R-LEG-02** | Addressing law wired | no silent empty 200 |
| **R-LEG-03** | TCRE pins required | digest in envelope |
| **R-LEG-04** | OCTS identity | engine_build_ref or stub policy |
| **R-LEG-05** | Index published | epoch > 0 for tenants with TCRE jobs |
| **R-LEG-06** | Identity replay safe | no conflict in scope |
| **R-LEG-07** | Replay double-run | tenant slice pass |

---

## Forbidden deployments

| ID | Condition |
| -- | --------- |
| **R-FORB-01** | Authoritative queries without `retrieval_policy_digest` pin |
| **R-FORB-02** | Index read before first successful publish job |
| **R-FORB-03** | Exploration partition feeding Phase 08 default path |
| **R-FORB-04** | Embedding / vector index table present |
| **R-FORB-05** | NL query box in admin |

---

## Runtime catalog API

`build_retrieval_runtime_legality_matrix_catalog_v1()` → sorted predicates + forbidden rows (mirror Phase 06).

Admin: `GET .../cortex/retrieval/runtime-legality-matrix`.

---

## Ship gates

| Milestone | Requirement |
| --------- | ------------- |
| Dev | R-LEG-01..02 |
| Staging | + R-LEG-03..05 |
| Production | all R-LEG + R-FORB + G-P07-CLOSE-01 |
