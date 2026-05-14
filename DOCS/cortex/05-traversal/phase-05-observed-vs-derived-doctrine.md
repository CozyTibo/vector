# Phase 05 — Observed vs derived traversal doctrine

**Normative step:** **2**. **Freeze bundle:** **FF-0**.  
**Depends on:** `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Guarantee **two disjoint provenance classes** for every hop and every materialized structure: **observed** (ledger-backed, import-visible) vs **derived** (replay-regenerable convenience). **MUST** prevent silent promotion of derived data to organizational truth.

---

## 2. Explicit anti-goals

- **MUST NOT** label a hop **observed** if any neighbor expansion used **precomputed reachability** not verified against authoritative edges at the anchor.  
- **MUST NOT** treat **derived** paths as merge or identity evidence.  
- **MUST NOT** hide derived provenance inside “engine internals” without surfacing in receipts.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Observed traversal** | Walk where **every hop** has `provenance_class=observed` per hop receipt schema. |
| **Derived traversal** | Any walk containing ≥1 hop with `provenance_class=derived`. |
| **Materialized shortcut** | Adjacency list, level index, transitive closure chunk, compressed graph — all **derived**. |
| **Authority surface** | Set of org links + nodes exportable per Phase 04 at **`projection_content_hash`**. |

---

## 4. Deterministic semantics

**RULE OVD-01:** `provenance_class` is **REQUIRED** on every **hop_receipt**.  
**RULE OVD-02:** If `walk_execution_strategy` uses a materialized structure, the walk result **MUST** set `execution_path_contains_derived=true` (boolean, canonical field).  
**RULE OVD-03:** Default for operator-critical paths is **`observed_only=true`** unless caller explicitly opts into derived (see exploration doctrine for additional isolation).

---

## 5. Replay semantics

**REPLAY REQUIREMENT OVD-01:** Replaying a walk with identical **`temporal_anchor`**, **`policy_hash`**, start vertices, and **authority surface** **MUST** yield identical **`walk_result_hash`** for **observed-only** walks.  
**REPLAY REQUIREMENT OVD-02:** Derived-inclusive walks **MUST** additionally pin **`index_epoch`** (if any derived structure touched) per index replay doctrine.

---

## 6. Temporal semantics

Observed hops **MUST** evaluate org link **validity intervals** at **`t_as_of`** only — no predictive extension. Derived structures **MUST** record **`materialized_as_of_epoch`** compatible with `index_epoch` law.

---

## 7. Provenance semantics

Each **hop_receipt** **MUST** include:

- `provenance_class`: `"observed"` | `"derived"`  
- `authority_binding`: nullable only when `provenance_class=derived` **and** `derivation_rule_id` present  
- `derivation_rule_id`: required for derived — stable id/version of algorithm (e.g. `DERIVED_ADJ_v3`)

---

## 8. Serialization contracts

Canonical ordering of hop receipts: **ascending `hop_sequence` (0-based integer)**. **MUST NOT** reorder for hashing.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-OVD-01** | `provenance_class=observed` while `authority_binding` is null. |
| **FS-OVD-02** | Derived neighbor expansion without bumping `execution_path_contains_derived`. |
| **FS-OVD-03** | Writing derived walk results into certification archives without `exploration` or `derived_audit` tag. |

---

## 10. Verification implications

- **G-P05-OVD-01:** Receipt audit — observed hops have valid `authority_binding`.  
- **G-P05-OVD-02:** Strategy law — if strategy touches index, epoch pinned.

---

## 11. Abuse scenarios

| Downstream | Abuse | Defense |
| ---------- | ----- | ------- |
| Phase 06 | Treat derived reachability as causal evidence | Receipt class + walk flag force explicit handling. |
| Optimizer | Cache BFS layers | Allowed only with derived labeling + epoch pin. |

---

## 12. Negative examples

**ILLEGAL:** hop receipt:

```json
{ "hop_sequence": 0, "provenance_class": "observed", "authority_binding": null }
```

**LEGAL:**

```json
{
  "hop_sequence": 0,
  "provenance_class": "observed",
  "authority_binding": { "org_link_id": "…", "edge_fingerprint": "sha256:…" }
}
```

---

## 13. CI oracle expectations

- Property tests: observed-only walk stable hash across JVM/Python reorderings.  
- Mutation tests: flipping `provenance_class` without binding **must** fail gate.
