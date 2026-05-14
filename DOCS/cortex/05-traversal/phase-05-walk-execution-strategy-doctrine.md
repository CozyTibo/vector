# Phase 05 — Walk execution strategy doctrine

**Normative step:** **15**. **Freeze bundle:** **FF-4**.  
**Depends on:** `phase-05-derived-index-contract-doctrine.md`, `phase-05-observed-vs-derived-doctrine.md`, `phase-05-hop-receipt-doctrine.md`, `phase-05-walk-result-contract.md`.

---

## 1. Constitutional intent

Pin when the engine may use **online expansion** vs **materialized structures**, and impose **fast-path equivalence obligations** so optimizations cannot change hashed outcomes when policy declares equivalence.

---

## 2. Explicit anti-goals

- Silent switch between online and derived.  
- Fast path that skips receipt fields.  
- Different hop counts between equivalent strategies for same policy (unless policy explicitly allows compression — **default forbidden**).

---

## 3. Formal terminology

| Strategy | Meaning |
| -------- | ------- |
| `ONLINE_OBSERVED` | Expand only from import bundle at anchor. |
| `MATERIALIZED_DERIVED` | Use derived adjacency per epoch. |
| `HYBRID_PINNED` | Starts online until epoch threshold — **MUST** document in policy with explicit thresholds in **integers** only. |

---

## 4. Deterministic semantics

**RULE WES-01:** `walk_execution_strategy` is part of **`walk_policy`** and therefore **`policy_hash`**.  
**RULE WES-02 — Fast-path equivalence obligations:** If `fast_path_allowed=true`, engine **MUST** prove per-tenant **offline equivalence suite** (`EQUIV-*` fixtures) passes: same `walk_result_hash` for golden cases vs online reference implementation.

---

## 5. Replay semantics

Changing strategy without policy version bump **ILLEGAL**.

---

## 6. Temporal semantics

Materialized strategy **MUST** pin `index_epoch` in `temporal_anchor` extension field `pinned_index_epoch` (uint64).

---

## 7. Provenance semantics

Any hop via materialized edge **MUST** mark `provenance_class=derived` and include `materialized_edge_record_id`.

---

## 8. Serialization contracts

`pinned_index_epoch` canonical key ordering inside anchor extension object sorted.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-WES-01** | `MATERIALIZED_DERIVED` without `pinned_index_epoch`. |
| **FS-WES-02** | Hash mismatch between fast path and online on same fixture while `fast_path_allowed=true`. |
| **FS-WES-03** | Forbidden optimization class used (see §11). |

---

## 10. Verification implications

- **G-P05-EQUIV-01:** Golden equivalence harness.  
- **G-P05-EQUIV-02:** CI runs online vs fast for `OCTS_VERIFICATION_MODE=strict` nightly.

---

## 11. Abuse scenarios

| Class | Forbidden optimization |
| ----- | ------------------------ |
| **FO-01** | Skip generating hop receipts when “obvious.” |
| **FO-02** | Merge hops in result for brevity. |
| **FO-03** | Use BFS layer cache without derived labeling. |

---

## 12. Negative examples

**ILLEGAL:** strategy toggles based on `if load > 0.8` without policy field.

---

## 13. CI oracle expectations

Dual-run harness in `phase-05-traversal-equivalence-doctrine.md` referenced from CI job graph.
