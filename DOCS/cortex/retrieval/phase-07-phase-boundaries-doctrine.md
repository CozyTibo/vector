# Phase 07 — Phase boundaries (06 / 08 / 09)

**Status:** normative.

---

## Phase 07 OWNS

| Concern | Deliverable |
| ------- | ----------- |
| Query contracts | Workload classes, envelopes, legality, replay identity |
| Addressing | `retrieval_lookup_id`, window/chain/walk refs |
| Evidence access | Deterministic fetch + bounded selection |
| Provenance surfacing | Per-hit envelopes tying to raw/canonical/graph/TCRE/OCTS |
| Temporal scopes | `as_of`, chronology windows, replay epochs |
| Index law | Materialized lookup rows (structural keys only) |
| Operator visibility | Retrieval debuggers, audit trail, health |
| Substrate completeness | Retrieval stage in overview pipeline |

---

## Phase 07 DOES NOT OWN

| Concern | Owner phase |
| ------- | ----------- |
| Temporal–causal reconstruction jobs | **Phase 06** TCRE |
| Bounded graph walks | **Phase 05** OCTS |
| Org link authority / merge | **Phase 04** Identity |
| Canonical transform | **Phase 03** |
| Raw exhaust ingest | **Phase 01–02** |
| **Synthesis** (summaries, narratives, answers) | **Phase 08** |
| **Operational products** (incident workflows, HITL products) | **Phase 09** |
| Cross-phase admin shell / RBAC | **Phase 10** (unifies nav; Phase 07 ships Retrieval slice) |

---

## Boundary with Phase 06 (TCRE)

| Rule | Text |
| ---- | ---- |
| **RET‑BND‑06‑01** | Phase 07 MAY read TCRE artifacts (jobs, chronology receipts, causal edges, chains) **as stored**; MUST NOT re-run reducers except via explicit **replay query class** that invokes pinned replay jobs. |
| **RET‑BND‑06‑02** | `chronology_legality_class` and `causal_legality_class` on hits MUST be **copied from upstream receipts**, not re-projected with different policy unless query declares **`policy_override_exploration`** (exploration partition only). |
| **RET‑BND‑06‑03** | TCRE `reconstruction_coverage_gap` MUST surface as retrieval **`RD-TCRE-GAP`** omissions — never as empty success. |

**Handoff artifact:** Phase 06 RUNTIME‑02 emits `retrieval_lookup_id`, `retrieval_chain_ref`, `chronology_window_ref` — Phase 07 index MUST index these keys.

---

## Boundary with Phase 08 (Synthesis)

| Rule | Text |
| ---- | ---- |
| **RET‑BND‑08‑01** | Phase 08 MUST consume **`RetrievalEvidenceHitV1[]`** + query receipt; MUST NOT bypass Phase 07 for “quick fetch.” |
| **RET‑BND‑08‑02** | Phase 07 MUST NOT return synthesis-shaped fields (`answer`, `summary`, `bullets`, `recommendation`). |
| **RET‑BND‑08‑03** | Exploration-partition retrieval responses MUST be labeled **`non_authoritative: true`** and blocked at Phase 08 ingress unless operator explicitly escalates (Phase 09 governance). |

---

## Boundary with Phase 09 (Operational Intelligence)

| Rule | Text |
| ---- | ---- |
| **RET‑BND‑09‑01** | Phase 09 workflows orchestrate **calls** to Phase 07/08; Phase 07 does not encode product UX. |
| **RET‑BND‑09‑02** | Human-in-the-loop approvals live in Phase 09; Phase 07 provides **audit trail** + replay identity only. |

---

## Dependency direction (acyclic)

```text
01–04 substrate → 05 OCTS → 06 TCRE → 07 Retrieval → 08 Synthesis → 09 Products
```

No backward dependency: TCRE MUST NOT call retrieval for reconstruction logic.
