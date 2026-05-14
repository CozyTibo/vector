# Phase 05 — Runtime legality matrix

**Status:** normative — **when OCTS runtime is allowed**, **what deployments are forbidden**, and **CI prerequisites**.  
**Pairs with:** `phase-05-normative-index.md` (**FF-***), `phase-05-ci-enforcement-architecture.md`, `phase-05-certification-pack-format.md`.

---

## 1. Dimensions (not interchangeable)

| Dimension | Meaning |
| --------- | ------- |
| **Doctrine closed** | No **P0** / **P1** rows in `phase-05-spec-gap-matrix.md` affecting that slice. |
| **CI-enforced** | Required **`G-P05-***` gates for that slice are **`hard_fail`** on merge pipeline. |
| **Runtime legal** | Process may set **`OCTS_RUNTIME_ADMITTED=true`** per §3. |
| **Implemented** | Code + migrations exist in `vector.domains.cortex.traversal` (exact package path in pack manifest). |

**INVARIANT RL-01:** **Doctrine closed** does **not** imply **Runtime legal**.

---

## 2. Freeze bundle prerequisites (normative)

| Bundle | Doctrine rows | CI stages (minimum) | Runtime legal for |
| ------ | -------------- | -------------------- | ----------------- |
| **FF-0** | Steps **1–2** closed | A | Nothing persistent |
| **FF-1** | **1–5** | A | Nothing persistent |
| **FF-2** | **1–8** | A, B | Nothing persistent |
| **FF-3** | **1–12** | A, B, C | Ephemeral in-memory walks in **dev** only |
| **FF-4** | **1–15** | A, B, C, D | **Dev + staging** persistence **walk tables only** |
| **FF-5** | **1–26** | A–D + **Z** on tag | **Production** persistence + admin surfaces |

---

## 3. Runtime legality predicates

**`OCTS_RUNTIME_ADMITTED=true` MAY be set** iff **all** hold:

1. **FF** level for the touched subsystem (§2) is satisfied.  
2. **`OCTS_SCHEMA_BUNDLE_HASH`** env matches manifest in active certification pack **or** dev override file `backend/.../octs_dev_manifest.json` (dev only, **FORBIDDEN** in prod).  
3. **`OCTS_VERIFICATION_MODE`** ∈ {`standard`, `strict`} — prod **MUST** use `standard` unless incident response temporarily sets `strict` (max 6h, audited).  
4. No row in **`phase-05-spec-gap-matrix.md`** §**Active P0** (must be empty section).

---

## 4. Forbidden deployment states

| ID | Deployment | Reason |
| -- | ---------- | ------ |
| **FD-01** | Multi-primary writer on **`cortex_walk_*`** / **`cortex_octs_index_*`** without **linearizable leader** documented in ops runbook | Unsupported consistency |
| **FD-02** | Read replicas serving **observed** walks **without** `read_follows_leader_commit=true` | Stale export hazard |
| **FD-03** | Shared Redis cache between **prod** and **staging** for walk results | Cache contamination |
| **FD-04** | `OCTS_RUNTIME_ADMITTED=true` in prod with non-empty **Active P0** | Constitutional violation |
| **FD-05** | Exploration queue consumers writing to **authoritative** DB role | Partition breach |

---

## 5. Unsupported models (explicit)

| Model | Status |
| ----- | ------ |
| CRDT merge of derived indexes without leader | **UNSUPPORTED** |
| Cross-region async primary for OCTS tables | **UNSUPPORTED** v1 |
| Exactly-once Celery delivery | **UNSUPPORTED**; at-least-once + idempotency only |
| Single walk split across workers without coordinator | **FORBIDDEN** |

---

## 6. Replay safety matrix (runtime)

| Scenario | Legal? | Preconditions |
| -------- | ------ | --------------- |
| Replay with missing edge in export | **No** (authoritative) | `dangling_evidence` |
| Replay exploration `best_effort` | **Yes** | `exploration_mode=true` + partition |
| Replay under **cancel** | **Yes** | §7 |
| Replay under **stale index** | **Yes** only if policy `allow_stale_derived_read=true` | logged + non_authoritative flag |
| Replay under **superseded** edge | **No** | export must exclude |

---

## 7. Cancellation and partial receipts (**closed**)

**RULE CAN-01:** On cooperative **`cancel_requested`**, engine **MUST** stop expansion **before** next hop enqueue; **MUST** emit `termination_reason=cancelled`.  
**RULE CAN-02:** **`walk_result_hash`** **MUST** include **only** hops that completed **`emit_receipt_before_expand=true`** path (default). Partial tail **MUST NOT** appear in `hash_body`.  
**RULE CAN-03:** Telemetry **MAY** list `partial_frontier` outside `hash_body`.

---

## 8. Stale / missing derived store

**RULE MISS-01:** If `MATERIALIZED_DERIVED` requested and `pinned_index_epoch` row missing → **`409`** `index_epoch_unavailable`.  
**RULE MISS-02:** If `allow_stale_derived_read=false` and epoch stale → **`409`** `stale_index`.

---

## 9. CI prerequisite table

| Gate cluster | PR merge | Deploy staging | Deploy prod |
| ------------ | -------- | -------------- | ----------- |
| A+B | ✓ | ✓ | ✓ |
| C | ✓ (OCTS paths) | ✓ | ✓ |
| D | ✓ | ✓ | ✓ |
| E | — | optional | **required** weekly min |
| Z + pack | — | optional | **required** per release tag |

---

## 10. Verification implications

`G-P05-LEGAL-01`: CI job asserts **Active P0** section empty before STAGE-Z.

---

## 11. Abuse scenarios

Downstream service sets `OCTS_RUNTIME_ADMITTED=true` in prod without pack hash → **FD-04**; admission controller **MUST** kill process (out of band spec: k8s hook).

---

## 12. Negative examples

**ILLEGAL:** feature flag enables walk persistence when STAGE-C last failed on `main`.

---

## 13. Versioning

Bump **`OCTS-LEGAL-1`** when forbidden table changes; record in gap matrix amendments.
