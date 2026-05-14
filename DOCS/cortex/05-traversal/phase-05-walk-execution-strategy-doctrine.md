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

---

## 14. Reference implementation (runtime)

- **Module:** `vector.domains.cortex.traversal.walk_execution_strategy_contract` (re-exported from `vector.domains.cortex.traversal`).
- **Policy hash / strategy:** **RULE WES-01** — ``walk_execution_strategy`` is merged into ``policy_hash`` material via ``walk_policy.walk_policy_merged_for_hash_v1`` / ``compute_policy_hash_v1``; static **G-P05-WES-01** (`verify_gp05_wes01_strategy_affects_policy_hash_static`).
- **Pinned epoch:** **FS-WES-01** — ``validate_fs_wes01_materialized_requires_pinned_index_epoch_v1`` (``pinned_index_epoch`` on anchor or under ``extension``); extension key order **§8** via ``validate_temporal_anchor_extension_sorted_keys_v1``.
- **Hybrid thresholds:** ``validate_hybrid_policy_integer_threshold_for_strategy_v1`` (**WES §3** — ``hybrid_switch_at_index_epoch`` int); wired into ``validate_walk_policy_for_request_v1`` after JSON Schema.
- **Fast-path equivalence:** **RULE WES-02** / **FS-WES-02** — ``validate_fast_path_equivalence_record_v1``; golden **G-P05-EQUIV-01** (`verify_gp05_equiv01_fast_path_online_equivalence_static`).
- **Materialized hop provenance:** ``validate_materialized_adjacency_hop_receipt_v1`` (**§7** — ``via_materialized_adjacency`` ⇒ ``materialized_edge_record_id``).
- **Forbidden optimizations:** **FS-WES-03** — ``list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1`` + static **G-P05-WES-02** (`verify_gp05_wes03_forbidden_optimization_hash_body_scan_static`).
- **Fixtures:** `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/walk_execution_strategy/`.
- **Pytest:** `backend/tests/vector/domains/cortex/traversal/test_phase05_step15_walk_execution_strategy_contract.py`.
