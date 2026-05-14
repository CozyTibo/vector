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
