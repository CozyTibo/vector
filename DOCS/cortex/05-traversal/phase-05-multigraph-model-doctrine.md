# Phase 05 — Multigraph model doctrine

**Normative step:** **6**. **Freeze bundle:** **FF-2**.  
**Depends on:** `phase-05-graph-import-boundary-doctrine.md`, `phase-05-normative-index.md`.

---

## 1. Constitutional intent

Model the traversable surface as a **directed multigraph** with **typed parallel edges** and **deterministic identity** for every edge instance suitable for receipts and replay.

---

## 2. Explicit anti-goals

- Collapsing parallel org links into a single “best” edge.  
- Undirected graph semantics unless `policy.undirected_mode=true` (then **MUST** emit symmetric pair visitation receipts — both directions explicit).  
- Floating-point weights on edges in canonical model.

---

## 3. Formal terminology

| Term | Definition |
| ---- | ---------- |
| **Node** | `org_entity` or `org_primitive` per import; stable `node_id` from export. |
| **Edge instance** | One authoritative org link row → at most one directed edge in default mode. |
| **Neighbor list** | Ordered multiset of **outgoing** `edge_fingerprint` values eligible at anchor. |

---

## 4. Deterministic semantics

**RULE MG-01 — Neighbor ordering:** For each `source_node_id`, sort eligible outgoing edges by:

1. `edge_fingerprint` ascending lexicographic (hex digest of SHA-256).  
2. If fingerprints collide (**ILLEGAL** state FS-MG-01), import **MUST** fail.

**RULE MG-02 — Path multiset canonicalization:** For **unordered diagnostic** views only, multiset of fingerprints sorted ascending; **default walk path** remains **visit order** (sequence order) for `walk_result_hash`.

---

## 5. Replay semantics

Identical import + anchor + policy **MUST** yield identical **neighbor expansion sequence** up to truncation.

---

## 6. Temporal semantics

Edge eligibility **MUST** filter by half-open validity at `t_as_of` **before** neighbor ordering.

---

## 7. Provenance semantics

`edge_fingerprint` **MUST** appear on every hop receipt and bind to `org_link_id`.

---

## 8. Serialization contracts

`edge_fingerprint` string format: `sha256:` + 64 hex lowercase.  
Canonical node id: export string **as-is** after NFC normalization.

---

## 9. Forbidden states

| ID | State |
| -- | ----- |
| **FS-MG-01** | Duplicate `edge_fingerprint` for distinct org links. |
| **FS-MG-02** | Neighbor order depends on DB physical row order. |
| **FS-MG-03** | Silent dedup of parallel edges in observed mode. |

---

## 10. Verification implications

- **G-P05-MG-01:** Golden graph — neighbor order byte-stable.  
- **G-P05-MG-02:** Collision detector on fingerprint set.

---

## 11. Abuse scenarios

| Abuser | Attack | Defense |
| ------ | ------ | ------- |
| Query optimizer | Hash join reorder changes expansion | Ordering law is total and hash-based, not physical order. |

---

## 12. Negative examples

**ILLEGAL:** “pick newest link by `updated_at`” without pinning that rule in **policy_hash** with explicit **total order** including tie on `org_link_id`.

**LEGAL:** policy pins `tie_break: lex_org_link_id` after fingerprint sort.

---

## 13. CI oracle expectations

Golden traversal tests on **parallel edge** fixtures; failure injection for duplicate fingerprint.
