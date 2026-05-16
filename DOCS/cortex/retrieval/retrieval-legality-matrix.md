# Phase 07 — Retrieval legality matrix

**Status:** normative (draft **Frozen** target at **FF‑P07‑4**).

---

## Query-level legality classes

| Class | Ordinal | Authoritative for Phase 08? |
| ----- | ------- | --------------------------- |
| `retrieval_replay_safe` | 0 | **Yes** |
| `retrieval_degraded` | 1 | **Yes** (with degradation visible) |
| `retrieval_partial` | 2 | **Yes** (audit intent only) |
| `retrieval_unverifiable` | 3 | **No** |
| `retrieval_forbidden` | 4 | **No** |

---

## Predicate table (R-LEG-01..07)

| ID | Predicate | Failure class |
| -- | --------- | ------------- |
| **R-LEG-01** | Anti-goals scan pass | `retrieval_forbidden` |
| **R-LEG-02** | Addressing resolves ≥1 target OR audit intent | `retrieval_partial` min |
| **R-LEG-03** | `tcre_policy_bundle_digest` pinned when TCRE scope | `retrieval_unverifiable` |
| **R-LEG-04** | `octs_engine_build_ref` available when walk scope | `retrieval_unverifiable` |
| **R-LEG-05** | Index epoch ≥ min required | `retrieval_degraded` |
| **R-LEG-06** | No upstream `replay_conflicted_identity` in scope | `retrieval_unverifiable` |
| **R-LEG-07** | G-P07-REPLAY-01 holds on verification slice | `retrieval_degraded` |

---

## Deployment forbidden rows

| Deployment | Reason |
| ---------- | ------ |
| Authoritative retrieval without index publish | R-LEG-05 |
| Production retrieval with `OCTS_DEV_ENGINE_ID` only | R-LEG-04 |
| Retrieval over exploration partition labeled authoritative | RET-ANTI-01 |

---

## Evidence-level floor

Hit with `evidence_unverifiable` forces query floor `retrieval_unverifiable` unless intent=`audit`.

---

## Matrix API

`GET .../cortex/retrieval/legality` returns:

- `retrieval_policy_digest`  
- `legality_classes[]`  
- `predicates[]` with descriptions  
- `forbidden_deployments[]`
