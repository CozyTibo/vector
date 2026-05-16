# Phase 07 — Closure gates & certification pack

**Status:** normative.

---

## **G-P07-CLOSE-01**

Certification pack format: **`RETRIEVAL-CERT-PACK-1`** (gzip tar).

Required root files:

| File | Content |
| ---- | ------- |
| `manifest.json` | format key, freeze version, policy digest |
| `gate_results.json` | all G-P07-* wired results |
| `vectors/manifest.json` | golden vector listing |
| `legality_matrix.json` | R-LEG snapshot |
| `policy_pack.sha256` | pinned policy bytes |

Verification: `verify_retrieval_cert_pack_v1(bytes)` — mirror TCRE-CERT-PACK-1.

---

## Phase completion criteria

| # | Criterion |
| - | --------- |
| 1 | Steps **1–30** doctrine **Frozen** |
| 2 | All **hard_fail** gates wired in CI |
| 3 | Admin surfaces **1–16** shipped |
| 4 | Substrate completeness retrieval stage live |
| 5 | Index publish job durable |
| 6 | G-P07-REPLAY-01 pass on golden tenant slice |
| 7 | R-LEG production predicates satisfied |
| 8 | RETRIEVAL-CERT-PACK-1 generated in CI artifact |
| 9 | No Active P0 in gap matrix |
| 10 | Phase 08 handoff doc signed (boundary tests) |

---

## Admin closure (Step 30)

- Nav tab enabled  
- Overview integration live  
- Dangerous actions policy-gated  
- Operator verification checklist in admin UI  

---

## FF-P07-5 bundle

Program freeze version `1`; constitutional changelog entry; tracker rows marked **Frozen (doctrine)**.
