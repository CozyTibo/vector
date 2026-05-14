# Phase 05 — Derived index contract doctrine

**Normative step:** **13**. **Freeze bundle:** **FF-4**.  
**Depends on:** `phase-05-observed-vs-derived-doctrine.md`, `phase-05-multigraph-model-doctrine.md`, `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Specify **materialized traversal structures** so they are **replay-regenerable**, **epoch-versioned**, and **never silently authoritative**.

---

## 2. Explicit anti-goals

- Serving derived adjacency without `index_epoch`.  
- Using stale derived index in **observed-only** walk without explicit policy allowing stale read (default **disallow**).  
- Optimizing away **read barriers** between index build completion and publish.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **index_epoch** | `uint64` monotonic per **index_partition_key** (default: tenant_id). Incremented on **successful committed** replay per `phase-05-index-replay-doctrine.md`. |
| **Derived artifact** | Any row/blob representing adjacency, reachability, rank-ignored summaries **without** narrative. |
| **Publish barrier** | Atomic flip: `BUILDING → PUBLISHED` with `(index_content_hash, index_epoch)` visible together. |

---

## 4. Deterministic semantics

**RULE DI-01:** `index_content_hash` **MUST** hash canonical serialized **entire** derived structure for partition (algorithm in index replay doctrine).  
**RULE DI-02:** **Stale index serving rules:** If `served_index_epoch < latest_committed_index_epoch`, reads **MUST** attach `stale_index_warning=true` to API response **outside** walk hash or inside **non-hashed** envelope per API contract — default strict mode **MUST** reject observed walks.

---

## 5. Replay semantics

Regenerating derived index from pinned import **MUST** reproduce `index_content_hash` or fail **G-P05-IDX-01**.

---

## 6. Temporal semantics

Derived structures **MUST** record `materialized_for_anchor` (same shape as temporal_anchor subset) or explicitly `materialized_for_index_epoch`.

---

## 7. Provenance semantics

Every edge row in derived store **MUST** include `source_observed_edge_fingerprints[]` (non-empty) proving derivation lineage.

---

## 8. Serialization contracts

Canonical adjacency list format: `{"nodes": [...], "adj": {...}}` with sorted keys — details in index replay doctrine; this contract defines **required metadata fields** only.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-DI-01** | Derived edge without lineage fingerprints. |
| **FS-DI-02** | Partial build visible as PUBLISHED. |
| **FS-DI-03** | `index_epoch` regression. |

---

## 10. Verification implications

- **G-P05-IDX-01:** Index hash stability.  
- **G-P05-IDX-02:** Lineage completeness scan.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Phase 07 | Cache semantic embeddings in index | Schema forbids non-structural payloads; import scan. |

---

## 12. Negative examples

**ILLEGAL:** adjacency row `{ "from": "A", "to": "B" }` without `lineage`.  
**LEGAL:** includes `source_observed_edge_fingerprints: ["sha256:…"]`.

---

## 13. CI oracle expectations

Rebuild-from-empty + compare hash; partial build injection must not publish.

---

## 14. Reference implementation (runtime)

- **Module:** `vector.domains.cortex.traversal.derived_index_contract` (re-exported from `vector.domains.cortex.traversal`).
- **Hashing:** `compute_index_content_hash_v1` / `canonical_derived_index_artifact_json_bytes_v1` implement **RULE DI-01** with preamble **`DERIVED_INDEX_CANON_VERSION`** (per index replay doctrine §8).
- **Lineage:** `list_fs_di01_derived_edge_lineage_violations` (**FS-DI-01**); full-artifact validation via `validate_derived_index_artifact_contract_v1` (temporal anchor law on `materialized_for_anchor` when present).
- **Epoch monotonicity:** `list_fs_di03_index_epoch_regression_violations` (**FS-DI-03**).
- **Publish barrier:** `validate_publish_barrier_record_v1` (**FS-DI-02** slice — no partial publish).
- **Stale reads:** `validate_stale_derived_read_policy_v1` (**RULE DI-02** — strict `ONLINE_OBSERVED` default).
- **Static gates:** **G-P05-IDX-01** (`verify_gp05_idx01_index_content_hash_stability_static`), **G-P05-IDX-02** (`verify_gp05_idx02_lineage_completeness_static`).
- **Fixtures:** `backend/tests/vector/domains/cortex/traversal/octs_golden_vectors/v1/derived_index/`.
- **Pytest:** `backend/tests/vector/domains/cortex/traversal/test_phase05_step13_derived_index_contract.py`.
